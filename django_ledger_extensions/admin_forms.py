"""
Django admin forms for Beleg (supporting document) workflows.
"""
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import DocumentInboxItem, SupportingDocumentModel


def _entity_id_from_form(form) -> str | None:
    if form.instance.pk and form.instance.entity_id:
        return str(form.instance.entity_id)
    entity = form.data.get('entity') or form.initial.get('entity')
    return str(entity) if entity else None


def _recent_for_entity(model, entity_id: str):
    return model.objects.filter(ledger__entity_id=entity_id).order_by('-updated')[:200]


class DocumentInboxItemAdminForm(forms.ModelForm):
    link_invoice = forms.ModelChoiceField(
        label=_('Link to invoice'),
        queryset=lazy_loader.get_invoice_model().objects.none(),
        required=False,
        help_text=_('Pick one target and save to attach this Beleg (weekly inbox workflow).'),
    )
    link_bill = forms.ModelChoiceField(
        label=_('Link to bill'),
        queryset=lazy_loader.get_bill_model().objects.none(),
        required=False,
    )
    link_journal_entry = forms.ModelChoiceField(
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
        if not entity_id:
            return

        InvoiceModel = lazy_loader.get_invoice_model()
        BillModel = lazy_loader.get_bill_model()
        JournalEntryModel = lazy_loader.get_journal_entry_model()

        self.fields['link_invoice'].queryset = _recent_for_entity(InvoiceModel, entity_id)
        self.fields['link_bill'].queryset = _recent_for_entity(BillModel, entity_id)
        self.fields['link_journal_entry'].queryset = JournalEntryModel.objects.filter(
            ledger__entity_id=entity_id,
        ).order_by('-updated')[:200]

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
        return cleaned


class SupportingDocumentAdminForm(forms.ModelForm):
    entity = forms.ModelChoiceField(
        label=_('Entity'),
        queryset=lazy_loader.get_entity_model().objects.all().order_by('name'),
        required=True,
        help_text=_('Filter targets below, then pick exactly one ledger object to attach this file to.'),
    )
    link_invoice = forms.ModelChoiceField(
        label=_('Attach to invoice'),
        queryset=lazy_loader.get_invoice_model().objects.none(),
        required=False,
    )
    link_bill = forms.ModelChoiceField(
        label=_('Attach to bill'),
        queryset=lazy_loader.get_bill_model().objects.none(),
        required=False,
    )
    link_journal_entry = forms.ModelChoiceField(
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
            return

        entity_id = self.data.get('entity') or self.initial.get('entity')
        if not entity_id:
            return

        InvoiceModel = lazy_loader.get_invoice_model()
        BillModel = lazy_loader.get_bill_model()
        JournalEntryModel = lazy_loader.get_journal_entry_model()

        self.fields['link_invoice'].queryset = _recent_for_entity(InvoiceModel, entity_id)
        self.fields['link_bill'].queryset = _recent_for_entity(BillModel, entity_id)
        self.fields['link_journal_entry'].queryset = JournalEntryModel.objects.filter(
            ledger__entity_id=entity_id,
        ).order_by('-updated')[:200]

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
        return cleaned

    def save(self, commit=True):
        target = self.cleaned_data['link_target']
        self.instance.content_object = target
        return super().save(commit=commit)
