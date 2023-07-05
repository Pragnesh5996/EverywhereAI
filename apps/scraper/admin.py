from django.contrib import admin
from django.contrib.admin.decorators import register
from apps.scraper import models

# Register your models here.
@register(models.Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("variable", "value")


@register(models.Spotify1DayData)
class Spotify1DayDataAdmin(admin.ModelAdmin):
    list_display = (
        "country",
        "listeners",
        "streams",
        "followers",
        "date",
        "date_scraped",
    )


@register(models.Spotify28DaysData)
class Spotify28DaysDataAdmin(admin.ModelAdmin):
    list_display = (
        "country",
        "listeners",
        "streams",
        "followers",
        "date",
        "date_scraped",
    )


@register(models.Spotify7DaysData)
class Spotify7DaysDataAdmin(admin.ModelAdmin):
    list_display = (
        "country",
        "listeners",
        "streams",
        "followers",
        "date",
        "date_scraped",
    )


@register(models.SpotifyPayoutData)
class SpotifyPayoutDataAdmin(admin.ModelAdmin):
    list_display = (
        "dsp",
        "country",
        "dollar_per_mil",
        "date_statement",
        "date_imported",
    )


@register(models.SpotifyPlaylistData)
class SpotifyPlaylistDataAdmin(admin.ModelAdmin):
    list_display = (
        "playlist_listeners",
        "playlist_streams",
        "time_filter",
        "date",
        "date_scraped",
    )


@register(models.SpotifyProfiles)
class SpotifyProfilesAdmin(admin.ModelAdmin):
    list_display = ("avatar_url", "profile_id", "profile_name", "is_active")
