"""
Django admin forms for Beleg (supporting document) workflows.
"""
from __future__ import annotations

from uuid import UUID

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import DocumentInboxItem, SupportingDocumentModel

RECENT_LEDGER_OBJECT_LIMIT = 200

_EMPTY_LINK_HELP = _(
    'No matches yet. Select Entity above (the page reloads), or save this row with '
    'Entity set and reopen it. Create bills in the ledger first if needed.'
)
_LINK_BILL_HELP = _('Pick the bill, then Save to attach this Beleg.')

# Shown read-only on SupportingDocument admin change view; must be on the form.
_SUPPORTING_DOC_CHANGE_READONLY_FIELDS = (
    'checksum',
    'content_type',
    'object_id',
    'immutable',
    'created',
    'updated',
)


class EntityLedgerModelChoiceField(forms.ModelChoiceField):
    """
    ModelChoiceField for ledger-backed objects (bill, invoice, JE).

    Resolves the submitted PK directly instead of requiring queryset membership,
    because the admin rebuilds the queryset on every POST.
    """

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, self.queryset.model):
            return value
        try:
            key = self.to_field_name or 'pk'
            value = self.queryset.model._meta.pk.to_python(value)
            return self.queryset.model.objects.get(**{key: value})
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
            )

    def validate(self, value):
        if self.required and value in self.empty_values:
            raise ValidationError(self.error_messages['required'], code='required')


def _entity_id_from_form(form) -> str | None:
    """Prefer submitted entity (admin edit) over the stored instance value."""
    entity = form.data.get('entity') or form.initial.get('entity')
    if entity:
        return str(entity)
    if form.instance.pk:
        instance_entity_id = getattr(form.instance, 'entity_id', None)
        if instance_entity_id:
            return str(instance_entity_id)
    return None


def _ledger_objects_queryset(model, entity_id: str):
    """Bills/invoices may be matched via ledger or direct entity_model FK."""
    if getattr(model, '_meta', None) and model._meta.model_name in ('billmodel', 'invoicemodel'):
        return model.objects.filter(
            Q(ledger__entity_id=entity_id) | Q(entity_model_id=entity_id)
        ).distinct()
    return model.objects.filter(ledger__entity_id=entity_id)


def _bill_label(bill) -> str:
    vendor_name = ''
    vendor = getattr(bill, 'vendor', None)
    if vendor is not None:
        vendor_name = getattr(vendor, 'vendor_name', '') or str(vendor)
    status = bill.get_bill_status_display()
    return f'{bill.bill_number} ({status}) — {vendor_name}'.strip(' —')


def _invoice_label(invoice) -> str:
    customer_name = ''
    customer = getattr(invoice, 'customer', None)
    if customer is not None:
        customer_name = getattr(customer, 'customer_name', '') or str(customer)
    status = invoice.get_invoice_status_display()
    return f'{invoice.invoice_number} ({status}) — {customer_name}'.strip(' —')


def _journal_entry_label(je) -> str:
    timestamp = getattr(je, 'timestamp', None)
    if timestamp:
        return f'{je.je_number} — {timestamp:%Y-%m-%d}'
    return str(je.je_number)


def _recent_for_entity(model, entity_id: str, *, selected_pk=None):
    """
    Ledger objects for the link-to dropdowns.

    Always include *selected_pk* when present so ModelChoiceField validation
    succeeds on POST even if the choice fell outside the recent-items window.
    """
    qs = _ledger_objects_queryset(model, entity_id).order_by('-updated')
    recent_pks = list(qs.values_list('pk', flat=True)[:RECENT_LEDGER_OBJECT_LIMIT])
    if selected_pk:
        try:
            selected_pk = UUID(str(selected_pk))
        except (TypeError, ValueError):
            selected_pk = None
        if selected_pk and selected_pk not in recent_pks:
            recent_pks.append(selected_pk)
    if not recent_pks:
        return model.objects.none()
    return _ledger_objects_queryset(model, entity_id).filter(
        pk__in=recent_pks
    ).order_by('-updated')


def _apply_link_field_labels(form) -> None:
    if 'link_bill' in form.fields:
        form.fields['link_bill'].label_from_instance = _bill_label
        count = form.fields['link_bill'].queryset.count()
        form.fields['link_bill'].help_text = _LINK_BILL_HELP if count else _EMPTY_LINK_HELP
    if 'link_invoice' in form.fields:
        form.fields['link_invoice'].label_from_instance = _invoice_label
        if not form.fields['link_invoice'].queryset.exists():
            form.fields['link_invoice'].help_text = _EMPTY_LINK_HELP
    if 'link_journal_entry' in form.fields:
        form.fields['link_journal_entry'].label_from_instance = _journal_entry_label
        if not form.fields['link_journal_entry'].queryset.exists():
            form.fields['link_journal_entry'].help_text = _EMPTY_LINK_HELP


def _recent_journal_entries_for_entity(entity_id: str, *, selected_pk=None):
    JournalEntryModel = lazy_loader.get_journal_entry_model()
    qs = JournalEntryModel.objects.filter(ledger__entity_id=entity_id).order_by('-updated')
    recent_pks = list(qs.values_list('pk', flat=True)[:RECENT_LEDGER_OBJECT_LIMIT])
    if selected_pk:
        try:
            selected_pk = UUID(str(selected_pk))
        except (TypeError, ValueError):
            selected_pk = None
        if selected_pk and selected_pk not in recent_pks:
            recent_pks.append(selected_pk)
    if not recent_pks:
        return JournalEntryModel.objects.none()
    return JournalEntryModel.objects.filter(
        pk__in=recent_pks,
        ledger__entity_id=entity_id,
    ).order_by('-updated')


def _set_link_field_querysets(form, entity_id: str) -> None:
    InvoiceModel = lazy_loader.get_invoice_model()
    BillModel = lazy_loader.get_bill_model()

    form.fields['link_invoice'].queryset = _recent_for_entity(
        InvoiceModel,
        entity_id,
        selected_pk=form.data.get('link_invoice'),
    )
    form.fields['link_bill'].queryset = _recent_for_entity(
        BillModel,
        entity_id,
        selected_pk=form.data.get('link_bill'),
    )
    form.fields['link_journal_entry'].queryset = _recent_journal_entries_for_entity(
        entity_id,
        selected_pk=form.data.get('link_journal_entry'),
    )


class DocumentInboxItemAdminForm(forms.ModelForm):
    link_invoice = EntityLedgerModelChoiceField(
        label=_('Link to invoice'),
        queryset=lazy_loader.get_invoice_model().objects.none(),
        required=False,
        help_text=_('Pick one target and save to attach this Beleg (weekly inbox workflow).'),
    )
    link_bill = EntityLedgerModelChoiceField(
        label=_('Link to bill'),
        queryset=lazy_loader.get_bill_model().objects.none(),
        required=False,
    )
    link_journal_entry = EntityLedgerModelChoiceField(
        label=_('Link to journal entry'),
        queryset=lazy_loader.get_journal_entry_model().objects.none(),
        required=False,
    )

    class Meta:
        model = DocumentInboxItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        entity_id = _entity_id_from_form(self)
        if entity_id:
            _set_link_field_querysets(self, entity_id)
            _apply_link_field_labels(self)
        elif self.instance.pk is None:
            for name in ('link_invoice', 'link_bill', 'link_journal_entry'):
                if name in self.fields:
                    self.fields[name].help_text = _(
                        'Select Entity above first (the page reloads), then pick a bill here.'
                    )

        if self.instance.pk and self.instance.status != DocumentInboxItem.Status.UNLINKED:
            for name in ('link_invoice', 'link_bill', 'link_journal_entry'):
                self.fields[name].disabled = True
                self.fields[name].help_text = _('Already linked — create a new inbox item for another Beleg.')

    def clean(self):
        cleaned = super().clean()
        targets = [
            cleaned.get('link_invoice'),
            cleaned.get('link_bill'),
            cleaned.get('link_journal_entry'),
        ]
        chosen = [target for target in targets if target is not None]
        if len(chosen) > 1:
            raise ValidationError(_('Link to only one invoice, bill, or journal entry at a time.'))
        cleaned['link_target'] = chosen[0] if chosen else None
        if cleaned['link_target'] is not None:
            self._validate_link_target_entity(cleaned['link_target'], entity_id=_entity_id_from_form(self))
        return cleaned

    def _validate_link_target_entity(self, target, *, entity_id: str | None) -> None:
        if not entity_id:
            return
        target_entity_id = getattr(getattr(target, 'ledger', None), 'entity_id', None)
        if target_entity_id and str(target_entity_id) != str(entity_id):
            raise ValidationError(
                _('The selected ledger object belongs to a different entity than this inbox item. '
                  'Use the same entity on the inbox row and the bill/invoice.')
            )
        bill_entity_id = getattr(target, 'entity_model_id', None)
        if bill_entity_id and str(bill_entity_id) != str(entity_id):
            raise ValidationError(
                _('The selected ledger object belongs to a different entity than this inbox item. '
                  'Use the same entity on the inbox row and the bill/invoice.')
            )


class SupportingDocumentAdminForm(forms.ModelForm):
    entity = forms.ModelChoiceField(
        label=_('Entity'),
        queryset=lazy_loader.get_entity_model().objects.all().order_by('name'),
        required=True,
        help_text=_('Filter targets below, then pick exactly one ledger object to attach this file to.'),
    )
    link_invoice = EntityLedgerModelChoiceField(
        label=_('Attach to invoice'),
        queryset=lazy_loader.get_invoice_model().objects.none(),
        required=False,
    )
    link_bill = EntityLedgerModelChoiceField(
        label=_('Attach to bill'),
        queryset=lazy_loader.get_bill_model().objects.none(),
        required=False,
    )
    link_journal_entry = EntityLedgerModelChoiceField(
        label=_('Attach to journal entry'),
        queryset=lazy_loader.get_journal_entry_model().objects.none(),
        required=False,
    )

    class Meta:
        model = SupportingDocumentModel
        fields = (
            'file',
            'document_type',
            'description',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            for name in ('entity', 'link_invoice', 'link_bill', 'link_journal_entry'):
                self.fields.pop(name, None)
            for name in _SUPPORTING_DOC_CHANGE_READONLY_FIELDS:
                if name not in self.fields:
                    model_field = SupportingDocumentModel._meta.get_field(name)
                    self.fields[name] = model_field.formfield()
            return

        entity_id = _entity_id_from_form(self)
        if not entity_id:
            for name in ('link_invoice', 'link_bill', 'link_journal_entry'):
                if name in self.fields:
                    self.fields[name].help_text = _(
                        'Select Entity above first (the page reloads), then pick a bill here.'
                    )
            return

        _set_link_field_querysets(self, entity_id)
        _apply_link_field_labels(self)

    def clean(self):
        cleaned = super().clean()
        if not self.instance._state.adding:
            return cleaned

        targets = [
            cleaned.get('link_invoice'),
            cleaned.get('link_bill'),
            cleaned.get('link_journal_entry'),
        ]
        chosen = [target for target in targets if target is not None]
        if len(chosen) != 1:
            raise ValidationError(_('Select exactly one invoice, bill, or journal entry to attach this Beleg to.'))
        cleaned['link_target'] = chosen[0]
        entity_id = _entity_id_from_form(self)
        if entity_id:
            target_entity_id = getattr(getattr(chosen[0], 'ledger', None), 'entity_id', None)
            if target_entity_id and str(target_entity_id) != str(entity_id):
                raise ValidationError(
                    _('The selected bill/invoice belongs to a different entity. '
                      'Pick the same entity above as the ledger object.')
                )
        return cleaned

    def save(self, commit=True):
        target = self.cleaned_data['link_target']
        self.instance.content_object = target
        return super().save(commit=commit)
