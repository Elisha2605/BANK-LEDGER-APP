# Generated by Django 4.1.5 on 2023-01-17 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bank_ledger_app", "0009_merge_20230117_1620"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ledger",
            name="origin",
            field=models.UUIDField(),
        ),
    ]
