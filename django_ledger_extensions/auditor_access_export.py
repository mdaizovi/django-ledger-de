"""
GoBD gap 5: data access for auditors and Steuerberater (CSV + description file).
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.utils.timezone import now

from django_ledger_extensions.audit_package_export import build_chart_of_accounts_export, _json_default
from django_ledger_extensions.datev_buchungsstapel import build_datev_buchungsstapel_rows
from django_ledger_extensions.steuerberater_export import (
    _period_bounds,
    build_steuerberater_bundle,
    bundle_to_csv,
)


DATEV_CSV_FIELDS = [
    'Umsatz',
    'Soll_Haben_Kennzeichen',
    'Konto',
    'Gegenkonto',
    'Belegdatum',
    'Buchungstext',
    'Belegnummer',
    'WKZ_Umsatz',
    'journal_entry_uuid',
]

KONTEN_CSV_FIELDS = [
    'code',
    'name',
    'role',
    'balance_type',
    'active',
    'locked',
    'account_uuid',
    'coa_slug',
]

BELEG_CSV_FIELDS = [
    'document_uuid',
    'document_type',
    'capture_method',
    'target_type',
    'target_id',
    'description',
    'checksum',
    'structured_checksum',
    'original_filename',
    'file',
    'structured_file',
]


def build_datenbeschreibung(
    entity,
    *,
    start: date,
    end: date,
    files: List[Dict[str, str]],
) -> Dict[str, Any]:
    return {
        'format': 'django-ledger-de-auditor-access',
        'format_version': 1,
        'language': 'de',
        'generated_at': now().isoformat(),
        'entity': {'slug': entity.slug, 'name': entity.name},
        'period': {'start': start.isoformat(), 'end': end.isoformat()},
        'encoding': 'UTF-8',
        'csv_delimiter_datev': ';',
        'csv_delimiter_standard': ',',
        'decimal_separator_datev': ',',
        'purpose': (
            'Datenzugriff für Betriebsprüfung / Steuerberater: maschinenlesbare Buchungen, '
            'Kontenrahmen, Belegindex und DATEV-orientierter Buchungsstapel.'
        ),
        'files': files,
        'column_descriptions': {
            'datev_buchungsstapel.csv': {
                'Umsatz': 'Betrag (absolut), Dezimaltrennzeichen Komma',
                'Soll_Haben_Kennzeichen': 'S = Soll, H = Haben',
                'Konto': 'DATEV Kontonummer (SKR03 ohne Leerzeichen, z. B. 120000)',
                'Gegenkonto': 'Erste Gegenbuchung derselben Journalbuchung ( bei Mehrfachzeilen prüfen)',
                'Belegdatum': 'TTMMJJJJ',
                'Buchungstext': 'Kurztext, max. 60 Zeichen',
                'Belegnummer': 'Interne Journalnummer (je_number)',
                'WKZ_Umsatz': 'Währung (EUR)',
                'journal_entry_uuid': 'Technische UUID für Rückverfolgung',
            },
            'buchungen_doppelt.csv': 'Vollständige doppelte Buchführung (eine Zeile pro Soll/Haben-TransactionModel)',
            'konten.csv': 'Kontenrahmen (SKR03) zum Importzeitpunkt',
            'belege.csv': 'Index verknüpfter Belege (Checksums, Pfade)',
            'steuerberater_bundle.json': 'JSON-Sammeldatei inkl. USt-Zusammenfassung',
        },
        'datev_import_hinweis': (
            'datev_buchungsstapel.csv ist ein vereinfachter Buchungsstapel für DATEV-Import-Assistenten '
            '(Semikolon-getrennt). Kein natives EXTF-Format. Bei komplexen Journalbuchungen mit mehr als '
            'einem Gegenkonto pro Seite Gegenkonto in DATEV prüfen oder buchungen_doppelt.csv verwenden.'
        ),
        'gobd_references': [
            'Vollständigkeit: nur gebuchte (posted) Transaktionen im Zeitraum',
            'Nachvollziehbarkeit: Belegindex + journal_entry_uuid',
            'Struktur: konten.csv dokumentiert SKR03',
        ],
    }


def _write_semicolon_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, '') for k in fieldnames})
    text = buffer.getvalue()
    path.write_text(text, encoding='utf-8')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _write_comma_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        out = {}
        for k in fieldnames:
            val = row.get(k, '')
            if hasattr(val, '__class__') and type(val).__name__ in ('Decimal',):
                val = _json_default(val)
            out[k] = val
        writer.writerow(out)
    text = buffer.getvalue()
    path.write_text(text, encoding='utf-8')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def write_auditor_access_package(
    entity,
    output_dir: Union[str, Path],
    *,
    year: int,
    month: Optional[int] = None,
) -> Path:
    start, end = _period_bounds(year, month)
    output_dir = Path(output_dir)
    suffix = f'{year}-{month:02d}' if month else str(year)
    package_dir = output_dir / f'auditor-access-{entity.slug}-{suffix}'
    package_dir.mkdir(parents=True, exist_ok=True)

    file_meta: List[Dict[str, str]] = []

    bundle = build_steuerberater_bundle(entity, year=year, month=month)
    bundle_text = json.dumps(bundle, indent=2, default=_json_default, ensure_ascii=False)
    bundle_path = package_dir / 'steuerberater_bundle.json'
    bundle_path.write_text(bundle_text, encoding='utf-8')
    file_meta.append(
        {
            'name': 'steuerberater_bundle.json',
            'sha256': hashlib.sha256(bundle_text.encode('utf-8')).hexdigest(),
            'description': 'JSON: Buchungszeilen, Belegindex, USt-Kurzbericht',
        }
    )

    journal_csv = bundle_to_csv(bundle['journal_lines'])
    journal_path = package_dir / 'buchungen_doppelt.csv'
    journal_path.write_text(journal_csv, encoding='utf-8')
    file_meta.append(
        {
            'name': 'buchungen_doppelt.csv',
            'sha256': hashlib.sha256(journal_csv.encode('utf-8')).hexdigest(),
            'description': 'Doppelte Buchführung (CSV, Komma)',
        }
    )

    datev_rows = build_datev_buchungsstapel_rows(entity, start=start, end=end)
    file_meta.append(
        {
            'name': 'datev_buchungsstapel.csv',
            'sha256': _write_semicolon_csv(package_dir / 'datev_buchungsstapel.csv', datev_rows, DATEV_CSV_FIELDS),
            'description': 'DATEV-orientierter Buchungsstapel (Semikolon, Komma-Dezimal)',
        }
    )

    coa_rows = build_chart_of_accounts_export(entity)
    file_meta.append(
        {
            'name': 'konten.csv',
            'sha256': _write_comma_csv(package_dir / 'konten.csv', coa_rows, KONTEN_CSV_FIELDS),
            'description': 'Kontenrahmen SKR03',
        }
    )

    file_meta.append(
        {
            'name': 'belege.csv',
            'sha256': _write_comma_csv(
                package_dir / 'belege.csv',
                bundle['beleg_index'],
                BELEG_CSV_FIELDS,
            ),
            'description': 'Belegindex zum Zeitraum',
        }
    )

    beschreibung = build_datenbeschreibung(entity, start=start, end=end, files=file_meta)
    beschreibung_text = json.dumps(beschreibung, indent=2, ensure_ascii=False)
    (package_dir / 'datenbeschreibung.json').write_text(beschreibung_text, encoding='utf-8')

    manifest = {
        'format': 'django-ledger-de-auditor-access-manifest',
        'format_version': 1,
        'generated_at': now().isoformat(),
        'entity': {'slug': entity.slug, 'name': entity.name},
        'period': {'start': start.isoformat(), 'end': end.isoformat()},
        'files': file_meta,
        'readme': 'Lesen Sie datenbeschreibung.json für Spaltenbedeutungen und DATEV-Hinweise.',
    }
    (package_dir / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    return package_dir
