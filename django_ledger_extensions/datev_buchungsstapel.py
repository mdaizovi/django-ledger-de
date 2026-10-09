"""
DATEV-oriented Buchungsstapel rows from posted journal entries (GoBD gap 5).

This is a pragmatic CSV subset for Steuerberater / DATEV import wizards — not a full
EXTF binary export. See datenbeschreibung.json in the auditor access package.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from django_ledger.models.utils import lazy_loader


def datev_kontonummer(account_code: str) -> str:
    """DATEV numeric account: ``1200 00`` → ``120000``."""
    return account_code.replace(' ', '').strip()


def format_datev_amount(amount: Decimal) -> str:
    """German decimal comma, two fraction digits."""
    return f'{amount:.2f}'.replace('.', ',')


def _buchungstext(tx, je) -> str:
    text = tx.description or je.description or ''
    return text.replace('\n', ' ')[:60]


def build_datev_buchungsstapel_rows(entity, *, start: date, end: date) -> List[Dict[str, Any]]:
    """
    One CSV row per posted transaction line.

    *Gegenkonto* is the first account on the opposite side of the same journal entry.
    Complex multi-line entries may need manual review in DATEV (documented in export README).
    """
    TransactionModel = lazy_loader.get_txs_model()
    txs = (
        TransactionModel.objects.for_entity(entity)
        .posted()
        .from_date(start)
        .to_date(end)
        .select_related('account', 'journal_entry', 'journal_entry__ledger')
        .order_by('journal_entry__timestamp', 'journal_entry__je_number')
    )

    by_je: dict = defaultdict(list)
    for tx in txs:
        by_je[tx.journal_entry_id].append(tx)

    rows: List[Dict[str, Any]] = []
    for je_id, je_txs in by_je.items():
        je = je_txs[0].journal_entry
        debits = [t for t in je_txs if t.tx_type == 'debit']
        credits = [t for t in je_txs if t.tx_type == 'credit']
        default_contra_for_debit = credits[0].account.code if credits else ''
        default_contra_for_credit = debits[0].account.code if debits else ''

        belegdatum = je.timestamp.strftime('%d%m%Y')

        for tx in debits:
            rows.append(
                {
                    'Umsatz': format_datev_amount(tx.amount),
                    'Soll_Haben_Kennzeichen': 'S',
                    'Konto': datev_kontonummer(tx.account.code),
                    'Gegenkonto': datev_kontonummer(default_contra_for_debit),
                    'Belegdatum': belegdatum,
                    'Buchungstext': _buchungstext(tx, je),
                    'Belegnummer': je.je_number,
                    'WKZ_Umsatz': 'EUR',
                    'journal_entry_uuid': str(je.uuid),
                }
            )
        for tx in credits:
            rows.append(
                {
                    'Umsatz': format_datev_amount(tx.amount),
                    'Soll_Haben_Kennzeichen': 'H',
                    'Konto': datev_kontonummer(tx.account.code),
                    'Gegenkonto': datev_kontonummer(default_contra_for_credit),
                    'Belegdatum': belegdatum,
                    'Buchungstext': _buchungstext(tx, je),
                    'Belegnummer': je.je_number,
                    'WKZ_Umsatz': 'EUR',
                    'journal_entry_uuid': str(je.uuid),
                }
            )
    return rows
