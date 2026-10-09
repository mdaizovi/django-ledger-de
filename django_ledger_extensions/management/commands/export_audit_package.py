from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.audit_package_export import write_audit_package


class Command(BaseCommand):
    help = (
        'Export GoBD audit package: chart of accounts, journal, account ledger, '
        'trial balance, financial statements, open items (JSON/CSV + manifest).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--year', type=int, required=True, help='Calendar year')
        parser.add_argument('--month', type=int, help='Optional calendar month (1–12)')
        parser.add_argument(
            '--output-dir',
            default='./audit-export',
            help='Parent directory for the package folder',
        )

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        month = options.get('month')
        if month is not None and not 1 <= month <= 12:
            raise CommandError('--month must be 1–12')

        path = write_audit_package(
            entity,
            options['output_dir'],
            year=options['year'],
            month=month,
        )
        self.stdout.write(self.style.SUCCESS(f'Audit package written to {path}/'))
