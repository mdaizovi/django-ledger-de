import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('django_ledger', '0031_alter_accountmodel_role'),
        ('django_ledger_extensions', '0007_rename_django_ledg_entity__b7e4a1_idx_django_ledg_entity__001349_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountingAuditLog',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(
                    choices=[
                        ('je_posted', 'Journal entry posted'),
                        ('je_unposted', 'Journal entry unposted'),
                        ('account_created', 'Account created'),
                        ('account_updated', 'Account updated'),
                    ],
                    max_length=32,
                )),
                ('object_id', models.UUIDField(blank=True, null=True)),
                ('summary', models.CharField(max_length=512)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('content_type', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='contenttypes.contenttype',
                )),
                ('entity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='accounting_audit_logs',
                    to='django_ledger.entitymodel',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='accounting_audit_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Accounting audit log',
                'verbose_name_plural': 'Accounting audit logs',
                'ordering': ('-created',),
                'indexes': [
                    models.Index(fields=['entity', 'action', '-created'], name='django_ledg_entity__audit_idx'),
                ],
            },
        ),
    ]
