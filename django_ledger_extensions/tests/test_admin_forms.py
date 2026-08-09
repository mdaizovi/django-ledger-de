from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from django_ledger.models.mixins import PaymentTermsMixIn
from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.admin_forms import DocumentInboxItemAdminForm, SupportingDocumentAdminForm
from django_ledger_extensions.documents import create_inbox_item


class DocumentInboxAdminFormTests(DjangoLedgerBaseTest):

    def test_link_invoice_dropdown_scoped_to_entity(self):
        entity = self.get_random_entity_model()
        customer = entity.create_customer(
            {
                'customer_name': 'Student',
                'email': 's@example.com',
            }
        )
        invoice = entity.create_invoice(
            customer_model=customer,
            terms=PaymentTermsMixIn.TERMS_ON_RECEIPT,
            commit=True,
        )
        inbox = create_inbox_item(
            entity,
            SimpleUploadedFile('r.jpg', b'bytes', content_type='image/jpeg'),
        )
        form = DocumentInboxItemAdminForm(instance=inbox)
        invoice_ids = list(form.fields['link_invoice'].queryset.values_list('pk', flat=True))
        self.assertIn(invoice.pk, invoice_ids)


class SupportingDocumentAdminFormTests(DjangoLedgerBaseTest):

    def test_add_form_includes_entity_and_link_fields(self):
        form = SupportingDocumentAdminForm()
        self.assertIn('entity', form.fields)
        self.assertIn('link_invoice', form.fields)
        self.assertIn('link_bill', form.fields)
        self.assertIn('link_journal_entry', form.fields)
        self.assertIn('file', form.fields)
