# Generated by Django 4.1.2 on 2022-11-13 16:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bank_ledger_app', '0004_employee_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='user',
        ),
    ]
