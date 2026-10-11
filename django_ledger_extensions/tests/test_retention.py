from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_ledger_extensions.models import SupportingDocumentModel
from django_ledger_extensions.retention import (
    compute_retain_until_date,
    retention_years_for_document_type,
)


class RetentionHelpersTest(SimpleTestCase):
    def test_beleg_default_eight_years(self):
        self.assertEqual(
            retention_years_for_document_type(SupportingDocumentModel.DocumentType.RECEIPT),
            8,
        )

    def test_bank_statement_ten_years(self):
        self.assertEqual(
            retention_years_for_document_type(SupportingDocumentModel.DocumentType.BANK_STATEMENT),
            10,
        )

    def test_compute_retain_until_leap_day(self):
        base = date(2024, 2, 29)
        end = compute_retain_until_date(base, SupportingDocumentModel.DocumentType.RECEIPT)
        self.assertEqual(end, date(2032, 2, 29))

    def test_delete_blocked_within_retention(self):
        doc = SupportingDocumentModel(retain_until=date(2099, 1, 1))
        with self.assertRaises(ValidationError):
            doc.delete()
