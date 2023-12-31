# Generated by Django 4.0.6 on 2023-03-09 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0008_payout_earning'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jobmilestones',
            name='milestone',
        ),
        migrations.AddField(
            model_name='jobmilestones',
            name='milestone_number',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobmilestones',
            name='price',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobmilestones',
            name='view_count',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
