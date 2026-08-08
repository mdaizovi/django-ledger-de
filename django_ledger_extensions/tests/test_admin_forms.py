from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from django_ledger.models.mixins import PaymentTermsMixIn
from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.admin_forms import DocumentInboxItemAdminForm
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
