from django.db import models
from apps.common.models import TimeStampModel
from apps.common.constants import ScraperConnectionType

# Create your models here.
class ScraperDowntime(TimeStampModel):
    scraper = models.CharField(max_length=45, blank=True, null=True)
    offline_at = models.DateTimeField(blank=True, null=True)
    back_online_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "scraper_downtime"


class Settings(TimeStampModel):
    variable = models.CharField(max_length=95, blank=True, null=True)
    value = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "settings"


class Spotify1DayData(TimeStampModel):
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_1day_data_scraper_group",
    )
    spotify_profile = models.ForeignKey(
        "scraper.SpotifyProfiles",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_1day_data_scraper_group",
    )
    country = models.CharField(max_length=95, blank=True, null=True)
    listeners = models.IntegerField(blank=True, null=True)
    streams = models.IntegerField(blank=True, null=True)
    followers = models.IntegerField(blank=True, null=True)
    date = models.DateTimeField(blank=True, null=True)
    date_scraped = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "spotify_1day_data"


class Spotify28DaysData(TimeStampModel):
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_28days_data_scraper_group",
    )
    spotify_profile = models.ForeignKey(
        "scraper.SpotifyProfiles",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_28days_data_scraper_group",
    )
    country = models.CharField(max_length=95, blank=True, null=True)
    listeners = models.IntegerField(blank=True, null=True)
    streams = models.IntegerField(blank=True, null=True)
    followers = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    date_scraped = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "spotify_28days_data"


class Spotify7DaysData(TimeStampModel):
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_7days_data_scraper_group",
    )
    spotify_profile = models.ForeignKey(
        "scraper.SpotifyProfiles",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_7days_data_scraper_group",
    )
    country = models.CharField(max_length=95, blank=True, null=True)
    listeners = models.IntegerField(blank=True, null=True)
    streams = models.IntegerField(blank=True, null=True)
    followers = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    date_scraped = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "spotify_7days_data"


class SpotifyPayoutData(TimeStampModel):
    dsp = models.CharField(max_length=45, blank=True, null=True)
    country = models.CharField(max_length=450, blank=True, null=True)
    dollar_per_mil = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    date_statement = models.DateTimeField(blank=True, null=True)
    date_imported = models.DateTimeField(blank=True, null=True)
    scraper_connection = models.ForeignKey(
        "scraper.ScraperConnection",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_payout_data_scraper_connection",
    )

    class Meta:
        managed = True
        db_table = "spotify_payout_data"


class SpotifyPlaylistData(TimeStampModel):
    spotify_profile = models.ForeignKey(
        "scraper.SpotifyProfiles",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_playlist_data_scraper_group",
    )
    playlist_listeners = models.IntegerField(blank=True, null=True)
    playlist_streams = models.IntegerField(blank=True, null=True)
    time_filter = models.CharField(max_length=45, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    date_scraped = models.DateTimeField(blank=True, null=True)
    playlist_followers = models.IntegerField(blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_playlist_data_scraper_group",
    )

    class Meta:
        managed = True
        db_table = "spotify_playlist_data"


class SpotifyProfiles(TimeStampModel):
    avatar_url = models.CharField(max_length=450, blank=True, null=True)
    profile_id = models.CharField(max_length=450, blank=True, null=True)
    profile_name = models.CharField(max_length=95, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_profiles_scraper_group",
    )
    scraper_connection = models.ForeignKey(
        "scraper.ScraperConnection",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spotify_profiles_scraper_connection",
    )

    class Meta:
        managed = True
        db_table = "spotify_profiles"


class ScraperConnection(models.Model):
    username = models.CharField(max_length=450, blank=True, null=True)
    password = models.CharField(max_length=450, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    ad_platform = models.PositiveSmallIntegerField(
        choices=ScraperConnectionType.CHOICES, blank=True, null=True
    )

    class Meta:
        managed = True
        db_table = "scraper_connection"
