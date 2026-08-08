from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from django_ledger.regional.registry import clear_country_plugin_cache
from django_ledger_extensions.models import EntityTaxProfile
from django_ledger_extensions.tax_profile import (
    build_tax_regime_behavior,
    resolve_invoice_legal_notice,
)
from django_ledger_countries.de.vat.service import default_invoice_legal_notice_for_entity
from django_ledger_countries.settings import clear_settings_cache


class EntityTaxRegimeBehaviorTests(SimpleTestCase):

    def test_exempt_regime_flags(self):
        profile = EntityTaxProfile(tax_regime=EntityTaxProfile.TaxRegime.EXEMPT)
        behavior = build_tax_regime_behavior(profile, invoice_legal_notice='')

        self.assertFalse(behavior.charges_vat)
        self.assertFalse(behavior.requires_vat_quarterly_filing)
        self.assertFalse(behavior.tracks_kleinunternehmer_turnover)

    def test_small_business_regime_flags(self):
        profile = EntityTaxProfile(tax_regime=EntityTaxProfile.TaxRegime.SMALL_BUSINESS)
        behavior = build_tax_regime_behavior(profile, invoice_legal_notice='')

        self.assertFalse(behavior.charges_vat)
        self.assertFalse(behavior.requires_vat_quarterly_filing)
        self.assertTrue(behavior.tracks_kleinunternehmer_turnover)

    def test_standard_regime_flags(self):
        profile = EntityTaxProfile(
            tax_regime=EntityTaxProfile.TaxRegime.STANDARD,
            default_vat_rate=Decimal('0.19'),
            vat_id='DE123456789',
        )
        behavior = build_tax_regime_behavior(profile, invoice_legal_notice='')

        self.assertTrue(behavior.charges_vat)
        self.assertTrue(behavior.requires_vat_quarterly_filing)
        self.assertFalse(behavior.tracks_kleinunternehmer_turnover)


class InvoiceLegalNoticeTests(SimpleTestCase):

    def tearDown(self):
        clear_country_plugin_cache()
        clear_settings_cache()

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    @patch('django_ledger.regional.dispatch.dispatch_get_invoice_legal_notice')
    def test_exempt_default_notice_uses_country_plugin(self, dispatch_notice):
        clear_settings_cache()
        dispatch_notice.return_value = 'Default § 4 UStG notice'
        entity = SimpleNamespace()
        profile = SimpleNamespace(
            show_invoice_legal_notice=True,
            invoice_legal_notice='',
            entity=entity,
        )

        notice = resolve_invoice_legal_notice(profile)

        dispatch_notice.assert_called_once_with(entity)
        self.assertEqual(notice, 'Default § 4 UStG notice')

    def test_custom_notice_override(self):
        profile = SimpleNamespace(
            show_invoice_legal_notice=True,
            invoice_legal_notice='Custom legal text from Steuerberater.',
            entity=SimpleNamespace(),
        )

        notice = resolve_invoice_legal_notice(profile)

        self.assertEqual(notice, 'Custom legal text from Steuerberater.')

    def test_notice_hidden_when_disabled(self):
        profile = SimpleNamespace(
            show_invoice_legal_notice=False,
            invoice_legal_notice='Should not appear',
            entity=SimpleNamespace(),
        )

        notice = resolve_invoice_legal_notice(profile)

        self.assertEqual(notice, '')

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_standard_notice_includes_vat_id(self):
        clear_settings_cache()
        tax_profile = EntityTaxProfile(
            tax_regime=EntityTaxProfile.TaxRegime.STANDARD,
            default_vat_rate=Decimal('0.19'),
            vat_id='DE999999999',
        )
        coa = MagicMock()
        entity = SimpleNamespace(default_coa=coa, tax_profile=tax_profile)

        notice = default_invoice_legal_notice_for_entity(entity)

        self.assertIn('DE999999999', notice)
        self.assertIn('19', notice)
