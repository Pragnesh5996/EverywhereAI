# Generated by Django 4.0.6 on 2023-03-24 05:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_company_expire_free_trial_company_is_free_trial_and_more'),
        ('payment', '0005_customer_expire_free_trial_customer_is_free_trial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payment',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='customer',
        ),
        migrations.AddField(
            model_name='payment',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.company'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.company'),
        ),
        migrations.DeleteModel(
            name='Customer',
        ),
    ]
