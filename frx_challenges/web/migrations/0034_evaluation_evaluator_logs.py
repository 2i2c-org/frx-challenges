# Generated by Django 5.1.2 on 2024-11-23 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0033_rename_date_created_submission_last_updated_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="evaluation",
            name="evaluator_logs",
            field=models.TextField(blank=True, null=True),
        ),
    ]