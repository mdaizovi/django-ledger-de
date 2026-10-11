from decimal import Decimal

from django.test import SimpleTestCase

from django_ledger_extensions.auditor_access_export import build_datenbeschreibung
from django_ledger_extensions.datev_buchungsstapel import datev_kontonummer, format_datev_amount


class DatevBuchungsstapelTests(SimpleTestCase):

    def test_datev_kontonummer_strips_space(self):
        self.assertEqual(datev_kontonummer('1200 00'), '120000')
        self.assertEqual(datev_kontonummer('8400 10'), '840010')

    def test_format_datev_amount_uses_comma(self):
        self.assertEqual(format_datev_amount(Decimal('1234.5')), '1234,50')

    def test_datenbeschreibung_includes_datev_hinweis(self):
        class _Entity:
            slug = 'school'
            name = 'School'

        beschreibung = build_datenbeschreibung(
            _Entity(),
            start=__import__('datetime').date(2026, 1, 1),
            end=__import__('datetime').date(2026, 1, 31),
            files=[],
        )
        self.assertIn('datev_buchungsstapel.csv', beschreibung['column_descriptions'])
        self.assertIn('EXTF', beschreibung['datev_import_hinweis'])
