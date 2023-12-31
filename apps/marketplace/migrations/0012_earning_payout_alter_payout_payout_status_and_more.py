# Generated by Django 4.0.6 on 2023-03-14 07:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('marketplace', '0011_jobmilestones_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='earning',
            name='payout',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='earning_payout', to='marketplace.payout'),
        ),
        migrations.AlterField(
            model_name='payout',
            name='payout_status',
            field=models.CharField(blank=True, choices=[('ready_for_payout', 'ready_for_payout'), ('paid_out', 'paid_out')], default='ready_for_payout', max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='payout',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payout_user', to=settings.AUTH_USER_MODEL),
        ),
    ]
