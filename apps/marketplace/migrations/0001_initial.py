# Generated by Django 4.0.6 on 2023-02-14 06:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BrandProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('brand_logo', models.TextField(blank=True, null=True)),
                ('brand_name', models.CharField(blank=True, max_length=60, null=True)),
                ('brand_description', models.CharField(blank=True, max_length=250, null=True)),
                ('website_url', models.TextField(blank=True, null=True)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'brand_profile',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='CreatorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('display_name', models.CharField(blank=True, max_length=60, null=True)),
                ('profile_picture', models.TextField(blank=True, null=True)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'creator_profile',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('publish_content_type', models.CharField(blank=True, choices=[('collect_video_only', 'creator_platform'), ('collect_video_and_post', 'collect_video_and_post')], max_length=45, null=True)),
                ('dimension', models.CharField(blank=True, choices=[('Vertical', 'Vertical'), ('Horizontal', 'Horizontal'), ('Square', 'Square')], max_length=100, null=True)),
                ('platforms', models.CharField(blank=True, choices=[('Tiktok', 'Tiktok'), ('Instagram', 'Instagram'), ('Snap', 'Snap')], max_length=100, null=True)),
                ('title', models.CharField(blank=True, max_length=45, null=True)),
                ('job_description', models.CharField(blank=True, max_length=400, null=True)),
                ('thumbnails', models.TextField(blank=True, null=True)),
                ('budget', models.IntegerField(blank=True, null=True)),
                ('selected_budget', models.TextField(blank=True, null=True)),
                ('job_requirements', models.JSONField(default=dict)),
                ('status', models.CharField(blank=True, choices=[('active', 'active'), ('closed', 'closed')], default='active', max_length=45, null=True)),
                ('brand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='brand_details', to='marketplace.brandprofile')),
            ],
            options={
                'db_table': 'job',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='JobCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category_name', models.CharField(blank=True, max_length=60, null=True, unique=True)),
            ],
            options={
                'db_table': 'job_category',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SocialCPM',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('platform_type', models.TextField(blank=True, null=True)),
                ('minimum', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('balanced', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('maximum', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
            ],
            options={
                'db_table': 'social_cpm',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_url', models.TextField(blank=True, null=True)),
                ('thumbnail_url', models.TextField(blank=True, null=True)),
                ('social_post_link', models.TextField(blank=True, null=True)),
                ('submission_date', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submission_detail', to='marketplace.job')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'submission',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SubmissionApprovalStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('approval_status', models.CharField(blank=True, choices=[('approval_needed', 'approval_needed'), ('creator_post_pending', 'creator_post_pending'), ('post_confirmation_pending', 'post_confirmation_pending'), ('accepted', 'accepted'), ('declined', 'declined')], default='approval_needed', max_length=45, null=True)),
                ('feedback', models.TextField(blank=True, default='', null=True)),
                ('submission', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approval_status', to='marketplace.submission')),
            ],
            options={
                'db_table': 'submission_approval_status',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SocialProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(blank=True, max_length=45, null=True)),
                ('last_name', models.CharField(blank=True, max_length=45, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('platforms', models.CharField(choices=[('Tiktok', 'Tiktok'), ('Instagram', 'Instagram'), ('Snap', 'Snap')], max_length=45)),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='creator_details', to='marketplace.creatorprofile')),
            ],
            options={
                'db_table': 'social_profile',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SocialAuthkey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('access_token', models.TextField(blank=True, null=True)),
                ('refresh_token', models.TextField(blank=True, null=True)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='marketplace.socialprofile')),
            ],
            options={
                'db_table': 'social_auth_key',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='JobMilestones',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('milestone', models.JSONField(default=dict)),
                ('job', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='milestone', to='marketplace.job')),
            ],
            options={
                'db_table': 'job_milestones',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='job',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='category_details', to='marketplace.jobcategory'),
        ),
        migrations.AddField(
            model_name='job',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_details', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='SubmissionViewCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('view_count', models.IntegerField(blank=True, null=True)),
                ('platforms', models.CharField(blank=True, max_length=100, null=True)),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job', to='marketplace.job')),
                ('submission', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='marketplace.submission')),
            ],
            options={
                'db_table': 'submission_view_count',
                'managed': True,
                'unique_together': {('job', 'platforms')},
            },
        ),
    ]
