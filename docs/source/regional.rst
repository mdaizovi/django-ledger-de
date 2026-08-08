Regional Plugins
================

Overview
--------

This fork adds a regional plugin system on top of upstream django-ledger. The core
accounting engine (``django_ledger``) stays country-agnostic. Country-specific behavior
lives in companion apps that implement a small plugin contract.

When ``DJANGO_LEDGER_COUNTRY`` is unset or set to ``us``, behavior matches upstream
django-ledger (US chart of accounts, ``$`` currency, no supporting-document requirement).

Architecture
------------

.. code-block:: text

   django_ledger/              Core engine + hook dispatch
   django_ledger/regional/     RegionalPlugin ABC, registry, dispatch helpers
   django_ledger_extensions/   Shared infrastructure (not country-specific)
   django_ledger_countries/    Country plugin implementations
   ├── us/                     Default passthrough
   └── de/                     Germany (SKR03, VAT, Belegpflicht hooks)

Dependency direction::

   django_ledger  ←  django_ledger_extensions  ←  django_ledger_countries/<code>/

Installation
------------

Add the apps **after** ``django_ledger``:

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       'django_ledger',
       'django_ledger_extensions',
       'django_ledger_countries',
   ]

Run migrations (extensions adds new tables):

.. code-block:: shell

   python manage.py migrate

Optional S3 storage for Belege (``django-storages`` + ``boto3``):

.. code-block:: shell

   pip install -r requirements-s3.txt
   # or: pip install "django-ledger[s3]"

Configuration
-------------

Active country
~~~~~~~~~~~~~~

.. code-block:: python

   # Default (US)
   DJANGO_LEDGER_COUNTRY = 'us'

   # Germany
   DJANGO_LEDGER_COUNTRY = 'de'

Setting resolution
~~~~~~~~~~~~~~~~~~

``django_ledger_countries.settings.get_ledger_setting(name)`` resolves values in order:

1. ``DJANGO_LEDGER_{COUNTRY}_{NAME}`` — e.g. ``DJANGO_LEDGER_DE_DEFAULT_COA``
2. ``DJANGO_LEDGER_{NAME}`` — global override
3. Active country plugin defaults
4. Core ``django_ledger.settings`` fallback

Supported setting names:

- ``CURRENCY_SYMBOL``
- ``SPACED_CURRENCY_SYMBOL``
- ``REQUIRE_SUPPORTING_DOCUMENT_ON_POST``
- ``DEFAULT_COA``
- ``DEFAULT_TAX_REGIME``
- ``DEFAULT_VAT_RATE``
- ``KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT``
- ``KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT``

Germany defaults (``django_ledger_countries/de/settings.py``):

.. list-table::
   :header-rows: 1

   * - Setting
     - Default
   * - ``CURRENCY_SYMBOL``
     - ``€``
   * - ``SPACED_CURRENCY_SYMBOL``
     - ``True``
   * - ``REQUIRE_SUPPORTING_DOCUMENT_ON_POST``
     - ``True``
   * - ``DEFAULT_COA``
     - ``skr03``
   * - ``DEFAULT_TAX_REGIME``
     - ``exempt``
   * - ``DEFAULT_VAT_RATE``
     - ``0.19``
   * - ``KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT``
     - ``22000``
   * - ``KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT``
     - ``50000``

Custom SKR03 data
~~~~~~~~~~~~~~~~~

Replace or extend the starter chart in ``django_ledger_countries/de/coa/skr03.py``,
or supply a full chart at runtime:

.. code-block:: python

   DJANGO_LEDGER_DE_SKR03_DATA = [
       {
           'code': '1200',
           'role': 'asset_ca_cash',
           'balance_type': 'debit',
           'name': 'Bank',
           'name_en': 'Bank',
           'parent': None,
       },
   ]

Each account dict must include ``code``, ``role``, ``balance_type``, ``name``, and
``parent``. Roles must exist in ``django_ledger.io.roles`` (including roles registered
by the country plugin at startup).

Supporting documents
~~~~~~~~~~~~~~~~~~~~

``django_ledger_extensions.models.SupportingDocumentModel`` attaches files to any ledger
object via a generic foreign key (journal entries, bills, invoices, etc.).

When ``REQUIRE_SUPPORTING_DOCUMENT_ON_POST`` is ``True`` (Germany default), the active
country plugin rejects posting a journal entry that has no linked supporting document.

Documents are marked immutable after the journal entry is posted.

Optional S3 storage — set a bucket name and install ``requirements-s3.txt`` (``boto3`` +
``django-storages``):

.. code-block:: python

   INSTALLED_APPS += ['storages']
   DJANGO_LEDGER_AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
   # DJANGO_LEDGER_AWS_S3_REGION_NAME = 'eu-central-1'   # default
   # DJANGO_LEDGER_AWS_STORAGE_LOCATION = 'belege'       # S3 key prefix

When the bucket name is set but ``storages`` is missing from ``INSTALLED_APPS``, Django
logs a warning at startup. Without S3 settings, files use local ``MEDIA_ROOT``.

Document inbox
~~~~~~~~~~~~~~

``django_ledger_extensions.models.DocumentInboxItem`` stages receipts and PDFs before you
know which invoice, bill, or journal entry they belong to. Link from Django admin (dropdown
on save) or via ``link_beleg`` / ``link_inbox_item_to_object()``.

Entity tax profile
~~~~~~~~~~~~~~~~~~

``django_ledger_extensions.models.EntityTaxProfile`` stores per-entity tax configuration:

- ``tax_regime``: ``standard``, ``small_business``, or ``exempt``
- ``default_vat_rate``: decimal fraction (e.g. ``0.19``) — used only for ``standard``
- ``vat_id``: VAT identification number (when applicable)
- ``show_invoice_legal_notice``: display regime-specific footnote on invoices (default ``True``)
- ``invoice_legal_notice``: optional override text (Steuerberater-approved wording)

Germany creates a default profile when a new entity is saved. Defaults come from
``DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME`` (``exempt``) and ``DJANGO_LEDGER_DE_DEFAULT_VAT_RATE``
(``0.19`` for standard regime only). Invoice footnotes resolve via
``django_ledger_extensions.tax_profile.get_entity_tax_regime_behavior()``.

Tax regimes
^^^^^^^^^^^

+---------------+------------------+-----------------------------------------------+
| Regime        | Admin value      | Behaviour                                     |
+===============+==================+===============================================+
| School exempt | ``exempt``       | No VAT lines; revenue on accounts such as     |
| (§ 4 UStG)    |                  | ``8100 00``; no USt-Voranmeldung for exempt   |
|               |                  | supplies                                      |
+---------------+------------------+-----------------------------------------------+
| Kleinunterneh | ``small_business`` | No VAT lines; gross on ``8200 00`` etc.;    |
| (§ 19 UStG)   |                  | monitor turnover vs § 19 limits                 |
+---------------+------------------+-----------------------------------------------+
| Standard VAT  | ``standard``     | Splits gross to net + Vorsteuer/Umsatzsteuer  |
|               |                  | on income/expense lines; USt-Voranmeldung     |
+---------------+------------------+-----------------------------------------------+

When Finanzamt status is confirmed, change ``tax_regime`` in Django admin and run:

.. code-block:: shell

   python manage.py sync_tax_regime --entity=your-entity-slug

This re-activates the starter account subset for that regime (VAT clearing accounts
only for ``standard``, exempt revenue account only for ``exempt``, etc.).

SKR03 chart and starter accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Germany loads the full DATEV SKR03 **Schulen freie Träger** CSV (~2,700 postable
accounts). Only a **starter set** (~30 accounts for Bildungsurlaub-style schools) is
``active=True`` by default so journal-entry pickers stay manageable.

Load or refresh:

.. code-block:: shell

   python manage.py sync_skr03 --entity=your-entity-slug
   python manage.py sync_skr03 --entity=your-entity-slug --force
   python manage.py sync_skr03 --entity=your-entity-slug --merge --dry-run
   python manage.py sync_skr03 --entity=your-entity-slug --merge

Optional overrides:

.. code-block:: python

   # Custom CSV path
   DJANGO_LEDGER_DE_SKR03_CSV = '/path/to/chart.csv'

   # Or select bundled file by year (2027_Schulen_freie_Träger.csv, etc.)
   DJANGO_LEDGER_DE_SKR03_YEAR = 2027

   # Replace default active starter codes entirely
   DJANGO_LEDGER_DE_SKR03_STARTER_CODES = [
       '1200 00',  # Bank
       '8100 00',  # Steuerfreie Umsätze
       # ...
   ]

Quarterly VAT and turnover report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Management command for ELSTER planning and Kleinunternehmer turnover checks.
Uses **posted** journal entries only.

.. code-block:: shell

   python manage.py vat_quarterly_report --entity=your-entity-slug
   python manage.py vat_quarterly_report --entity=slug --year=2026 --quarter=1
   python manage.py vat_quarterly_report --entity=slug --year=2026 --quarter=1 --json

**Standard VAT** — Vorsteuer, Umsatzsteuer, and expected **Zahllast** (payment).

**Kleinunternehmer** — quarter and YTD turnover vs configurable limits
(``KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT`` / ``KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT``);
no VAT return required under § 19.

**Exempt** — turnover summary for records; no USt-Voranmeldung for exempt course fees.

Programmatic access:

.. code-block:: python

   from django_ledger_countries.de.vat.reporting import build_vat_quarterly_report

   report = build_vat_quarterly_report(entity, year=2026, quarter=1)
   print(report.net_vat_payable)   # standard regime only
   print(report.ytd_turnover)      # all regimes

**Full walkthrough:** see the :doc:`German school / Bildungsurlaub how-to <de_school_howto>` (setup, starter accounts, daily booking examples, quarterly reports, FAQ).

Plugin contract
---------------

Implement ``django_ledger.regional.base.RegionalPlugin``:

.. code-block:: python

   class RegionalPlugin(ABC):
       code: str

       def get_setting_defaults(self) -> dict: ...
       def get_default_coa(self, entity) -> list[dict] | None: ...
       def register_roles(self) -> None: ...
       def on_entity_created(self, entity) -> None: ...
       def on_coa_populated(self, entity, coa_model) -> None: ...
       def adjust_posting(self, document, transactions) -> list: ...
       def validate_journal_entry(self, journal_entry) -> None: ...
       def on_journal_entry_posted(self, journal_entry, *, committed=True) -> None: ...

Core hook sites
~~~~~~~~~~~~~~~

+---------------------------+--------------------------------------------------+
| Location                  | Dispatch                                         |
+===========================+==================================================+
| ``EntityModel.populate_   | ``get_regional_default_coa``,                    |
| default_coa()``           | ``dispatch_on_coa_populated``                    |
+---------------------------+--------------------------------------------------+
| ``AccrualMixIn.           | ``dispatch_adjust_posting``                      |
| migrate_state()``         |                                                  |
+---------------------------+--------------------------------------------------+
| ``EntityModel`` post_save | ``dispatch_on_entity_created``                   |
+---------------------------+--------------------------------------------------+
| ``journal_entry_posted``  | ``dispatch_validate_journal_entry``,             |
| signal (extensions)       | ``dispatch_on_journal_entry_posted``             |
+---------------------------+--------------------------------------------------+

Extensions models
-----------------

EntityTaxProfile
   One-to-one with ``EntityModel``. Tax regime, VAT defaults, invoice legal footnotes.

DocumentInboxItem
   Staged Beleg upload before linking to invoice, bill, or journal entry.

SupportingDocumentModel
   Generic file attachment with SHA-256 checksum and immutability after post.

ExternalPaymentRecord / ExternalRefundRecord
   Idempotent class-webapp (or other provider) payment and refund imports.

AccountingReminderRule
   Per-entity deadline reminders (USt-Voranmeldung, bookkeeping close, etc.).

AccountTranslationModel / ItemTranslationModel
   Locale-specific names (and optional regional codes for items).

Extensions management commands
------------------------------

Located under ``django_ledger_extensions/management/commands/``:

- ``link_beleg`` — link inbox item to invoice, bill, or journal entry
- ``import_external_payment`` / ``import_external_refund`` — webapp payment connectors
- ``seed_accounting_reminders`` — one-time default reminder rules per entity
- ``send_accounting_reminders`` — daily cron for deadline emails
- ``accounting_health_check`` — draft invoices, unlinked Belege, unmatched payments
- ``match_bank_payments`` — link webapp payments to bank import lines
- ``export_steuerberater`` — JSON + CSV bundle for Steuerberater handoff

Extension settings (global ``DJANGO_LEDGER_*``):

- ``REMINDER_DEFAULT_LEAD_DAYS`` (default ``14``)
- ``REMINDER_GRACE_DAYS`` (default ``3``)
- ``REMINDER_FROM_EMAIL`` (falls back to ``DEFAULT_FROM_EMAIL``)
- ``HEALTH_CHECK_STALE_DRAFT_DAYS`` (default ``14``)
- ``BANK_MATCH_AMOUNT_TOLERANCE`` (default ``0.01``)
- ``BANK_MATCH_DAY_TOLERANCE`` (default ``7``)
- ``AWS_STORAGE_BUCKET_NAME``, ``AWS_S3_REGION_NAME``, ``AWS_STORAGE_LOCATION`` — S3 Belege

**Operational walkthrough:** :doc:`de_school_howto` (install checklist, weekly Beleg admin
workflow, production deploy, cron).

Germany plugin
--------------

Located under ``django_ledger_countries/de/``:

``plugin.py``
   ``GermanyRegionalPlugin`` — wires SKR03, VAT, validation.

``coa/skr03.py`` / ``coa/datev_loader.py``
   Full SKR03 DATEV CSV loader; DATEV ``NNNN NN`` account codes preserved.

``coa/starter.py``
   Default active accounts for schools (Bildungsurlaub); filtered by tax regime.

``vat/``
   Pluggable VAT regime handlers (``standard``, ``small_business``, ``exempt``).

``vat/reporting.py``
   Quarterly Vorsteuer/Umsatzsteuer/Zahllast and turnover summaries.

``roles.py``
   Registers ``asset_ca_vat_recv`` and ``lia_cl_vat_payable`` roles.

Standard VAT splits gross income/expense lines into net + VAT clearing accounts.
``small_business`` and ``exempt`` pass transactions through unchanged and block use
of VAT clearing accounts on manual journal entries.

Management commands (``django_ledger_countries/management/commands/``):

- ``sync_skr03`` — load DATEV chart; ``--merge`` for annual CSV updates (retire missing codes)
- ``sync_tax_regime`` — re-apply active accounts after changing tax profile
- ``vat_quarterly_report`` — quarterly VAT or turnover summary

Adding a new country
--------------------

1. Create ``django_ledger_countries/<code>/plugin.py`` implementing ``RegionalPlugin``.
2. Add a branch in ``django_ledger_countries/settings._get_plugin_for_country``.
3. Optionally add ``<code>/settings.py`` with ``DJANGO_LEDGER_<CODE>_*`` defaults.
4. Register any new account roles via ``django_ledger.regional.roles.register_extra_roles``.
5. Add tests in ``django_ledger_countries/tests/test_<code>.py``.

Tests
-----

.. code-block:: shell

   python manage.py test django_ledger_countries.tests.test_regional
   python manage.py test django_ledger_countries.tests.test_germany
