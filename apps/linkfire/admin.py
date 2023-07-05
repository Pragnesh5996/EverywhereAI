from django.contrib import admin
from django.contrib.admin.decorators import register
from apps.linkfire import models

# Register your models here.
@register(models.LinkfireBoards)
class LinkfireBoardsAdmin(admin.ModelAdmin):
    list_display = ("name", "board_id")


@register(models.LinkfireData)
class LinkfireDataAdmin(admin.ModelAdmin):
    list_display = (
        "linkfire_id",
        "date",
        "country",
        "country_code",
        "visits",
        "ctr",
        "notification",
    )


@register(models.LinkfireGeneratedLinks)
class LinkfireGeneratedLinksAdmin(admin.ModelAdmin):
    list_display = (
        "ad_scheduler_id",
        "link_id",
        "domain",
        "shorttag",
        "status",
        "is_scraped",
        "added_on",
    )


@register(models.LinkfireLinkSettings)
class LinkfireLinkSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "sortorder",
        "mediaservicename",
        "mediaserviceid",
        "url",
        "heading",
        "caption",
        "artwork",
    )


@register(models.ScrapeLinkfires)
class ScrapeLinkfiresAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "shorttag",
        "insights_shorttag",
        "scraped",
        "last_scraped",
        "is_active",
        "addedon",
    )
