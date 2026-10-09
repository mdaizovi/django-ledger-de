from django.test import SimpleTestCase

from django_ledger_extensions.verfahrensdokumentation import build_verfahrensdokumentation_context


class VerfahrensdokumentationContextTest(SimpleTestCase):
    def test_build_context_has_required_sections(self):
        ctx = build_verfahrensdokumentation_context()
        self.assertIn('software', ctx)
        self.assertIn('gobd_software_controls', ctx)
        self.assertIn('export_audit_package', ctx['gobd_software_controls']['exports'])
        self.assertIn('retention_beleg_years', ctx['gobd_software_controls']['retention_settings'])
