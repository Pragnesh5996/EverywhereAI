# Generated by Django 4.0.6 on 2023-03-02 05:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0006_draft'),
    ]

    operations = [
        migrations.AddField(
            model_name='submissionviewcount',
            name='media_id',
            field=models.CharField(blank=True, max_length=45, null=True),
        ),
    ]