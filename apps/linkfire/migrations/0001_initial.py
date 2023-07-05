# Generated by Django 4.0.6 on 2023-02-14 06:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('scraper', '0001_initial'),
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinkfireBoards',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=45, null=True)),
                ('board_id', models.TextField(blank=True, null=True)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_boards_profile', to='common.profile')),
            ],
            options={
                'db_table': 'linkfire_boards',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='ScrapeLinkfires',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('url', models.CharField(blank=True, max_length=450, null=True)),
                ('shorttag', models.CharField(blank=True, max_length=450, null=True)),
                ('insights_shorttag', models.CharField(blank=True, max_length=450, null=True)),
                ('scraped', models.IntegerField(blank=True, null=True)),
                ('last_scraped', models.DateTimeField(blank=True, null=True)),
                ('active', models.CharField(blank=True, max_length=45, null=True)),
                ('addedon', models.DateTimeField(blank=True, db_column='addedOn', null=True)),
                ('board_id', models.CharField(blank=True, max_length=450, null=True)),
                ('link_id', models.CharField(blank=True, max_length=450, null=True)),
                ('scraper_connection', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scrape_linkfires_scraper_connection', to='scraper.scraperconnection')),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scrape_linkfires_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'scrape_linkfires',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LinkfireUrl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('mediaServiceId', models.CharField(blank=True, max_length=450, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('isoCode', models.CharField(blank=True, max_length=56, null=True)),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_url_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'linkfire_url',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LinkfireMediaservices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('mediaservice_id', models.CharField(blank=True, max_length=450, null=True)),
                ('buttontype', models.CharField(blank=True, db_column='buttonType', max_length=95, null=True)),
                ('name', models.CharField(blank=True, max_length=450, null=True)),
                ('description', models.CharField(blank=True, max_length=450, null=True)),
                ('linkfire_board', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_media_services_linkfire_board', to='linkfire.linkfireboards')),
            ],
            options={
                'db_table': 'linkfire_media_services',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LinkfireLinkSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sortorder', models.DecimalField(blank=True, db_column='sortOrder', decimal_places=2, max_digits=4, null=True)),
                ('mediaservicename', models.CharField(blank=True, db_column='mediaServiceName', max_length=450, null=True)),
                ('mediaserviceid', models.CharField(blank=True, db_column='mediaServiceId', max_length=450, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('customctatext', models.CharField(blank=True, db_column='customCTAText', max_length=45, null=True)),
                ('heading', models.CharField(blank=True, max_length=55, null=True)),
                ('caption', models.CharField(blank=True, max_length=55, null=True)),
                ('artwork', models.TextField(blank=True, null=True)),
                ('default_url', models.CharField(blank=True, default='No', max_length=45, null=True)),
                ('territory_url', models.CharField(blank=True, default='No', max_length=45, null=True)),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_link_settings_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'linkfire_link_settings',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LinkfireGeneratedLinks',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad_scheduler_id', models.IntegerField(blank=True, null=True)),
                ('link_id', models.CharField(blank=True, max_length=450, null=True)),
                ('domain', models.CharField(blank=True, max_length=95, null=True)),
                ('shorttag', models.CharField(blank=True, max_length=95, null=True)),
                ('status', models.CharField(blank=True, max_length=45, null=True)),
                ('is_scraped', models.CharField(blank=True, max_length=45, null=True)),
                ('added_on', models.DateTimeField(blank=True, null=True)),
                ('linkfire_board', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_generated_links_linkfire_board', to='linkfire.linkfireboards')),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_generated_links_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'linkfire_generated_links',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LinkfireDataServices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateTimeField(blank=True, null=True)),
                ('mediaservice', models.CharField(blank=True, max_length=200, null=True)),
                ('visits', models.IntegerField(blank=True, null=True)),
                ('notification', models.CharField(blank=True, default='No', max_length=45, null=True)),
                ('linkfire', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_data_services_linkfire', to='linkfire.scrapelinkfires')),
            ],
            options={
                'db_table': 'linkfire_data_services',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LinkfireData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateTimeField(blank=True, null=True)),
                ('country', models.CharField(blank=True, max_length=95, null=True)),
                ('country_code', models.CharField(blank=True, max_length=45, null=True)),
                ('visits', models.IntegerField(blank=True, null=True)),
                ('ctr', models.CharField(blank=True, db_column='CTR', max_length=45, null=True)),
                ('notification', models.CharField(blank=True, max_length=45, null=True)),
                ('linkfire', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_data_linkfire', to='linkfire.scrapelinkfires')),
                ('scraper_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='linkfire_data_scraper_group', to='common.scrapergroup')),
            ],
            options={
                'db_table': 'linkfire_data',
                'managed': True,
            },
        ),
    ]
