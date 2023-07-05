from django.db import models
from apps.common.models import TimeStampModel

# Create your models here.
class LinkfireBoards(TimeStampModel):
    name = models.CharField(max_length=45, blank=True, null=True)
    board_id = models.TextField(blank=True, null=True)
    profile = models.ForeignKey(
        "common.Profile",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_boards_profile",
    )

    class Meta:
        managed = True
        db_table = "linkfire_boards"


class LinkfireData(TimeStampModel):
    date = models.DateTimeField(blank=True, null=True)
    country = models.CharField(max_length=95, blank=True, null=True)
    country_code = models.CharField(max_length=45, blank=True, null=True)
    visits = models.IntegerField(blank=True, null=True)
    ctr = models.CharField(db_column="CTR", max_length=45, blank=True, null=True)
    notification = models.CharField(max_length=45, blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_data_scraper_group",
    )
    linkfire = models.ForeignKey(
        "linkfire.ScrapeLinkfires",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_data_linkfire",
    )  # field name is scrape_linkfires but we add linkfire

    class Meta:
        managed = True
        db_table = "linkfire_data"


class LinkfireDataServices(TimeStampModel):
    linkfire = models.ForeignKey(
        "linkfire.ScrapeLinkfires",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_data_services_linkfire",
    )  # field name is scrape_linkfires but we add linkfire
    date = models.DateTimeField(blank=True, null=True)
    mediaservice = models.CharField(max_length=200, blank=True, null=True)
    visits = models.IntegerField(blank=True, null=True)
    notification = models.CharField(max_length=45, default="No", blank=True, null=True)

    class Meta:
        managed = True
        db_table = "linkfire_data_services"


class LinkfireGeneratedLinks(TimeStampModel):
    ad_scheduler_id = models.IntegerField(blank=True, null=True)
    # board_id = models.CharField(max_length=450, blank=True, null=True)
    link_id = models.CharField(max_length=450, blank=True, null=True)
    domain = models.CharField(max_length=95, blank=True, null=True)
    shorttag = models.CharField(max_length=95, blank=True, null=True)
    status = models.CharField(max_length=45, blank=True, null=True)
    is_scraped = models.CharField(max_length=45, blank=True, null=True)
    added_on = models.DateTimeField(blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_generated_links_scraper_group",
    )
    linkfire_board = models.ForeignKey(
        "linkfire.LinkfireBoards",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_generated_links_linkfire_board",
    )

    class Meta:
        managed = True
        db_table = "linkfire_generated_links"


class LinkfireLinkSettings(TimeStampModel):
    sortorder = models.DecimalField(
        db_column="sortOrder", max_digits=4, decimal_places=2, blank=True, null=True
    )
    mediaservicename = models.CharField(
        db_column="mediaServiceName", max_length=450, blank=True, null=True
    )
    mediaserviceid = models.CharField(
        db_column="mediaServiceId", max_length=450, blank=True, null=True
    )
    url = models.TextField(blank=True, null=True)
    customctatext = models.CharField(
        db_column="customCTAText", max_length=45, blank=True, null=True
    )
    heading = models.CharField(max_length=55, blank=True, null=True)
    caption = models.CharField(max_length=55, blank=True, null=True)
    artwork = models.TextField(blank=True, null=True)
    default_url = models.CharField(max_length=45, default="No", blank=True, null=True)
    territory_url = models.CharField(max_length=45, default="No", blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_link_settings_scraper_group",
    )

    class Meta:
        managed = True
        db_table = "linkfire_link_settings"


class LinkfireUrl(TimeStampModel):
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_url_scraper_group",
    )
    mediaServiceId = models.CharField(max_length=450, blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    isoCode = models.CharField(max_length=56, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "linkfire_url"


class ScrapeLinkfires(TimeStampModel):
    url = models.CharField(max_length=450, blank=True, null=True)
    shorttag = models.CharField(max_length=450, blank=True, null=True)
    insights_shorttag = models.CharField(max_length=450, blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="scrape_linkfires_scraper_group",
    )
    scraped = models.IntegerField(blank=True, null=True)
    last_scraped = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    addedon = models.DateTimeField(db_column="addedOn", blank=True, null=True)
    scraper_connection = models.ForeignKey(
        "scraper.ScraperConnection",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="scrape_linkfires_scraper_connection",
    )
    board_id = models.CharField(max_length=450, blank=True, null=True)
    link_id = models.CharField(max_length=450, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "scrape_linkfires"


class LinkfireMediaservices(TimeStampModel):
    mediaservice_id = models.CharField(max_length=450, blank=True, null=True)
    buttontype = models.CharField(
        db_column="buttonType", max_length=95, blank=True, null=True
    )
    name = models.CharField(max_length=450, blank=True, null=True)
    description = models.CharField(max_length=450, blank=True, null=True)
    linkfire_board = models.ForeignKey(
        "linkfire.LinkfireBoards",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="linkfire_media_services_linkfire_board",
    )

    class Meta:
        managed = True
        db_table = "linkfire_media_services"
