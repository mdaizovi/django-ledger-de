from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from django_ledger.tests.base import DjangoLedgerBaseTest

from django_ledger_extensions.documents import attach_supporting_document
from django_ledger_extensions.models import AccountingAuditLog


@override_settings(DJANGO_LEDGER_COUNTRY='de')
class GoBDImmutabilityTests(DjangoLedgerBaseTest):

    def test_de_posted_journal_entry_cannot_unpost_or_edit(self):
        entity = self.get_random_entity_model()
        je = self.get_random_je(entity, posted=False)
        attach_supporting_document(
            je,
            SimpleUploadedFile('receipt.pdf', b'pdf', content_type='application/pdf'),
        )
        je.mark_as_posted(commit=True, verify=True, raise_exception=True)

        self.assertFalse(je.can_unpost())
        self.assertFalse(je.can_edit())

    def test_posting_writes_audit_log_and_locks(self):
        entity = self.get_random_entity_model()
        je = self.get_random_je(entity, posted=False)
        attach_supporting_document(
            je,
            SimpleUploadedFile('receipt.pdf', b'pdf', content_type='application/pdf'),
        )
        before = AccountingAuditLog.objects.filter(entity=entity).count()
        je.mark_as_posted(commit=True, verify=True, raise_exception=True)
        je.refresh_from_db()

        self.assertTrue(je.is_locked())
        self.assertEqual(
            AccountingAuditLog.objects.filter(
                entity=entity,
                action=AccountingAuditLog.Action.JOURNAL_ENTRY_POSTED,
                object_id=je.pk,
            ).count(),
            1,
        )
        self.assertGreater(AccountingAuditLog.objects.filter(entity=entity).count(), before)

    def test_account_save_writes_audit_log(self):
        entity = self.get_random_entity_model()
        account = entity.get_coa_accounts(active=True).first()
        self.assertIsNotNone(account)
        before = AccountingAuditLog.objects.filter(
            entity=entity,
            action=AccountingAuditLog.Action.ACCOUNT_UPDATED,
            object_id=account.pk,
        ).count()
        account.name = (account.name or '')[:90] + ' (audit test)'
        account.save(update_fields=['name', 'updated'])
        after = AccountingAuditLog.objects.filter(
            entity=entity,
            action=AccountingAuditLog.Action.ACCOUNT_UPDATED,
            object_id=account.pk,
        ).count()
        self.assertGreater(after, before)
