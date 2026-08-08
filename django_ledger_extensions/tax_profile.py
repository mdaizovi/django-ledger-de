"""
Entity tax profile helpers — invoice legal notices and regime-driven behaviour flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django_ledger_extensions.models import EntityTaxProfile


@dataclass(frozen=True)
class EntityTaxRegimeBehavior:
    """
    Operational flags derived from an entity's ``EntityTaxProfile``.

    Used for invoice footnotes, reporting expectations, and future UI hints.
    """

    tax_regime: str
    tax_regime_label: str
    charges_vat: bool
    show_vat_amounts_on_invoices: bool
    requires_vat_quarterly_filing: bool
    tracks_kleinunternehmer_turnover: bool
    show_invoice_legal_notice: bool
    invoice_legal_notice: str
    compliance_hint: str


_COMPLIANCE_HINTS = {
    EntityTaxProfile.TaxRegime.EXEMPT: (
        'No USt-Voranmeldung. Exempt education/training supplies under § 4 UStG — '
        'invoice amounts are gross with no VAT charged.'
    ),
    EntityTaxProfile.TaxRegime.SMALL_BUSINESS: (
        'No USt-Voranmeldung. Monitor turnover quarterly against § 19 UStG '
        'Kleinunternehmer limits (run vat_quarterly_report).'
    ),
    EntityTaxProfile.TaxRegime.STANDARD: (
        'Standard VAT (Regelbesteuerung). File USt-Voranmeldung quarterly and run '
        'vat_quarterly_report for Vorsteuer, Umsatzsteuer, and Zahllast.'
    ),
}


def resolve_invoice_legal_notice(profile) -> str:
    """Return the legal footnote for customer invoices (override or country default)."""
    if not profile.show_invoice_legal_notice:
        return ''
    override = (getattr(profile, 'invoice_legal_notice', '') or '').strip()
    if override:
        return override

    from django_ledger.regional.dispatch import dispatch_get_invoice_legal_notice

    return dispatch_get_invoice_legal_notice(profile.entity) or ''


def build_tax_regime_behavior(
    profile: EntityTaxProfile,
    *,
    invoice_legal_notice: str | None = None,
) -> EntityTaxRegimeBehavior:
    regime = profile.tax_regime
    if invoice_legal_notice is None:
        invoice_legal_notice = resolve_invoice_legal_notice(profile)
    return EntityTaxRegimeBehavior(
        tax_regime=regime,
        tax_regime_label=str(profile.get_tax_regime_display()),
        charges_vat=regime == EntityTaxProfile.TaxRegime.STANDARD,
        show_vat_amounts_on_invoices=regime == EntityTaxProfile.TaxRegime.STANDARD,
        requires_vat_quarterly_filing=regime == EntityTaxProfile.TaxRegime.STANDARD,
        tracks_kleinunternehmer_turnover=regime == EntityTaxProfile.TaxRegime.SMALL_BUSINESS,
        show_invoice_legal_notice=profile.show_invoice_legal_notice,
        invoice_legal_notice=invoice_legal_notice,
        compliance_hint=_COMPLIANCE_HINTS.get(regime, ''),
    )


def get_entity_tax_regime_behavior(entity) -> Optional[EntityTaxRegimeBehavior]:
    try:
        profile = entity.tax_profile
    except EntityTaxProfile.DoesNotExist:
        return None

    return build_tax_regime_behavior(profile)
