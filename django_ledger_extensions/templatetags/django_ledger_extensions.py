from django import template

from django_ledger_extensions.tax_profile import get_entity_tax_regime_behavior

register = template.Library()


@register.simple_tag
def invoice_tax_footnote(invoice) -> str:
    entity = invoice.ledger.entity
    behavior = get_entity_tax_regime_behavior(entity)
    if behavior is None:
        return ''
    return behavior.invoice_legal_notice


@register.simple_tag
def invoice_charges_vat(invoice) -> bool:
    entity = invoice.ledger.entity
    behavior = get_entity_tax_regime_behavior(entity)
    return bool(behavior and behavior.charges_vat)
