from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.documents import (
    attach_supporting_document,
    create_inbox_item,
    link_inbox_item_to_object,
    supporting_documents_for,
)
from django_ledger_extensions.models import (
    BelegCaptureMethod,
    DocumentInboxItem,
    SupportingDocumentModel,
)


class BelegPrinzipTests(DjangoLedgerBaseTest):

    def test_inbox_infers_capture_method_from_camera_source(self):
        entity = self.get_random_entity_model()
        inbox = create_inbox_item(
            entity,
            SimpleUploadedFile('photo.jpg', b'jpg', content_type='image/jpeg'),
            source=DocumentInboxItem.Source.CAMERA,
        )
        self.assertEqual(inbox.capture_method, BelegCaptureMethod.PHOTO)

    def test_einvoice_requires_structured_file(self):
        entity = self.get_random_entity_model()
        je = self.get_random_je(entity, posted=False)
        doc = SupportingDocumentModel(
            content_object=je,
            file=SimpleUploadedFile('view.pdf', b'pdf', content_type='application/pdf'),
            document_type=SupportingDocumentModel.DocumentType.EINVOICE,
            capture_method=BelegCaptureMethod.E_INVOICE,
        )
        with self.assertRaises(ValidationError):
            doc.full_clean()

    def test_link_inbox_copies_structured_einvoice_and_supporting_documents_for(self):
        entity = self.get_random_entity_model()
        je = self.get_random_je(entity, posted=False)
        inbox = create_inbox_item(
            entity,
            SimpleUploadedFile('invoice.pdf', b'pdf', content_type='application/pdf'),
            structured_file=SimpleUploadedFile('invoice.xml', b'<xml/>', content_type='application/xml'),
            document_type=SupportingDocumentModel.DocumentType.EINVOICE,
            capture_method=BelegCaptureMethod.E_INVOICE,
        )
        doc = link_inbox_item_to_object(inbox, je)
        self.assertTrue(doc.structured_file)
        self.assertTrue(doc.structured_checksum)
        self.assertEqual(doc.capture_method, BelegCaptureMethod.E_INVOICE)
        self.assertEqual(supporting_documents_for(je).get(pk=doc.pk).pk, doc.pk)

    def test_immutable_document_rejects_file_replacement(self):
        entity = self.get_random_entity_model()
        je = self.get_random_je(entity, posted=False)
        doc = attach_supporting_document(
            je,
            SimpleUploadedFile('a.pdf', b'a', content_type='application/pdf'),
        )
        doc.immutable = True
        doc.save(update_fields=['immutable'])
        doc.file.save('b.pdf', SimpleUploadedFile('b.pdf', b'b', content_type='application/pdf'), save=False)
        with self.assertRaises(ValidationError):
            doc.save()
