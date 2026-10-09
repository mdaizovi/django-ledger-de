from django.test import SimpleTestCase

from django_ledger_extensions.completeness import find_journal_entry_number_gaps
from django_ledger_extensions.settings import get_extension_setting


class CompletenessSettingsTests(SimpleTestCase):

    def test_timeliness_defaults(self):
        self.assertEqual(get_extension_setting('HEALTH_CHECK_BOOKING_TIMELINESS_DAYS'), 10)
        self.assertEqual(get_extension_setting('HEALTH_CHECK_CASH_TIMELINESS_DAYS'), 1)
        self.assertEqual(get_extension_setting('HEALTH_CHECK_BANK_LINE_DAYS'), 10)


class JournalEntryGapLogicTests(SimpleTestCase):
    """Gap detection is exercised via find_journal_entry_number_gaps (DB integration in CI)."""

    def test_gap_helper_empty_entity_slug_safe(self):
        # Ensures import and callable without side effects when no rows match.
        class _EmptyQs:
            def filter(self, *args, **kwargs):
                return self

            def exclude(self, *args, **kwargs):
                return self

            def values_list(self, *args, **kwargs):
                return []

        class _Entity:
            slug = 'test'

        class _JeManager:
            def filter(self, **kwargs):
                return _EmptyQs()

        import django_ledger_extensions.completeness as completeness_module

        original = completeness_module.lazy_loader.get_journal_entry_model
        try:
            completeness_module.lazy_loader.get_journal_entry_model = lambda: type(
                'JE', (), {'objects': _JeManager()}
            )
            gaps = find_journal_entry_number_gaps(_Entity(), fiscal_year=2026)
            self.assertEqual(gaps, {})
        finally:
            completeness_module.lazy_loader.get_journal_entry_model = original
