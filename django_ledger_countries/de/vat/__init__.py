"""
Pluggable German VAT posting by entity tax regime.

Toggle per entity via ``EntityTaxProfile.tax_regime`` (Django admin). New entities
default from ``DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME`` / ``DEFAULT_VAT_RATE`` settings.
"""
from django_ledger_countries.de.vat.reporting import (
    build_vat_quarterly_report,
    format_vat_quarterly_report,
)
from django_ledger_countries.de.vat.service import (
    adjust_posting,
    apply_regime_starter_activation,
    get_default_tax_profile_values,
    get_vat_handler_for_profile,
    invoice_vat_notice_for_entity,
    validate_vat_journal_entry,
)

__all__ = [
    'adjust_posting',
    'apply_regime_starter_activation',
    'build_vat_quarterly_report',
    'format_vat_quarterly_report',
    'get_default_tax_profile_values',
    'get_vat_handler_for_profile',
    'invoice_vat_notice_for_entity',
    'validate_vat_journal_entry',
]
