# Generated by Django 5.0.7 on 2024-10-16 19:18

import django_jsonform.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0024_delete_submissionmetadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="metadata",
            field=django_jsonform.models.fields.JSONField(blank=True, null=True),
        ),
    ]
