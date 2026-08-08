from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel
from django_ledger_countries.de import vat as vat_module
from django_ledger_countries.de.coa import skr03
from django_ledger_countries.de.coa.datev_loader import clear_datev_coa_cache, get_skr03_edition_label
from django_ledger_countries.de.coa.starter import get_starter_account_codes
from django_ledger_countries.de.coa.sync import format_merge_report, merge_skr03_chart, record_skr03_edition


class Command(BaseCommand):
    help = (
        'Load or refresh SKR03 accounts from the configured DATEV CSV for an entity. '
        'Use --merge when applying a new annual Branchenpaket export.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument(
            '--merge',
            action='store_true',
            help=(
                'Merge CSV into an existing chart: add new codes, update names, '
                'retire removed codes (active=False). Required for annual DATEV updates.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='With --merge, show the merge diff without saving changes.',
        )
        parser.add_argument(
            '--no-retire-missing',
            action='store_true',
            help='With --merge, do not deactivate accounts absent from the CSV.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Initial load only: insert accounts even when the chart already has non-root accounts.',
        )
        parser.add_argument(
            '--activate-all',
            action='store_true',
            help='Activate every imported account (default: starter set only).',
        )
        parser.add_argument(
            '--deactivate-all',
            action='store_true',
            help='Deactivate every non-root account after import.',
        )

    def handle(self, *args, **options):
        clear_datev_coa_cache()
        skr03.clear_datev_coa_cache()

        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        csv_path = skr03.resolve_csv_path()
        if not csv_path.exists():
            raise CommandError(f'SKR03 CSV not found: {csv_path}')

        coa = entity.default_coa
        if coa is None:
            coa = entity.create_chart_of_accounts(assign_as_default=True, commit=True)

        has_accounts = coa.accountmodel_set.not_coa_root().exists()
        edition = get_skr03_edition_label(csv_path)

        if options['merge']:
            if not has_accounts:
                raise CommandError(
                    'Chart has no accounts yet — run without --merge for the initial SKR03 load.'
                )
            result = merge_skr03_chart(
                entity,
                coa,
                csv_path=csv_path,
                dry_run=options['dry_run'],
                retire_missing=not options['no_retire_missing'],
            )
            self.stdout.write(format_merge_report(result))
            if options['dry_run']:
                return
            active_count = self._apply_activation(entity, coa, options)
            self._print_summary(entity, coa, edition, active_count, mode='merge')
            return

        if has_accounts:
            self.stdout.write(
                self.style.WARNING(
                    'Chart already has accounts. For a new DATEV Branchenpaket export '
                    '(e.g. 2027), run with --merge (and --dry-run first to preview). '
                    'Re-applying starter activation only.'
                )
            )
            active_count = self._apply_activation(entity, coa, options)
            self._print_summary(entity, coa, edition, active_count, mode='refresh')
            return

        self.stdout.write(f'Loading SKR03 from {csv_path}')
        entity.populate_default_coa(
            activate_accounts=False,
            force=options['force'],
            coa_model=coa,
        )
        record_skr03_edition(entity, csv_path)

        active_count = self._apply_activation(entity, coa, options)
        self._print_summary(entity, coa, edition, active_count, mode='initial')

    def _apply_activation(self, entity, coa, options) -> int:
        if options['deactivate_all']:
            coa.accountmodel_set.not_coa_root().update(active=False)
            return 0
        if options['activate_all']:
            return coa.accountmodel_set.not_coa_root().update(active=True)
        return vat_module.apply_regime_starter_activation(coa)

    def _print_summary(self, entity, coa, edition, active_count, *, mode: str) -> None:
        total = coa.accountmodel_set.not_coa_root().count()
        try:
            regime = entity.tax_profile.tax_regime
        except Exception:
            regime = vat_module.get_default_tax_profile_values()['tax_regime']
        starter = len(get_starter_account_codes())
        meta = entity.meta or {}
        synced_at = meta.get('skr03_synced_at', 'n/a')
        self.stdout.write(
            self.style.SUCCESS(
                f'SKR03 {mode} complete on {entity.slug}: edition={edition}, '
                f'{total} accounts on chart, {active_count} active '
                f'(tax regime: {regime}, full starter: {starter}, synced_at: {synced_at}).'
            )
        )
