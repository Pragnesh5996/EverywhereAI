# Generated by Django 4.0.6 on 2023-02-14 06:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AdAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account_id', models.CharField(blank=True, max_length=45, null=True)),
                ('account_name', models.CharField(blank=True, max_length=45, null=True)),
                ('active', models.PositiveSmallIntegerField(choices=[(0, 'no'), (1, 'pending'), (2, 'yes')], default=0)),
                ('live_ad_account_status', models.CharField(blank=True, max_length=45, null=True)),
                ('timezone', models.CharField(blank=True, max_length=100, null=True)),
                ('currency', models.CharField(blank=True, max_length=100, null=True)),
                ('last_28days_spend_status', models.PositiveSmallIntegerField(choices=[(0, 'Not Started'), (1, 'InProgress'), (2, 'Failed'), (3, 'Success')], default=0)),
                ('utc_offset', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AdAdsets',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('adset_id', models.CharField(blank=True, max_length=95, null=True)),
                ('adset_name', models.TextField(blank=True, null=True)),
                ('target_country', models.CharField(blank=True, max_length=95, null=True)),
                ('landingpage', models.CharField(blank=True, max_length=450, null=True)),
                ('bid', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('budget', models.IntegerField(blank=True, null=True)),
                ('max_budget', models.IntegerField(blank=True, null=True)),
                ('active', models.CharField(blank=True, max_length=45, null=True)),
                ('last_checked', models.DateTimeField(blank=True, null=True)),
                ('ignore_until', models.DateTimeField(blank=True, null=True)),
                ('manual_change_updated', models.CharField(blank=True, max_length=45, null=True)),
                ('manual_change_reason', models.TextField(blank=True, null=True)),
                ('maturity', models.CharField(blank=True, max_length=45, null=True)),
                ('strategy', models.CharField(blank=True, max_length=45, null=True)),
                ('max_cpc', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('updated_volume_adset', models.DateField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ad_adsets',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='AdLogs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('campaign_id', models.BigIntegerField(blank=True, null=True)),
                ('adset_id', models.BigIntegerField(blank=True, null=True)),
                ('old_bid', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('new_bid', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('loggedon', models.DateTimeField(blank=True, db_column='loggedOn', null=True)),
                ('email_sent', models.CharField(blank=True, max_length=45, null=True)),
            ],
            options={
                'db_table': 'ad_logs',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='AdScheduler',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uploadsesid', models.CharField(blank=True, db_column='uploadSesId', max_length=450, null=True)),
                ('platform', models.CharField(blank=True, max_length=95, null=True)),
                ('type_post', models.CharField(blank=True, max_length=95, null=True)),
                ('placement_type', models.CharField(blank=True, max_length=45, null=True)),
                ('campaign_name', models.CharField(blank=True, max_length=100, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('adaccount_id', models.CharField(blank=True, max_length=150, null=True)),
                ('extra_name', models.CharField(blank=True, max_length=450, null=True)),
                ('bundle_countries', models.CharField(blank=True, max_length=45, null=True)),
                ('countries', models.TextField(blank=True, null=True)),
                ('age_range', models.CharField(blank=True, max_length=45, null=True)),
                ('budget', models.IntegerField(blank=True, null=True)),
                ('max_budget', models.IntegerField(blank=True, null=True)),
                ('dayparting', models.CharField(blank=True, max_length=336, null=True)),
                ('language', models.CharField(blank=True, max_length=56, null=True)),
                ('landingpage_url', models.TextField(blank=True, null=True)),
                ('heading', models.CharField(blank=True, max_length=450, null=True)),
                ('caption', models.TextField(blank=True, null=True)),
                ('bid_strategy', models.CharField(blank=True, max_length=45, null=True)),
                ('bid', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('objective', models.CharField(blank=True, max_length=45, null=True)),
                ('pixel_id', models.CharField(blank=True, max_length=45, null=True)),
                ('event_type', models.CharField(blank=True, max_length=45, null=True)),
                ('app_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('application_id', models.CharField(blank=True, max_length=45, null=True)),
                ('custom_audiences', models.TextField(blank=True, null=True)),
                ('ignore_until', models.DateTimeField(blank=True, null=True)),
                ('scheduled_for', models.DateTimeField(blank=True, null=True)),
                ('strategy', models.CharField(blank=True, max_length=45, null=True)),
                ('interests', models.CharField(blank=True, max_length=256, null=True)),
                ('accelerated_spend', models.CharField(blank=True, max_length=45, null=True)),
                ('created_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('completed', models.CharField(blank=True, default='No', max_length=45, null=True)),
                ('user_id', models.CharField(blank=True, max_length=45, null=True)),
                ('authkey_email_user', models.CharField(blank=True, max_length=95, null=True)),
                ('tiktok_identity_type', models.CharField(blank=True, max_length=45, null=True)),
                ('tiktok_identity_id', models.CharField(blank=True, max_length=450, null=True)),
                ('company_name', models.CharField(blank=True, max_length=450, null=True)),
            ],
            options={
                'db_table': 'ad_scheduler',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='AdsetInsights',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('platform', models.CharField(blank=True, max_length=45, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('adset_id', models.CharField(blank=True, max_length=95, null=True)),
                ('cpc', models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True)),
                ('spend', models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True)),
                ('date', models.DateField(blank=True, null=True)),
                ('date_updated', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'adset_insights',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='BibleClientId',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client_id', models.CharField(blank=True, max_length=450, null=True)),
                ('date_generated', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'bible_client_id',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='CustomAudiences',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('platform', models.CharField(blank=True, max_length=45, null=True)),
                ('account_id', models.CharField(blank=True, max_length=45, null=True)),
                ('audience_id', models.CharField(blank=True, max_length=95, null=True)),
                ('name', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('added', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'custom_audiences',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='CustomConversionEvents',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('platform', models.CharField(blank=True, max_length=45, null=True)),
                ('account_id', models.CharField(blank=True, max_length=45, null=True)),
                ('event_id', models.CharField(blank=True, max_length=45, null=True)),
                ('pixel_id', models.CharField(blank=True, max_length=45, null=True)),
                ('name', models.CharField(blank=True, max_length=45, null=True)),
                ('external_action', models.CharField(blank=True, max_length=45, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('rules', models.TextField(blank=True, null=True)),
                ('added', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'custom_conversion_events',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Logs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('component', models.CharField(blank=True, max_length=45, null=True)),
                ('type', models.CharField(blank=True, max_length=45, null=True)),
                ('message', models.TextField(blank=True, null=True)),
                ('datelogged', models.DateTimeField(blank=True, db_column='dateLogged', null=True)),
            ],
            options={
                'db_table': 'logs',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Pixels',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('advertiser_id', models.CharField(blank=True, max_length=95, null=True)),
                ('pixel_id', models.CharField(blank=True, max_length=450, null=True)),
                ('name', models.CharField(blank=True, max_length=450, null=True)),
                ('platform', models.CharField(blank=True, max_length=45, null=True)),
                ('date_added', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'pixels',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(blank=True, max_length=45, null=True)),
                ('last_name', models.CharField(blank=True, max_length=45, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('ad_platform', models.CharField(choices=[('Tiktok', 'Tiktok'), ('Facebook', 'Facebook'), ('Snap', 'Snap'), ('Google', 'Google'), ('Linkfire', 'Linkfire')], max_length=45)),
                ('active', models.CharField(blank=True, default='Yes', max_length=5, null=True)),
                ('is_connection_established', models.BooleanField(default=True)),
                ('connection_error_message', models.TextField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ProfitMargins',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('profit_margin', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'profit_margins',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='RateLimits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('platform', models.CharField(blank=True, max_length=45, null=True)),
                ('type', models.CharField(blank=True, max_length=45, null=True)),
                ('subtype', models.CharField(blank=True, max_length=45, null=True)),
                ('account_id', models.CharField(blank=True, max_length=45, null=True)),
                ('call_count', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('total_cputime', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('total_time', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('call_time', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'rate_limits',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SchedulePresets',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('preset_name', models.CharField(max_length=256)),
            ],
            options={
                'db_table': 'schedule_presets',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ScraperGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group_name', models.CharField(blank=True, max_length=95, null=True)),
                ('number_1day_data_map', models.CharField(blank=True, db_column='1day_data_map', max_length=95, null=True)),
                ('number_7day_data_map', models.CharField(blank=True, db_column='7day_data_map', max_length=95, null=True)),
                ('number_28day_data_map', models.CharField(blank=True, db_column='28day_data_map', max_length=95, null=True)),
                ('playlist_data_map', models.CharField(blank=True, max_length=95, null=True)),
                ('inflation_value', models.IntegerField(blank=True, null=True)),
                ('data_days', models.IntegerField(blank=True, null=True)),
                ('facebook_heading', models.CharField(blank=True, max_length=95, null=True)),
                ('facebook_caption', models.TextField(blank=True, null=True)),
                ('facebook_button', models.CharField(blank=True, max_length=95, null=True)),
                ('facebook_agerange', models.CharField(blank=True, max_length=255, null=True)),
                ('tiktok_caption', models.CharField(blank=True, max_length=100, null=True)),
                ('tiktok_button', models.CharField(blank=True, max_length=95, null=True)),
                ('tiktok_agerange', models.CharField(blank=True, max_length=255, null=True)),
                ('snap_caption', models.CharField(blank=True, max_length=100, null=True)),
                ('snap_button', models.CharField(blank=True, max_length=95, null=True)),
                ('snap_agerange', models.CharField(blank=True, max_length=255, null=True)),
                ('profile_url', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'scraper_groups',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Users',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('idusers', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=45, null=True)),
                ('password', models.CharField(max_length=128)),
                ('email', models.CharField(blank=True, max_length=45, null=True)),
                ('last_loggedin', models.DateTimeField(blank=True, null=True)),
                ('createdon', models.DateTimeField(blank=True, db_column='createdOn', null=True)),
            ],
            options={
                'db_table': 'users',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SpendData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('country', models.CharField(blank=True, max_length=95, null=True)),
                ('spend', models.DecimalField(blank=True, decimal_places=5, max_digits=11, null=True)),
                ('data_days', models.IntegerField(blank=True, null=True)),
                ('date_updated', models.DateTimeField()),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='spend_data_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'spend_data',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='SchedulePresetsSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('preset_json_data', models.JSONField(blank=True, null=True)),
                ('schedule_preset_id_old', models.IntegerField(blank=True, null=True)),
                ('platform', models.CharField(blank=True, max_length=95, null=True)),
                ('campaign_name', models.CharField(blank=True, max_length=100, null=True)),
                ('campaign_type', models.CharField(blank=True, max_length=256, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('adaccount_id', models.CharField(blank=True, max_length=150, null=True)),
                ('extra_name', models.CharField(blank=True, max_length=450, null=True)),
                ('bundle_countries', models.CharField(blank=True, max_length=45, null=True)),
                ('countries', models.TextField(blank=True, null=True)),
                ('age_range', models.CharField(blank=True, max_length=45, null=True)),
                ('budget', models.IntegerField(blank=True, null=True)),
                ('max_budget', models.IntegerField(blank=True, null=True)),
                ('heading', models.CharField(blank=True, max_length=450, null=True)),
                ('caption', models.TextField(blank=True, null=True)),
                ('bid_strategy', models.CharField(blank=True, max_length=45, null=True)),
                ('bid', models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ('objective', models.CharField(blank=True, max_length=45, null=True)),
                ('pixel_id', models.CharField(blank=True, max_length=45, null=True)),
                ('event_type', models.CharField(blank=True, max_length=45, null=True)),
                ('app_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('application_id', models.CharField(blank=True, max_length=45, null=True)),
                ('custom_audiences', models.TextField(blank=True, null=True)),
                ('scheduled_for', models.DateTimeField(blank=True, null=True)),
                ('strategy', models.CharField(blank=True, max_length=45, null=True)),
                ('interests', models.CharField(blank=True, max_length=256, null=True)),
                ('search_interest', models.CharField(blank=True, max_length=128, null=True)),
                ('completed', models.CharField(blank=True, max_length=45, null=True)),
                ('user_id', models.CharField(blank=True, max_length=45, null=True)),
                ('authkey_email_user', models.CharField(blank=True, max_length=256, null=True)),
                ('maxads_per_adgroup', models.CharField(blank=True, max_length=256, null=True)),
                ('campaign_auto_generate', models.CharField(blank=True, max_length=256, null=True)),
                ('use_custom_audience', models.CharField(blank=True, max_length=256, null=True)),
                ('tiktok_identity_type', models.CharField(blank=True, max_length=256, null=True)),
                ('tiktok_identity_id', models.CharField(blank=True, max_length=256, null=True)),
                ('schedule_preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='schedule_presets_settings_schedule_preset', to='common.schedulepresets')),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='schedule_presets_settings_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'schedule_presets_settings',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country_code', models.CharField(blank=True, max_length=56, null=True)),
                ('language_string', models.CharField(blank=True, max_length=336, null=True)),
                ('ad_scheduler', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='language_ad_scheduler', to='common.adscheduler')),
            ],
            options={
                'db_table': 'language',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='InflationValues',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('inflation_value', models.IntegerField(blank=True, null=True)),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='inflation_values_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'inflation_values',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Day_Parting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country_code', models.CharField(blank=True, max_length=56, null=True)),
                ('dayparting_string', models.CharField(blank=True, max_length=336, null=True)),
                ('ad_scheduler', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='day_parting_ad_scheduler', to='common.adscheduler')),
            ],
            options={
                'db_table': 'dayparting',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='DailyAdspendGenre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('platform', models.CharField(blank=True, max_length=45, null=True)),
                ('spend', models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True)),
                ('date', models.DateField(blank=True, null=True)),
                ('date_updated', models.DateTimeField(blank=True, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('ad_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_ads_spend_data_ad_account', to='common.adaccount')),
            ],
            options={
                'db_table': 'daily_adspend_genre',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business_id', models.CharField(blank=True, max_length=45, null=True)),
                ('organization_id', models.CharField(blank=True, max_length=45, null=True)),
                ('business_center_id', models.CharField(blank=True, max_length=45, null=True)),
                ('name', models.CharField(blank=True, max_length=45, null=True)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='business_profile', to='common.profile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Authkey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('access_token', models.TextField(blank=True, null=True)),
                ('refresh_token', models.TextField(blank=True, null=True)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='authkey_profile', to='common.profile')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='adscheduler',
            name='scraper_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ad_scheduler_scraper_group', to='common.scrapergroup'),
        ),
        migrations.CreateModel(
            name='AdCreativeIds',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uploadsesid', models.CharField(blank=True, db_column='uploadSesId', max_length=450, null=True)),
                ('ad_scheduler_id', models.IntegerField(blank=True, null=True)),
                ('ad_platform', models.CharField(blank=True, max_length=150, null=True)),
                ('filename', models.CharField(blank=True, max_length=150, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('thumbnail_url', models.CharField(blank=True, max_length=450, null=True)),
                ('creative_type', models.CharField(blank=True, max_length=45, null=True)),
                ('placement_type', models.CharField(blank=True, max_length=45, null=True)),
                ('creative_id', models.CharField(blank=True, max_length=350, null=True)),
                ('uploaded_on', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('user_id', models.CharField(blank=True, max_length=45, null=True)),
                ('landingpage_url', models.TextField(blank=True, null=True)),
                ('heading', models.CharField(blank=True, max_length=450, null=True)),
                ('resolution', models.CharField(blank=True, max_length=450, null=True)),
                ('caption', models.TextField(blank=True, null=True)),
                ('creative_size', models.CharField(blank=True, max_length=450, null=True)),
                ('linkfire_id', models.BigIntegerField(blank=True, null=True)),
                ('ad_adset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ad_creative_ids_adset', to='common.adadsets')),
                ('scheduler', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ad_creative_ids_scheduler', to='common.adscheduler')),
            ],
            options={
                'db_table': 'ad_creative_ids',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='AdCampaigns',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('automatic', models.CharField(blank=True, max_length=45, null=True)),
                ('ios14', models.CharField(blank=True, max_length=45, null=True)),
                ('ad_platform', models.CharField(blank=True, max_length=45, null=True)),
                ('advertiserid', models.CharField(blank=True, db_column='advertiserID', max_length=95, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=95, null=True)),
                ('campaign_name', models.TextField(blank=True, null=True)),
                ('objective', models.CharField(blank=True, max_length=45, null=True)),
                ('active', models.CharField(blank=True, max_length=45, null=True)),
                ('api_status', models.CharField(blank=True, max_length=45, null=True)),
                ('addedon', models.DateTimeField(blank=True, db_column='addedOn', null=True)),
                ('last_checked', models.DateTimeField(blank=True, null=True)),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ad_campaigns_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'ad_campaigns',
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='adadsets',
            name='scheduler',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='adsets_scheduler', to='common.adscheduler'),
        ),
        migrations.AddField(
            model_name='adaccount',
            name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='adaccount_business', to='common.business'),
        ),
        migrations.AddField(
            model_name='adaccount',
            name='profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='adaccount_profile', to='common.profile'),
        ),
    ]