# Generated by Django 4.0.6 on 2023-02-24 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facebook', '0002_facebookpages_room_left'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facebookpages',
            name='room_left',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
