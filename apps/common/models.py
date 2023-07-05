from django.db import models
from django.db.models import JSONField
from apps.common.constants import PlatFormType, AdAccountActiveType, ProgressType


# Create your models here.
class TimeStampModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AdAdsets(TimeStampModel):
    ad_platform = models.CharField(max_length=45, blank=True, null=True)
    campaign_id = models.CharField(max_length=95, blank=True, null=True)
    adset_id = models.CharField(max_length=95, blank=True, null=True)
    adset_name = models.TextField(blank=True, null=True)
    target_country = models.CharField(max_length=95, blank=True, null=True)
    landingpage = models.CharField(max_length=450, blank=True, null=True)
    bid = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    budget = models.IntegerField(blank=True, null=True)
    max_budget = models.IntegerField(blank=True, null=True)
    active = models.CharField(max_length=45, blank=True, null=True)
    last_checked = models.DateTimeField(blank=True, null=True)
    ignore_until = models.DateTimeField(blank=True, null=True)
    manual_change_updated = models.CharField(max_length=45, blank=True, null=True)
    manual_change_reason = models.TextField(blank=True, null=True)
    maturity = models.CharField(max_length=45, blank=True, null=True)
    strategy = models.CharField(max_length=45, blank=True, null=True)
    max_cpc = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    updated_volume_adset = models.DateField(blank=True, null=True)
    scheduler = models.ForeignKey(
        "common.AdScheduler",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="adsets_scheduler",
    )

    class Meta:
        managed = True
        db_table = "ad_adsets"


class AdCampaigns(TimeStampModel):
    automatic = models.CharField(max_length=45, blank=True, null=True)
    ios14 = models.CharField(max_length=45, blank=True, null=True)
    ad_platform = models.CharField(max_length=45, blank=True, null=True)
    advertiserid = models.CharField(
        db_column="advertiserID", max_length=95, blank=True, null=True
    )
    campaign_id = models.CharField(max_length=95, blank=True, null=True)
    campaign_name = models.TextField(blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="ad_campaigns_scraper_group",
    )
    objective = models.CharField(max_length=45, blank=True, null=True)
    active = models.CharField(max_length=45, blank=True, null=True)
    api_status = models.CharField(max_length=45, blank=True, null=True)
    addedon = models.DateTimeField(db_column="addedOn", blank=True, null=True)
    last_checked = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ad_campaigns"


class AdCreativeIds(TimeStampModel):
    uploadsesid = models.CharField(
        db_column="uploadSesId", max_length=450, blank=True, null=True
    )
    ad_scheduler_id = models.IntegerField(blank=True, null=True)
    ad_platform = models.CharField(max_length=150, blank=True, null=True)
    filename = models.CharField(max_length=150, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    thumbnail_url = models.CharField(max_length=450, blank=True, null=True)
    creative_type = models.CharField(max_length=45, blank=True, null=True)
    placement_type = models.CharField(max_length=45, blank=True, null=True)
    creative_id = models.CharField(max_length=350, blank=True, null=True)
    uploaded_on = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    user_id = models.CharField(max_length=45, blank=True, null=True)
    landingpage_url = models.TextField(blank=True, null=True)
    heading = models.CharField(max_length=450, blank=True, null=True)
    resolution = models.CharField(max_length=450, blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    ad_adset = models.ForeignKey(
        "common.AdAdsets",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ad_creative_ids_adset",
    )
    scheduler = models.ForeignKey(
        "common.AdScheduler",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ad_creative_ids_scheduler",
    )
    creative_size = models.CharField(max_length=450, blank=True, null=True)
    linkfire_id = models.BigIntegerField(blank=True, null=True)
    advantage_placement = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ad_creative_ids"


class AdLogs(TimeStampModel):
    ad_platform = models.CharField(max_length=45, blank=True, null=True)
    campaign_id = models.BigIntegerField(blank=True, null=True)
    adset_id = models.BigIntegerField(blank=True, null=True)
    old_bid = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    new_bid = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    loggedon = models.DateTimeField(db_column="loggedOn", blank=True, null=True)
    email_sent = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ad_logs"


class AdScheduler(TimeStampModel):
    uploadsesid = models.CharField(
        db_column="uploadSesId", max_length=450, blank=True, null=True
    )
    platform = models.CharField(max_length=95, blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="ad_scheduler_scraper_group",
    )
    type_post = models.CharField(max_length=95, blank=True, null=True)
    placement_type = models.CharField(max_length=45, blank=True, null=True)
    campaign_name = models.CharField(max_length=100, blank=True, null=True)
    campaign_id = models.CharField(max_length=95, blank=True, null=True)
    adaccount_id = models.CharField(max_length=150, blank=True, null=True)
    extra_name = models.CharField(max_length=450, blank=True, null=True)
    bundle_countries = models.BooleanField(default=False)
    countries = models.TextField(blank=True, null=True)
    age_range = models.CharField(max_length=45, blank=True, null=True)
    budget = models.IntegerField(blank=True, null=True)
    max_budget = models.IntegerField(blank=True, null=True)
    dayparting = models.BooleanField(default=False)
    language = models.BooleanField(default=False)
    landingpage_url = models.TextField(blank=True, null=True)
    heading = models.CharField(max_length=450, blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    bid_strategy = models.CharField(max_length=45, blank=True, null=True)
    bid = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    objective = models.CharField(max_length=45, blank=True, null=True)
    pixel_id = models.CharField(max_length=45, blank=True, null=True)
    event_type = models.CharField(max_length=45, blank=True, null=True)
    app_platform = models.CharField(max_length=45, blank=True, null=True)
    application_id = models.CharField(max_length=45, blank=True, null=True)
    custom_audiences = models.TextField(blank=True, null=True)
    ignore_until = models.DateTimeField(blank=True, null=True)
    scheduled_for = models.DateTimeField(blank=True, null=True)
    strategy = models.CharField(max_length=45, blank=True, null=True)
    interests = models.TextField(blank=True, null=True)
    accelerated_spend = models.BooleanField(default=False)
    created_on = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    completed = models.CharField(max_length=45, blank=True, null=True, default="No")
    user_id = models.CharField(max_length=45, blank=True, null=True)
    authkey_email_user = models.CharField(max_length=95, blank=True, null=True)
    tiktok_identity_type = models.CharField(max_length=45, blank=True, null=True)
    tiktok_identity_id = models.CharField(max_length=450, blank=True, null=True)
    company_name = models.CharField(max_length=450, blank=True, null=True)
    music_sharing = models.CharField(
        max_length=56, blank=True, null=True, default="False"
    )
    stitch_duet = models.CharField(
        max_length=56, blank=True, null=True, default="False"
    )
    instagram_id = models.TextField(blank=True, null=True)
    facebook_pages_ids = models.TextField(blank=True, null=True)
    profile = models.ForeignKey(
        "common.Profile",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="ad_scheduler_profile",
    )
    automatic_placement = models.BooleanField(default=False)
    selected_placement = models.CharField(max_length=456, blank=True, null=True)
    ad_type = models.CharField(max_length=456, blank=True, null=True, default="Single")
    carousel_card_order = models.CharField(max_length=256, blank=True, null=True)
    max_cards_per_carousel = models.IntegerField(blank=True, null=True)
    auto_scheduler_json = JSONField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ad_scheduler"


class Language(TimeStampModel):
    ad_scheduler = models.ForeignKey(
        AdScheduler, on_delete=models.CASCADE, related_name="language_ad_scheduler"
    )
    country_code = models.TextField(blank=True, null=True)
    language_string = models.CharField(max_length=336, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "language"


class Day_Parting(TimeStampModel):
    ad_scheduler = models.ForeignKey(
        AdScheduler, on_delete=models.CASCADE, related_name="day_parting_ad_scheduler"
    )
    country_code = models.TextField(blank=True, null=True)
    dayparting_string = models.CharField(max_length=336, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "dayparting"


class AdsetInsights(TimeStampModel):
    id = models.BigAutoField(primary_key=True)
    platform = models.CharField(max_length=45, blank=True, null=True)
    campaign_id = models.CharField(max_length=95, blank=True, null=True)
    adset_id = models.CharField(max_length=95, blank=True, null=True)
    cpc = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    spend = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    date_updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "adset_insights"


class BibleClientId(TimeStampModel):
    client_id = models.CharField(max_length=450, blank=True, null=True)
    date_generated = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "bible_client_id"


class CustomAudiences(TimeStampModel):
    platform = models.CharField(max_length=45, blank=True, null=True)
    account_id = models.CharField(max_length=45, blank=True, null=True)
    audience_id = models.CharField(max_length=95, blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    added = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "custom_audiences"


class CustomConversionEvents(TimeStampModel):
    platform = models.CharField(max_length=45, blank=True, null=True)
    account_id = models.CharField(max_length=45, blank=True, null=True)
    event_id = models.CharField(max_length=45, blank=True, null=True)
    pixel_id = models.CharField(max_length=45, blank=True, null=True)
    name = models.CharField(max_length=45, blank=True, null=True)
    external_action = models.CharField(max_length=45, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rules = models.TextField(blank=True, null=True)
    added = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "custom_conversion_events"


class DailyAdspendGenre(TimeStampModel):
    platform = models.CharField(max_length=45, blank=True, null=True)
    spend = models.DecimalField(max_digits=11, decimal_places=2, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    date_updated = models.DateTimeField(blank=True, null=True)
    ad_account = models.ForeignKey(
        "common.AdAccount",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="daily_ads_spend_data_ad_account",
    )
    campaign_id = models.CharField(max_length=95, blank=True, null=True)
    account_id = models.CharField(max_length=95, blank=True, null=True)
    company_uid = models.CharField(max_length=95, blank=True, null=True)
    ad_account_currency = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "daily_adspend_genre"


class ScraperGroup(TimeStampModel):
    group_name = models.CharField(max_length=95, blank=True, null=True)
    number_1day_data_map = models.CharField(
        db_column="1day_data_map", max_length=95, blank=True, null=True
    )
    number_7day_data_map = models.CharField(
        db_column="7day_data_map", max_length=95, blank=True, null=True
    )
    number_28day_data_map = models.CharField(
        db_column="28day_data_map", max_length=95, blank=True, null=True
    )
    playlist_data_map = models.CharField(max_length=95, blank=True, null=True)
    inflation_value = models.IntegerField(blank=True, null=True)
    data_days = models.IntegerField(blank=True, null=True)
    facebook_heading = models.CharField(max_length=95, blank=True, null=True)
    facebook_caption = models.TextField(blank=True, null=True)
    facebook_button = models.CharField(max_length=95, blank=True, null=True)
    facebook_agerange = models.CharField(max_length=255, blank=True, null=True)
    tiktok_caption = models.CharField(max_length=100, blank=True, null=True)
    tiktok_button = models.CharField(max_length=95, blank=True, null=True)
    tiktok_agerange = models.CharField(max_length=255, blank=True, null=True)
    snap_caption = models.CharField(max_length=100, blank=True, null=True)
    snap_button = models.CharField(max_length=95, blank=True, null=True)
    snap_agerange = models.CharField(max_length=255, blank=True, null=True)
    profile_url = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "scraper_groups"


class InflationValues(TimeStampModel):
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="inflation_values_scraper_group",
    )
    inflation_value = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "inflation_values"


class Logs(TimeStampModel):
    component = models.CharField(max_length=45, blank=True, null=True)
    type = models.CharField(max_length=45, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    datelogged = models.DateTimeField(db_column="dateLogged", blank=True, null=True)

    class Meta:
        managed = True
        db_table = "logs"


class Pixels(TimeStampModel):
    advertiser_id = models.CharField(max_length=95, blank=True, null=True)
    pixel_id = models.CharField(max_length=450, blank=True, null=True)
    name = models.CharField(max_length=450, blank=True, null=True)
    platform = models.CharField(max_length=45, blank=True, null=True)
    date_added = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "pixels"


class ProfitMargins(TimeStampModel):
    ad_platform = models.CharField(max_length=45, blank=True, null=True)
    profit_margin = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "profit_margins"


class RateLimits(TimeStampModel):
    platform = models.CharField(max_length=45, blank=True, null=True)
    type = models.CharField(max_length=45, blank=True, null=True)
    subtype = models.CharField(max_length=45, blank=True, null=True)
    account_id = models.CharField(max_length=45, blank=True, null=True)
    call_count = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    total_cputime = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    total_time = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    call_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "rate_limits"


class SpendData(TimeStampModel):
    ad_platform = models.CharField(max_length=45, blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spend_data_scraper_group",
    )
    country = models.CharField(max_length=95, blank=True, null=True)
    spend = models.DecimalField(max_digits=11, decimal_places=5, blank=True, null=True)
    data_days = models.IntegerField(blank=True, null=True)
    date_updated = models.DateTimeField()

    class Meta:
        managed = True
        db_table = "spend_data"


class Users(TimeStampModel):
    idusers = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45, blank=True, null=True)
    password = models.CharField(max_length=128)
    email = models.CharField(max_length=45, blank=True, null=True)
    last_loggedin = models.DateTimeField(blank=True, null=True)
    createdon = models.DateTimeField(db_column="createdOn", blank=True, null=True)

    class Meta:
        managed = True
        db_table = "users"


class SchedulePresets(TimeStampModel):
    preset_name = models.CharField(max_length=256)
    created_by = models.ForeignKey(
        "main.User", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        managed = True
        db_table = "schedule_presets"


class SchedulePresetsSettings(TimeStampModel):
    preset_json_data = JSONField(blank=True, null=True)
    schedule_preset = models.ForeignKey(
        SchedulePresets,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="schedule_presets_settings_schedule_preset",
    )

    class Meta:
        managed = True
        db_table = "schedule_presets_settings"


class Profile(TimeStampModel):
    first_name = models.CharField(max_length=45, blank=True, null=True)
    last_name = models.CharField(max_length=45, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    ad_platform = models.CharField(max_length=45, choices=PlatFormType.CHOICES)
    is_active = models.BooleanField(default=True)
    is_connection_established = models.BooleanField(default=True)
    connection_error_message = models.TextField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)
    social_profile_id = models.CharField(max_length=255, blank=True, null=True)


class Authkey(TimeStampModel):
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="authkey_profile",
    )


class Business(TimeStampModel):
    business_id = models.CharField(max_length=45, blank=True, null=True)
    organization_id = models.CharField(max_length=45, blank=True, null=True)
    business_center_id = models.CharField(max_length=45, blank=True, null=True)
    name = models.CharField(max_length=45, blank=True, null=True)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="business_profile",
    )


class AdAccount(TimeStampModel):
    account_id = models.CharField(max_length=45, blank=True, null=True)
    account_name = models.CharField(max_length=45, blank=True, null=True)
    active = models.PositiveSmallIntegerField(
        choices=AdAccountActiveType.CHOICES, default=AdAccountActiveType.NO
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="adaccount_profile",
    )
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="adaccount_business",
    )
    live_ad_account_status = models.CharField(max_length=45, blank=True, null=True)
    timezone = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=100, blank=True, null=True)
    last_28days_spend_status = models.PositiveSmallIntegerField(
        choices=ProgressType.CHOICES, default=ProgressType.NOTSTARTED
    )
    utc_offset = models.CharField(max_length=100, blank=True, null=True)


class AutoSchedulerDraft(TimeStampModel):
    user = models.OneToOneField(
        "main.User", on_delete=models.CASCADE, blank=True, null=True
    )
    draft_data = JSONField(null=False, default=dict)
    current_page = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "auto_scheduler_draft"


