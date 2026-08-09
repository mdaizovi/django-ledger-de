from pathlib import Path

from django.test import SimpleTestCase, TestCase, override_settings

from django_ledger.io import roles
from django_ledger.io.roles import CREDIT, DEBIT
from django_ledger.models.accounts import AccountModel
from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_countries.de.coa.datev_loader import (
    csv_path_for_year,
    get_skr03_edition_label,
    resolve_csv_path,
)
from django_ledger_countries.de.coa.sync import format_merge_report, merge_skr03_chart


class Skr03CsvPathTests(SimpleTestCase):

    def test_edition_label_from_filename(self):
        path = Path('/tmp/2027_Schulen_freie_Träger.csv')
        self.assertEqual(get_skr03_edition_label(path), '2027_Schulen_freie_Träger')

    @override_settings(
        DJANGO_LEDGER_DE_SKR03_CSV=None,
        DJANGO_LEDGER_DE_SKR03_YEAR=2026,
    )
    def test_resolve_csv_path_by_year(self):
        path = resolve_csv_path()
        self.assertEqual(path.name, '2026_Schulen_freie_Träger.csv')
        self.assertTrue(path.exists())

    def test_csv_path_for_year_helper(self):
        path = csv_path_for_year(2026)
        self.assertEqual(path.name, '2026_Schulen_freie_Träger.csv')


class Skr03MergeTests(DjangoLedgerBaseTest):

    @override_settings(DJANGO_LEDGER_COUNTRY='us')
    def test_merge_adds_updates_and_retires(self):
        entity = self.get_random_entity_model()
        coa = entity.default_coa
        coa.accountmodel_set.not_coa_root().update(active=False)
        root_qs = coa.get_coa_root_accounts_qs()
        bank = AccountModel(
            code='1200 00',
            name='Old Bank Name',
            role=roles.ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            coa_model=coa,
        )
        bank.clean()
        coa.insert_account(bank, root_account_qs=root_qs)

        legacy = AccountModel(
            code='6999 99',
            name='Retired legacy account',
            role=roles.EXPENSE_OTHER,
            balance_type=DEBIT,
            active=True,
            coa_model=coa,
        )
        legacy.clean()
        coa.insert_account(legacy, root_account_qs=root_qs)

        rows = [
            {
                'code': '1200 00',
                'name': 'Bank',
                'role': roles.ASSET_CA_CASH,
                'balance_type': DEBIT,
                'active': False,
                'name_en': 'Bank',
            },
            {
                'code': '4000 00',
                'name': 'Course Revenue',
                'role': roles.INCOME_OPERATIONAL,
                'balance_type': CREDIT,
                'active': True,
                'name_en': 'Course revenue',
            },
        ]

        result = merge_skr03_chart(
            entity,
            coa,
            csv_path=Path('unused.csv'),
            rows=rows,
            retire_missing=True,
        )

        self.assertEqual(result.added, 1)
        self.assertEqual(result.updated, 1)
        self.assertEqual(result.retired, 1)
        self.assertIn('retired', format_merge_report(result))

        bank.refresh_from_db()
        legacy.refresh_from_db()
        new_revenue = coa.accountmodel_set.get(code='4000 00')

        self.assertEqual(bank.name, 'Bank')
        self.assertTrue(bank.active)
        self.assertFalse(legacy.active)
        self.assertTrue(new_revenue.active)

        entity.refresh_from_db()
        self.assertEqual(entity.meta.get('skr03_edition'), 'unused')

    @override_settings(DJANGO_LEDGER_COUNTRY='us')
    def test_merge_dry_run_does_not_persist(self):
        entity = self.get_random_entity_model()
        coa = entity.default_coa
        rows = [
            {
                'code': '1200 00',
                'name': 'Bank',
                'role': roles.ASSET_CA_CASH,
                'balance_type': DEBIT,
                'active': True,
            }
        ]

        before = coa.accountmodel_set.not_coa_root().count()
        result = merge_skr03_chart(
            entity,
            coa,
            csv_path=Path('preview.csv'),
            rows=rows,
            dry_run=True,
        )

        self.assertTrue(result.dry_run)
        self.assertEqual(result.added, 1)
        self.assertEqual(coa.accountmodel_set.not_coa_root().count(), before)
        entity.refresh_from_db()
        self.assertNotIn('skr03_edition', entity.meta or {})

    @override_settings(DJANGO_LEDGER_COUNTRY='us')
    def test_merge_updates_role_when_csv_differs(self):
        entity = self.get_random_entity_model()
        coa = entity.default_coa
        root_qs = coa.get_coa_root_accounts_qs()
        prepaid = AccountModel(
            code='2020 00',
            name='Periodenfremde Aufwendungen',
            role=roles.EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
            coa_model=coa,
        )
        prepaid.clean()
        coa.insert_account(prepaid, root_account_qs=root_qs)

        rows = [
            {
                'code': '2020 00',
                'name': 'Periodenfremde Aufwendungen',
                'role': roles.ASSET_CA_PREPAID,
                'balance_type': DEBIT,
                'active': True,
            }
        ]

        result = merge_skr03_chart(
            entity,
            coa,
            csv_path=Path('unused.csv'),
            rows=rows,
            retire_missing=False,
        )

        self.assertEqual(result.updated, 1)
        prepaid.refresh_from_db()
        self.assertEqual(prepaid.role, roles.ASSET_CA_PREPAID)
