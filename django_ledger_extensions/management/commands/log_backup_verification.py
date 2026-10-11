from datetime import date

from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.models import BackupVerificationLog


class Command(BaseCommand):
    help = 'Append a GoBD backup verification log entry (off-site copy / restore test documentation).'

    def add_arguments(self, parser):
        parser.add_argument('--verified-at', required=True, help='Date backup was verified (YYYY-MM-DD)')
        parser.add_argument(
            '--storage-location',
            required=True,
            help='Off-site location or provider description',
        )
        parser.add_argument(
            '--restore-tested',
            action='store_true',
            help='Set if a restore or spot-check was performed',
        )
        parser.add_argument('--entity', help='Optional entity slug (omit for whole-system backup)')
        parser.add_argument('--notes', default='', help='Optional free-text notes')

    def handle(self, *args, **options):
        try:
            verified_at = date.fromisoformat(options['verified_at'])
        except ValueError as exc:
            raise CommandError('--verified-at must be YYYY-MM-DD') from exc

        entity = None
        if options.get('entity'):
            try:
                entity = EntityModel.objects.get(slug=options['entity'])
            except EntityModel.DoesNotExist as exc:
                raise CommandError(f'Entity not found: {options["entity"]}') from exc

        log = BackupVerificationLog.objects.create(
            entity=entity,
            verified_at=verified_at,
            storage_location=options['storage_location'],
            restore_tested=options['restore_tested'],
            notes=options['notes'],
        )
        self.stdout.write(self.style.SUCCESS(f'Backup verification logged: {log.uuid}'))
