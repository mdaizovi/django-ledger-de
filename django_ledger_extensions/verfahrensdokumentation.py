"""
Context for GoBD Verfahrensdokumentation (fill-in template in docs).
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict

from django.utils import timezone

from django_ledger_countries.settings import get_country_code, get_ledger_setting
from django_ledger_extensions.settings import get_extension_setting


def _package_version() -> str:
    try:
        return version('django-ledger')
    except PackageNotFoundError:
        return 'unknown'


def build_verfahrensdokumentation_context() -> Dict[str, Any]:
    """
    Machine-readable snapshot for Anwender-/System-/Organisationsdokumentation.
    Host apps should merge deployment-specific fields (hosting, roles, backup vendor).
    """
    return {
        'generated_at': timezone.now().isoformat(),
        'software': {
            'name': 'django-ledger-de (fork)',
            'package_version': _package_version(),
            'template_version': '1.0',
            'country_plugin': get_country_code(),
        },
        'gobd_software_controls': {
            'immutability': {
                'allow_journal_entry_unpost': get_ledger_setting('ALLOW_JOURNAL_ENTRY_UNPOST'),
                'allow_edit_posted_journal_entry': get_ledger_setting('ALLOW_EDIT_POSTED_JOURNAL_ENTRY'),
                'lock_journal_entry_on_post': get_ledger_setting('LOCK_JOURNAL_ENTRY_ON_POST'),
                'require_supporting_document_on_post': get_ledger_setting('REQUIRE_SUPPORTING_DOCUMENT_ON_POST'),
                'audit_log_model': 'django_ledger_extensions.AccountingAuditLog',
            },
            'exports': [
                'export_audit_package',
                'export_auditor_access',
                'export_steuerberater',
            ],
            'operations': [
                'accounting_health_check',
                'retention_report',
                'log_backup_verification',
                'match_bank_payments',
                'link_beleg',
            ],
            'retention_settings': {
                'retention_beleg_years': get_extension_setting('RETENTION_BELEG_YEARS'),
                'retention_books_years': get_extension_setting('RETENTION_BOOKS_YEARS'),
                'backup_verification_max_age_days': get_extension_setting('BACKUP_VERIFICATION_MAX_AGE_DAYS'),
            },
            'timeliness_settings': {
                'health_check_booking_timeliness_days': get_extension_setting(
                    'HEALTH_CHECK_BOOKING_TIMELINESS_DAYS'
                ),
                'health_check_cash_timeliness_days': get_extension_setting('HEALTH_CHECK_CASH_TIMELINESS_DAYS'),
                'health_check_bank_line_days': get_extension_setting('HEALTH_CHECK_BANK_LINE_DAYS'),
            },
        },
        'organisation_placeholders': {
            'legal_entity_name': '[FILL IN: legal name]',
            'responsible_person_finance': '[FILL IN: name, role]',
            'responsible_person_it': '[FILL IN: name, role]',
            'steuerberater_contact': '[FILL IN: name, firm]',
            'backup_provider_and_schedule': '[FILL IN: e.g. daily DB dump + weekly file sync]',
            'off_site_storage_location': '[FILL IN: region / provider]',
            'user_access_roles': '[FILL IN: who may post, who may delete drafts, admin]',
            'beleg_capture_channels': '[FILL IN: scan, email inbox, camera, API]',
        },
        'documentation_references': {
            'sphinx_template': 'docs/source/verfahrensdokumentation.rst',
            'operational_howto': 'docs/source/de_school_howto.rst',
            'regional_settings': 'docs/source/regional.rst',
        },
    }
