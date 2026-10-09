import json

from django.core.management.base import BaseCommand

from django_ledger_extensions.verfahrensdokumentation import build_verfahrensdokumentation_context


class Command(BaseCommand):
    help = (
        'Print JSON context for GoBD Verfahrensdokumentation (software version, controls, settings). '
        'Merge with your hosting and organisation details from docs/source/verfahrensdokumentation.rst.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            help='Optional path to write JSON (default: stdout)',
        )

    def handle(self, *args, **options):
        payload = build_verfahrensdokumentation_context()
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        if options.get('output'):
            with open(options['output'], 'w', encoding='utf-8') as handle:
                handle.write(text)
                handle.write('\n')
            self.stdout.write(self.style.SUCCESS(f'Wrote {options["output"]}'))
        else:
            self.stdout.write(text)
