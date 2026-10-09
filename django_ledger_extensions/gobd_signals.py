"""
GoBD-oriented audit logging and posting locks.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_ledger.models.signals import journal_entry_posted, journal_entry_unposted
from django_ledger.models.utils import lazy_loader

from django_ledger_countries.settings import get_country_code, get_ledger_setting

from django_ledger_extensions.audit_log import entity_for_journal_entry, log_accounting_audit
from django_ledger_extensions.models import AccountingAuditLog


@receiver(journal_entry_posted)
def gobd_lock_journal_entry_on_post(sender, instance, commited=False, **kwargs):
    if not commited or not get_ledger_setting('LOCK_JOURNAL_ENTRY_ON_POST'):
        return
    if not instance.is_locked():
        instance.mark_as_locked(commit=True, raise_exception=False)


@receiver(journal_entry_posted)
def audit_journal_entry_posted(sender, instance, commited=False, **kwargs):
    if not commited:
        return
    entity = entity_for_journal_entry(instance)
    if entity is None:
        return
    log_accounting_audit(
        entity=entity,
        action=AccountingAuditLog.Action.JOURNAL_ENTRY_POSTED,
        summary=f'Posted {instance.je_number}',
        user_model=kwargs.get('user_model'),
        obj=instance,
        details={
            'je_number': instance.je_number,
            'document_timestamp': instance.timestamp.isoformat() if instance.timestamp else None,
            'posted_at': instance.updated.isoformat() if instance.updated else None,
            'description': instance.description or '',
        },
    )


@receiver(journal_entry_unposted)
def audit_journal_entry_unposted(sender, instance, commited=False, **kwargs):
    if not commited:
        return
    entity = entity_for_journal_entry(instance)
    if entity is None:
        return
    log_accounting_audit(
        entity=entity,
        action=AccountingAuditLog.Action.JOURNAL_ENTRY_UNPOSTED,
        summary=f'Unposted {instance.je_number}',
        user_model=kwargs.get('user_model'),
        obj=instance,
        details={'je_number': instance.je_number},
    )


def _connect_account_audit_signals():
    AccountModel = lazy_loader.get_account_model()

    @receiver(post_save, sender=AccountModel)
    def audit_account_save(sender, instance, created, **kwargs):
        if get_country_code() != 'de':
            return
        coa = getattr(instance, 'coa_model', None)
        entity = getattr(coa, 'entity', None) if coa is not None else None
        if entity is None:
            return
        action = (
            AccountingAuditLog.Action.ACCOUNT_CREATED
            if created
            else AccountingAuditLog.Action.ACCOUNT_UPDATED
        )
        verb = 'Created' if created else 'Updated'
        log_accounting_audit(
            entity=entity,
            action=action,
            summary=f'{verb} account {instance.code}',
            obj=instance,
            details={
                'code': instance.code,
                'name': instance.name,
                'active': instance.active,
                'locked': instance.locked,
            },
        )


_connect_account_audit_signals()
