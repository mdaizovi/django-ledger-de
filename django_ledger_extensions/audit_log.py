"""
Append-only accounting audit log helpers (GoBD traceability).
"""
from __future__ import annotations

from typing import Any, Optional

from django.contrib.contenttypes.models import ContentType

from django_ledger_extensions.models import AccountingAuditLog


def _resolve_user(user=None, user_model=None):
    if user is not None:
        return user
    if user_model is not None and getattr(user_model, 'is_authenticated', False):
        return user_model
    return None


def log_accounting_audit(
    *,
    entity,
    action: str,
    summary: str,
    user=None,
    user_model=None,
    obj=None,
    details: Optional[dict[str, Any]] = None,
) -> AccountingAuditLog:
    content_type = None
    object_id = None
    if obj is not None:
        content_type = ContentType.objects.get_for_model(obj)
        object_id = getattr(obj, 'pk', None)

    return AccountingAuditLog.objects.create(
        entity=entity,
        user=_resolve_user(user, user_model),
        action=action,
        content_type=content_type,
        object_id=object_id,
        summary=summary[:512],
        details=details or {},
    )


def entity_for_journal_entry(journal_entry):
    ledger = getattr(journal_entry, 'ledger', None)
    if ledger is None:
        return None
    return getattr(ledger, 'entity', None)
