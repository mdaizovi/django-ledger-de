from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_ledger_extensions', '0005_reminders_and_payment_extensions'),
    ]

    operations = [
        migrations.AddField(
            model_name='entitytaxprofile',
            name='invoice_legal_notice',
            field=models.TextField(
                blank=True,
                default='',
                help_text=(
                    'Optional override for the invoice legal footnote. Leave blank to use '
                    'the default text for the selected tax regime (§ 4 / § 19 UStG or '
                    'standard VAT wording).'
                ),
            ),
        ),
        migrations.AddField(
            model_name='entitytaxprofile',
            name='show_invoice_legal_notice',
            field=models.BooleanField(
                default=True,
                help_text=(
                    'When enabled, customer invoices show the legal VAT footnote for the '
                    'current tax regime (or your custom text below).'
                ),
            ),
        ),
    ]
