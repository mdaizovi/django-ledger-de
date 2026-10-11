"""
Completeness and timeliness helpers (GoBD gap 3).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Q

from django_ledger.models.utils import lazy_loader


def _cash_account_qs(entity):
    AccountModel = lazy_loader.get_account_model()

    qs = AccountModel.objects.filter(coa_model__entity=entity, active=True)
    return qs.filter(
        Q(role__in=['asset_ca_cash']) | Q(code__startswith='1200')
    )


def find_unposted_journal_entries_past_timeliness(
    entity,
    *,
    reference: date,
    max_booking_age_days: int,
    cash_max_age_days: int,
) -> Tuple[List[Any], List[Any]]:
    """
    Return (general_overdue, cash_overdue) unposted journal entries.

    *general_overdue* uses *max_booking_age_days* (commonly ~10 days).
    *cash_overdue* uses *cash_max_age_days* (commonly daily for cash/bank).
    """
    JournalEntryModel = lazy_loader.get_journal_entry_model()
    booking_cutoff = reference - timedelta(days=max_booking_age_days)
    cash_cutoff = reference - timedelta(days=cash_max_age_days)

    unposted = JournalEntryModel.objects.filter(
        ledger__entity=entity,
        posted=False,
    ).select_related('ledger')

    general = list(unposted.filter(timestamp__date__lte=booking_cutoff).order_by('timestamp')[:50])
    cash_account_ids = list(_cash_account_qs(entity).values_list('pk', flat=True))
    if not cash_account_ids:
        return general, []

    TransactionModel = lazy_loader.get_txs_model()
    cash_je_ids = TransactionModel.objects.filter(
        account_id__in=cash_account_ids,
        journal_entry__in=unposted,
    ).values_list('journal_entry_id', flat=True).distinct()

    cash_overdue = list(
        unposted.filter(pk__in=cash_je_ids, timestamp__date__lte=cash_cutoff).order_by('timestamp')[:50]
    )
    return general, cash_overdue


def find_stale_unmatched_bank_lines(
    entity,
    *,
    reference: date,
    max_age_days: int,
):
    StagedTransactionModel = lazy_loader.get_staged_txs_model()
    cutoff = reference - timedelta(days=max_age_days)
    try:
        return (
            StagedTransactionModel.objects.for_entity(entity)
            .filter(
                transaction_model__isnull=True,
                matched_transaction_model__isnull=True,
                date_posted__lte=cutoff,
            )
            .order_by('date_posted')
        )
    except Exception:
        return StagedTransactionModel.objects.none()


def find_journal_entry_number_gaps(entity, *, fiscal_year: Optional[int] = None) -> Dict[str, List[int]]:
    """
    Detect missing sequence numbers in posted journal entry numbers for the entity.

    Groups by ``{prefix}-{fiscal_year}-…`` (all but the last ``-`` segment).
    """
    JournalEntryModel = lazy_loader.get_journal_entry_model()
    qs = JournalEntryModel.objects.filter(ledger__entity=entity, posted=True).exclude(je_number='')
    if fiscal_year is not None:
        qs = qs.filter(je_number__contains=f'-{fiscal_year}-')

    sequences: dict[str, set[int]] = defaultdict(set)
    for je in qs.values_list('je_number', flat=True):
        if not je or '-' not in je:
            continue
        prefix, seq_str = je.rsplit('-', 1)
        try:
            sequences[prefix].add(int(seq_str))
        except ValueError:
            continue

    gaps: Dict[str, List[int]] = {}
    for prefix, seq_set in sequences.items():
        if len(seq_set) < 2:
            continue
        low, high = min(seq_set), max(seq_set)
        missing = [n for n in range(low, high + 1) if n not in seq_set]
        if missing:
            gaps[prefix] = missing
    return gaps
