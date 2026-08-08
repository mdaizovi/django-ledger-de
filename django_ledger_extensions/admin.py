from django.contrib import admin

from django_ledger_extensions.models import (
    AccountTranslationModel,
    AccountingReminderLog,
    AccountingReminderRule,
    DocumentInboxItem,
    EntityTaxProfile,
    ExternalPaymentRecord,
    ItemTranslationModel,
    SupportingDocumentModel,
)


@admin.register(EntityTaxProfile)
class EntityTaxProfileAdmin(admin.ModelAdmin):
    list_display = (
        'entity',
        'tax_regime',
        'default_vat_rate',
        'vat_id',
        'show_invoice_legal_notice',
    )
    search_fields = ('entity__name', 'vat_id')
    readonly_fields = ('regime_behavior_summary',)

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'entity',
                    'tax_regime',
                    'default_vat_rate',
                    'vat_id',
                ),
            },
        ),
        (
            'Customer invoices',
            {
                'fields': (
                    'show_invoice_legal_notice',
                    'invoice_legal_notice',
                    'regime_behavior_summary',
                ),
            },
        ),
    )

    @admin.display(description='Regime behaviour (read-only)')
    def regime_behavior_summary(self, obj: EntityTaxProfile) -> str:
        behavior = obj.get_tax_regime_behavior()
        if behavior is None:
            return ''
        lines = [
            f'Charges VAT: {"yes" if behavior.charges_vat else "no"}',
            f'USt-Voranmeldung required: {"yes" if behavior.requires_vat_quarterly_filing else "no"}',
            f'Track Kleinunternehmer turnover: {"yes" if behavior.tracks_kleinunternehmer_turnover else "no"}',
            f'Invoice footnote preview: {behavior.invoice_legal_notice or "(hidden)"}',
            behavior.compliance_hint,
        ]
        return '\n'.join(lines)


@admin.register(SupportingDocumentModel)
class SupportingDocumentAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'document_type', 'content_type', 'object_id', 'immutable', 'created')
    list_filter = ('document_type', 'immutable')
    readonly_fields = ('checksum', 'created', 'updated')


@admin.register(DocumentInboxItem)
class DocumentInboxItemAdmin(admin.ModelAdmin):
    list_display = (
        'uuid',
        'entity',
        'status',
        'source',
        'document_type',
        'suggested_amount',
        'suggested_date',
        'external_source',
        'external_id',
        'created',
    )
    list_filter = ('status', 'source', 'document_type')
    search_fields = ('description', 'vendor_name', 'reference', 'external_id')
    readonly_fields = ('checksum', 'linked_content_type', 'linked_object_id', 'created', 'updated')


@admin.register(ExternalPaymentRecord)
class ExternalPaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        'uuid',
        'entity',
        'record_type',
        'provider',
        'external_id',
        'amount',
        'currency',
        'paid_at',
        'status',
        'invoice',
        'staged_transaction',
    )
    list_filter = ('provider', 'status', 'record_type')
    search_fields = ('external_id', 'customer_email', 'customer_name', 'description')
    readonly_fields = ('error_message', 'created', 'updated')
    raw_id_fields = ('original_payment', 'staged_transaction', 'invoice', 'inbox_item')


@admin.register(AccountingReminderRule)
class AccountingReminderRuleAdmin(admin.ModelAdmin):
    list_display = ('entity', 'kind', 'title', 'lead_days', 'email_to', 'is_active')
    list_filter = ('kind', 'is_active')
    search_fields = ('entity__name', 'title', 'email_to')


@admin.register(AccountingReminderLog)
class AccountingReminderLogAdmin(admin.ModelAdmin):
    list_display = ('rule', 'period_key', 'due_date', 'sent_at')
    list_filter = ('due_date',)
    readonly_fields = ('sent_at', 'created', 'updated')


@admin.register(AccountTranslationModel)
class AccountTranslationAdmin(admin.ModelAdmin):
    list_display = ('account', 'locale', 'name')
    list_filter = ('locale',)


@admin.register(ItemTranslationModel)
class ItemTranslationAdmin(admin.ModelAdmin):
    list_display = ('item', 'locale', 'name', 'regional_code')
    list_filter = ('locale',)
