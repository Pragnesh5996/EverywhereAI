from django.contrib import admin
from django.contrib.admin.decorators import register
from apps.common import models

# Register your models here.
@register(models.AdAdsets)
class AdAdsetsAdmin(admin.ModelAdmin):
    list_display = (
        "ad_platform",
        "campaign_id",
        "adset_id",
        "adset_name",
        "target_country",
        "landingpage",
        "bid",
        "budget",
        "active",
        "last_checked",
        "ignore_until",
        "manual_change_updated",
        "manual_change_reason",
        "maturity",
    )


@register(models.AdCampaigns)
class AdCampaignsAdmin(admin.ModelAdmin):
    list_display = (
        "automatic",
        "ios14",
        "ad_platform",
        "advertiserid",
        "campaign_id",
        "campaign_name",
        "objective",
        "active",
        "last_checked",
    )


@register(models.AdCreativeIds)
class AdCreativeIdsAdmin(admin.ModelAdmin):
    list_display = (
        "uploadsesid",
        "ad_scheduler_id",
        "ad_platform",
        "filename",
        "url",
        "thumbnail_url",
        "creative_type",
        "placement_type",
        "creative_id",
        "uploaded_on",
        "notes",
        "user_id",
    )


@register(models.AdLogs)
class AdLogsAdmin(admin.ModelAdmin):
    list_display = (
        "ad_platform",
        "campaign_id",
        "adset_id",
        "old_bid",
        "new_bid",
        "reason",
        "loggedon",
        "email_sent",
    )


@register(models.AdScheduler)
class AdSchedulerAdmin(admin.ModelAdmin):
    list_display = (
        "uploadsesid",
        "platform",
        "type_post",
        "placement_type",
        "campaign_id",
        "adaccount_id",
        "extra_name",
        "bundle_countries",
        "countries",
        "age_range",
        "budget",
        "landingpage_url",
        "heading",
        "caption",
        "bid_strategy",
        "bid",
        "objective",
        "pixel_id",
        "event_type",
        "app_platform",
        "application_id",
        "custom_audiences",
        "ignore_until",
        "scheduled_for",
        "created_on",
        "completed",
        "user_id",
        "authkey_email_user",
        "tiktok_identity_type",
        "tiktok_identity_id",
    )


@register(models.BibleClientId)
class BibleClientIdAdmin(admin.ModelAdmin):
    list_display = ("client_id", "date_generated")


@register(models.CustomAudiences)
class CustomAudiencesAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "account_id",
        "audience_id",
        "name",
        "description",
        "added",
    )


@register(models.CustomConversionEvents)
class CustomConversionEventsAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "account_id",
        "event_id",
        "pixel_id",
        "name",
        "external_action",
        "description",
        "rules",
    )


@register(models.DailyAdspendGenre)
class DailyAdspendGenreAdmin(admin.ModelAdmin):
    list_display = ("platform", "spend", "date", "date_updated")


@register(models.InflationValues)
class InflationValuesAdmin(admin.ModelAdmin):
    list_display = ("inflation_value",)


@register(models.Logs)
class LogsAdmin(admin.ModelAdmin):
    list_display = ("component", "type", "message", "datelogged")


@register(models.Pixels)
class PixelsAdmin(admin.ModelAdmin):
    list_display = ("advertiser_id", "pixel_id", "name", "platform", "date_added")


@register(models.ProfitMargins)
class ProfitMarginsAdmin(admin.ModelAdmin):
    list_display = ("ad_platform", "profit_margin")


@register(models.RateLimits)
class RateLimitsAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "type",
        "subtype",
        "account_id",
        "call_count",
        "total_cputime",
        "total_time",
        "call_time",
    )


@register(models.SpendData)
class SpendDataAdmin(admin.ModelAdmin):
    list_display = (
        "ad_platform",
        "country",
        "spend",
        "data_days",
        "date_updated",
    )


@register(models.Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = (
        "idusers",
        "name",
        "password",
        "email",
        "last_loggedin",
        "createdon",
    )
