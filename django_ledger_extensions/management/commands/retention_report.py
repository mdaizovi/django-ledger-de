import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.retention_report import build_retention_report


class Command(BaseCommand):
    help = (
        'Summarise GoBD retention: supporting documents within retention vs eligible for archival review, '
        'and latest backup verification log. Does not delete Belege.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--entity', help='Optional entity slug (default: all Belege in database)')
        parser.add_argument('--json', action='store_true', help='Print JSON instead of plain text')
        parser.add_argument(
            '--reference-date',
            help='ISO date (YYYY-MM-DD) for retention comparison (default: today)',
        )

    def handle(self, *args, **options):
        entity = None
        if options.get('entity'):
            try:
                entity = EntityModel.objects.get(slug=options['entity'])
            except EntityModel.DoesNotExist as exc:
                raise CommandError(f'Entity not found: {options["entity"]}') from exc

        reference = None
        if options.get('reference_date'):
            try:
                reference = date.fromisoformat(options['reference_date'])
            except ValueError as exc:
                raise CommandError('--reference-date must be YYYY-MM-DD') from exc

        report = build_retention_report(entity=entity, reference=reference)

        if options['json']:
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False))
            return

        sd = report['supporting_documents']
        self.stdout.write(f'Retention report — reference {report["reference_date"]}')
        if report['entity_slug']:
            self.stdout.write(f'Entity: {report["entity_slug"]}')
        self.stdout.write('')
        self.stdout.write(f'  Supporting documents within retention: {sd["within_retention"]}')
        self.stdout.write(f'  Eligible for archival review (retain_until passed): {sd["eligible_for_archival_review"]}')
        if sd['retain_until_unset']:
            self.stdout.write(f'  retain_until not set (run migrate / re-save): {sd["retain_until_unset"]}')
        self.stdout.write(f'  Total: {sd["total"]}')
        self.stdout.write('')
        backup = report['latest_backup_verification']
        if backup:
            self.stdout.write(
                f'  Latest backup verification: {backup["verified_at"]} @ {backup["storage_location"]} '
                f'(restore tested: {"yes" if backup["restore_tested"] else "no"})'
            )
        else:
            self.stdout.write('  No backup verification log — record one in admin or log_backup_verification.')
