# Generated by Django 4.0.6 on 2023-04-27 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0017_alter_day_parting_country_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='adscheduler',
            name='auto_scheduler_json',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
