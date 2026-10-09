from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from django_ledger_extensions.audit_package_export import (
    _json_default,
    build_audit_package_manifest,
)


class AuditPackageExportTests(SimpleTestCase):

    def test_json_default_serializes_decimal_and_date(self):
        self.assertEqual(_json_default(Decimal('1.50')), '1.50')
        self.assertEqual(_json_default(date(2026, 3, 31)), '2026-03-31')

    def test_manifest_lists_files(self):
        class _Entity:
            slug = 'school'
            name = 'School'

        manifest = build_audit_package_manifest(
            _Entity(),
            start=date(2026, 1, 1),
            end=date(2026, 1, 31),
            files=[{'name': 'journal_chronological.csv', 'sha256': 'abc', 'description': 'Journal'}],
        )
        self.assertEqual(manifest['format_version'], 1)
        self.assertEqual(manifest['entity']['slug'], 'school')
        self.assertEqual(len(manifest['files']), 1)
