from rest_framework import serializers
from apps.linkfire.models import (
    LinkfireUrl,
    LinkfireLinkSettings,
    LinkfireMediaservices,
    ScrapeLinkfires,
    LinkfireGeneratedLinks,
    LinkfireData,
)
from apps.common.models import ScraperGroup
from apps.scraper.models import SpotifyProfiles
from apps.common.models import AdCampaigns


class ScraperGroupSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for ScraperGroup.
    It allows for the serialization of all fields of the Genre model.
    """

    with_counting = False

    def __init__(self, *args, **kwargs):
        super(ScraperGroupSerializer, self).__init__(*args, **kwargs)
        ScraperGroupSerializer.with_counting = self.with_counting

    counting = serializers.SerializerMethodField()

    def get_counting(self, scraper_group):
        if self.with_counting:
            ad_campaigns_count = AdCampaigns.objects.filter(
                scraper_group=scraper_group.id
            ).count()
            linkfiredata_count = LinkfireData.objects.filter(
                scraper_group=scraper_group.id
            ).count()
            spotify_count = SpotifyProfiles.objects.filter(
                scraper_group=scraper_group.id
            ).count()
            return {
                "ad_campaigns": ad_campaigns_count,
                "linkfires": linkfiredata_count,
                "spotify_profiles": spotify_count,
            }
        else:
            return None

    class Meta:
        model = ScraperGroup
        fields = ("id","group_name", "profile_url", "counting", "created_at", "updated_at")


class LinkfireMediaservicesSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for LinkFire media services.
    It allows for the serialization of all fields of the LinkFire media service model.
    """

    class Meta:
        model = LinkfireMediaservices
        fields = "__all__"


class LinkFireUrlsSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for LinkFire URLs.
    It allows for the serialization of all fields of the LinkFire URL model.
    """

    class Meta:
        model = LinkfireUrl
        fields = "__all__"


class LinkFireLinkSetingsSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for LinkFire link settings.
    It includes a method for retrieving the associated LinkFire URLs for a given setting.
    """

    linkfire_url = serializers.SerializerMethodField()

    def get_linkfire_url(self, linkfire_link_setting):
        filter_linkfire_url = LinkfireUrl.objects.filter(
            scraper_group_id=linkfire_link_setting.scraper_group_id,
            mediaServiceId=linkfire_link_setting.mediaserviceid,
        )
        return LinkFireUrlsSerializer(filter_linkfire_url, many=True).data

    class Meta:
        model = LinkfireLinkSettings
        fields = "__all__"


class ScrapeLinkfiresReadSerializer(serializers.ModelSerializer):

    scraper_group = serializers.SerializerMethodField()

    def get_scraper_group(self, scrape_linkfires):
        filter_group_name = (
            ScraperGroup.objects.filter(
                id=scrape_linkfires.scraper_group_id,
            )
            .values("id", "group_name", "profile_url")
            .first()
        )
        return filter_group_name

    class Meta:
        model = ScrapeLinkfires
        fields = "__all__"


class ScrapeLinkfiresUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapeLinkfires
        fields = ("is_active",)


class SpotifyScraperInfoSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Spotify Scraper Info.
    """

    class Meta:
        model = SpotifyProfiles
        fields = "__all__"


class LinkfireGeneratorSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Link Fire Generator.
    """

    scraper_group = serializers.SerializerMethodField()

    def get_scraper_group(self, linkfire_generated_links):
        filter_group_name = (
            ScraperGroup.objects.filter(
                id=linkfire_generated_links.scraper_group_id,
            )
            .values("id", "group_name", "profile_url")
            .first()
        )
        return filter_group_name

    class Meta:
        model = LinkfireGeneratedLinks
        fields = "__all__"
