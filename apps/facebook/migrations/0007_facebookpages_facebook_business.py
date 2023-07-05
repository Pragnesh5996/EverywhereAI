# Generated by Django 4.0.6 on 2023-05-09 18:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0020_alter_adscheduler_interests'),
        ('facebook', '0006_remove_instagramaccounts_facebook_page_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='facebookpages',
            name='facebook_business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='facebook_pages_facebook_business', to='common.business'),
        ),
    ]