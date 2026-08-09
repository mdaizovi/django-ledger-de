from django.core.management.base import BaseCommand, CommandError

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models.entity import EntityModel


class Command(BaseCommand):
    help = (
        'Show which accounts the bill create form can use for cash, prepaid, and payable '
        '(active accounts on the entity default chart with bill roles).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        coa = entity.default_coa
        if coa is None:
            raise CommandError(f'Entity {entity.slug} has no default chart of accounts.')

        bill_qs = coa.accountmodel_set.all().for_bill()
        roles = {
            'cash': (ASSET_CA_CASH, bill_qs.filter(role=ASSET_CA_CASH)),
            'prepaid': (ASSET_CA_PREPAID, bill_qs.filter(role=ASSET_CA_PREPAID)),
            'payable': (LIABILITY_CL_ACC_PAYABLE, bill_qs.filter(role=LIABILITY_CL_ACC_PAYABLE)),
        }

        self.stdout.write(f'Entity: {entity.slug}')
        self.stdout.write(f'Default chart: {coa.name} ({coa.slug})')
        self.stdout.write('')

        for label, (role, qs) in roles.items():
            accounts = list(qs.order_by('code'))
            self.stdout.write(f'{label.upper()} ({role}): {len(accounts)} available')
            for account in accounts:
                self.stdout.write(f'  - {account.code} {account.name}')
            if not accounts:
                inactive_qs = coa.accountmodel_set.filter(role=role, active=False).order_by('code')
                inactive_sample = list(inactive_qs[:5])
                if inactive_sample:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ({inactive_qs.count()} account(s) with role {role} exist but are inactive/locked/unavailable)'
                        )
                    )
                    for account in inactive_sample:
                        locked = ' locked' if account.locked else ''
                        self.stdout.write(f'    inactive: {account.code} {account.name}{locked}')
            self.stdout.write('')

        prepaid_available = roles['prepaid'][1].exists()
        if not prepaid_available:
            self.stdout.write(
                self.style.ERROR(
                    'No prepaid account available for bills. Fix: '
                    'python manage.py sync_skr03 --entity=%s  '
                    '(activates starter set including 2020 00 with Prepaid role).'
                    % entity.slug
                )
            )
