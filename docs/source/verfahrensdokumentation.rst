Verfahrensdokumentation (GoBD template)
=======================================

This page is a **starter template** for the three documentation types expected under
GoBD (Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern, Aufzeichnungen
und Unterlagen in elektronischer Form). Adapt it for your legal entity, hosting, and
processes. Keep **dated revisions** when software or procedures change.

**Software snapshot:** django-ledger-de package version **0.8.5** (see
``build_verfahrensdokumentation_context`` for live values from your deployment).

Generate a machine-readable snapshot:

.. code-block:: bash

   python manage.py build_verfahrensdokumentation_context
   python manage.py build_verfahrensdokumentation_context --output=./verfahrensdokumentation-context.json

Cross-read :doc:`de_school_howto` for weekly workflows and :doc:`regional` for settings.

Document control
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Value
   * - Document title
     - Verfahrensdokumentation — [FILL IN: legal entity name]
   * - Version
     - 1.0 — [FILL IN: date YYYY-MM-DD]
   * - Author / owner
     - [FILL IN: finance lead]
   * - Approved by
     - [FILL IN: management / Steuerberater]
   * - Next review date
     - [FILL IN: e.g. annual or after each major release]
   * - Software version covered
     - [FILL IN: output of ``build_verfahrensdokumentation_context`` → ``software.package_version``]

1. Anwenderdokumentation (user procedures)
------------------------------------------

Describe **who does what** in plain language for staff who book, attach Belege, and run
monthly checks.

**Scope of this system**

- Double-entry ledger per entity (school / Bildungsurlaub provider).
- Customer invoices, vendor bills, bank import, journal entries, SKR03 chart (Germany).
- Supporting documents (Belege) linked to invoices, bills, and journal entries.

**Typical workflows** (detail your internal steps)

- **Incoming Beleg:** scan / email / camera → document inbox → link to bill or JE
  (``link_beleg`` or admin). Set capture method.
- **Outgoing invoice:** draft → approve → post; attach contract or calculation if required.
- **Bank:** import statement → match webapp payments (``match_bank_payments``) → commit to ledger.
- **Month-end:** ``accounting_health_check``; clear warnings; ``export_steuerberater`` or
  ``export_auditor_access`` for advisor handoff.
- **Corrections:** do **not** edit posted entries (DE defaults); post reversing or correcting JEs.

**Roles and access** — [FILL IN]

.. list-table::
   :header-rows: 1

   * - Role
     - Permissions
     - Tasks
   * - Bookkeeper
     - [FILL IN]
     - Draft bills/JEs, attach Belege
   * - Approver
     - [FILL IN]
     - Approve invoices/bills, post
   * - Admin
     - [FILL IN]
     - User management, read-only audit log, backup log

2. Systemdokumentation (IT / software)
---------------------------------------

Describe **how the application is built, deployed, and secured**.

**Components** — [FILL IN for your host]

.. list-table::
   :header-rows: 1

   * - Layer
     - Technology
     - Notes
   * - Application
     - Django + django-ledger-de fork
     - ``DJANGO_LEDGER_COUNTRY=de``
   * - Database
     - [FILL IN: PostgreSQL version]
     - Backups: [FILL IN: schedule]
   * - File storage (Belege)
     - [FILL IN: local / S3]
     - Immutable checksums on supporting documents
   * - Background jobs
     - [FILL IN: cron for health check, reminders, backups]

**GoBD-relevant software behaviour** (implemented in this fork)

- Posted JE immutability, auto-lock, append-only ``AccountingAuditLog``.
- Beleg checksums, capture method, e-invoice structured file field.
- Exports: ``export_audit_package``, ``export_auditor_access``, ``export_steuerberater``.
- Retention: ``retain_until`` on Belege; ``retention_report``; ``BackupVerificationLog``.
- Timeliness checks: ``accounting_health_check`` (configurable thresholds).

**Interfaces** — [FILL IN]

- Bank import format: [FILL IN]
- Webapp payment import: ``import_external_payment`` / ``import_external_refund``
- DATEV: Buchungsstapel CSV via ``export_auditor_access`` (confirm mapping with Steuerberater)

**Change management**

- Track django-ledger-de **git tag / commit** deployed to production.
- After upgrade: ``migrate``, smoke-test post + export, update this document version.

3. Organisationsdokumentation (internal control)
--------------------------------------------------

Describe **internal controls**, retention, and availability obligations.

**Retention policy**

- Belege: **8 years** default (``RETENTION_BELEG_YEARS``); bank statements / contracts **10 years**.
- ``retain_until`` is earliest **review** date — legal holds or audits may require longer retention.
- No automatic deletion in software; destruction only after written policy + legal review.

**Backups and availability**

- Production backup schedule: [FILL IN]
- Off-site copy: [FILL IN] — log with ``log_backup_verification`` or admin **Backup verification log**.
- Restore test frequency: [FILL IN] — set ``--restore-tested`` when performed.
- ``accounting_health_check`` warns if verification is older than ``BACKUP_VERIFICATION_MAX_AGE_DAYS``.

**Segregation of duties** — [FILL IN]

- Who can post vs approve vs administer users.
- Who can delete **draft** objects vs who cannot delete Belege within retention.

**Evidence for tax audit / Betriebsprüfung**

- Period exports: audit package + auditor access folder + Steuerberater JSON.
- Audit log in admin for posting and chart changes.
- This Verfahrensdokumentation + revision history stored with company records.

Revision log
------------

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Date
     - Version
     - Summary of change
   * - [FILL IN]
     - 1.0
     - Initial template populated for django-ledger-de GoBD extensions
