"""
GoBD gap 4: structure and auditability — machine-readable export bundle.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from django.utils.timezone import now

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.steuerberater_export import _period_bounds


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f'Object of type {type(value)!r} is not JSON serializable')


def _write_json(path: Path, payload: Any) -> str:
    text = json.dumps(payload, indent=2, default=_json_default, ensure_ascii=False)
    path.write_text(text, encoding='utf-8')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _json_default(row[k]) if isinstance(row.get(k), (Decimal, date, datetime, UUID)) else row.get(k, '') for k in fieldnames})
    text = buffer.getvalue()
    path.write_text(text, encoding='utf-8')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build_chart_of_accounts_export(entity) -> List[Dict[str, Any]]:
    """Documented SKR/chart structure for auditors (all accounts in default CoA)."""
    coa = entity.default_coa
    if coa is None:
        return []
    qs = coa.accountmodel_set.all().order_by('code')
    rows = []
    for account in qs:
        rows.append(
            {
                'account_uuid': account.uuid,
                'code': account.code,
                'name': account.name,
                'role': account.role,
                'balance_type': account.balance_type,
                'active': account.active,
                'locked': account.locked,
                'coa_slug': coa.slug,
            }
        )
    return rows


def build_journal_chronological_export(entity, *, start: date, end: date) -> List[Dict[str, Any]]:
    """Chronological journal (posted transactions)."""
    TransactionModel = lazy_loader.get_txs_model()
    txs = (
        TransactionModel.objects.for_entity(entity)
        .posted()
        .from_date(start)
        .to_date(end)
        .select_related('account', 'journal_entry', 'journal_entry__ledger')
        .order_by('journal_entry__timestamp', 'journal_entry__je_number', 'account__code')
    )
    lines = []
    for tx in txs:
        je = tx.journal_entry
        lines.append(
            {
                'date': je.timestamp.date().isoformat(),
                'je_uuid': str(je.uuid),
                'je_number': je.je_number,
                'ledger': je.ledger.name,
                'account_code': tx.account.code,
                'account_name': tx.account.name,
                'tx_type': tx.tx_type,
                'amount': tx.amount,
                'description': tx.description or je.description or '',
            }
        )
    return lines


def build_account_ledger_export(entity, *, start: date, end: date) -> List[Dict[str, Any]]:
    """Account view: same transactions grouped and sorted by account code."""
    lines = build_journal_chronological_export(entity, start=start, end=end)
    return sorted(lines, key=lambda row: (row['account_code'], row['date'], row['je_number']))


def build_trial_balance_export(entity, *, start: date, end: date) -> List[Dict[str, Any]]:
    io_digest = entity.digest(
        entity_model=entity.slug,
        from_date=start,
        to_date=end,
    )
    return list(io_digest.IO_DATA.get('accounts') or [])


def build_financial_statements_export(entity, *, start: date, end: date) -> Dict[str, Any]:
    bs_digest = entity.digest_balance_sheet(to_date=end)
    is_digest = entity.digest_income_statement(from_date=start, to_date=end)
    return {
        'period': {'start': start.isoformat(), 'end': end.isoformat()},
        'balance_sheet': bs_digest.get_balance_sheet_data(raise_exception=False),
        'income_statement': is_digest.get_income_statement_data(raise_exception=False),
    }


def build_open_items_export(entity) -> Dict[str, Any]:
    InvoiceModel = lazy_loader.get_invoice_model()
    BillModel = lazy_loader.get_bill_model()
    open_invoices = InvoiceModel.objects.filter(
        ledger__entity=entity,
        invoice_status__in=['approved', 'draft'],
    ).exclude(amount_due=0)
    open_bills = BillModel.objects.filter(
        ledger__entity=entity,
        bill_status='approved',
    )
    return {
        'invoices': [
            {
                'uuid': str(inv.uuid),
                'invoice_number': inv.invoice_number,
                'status': inv.invoice_status,
                'amount_due': inv.amount_due,
                'updated': inv.updated.date().isoformat() if inv.updated else None,
            }
            for inv in open_invoices.order_by('-updated')[:500]
        ],
        'bills': [
            {
                'uuid': str(bill.uuid),
                'bill_number': bill.bill_number,
                'status': bill.bill_status,
                'amount_due': bill.amount_due,
                'updated': bill.updated.date().isoformat() if bill.updated else None,
            }
            for bill in open_bills.order_by('-updated')[:500]
        ],
    }


def build_audit_package_manifest(
    entity,
    *,
    start: date,
    end: date,
    files: List[Dict[str, str]],
) -> Dict[str, Any]:
    return {
        'format': 'django-ledger-de-audit-package',
        'format_version': 1,
        'generated_at': now().isoformat(),
        'entity': {'slug': entity.slug, 'name': entity.name},
        'period': {'start': start.isoformat(), 'end': end.isoformat()},
        'purpose': (
            'GoBD-oriented structure and auditability export: chart of accounts, '
            'chronological journal, account ledger, trial balance, financial statements, open items.'
        ),
        'files': files,
        'notes': [
            'Re-run export for the same period to verify figures match (deterministic posted data).',
            'UI reports: ledger journal list + account transaction views mirror journal/account CSV files.',
        ],
    }


def write_audit_package(
    entity,
    output_dir: Union[str, Path],
    *,
    year: int,
    month: Optional[int] = None,
) -> Path:
    start, end = _period_bounds(year, month)
    output_dir = Path(output_dir)
    suffix = f'{year}-{month:02d}' if month else str(year)
    package_dir = output_dir / f'audit-package-{entity.slug}-{suffix}'
    package_dir.mkdir(parents=True, exist_ok=True)

    file_meta: List[Dict[str, str]] = []

    coa_rows = build_chart_of_accounts_export(entity)
    file_meta.append(
        {
            'name': 'chart_of_accounts.json',
            'sha256': _write_json(package_dir / 'chart_of_accounts.json', coa_rows),
            'description': 'Full chart of accounts (SKR/documented structure).',
        }
    )
    file_meta.append(
        {
            'name': 'chart_of_accounts.csv',
            'sha256': _write_csv(
                package_dir / 'chart_of_accounts.csv',
                coa_rows,
                ['code', 'name', 'role', 'balance_type', 'active', 'locked', 'account_uuid', 'coa_slug'],
            ),
            'description': 'Chart of accounts (CSV).',
        }
    )

    journal_rows = build_journal_chronological_export(entity, start=start, end=end)
    journal_fields = [
        'date', 'je_number', 'je_uuid', 'ledger', 'account_code', 'account_name', 'tx_type', 'amount', 'description',
    ]
    file_meta.append(
        {
            'name': 'journal_chronological.csv',
            'sha256': _write_csv(package_dir / 'journal_chronological.csv', journal_rows, journal_fields),
            'description': 'Chronological journal (posted transactions).',
        }
    )
    file_meta.append(
        {
            'name': 'journal_chronological.json',
            'sha256': _write_json(package_dir / 'journal_chronological.json', journal_rows),
            'description': 'Chronological journal (JSON).',
        }
    )

    account_rows = build_account_ledger_export(entity, start=start, end=end)
    file_meta.append(
        {
            'name': 'account_ledger.csv',
            'sha256': _write_csv(package_dir / 'account_ledger.csv', account_rows, journal_fields),
            'description': 'Account view (transactions by account code).',
        }
    )

    trial_balance = build_trial_balance_export(entity, start=start, end=end)
    file_meta.append(
        {
            'name': 'trial_balance.json',
            'sha256': _write_json(package_dir / 'trial_balance.json', trial_balance),
            'description': 'Trial balance / account balances for the period.',
        }
    )

    financials = build_financial_statements_export(entity, start=start, end=end)
    file_meta.append(
        {
            'name': 'financial_statements.json',
            'sha256': _write_json(package_dir / 'financial_statements.json', financials),
            'description': 'Balance sheet (as-of period end) and income statement.',
        }
    )

    open_items = build_open_items_export(entity)
    file_meta.append(
        {
            'name': 'open_items.json',
            'sha256': _write_json(package_dir / 'open_items.json', open_items),
            'description': 'Open invoices and approved unpaid bills.',
        }
    )

    manifest = build_audit_package_manifest(entity, start=start, end=end, files=file_meta)
    _write_json(package_dir / 'manifest.json', manifest)

    return package_dir
