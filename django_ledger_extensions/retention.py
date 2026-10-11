"""
GoBD retention helpers (8-year Belege / 10-year books — configurable).
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django_ledger_extensions.settings import get_extension_setting

if TYPE_CHECKING:
    from django_ledger_extensions.models import SupportingDocumentModel

# Match SupportingDocumentModel.DocumentType values (avoid importing models here).
LONG_RETENTION_DOCUMENT_TYPES = frozenset({'bank_statement', 'contract'})


def _add_calendar_years(start: date, years: int) -> date:
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        # 29 Feb → 28 Feb
        return start.replace(year=start.year + years, day=28)


def retention_years_for_document_type(document_type: str) -> int:
    if document_type in LONG_RETENTION_DOCUMENT_TYPES:
        return int(get_extension_setting('RETENTION_BOOKS_YEARS'))
    return int(get_extension_setting('RETENTION_BELEG_YEARS'))


def compute_retain_until_date(base_date: date, document_type: str) -> date:
    return _add_calendar_years(base_date, retention_years_for_document_type(document_type))


def assign_retain_until(document: SupportingDocumentModel) -> date:
    base = document.created.date() if document.created else date.today()
    return compute_retain_until_date(base, document.document_type)
