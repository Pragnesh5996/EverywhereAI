# Generated by Django 4.0.6 on 2023-03-13 05:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_webhook'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='uid',
            field=models.UUIDField(primary_key=True, serialize=False),
        ),
    ]