# Generated by Django 4.0.6 on 2023-02-28 09:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0003_rename_content_url_submission_video_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialBusiness',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('fb_page_id', models.CharField(blank=True, max_length=45, null=True)),
                ('business_id', models.CharField(blank=True, max_length=45, null=True)),
                ('organization_id', models.CharField(blank=True, max_length=45, null=True)),
                ('business_center_id', models.CharField(blank=True, max_length=45, null=True)),
                ('name', models.CharField(blank=True, max_length=45, null=True)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='social_profile', to='marketplace.socialprofile')),
            ],
            options={
                'db_table': 'social_business',
                'managed': True,
            },
        ),
    ]
