# Generated by Django 4.0.6 on 2023-04-07 04:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0014_dailyadspendgenre_account_id_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DailyAdspendBilling',
        ),
    ]
