from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django_ledger_extensions.admin_forms import DocumentInboxItemAdminForm, SupportingDocumentAdminForm
from django_ledger_extensions.documents import link_inbox_item_to_object
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
    form = SupportingDocumentAdminForm
    list_display = ('uuid', 'document_type', 'linked_object_display', 'immutable', 'created')
    list_filter = ('document_type', 'immutable')
    search_fields = ('description', 'object_id')
    readonly_fields = ('checksum', 'content_type', 'object_id', 'linked_object_display', 'created', 'updated')

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = SupportingDocumentAdminForm
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (
                    _('Attach Beleg'),
                    {
                        'description': _(
                            'Choose your entity, pick one ledger object, upload the file, then save. '
                            'No command line required.'
                        ),
                        'fields': (
                            'entity',
                            'link_invoice',
                            'link_bill',
                            'link_journal_entry',
                            'file',
                            'document_type',
                            'description',
                        ),
                    },
                ),
            )
        return (
            (
                None,
                {
                    'fields': (
                        'linked_object_display',
                        'content_type',
                        'object_id',
                        'file',
                        'document_type',
                        'description',
                        'checksum',
                        'immutable',
                        'created',
                        'updated',
                    ),
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly.extend(['file', 'document_type', 'description'])
            if obj.immutable:
                return readonly
        return readonly

    @admin.display(description=_('Linked to'))
    def linked_object_display(self, obj: SupportingDocumentModel) -> str:
        if not obj.content_type_id:
            return '—'
        try:
            target = obj.content_object
        except Exception:
            target = None
        if target is None:
            return f'{obj.content_type.model} {obj.object_id}'
        return str(target)


@admin.register(DocumentInboxItem)
class DocumentInboxItemAdmin(admin.ModelAdmin):
    form = DocumentInboxItemAdminForm
    list_display = (
        'created',
        'status_badge',
        'entity',
        'description',
        'vendor_name',
        'suggested_amount',
        'suggested_date',
        'document_type',
    )
    list_filter = ('status', 'source', 'document_type', 'entity')
    search_fields = ('description', 'vendor_name', 'reference', 'external_id')
    readonly_fields = (
        'checksum',
        'linked_target_display',
        'linked_content_type',
        'linked_object_id',
        'created',
        'updated',
    )
    ordering = ('-created',)

    fieldsets = (
        (
            _('Beleg file'),
            {
                'fields': (
                    'entity',
                    'file',
                    'source',
                    'status',
                    'document_type',
                    'description',
                    'vendor_name',
                    'reference',
                    'suggested_amount',
                    'suggested_date',
                    'external_source',
                    'external_id',
                    'metadata',
                    'checksum',
                    'created',
                    'updated',
                ),
            },
        ),
        (
            _('Link to ledger object'),
            {
                'description': _(
                    'Weekly workflow: upload receipts here first. When you know which invoice, bill, '
                    'or journal entry they belong to, pick one target below and click Save.'
                ),
                'fields': (
                    'link_invoice',
                    'link_bill',
                    'link_journal_entry',
                    'linked_target_display',
                    'linked_content_type',
                    'linked_object_id',
                ),
            },
        ),
    )

    @admin.display(description=_('Status'), ordering='status')
    def status_badge(self, obj: DocumentInboxItem) -> str:
        colors = {
            DocumentInboxItem.Status.UNLINKED: '#b45309',
            DocumentInboxItem.Status.LINKED: '#15803d',
            DocumentInboxItem.Status.ARCHIVED: '#64748b',
        }
        color = colors.get(obj.status, '#64748b')
        label = obj.get_status_display()
        return format_html('<span style="color:{}; font-weight:600;">{}</span>', color, label)

    @admin.display(description=_('Linked to'))
    def linked_target_display(self, obj: DocumentInboxItem) -> str:
        if obj.status == DocumentInboxItem.Status.UNLINKED:
            return _('Not linked yet')
        if obj.linked_object is not None:
            return str(obj.linked_object)
        if obj.linked_content_type_id and obj.linked_object_id:
            return f'{obj.linked_content_type.model} {obj.linked_object_id}'
        return '—'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        target = form.cleaned_data.get('link_target')
        if target is None:
            return
        if obj.status != DocumentInboxItem.Status.UNLINKED:
            return
        doc = link_inbox_item_to_object(obj, target)
        ct = ContentType.objects.get_for_model(target)
        messages.success(
            request,
            _('Beleg linked to %(target)s (supporting document %(doc)s).')
            % {'target': target, 'doc': doc.uuid},
        )


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
