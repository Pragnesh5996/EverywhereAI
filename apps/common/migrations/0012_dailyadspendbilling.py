# Generated by Django 4.0.6 on 2023-04-06 05:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0011_adscheduler_ad_type_adscheduler_carousel_card_order_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyAdspendBilling',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad_platform', models.CharField(choices=[('Tiktok', 'Tiktok'), ('Facebook', 'Facebook'), ('Snap', 'Snap'), ('Google', 'Google'), ('Linkfire', 'Linkfire')], max_length=45)),
                ('spend', models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True)),
                ('date', models.DateField(blank=True, null=True)),
                ('ad_account', models.CharField(blank=True, max_length=95, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('company_uid', models.CharField(blank=True, max_length=95, null=True)),
            ],
            options={
                'db_table': 'daily_adspend_billing',
                'managed': True,
            },
        ),
    ]
