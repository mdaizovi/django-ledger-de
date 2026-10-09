"""
Retention summary for GoBD (Belege / books retention periods).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import BackupVerificationLog, SupportingDocumentModel


def supporting_documents_queryset_for_entity(entity):
    JournalEntryModel = lazy_loader.get_journal_entry_model()
    InvoiceModel = lazy_loader.get_invoice_model()
    BillModel = lazy_loader.get_bill_model()

    je_ct = ContentType.objects.get_for_model(JournalEntryModel)
    invoice_ct = ContentType.objects.get_for_model(InvoiceModel)
    bill_ct = ContentType.objects.get_for_model(BillModel)

    je_ids = JournalEntryModel.objects.filter(ledger__entity=entity).values_list('uuid', flat=True)
    invoice_ids = InvoiceModel.objects.filter(ledger__entity=entity).values_list('uuid', flat=True)
    bill_ids = BillModel.objects.filter(ledger__entity=entity).values_list('uuid', flat=True)

    return SupportingDocumentModel.objects.filter(
        Q(content_type=je_ct, object_id__in=je_ids)
        | Q(content_type=invoice_ct, object_id__in=invoice_ids)
        | Q(content_type=bill_ct, object_id__in=bill_ids)
    )


def latest_backup_verification(*, entity=None) -> Optional[BackupVerificationLog]:
    if entity is not None:
        entity_log = BackupVerificationLog.objects.filter(entity=entity).order_by('-verified_at').first()
        if entity_log:
            return entity_log
    return BackupVerificationLog.objects.filter(entity__isnull=True).order_by('-verified_at').first()


def build_retention_report(*, entity=None, reference: Optional[date] = None) -> Dict[str, Any]:
    reference = reference or date.today()
    qs = supporting_documents_queryset_for_entity(entity) if entity else SupportingDocumentModel.objects.all()

    within = qs.filter(retain_until__gt=reference).count()
    eligible_review = qs.filter(retain_until__lte=reference).count()
    unset = qs.filter(retain_until__isnull=True).count()

    backup = latest_backup_verification(entity=entity)
    backup_payload = None
    if backup:
        backup_payload = {
            'verified_at': backup.verified_at.isoformat(),
            'storage_location': backup.storage_location,
            'restore_tested': backup.restore_tested,
            'entity_slug': backup.entity.slug if backup.entity_id else None,
        }

    return {
        'reference_date': reference.isoformat(),
        'entity_slug': entity.slug if entity else None,
        'supporting_documents': {
            'within_retention': within,
            'eligible_for_archival_review': eligible_review,
            'retain_until_unset': unset,
            'total': qs.count(),
        },
        'latest_backup_verification': backup_payload,
    }
