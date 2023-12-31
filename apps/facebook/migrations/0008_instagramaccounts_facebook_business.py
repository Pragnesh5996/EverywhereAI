# Generated by Django 4.0.6 on 2023-05-15 18:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0020_alter_adscheduler_interests'),
        ('facebook', '0007_facebookpages_facebook_business'),
    ]

    operations = [
        migrations.AddField(
            model_name='instagramaccounts',
            name='facebook_business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='InstagramAccounts_facebook_business', to='common.business'),
        ),
    ]
