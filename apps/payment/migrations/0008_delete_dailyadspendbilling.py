# Generated by Django 4.0.6 on 2023-04-06 05:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0007_dailyadspendbilling_subscription_ad_spend_limit'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DailyAdspendBilling',
        ),
    ]
