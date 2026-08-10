from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile

from django_ledger.models.mixins import PaymentTermsMixIn
from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.admin_forms import DocumentInboxItemAdminForm, SupportingDocumentAdminForm
from django_ledger_extensions.documents import create_inbox_item
from django_ledger_extensions.models import SupportingDocumentModel


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

    def test_link_bill_validates_on_post_for_in_review_bill(self):
        from random import choice

        entity = self.get_random_entity_model()
        bill_model = choice(list(entity.get_bills()))
        self.assertIsNotNone(bill_model.ledger_id)

        inbox = create_inbox_item(
            entity,
            SimpleUploadedFile('hosting.pdf', b'pdf-bytes', content_type='application/pdf'),
        )
        data = {
            'entity': str(entity.pk),
            'file': SimpleUploadedFile('hosting.pdf', b'pdf-bytes', content_type='application/pdf'),
            'source': inbox.source,
            'status': inbox.status,
            'document_type': inbox.document_type,
            'description': inbox.description,
            'vendor_name': '',
            'reference': '',
            'external_source': '',
            'external_id': '',
            'metadata': '{}',
            'link_bill': str(bill_model.pk),
        }
        form = DocumentInboxItemAdminForm(data=data, instance=inbox)
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())
        self.assertEqual(form.cleaned_data['link_target'], bill_model)


class SupportingDocumentAdminFormTests(DjangoLedgerBaseTest):

    def test_add_form_includes_entity_and_link_fields(self):
        form = SupportingDocumentAdminForm()
        self.assertIn('entity', form.fields)
        self.assertIn('link_invoice', form.fields)
        self.assertIn('link_bill', form.fields)
        self.assertIn('link_journal_entry', form.fields)
        self.assertIn('file', form.fields)

    def test_supporting_document_admin_add_fieldsets_match_form(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.admin.options import flatten_fieldsets

        from django_ledger_extensions.admin import SupportingDocumentAdmin

        admin = SupportingDocumentAdmin(SupportingDocumentModel, AdminSite())
        fieldsets = admin.get_fieldsets(request=None, obj=None)
        field_names = fieldsets[0][1]['fields']
        form = SupportingDocumentAdminForm()
        for name in field_names:
            self.assertIn(name, form.fields, msg=f'Missing admin field: {name}')

    def test_supporting_document_admin_get_form_ignores_fieldset_fields_kwarg(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.admin.options import flatten_fieldsets

        from django_ledger_extensions.admin import SupportingDocumentAdmin

        admin = SupportingDocumentAdmin(SupportingDocumentModel, AdminSite())
        fields = flatten_fieldsets(admin.get_fieldsets(request=None, obj=None))
        form_class = admin.get_form(request=None, obj=None, change=False, fields=fields)
        self.assertIs(form_class, SupportingDocumentAdminForm)
        form = form_class()
        for name in fields:
            self.assertIn(name, form.fields, msg=f'Missing admin field: {name}')
