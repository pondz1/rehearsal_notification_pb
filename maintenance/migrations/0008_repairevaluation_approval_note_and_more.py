# Generated by Django 5.2 on 2025-04-18 08:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0007_remove_maintenancerequest_approval_note_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='repairevaluation',
            name='approval_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='repairevaluation',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='repairevaluation',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_maintenance_requests', to=settings.AUTH_USER_MODEL),
        ),
    ]
