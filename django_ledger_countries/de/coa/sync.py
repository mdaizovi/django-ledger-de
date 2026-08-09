"""
Merge DATEV SKR03 CSV exports into an existing chart of accounts.

Used for annual Branchenpaket updates: add new account codes, refresh names,
and retire codes removed from the new export (``active=False`` — never delete).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from django_ledger.models.accounts import AccountModel
from django_ledger_extensions.models import AccountTranslationModel

from django_ledger_countries.de.coa.datev_loader import (
    get_skr03_edition_label,
    load_datev_coa_rows,
    resolve_csv_path,
)


@dataclass
class Skr03MergeResult:
    edition: str
    csv_path: str
    added: int = 0
    updated: int = 0
    retired: int = 0
    unchanged: int = 0
    active_count: int = 0
    dry_run: bool = False

    @property
    def total_in_csv(self) -> int:
        return self.added + self.updated + self.unchanged


def format_merge_report(result: Skr03MergeResult) -> str:
    prefix = 'DRY RUN — ' if result.dry_run else ''
    lines = [
        (
            f'{prefix}SKR03 merge ({result.edition}): '
            f'+{result.added} added, {result.updated} updated, '
            f'{result.retired} retired, {result.unchanged} unchanged'
        ),
        f'CSV: {result.csv_path}',
    ]
    if not result.dry_run:
        lines.append(f'Active accounts after merge: {result.active_count}')
    return '\n'.join(lines)


def record_skr03_edition(entity, csv_path: Path) -> None:
    meta = dict(entity.meta or {})
    meta['skr03_edition'] = get_skr03_edition_label(csv_path)
    meta['skr03_csv_path'] = str(csv_path)
    meta['skr03_synced_at'] = datetime.now(timezone.utc).isoformat()
    entity.meta = meta
    entity.save(update_fields=['meta', 'updated'])


def upsert_account_translations(account: AccountModel, row: dict) -> None:
    AccountTranslationModel.objects.update_or_create(
        account=account,
        locale='de',
        defaults={'name': row['name']},
    )
    name_en = (row.get('name_en') or '').strip()
    if name_en:
        AccountTranslationModel.objects.update_or_create(
            account=account,
            locale='en',
            defaults={'name': name_en},
        )


def merge_skr03_chart(
    entity,
    coa_model,
    *,
    csv_path: Optional[Path] = None,
    rows: Optional[List[dict]] = None,
    dry_run: bool = False,
    retire_missing: bool = True,
) -> Skr03MergeResult:
    """
    Upsert SKR03 accounts from a DATEV CSV into *coa_model*.

    - New codes are inserted (``active`` from starter/regime defaults in the loader).
    - Existing codes get updated names and translations; ``active`` is preserved.
    - Codes in the DB but absent from the CSV are retired (``active=False``).
    """
    path = csv_path or resolve_csv_path()
    edition = get_skr03_edition_label(path)
    row_list = rows if rows is not None else load_datev_coa_rows(path)
    csv_codes = {row['code'] for row in row_list}

    existing_by_code = {
        account.code: account
        for account in coa_model.accountmodel_set.not_coa_root()
    }

    result = Skr03MergeResult(
        edition=edition,
        csv_path=str(path),
        dry_run=dry_run,
    )
    root_account_qs = coa_model.get_coa_root_accounts_qs()

    for row in row_list:
        code = row['code']
        existing = existing_by_code.get(code)
        if existing is None:
            result.added += 1
            if not dry_run:
                account = AccountModel(
                    code=code,
                    name=row['name'],
                    role=row['role'],
                    balance_type=row['balance_type'],
                    active=row.get('active', False),
                    coa_model=coa_model,
                )
                account.clean()
                account = coa_model.insert_account(account, root_account_qs=root_account_qs)
                upsert_account_translations(account, row)
            continue

        name_changed = existing.name != row['name']
        role_changed = existing.role != row['role']
        balance_changed = existing.balance_type != row['balance_type']
        if name_changed or role_changed or balance_changed:
            result.updated += 1
            if not dry_run:
                update_fields = ['updated']
                if name_changed:
                    existing.name = row['name']
                    update_fields.append('name')
                if role_changed:
                    existing.role = row['role']
                    update_fields.append('role')
                if balance_changed:
                    existing.balance_type = row['balance_type']
                    update_fields.append('balance_type')
                existing.save(update_fields=update_fields)
                upsert_account_translations(existing, row)
        else:
            result.unchanged += 1
            if not dry_run:
                upsert_account_translations(existing, row)

    if retire_missing:
        for code, account in existing_by_code.items():
            if code in csv_codes:
                continue
            if not account.active:
                continue
            result.retired += 1
            if not dry_run:
                account.active = False
                account.save(update_fields=['active', 'updated'])

    if dry_run:
        result.active_count = sum(1 for account in existing_by_code.values() if account.active)
    else:
        record_skr03_edition(entity, path)
        result.active_count = coa_model.accountmodel_set.not_coa_root().filter(active=True).count()

    return result
