# Generated by Django 4.0.6 on 2023-03-24 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0010_alter_adscheduler_accelerated_spend_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='adscheduler',
            name='ad_type',
            field=models.CharField(blank=True, default='Single', max_length=456, null=True),
        ),
        migrations.AddField(
            model_name='adscheduler',
            name='carousel_card_order',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='adscheduler',
            name='max_cards_per_carousel',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
