# Generated by Django 4.0.6 on 2023-04-11 06:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0009_subscription_stripe_invoice_id_alter_plan_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='ad_spend_percentage',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
