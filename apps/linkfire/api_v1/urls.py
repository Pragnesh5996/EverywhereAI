from django.urls import re_path
from rest_framework import routers
from apps.linkfire.api_v1 import views

router = routers.SimpleRouter()
router.register("scraper-group", views.ScraperGroupAPIViewSet)
router.register("linkfire-media-service", views.LinkfireMediaServicesAPIViewSet)
router.register("linkfire-link-setting", views.LinkfireLinkSettingsAPIViewSet)
router.register("linkfire-data-scraper", views.LinkfireDataScraperAPIViewSet)
router.register("spotify-scraper-info", views.SpotifyScraperInfoAPIViewSet)
router.register("linkfire-generator", views.LinkfireGeneratorAPIViewSet)


app_name = "linkfire"
urlpatterns = [
    re_path(r"linkfire-api/", views.LinkfireAPIView.as_view()),
    re_path(
        r"linkfire-data-scraper-connection/",
        views.LinkfireDataScraperConnectionAPIView.as_view(),
    ),
    re_path(
        r"spotify-scraper-connection/", views.SpotifyScraperConnectionAPIView.as_view()
    ),
    re_path(
        r"connect-linkfire-generator/",
        views.ConnectLinkFireGeneratorApiView.as_view(),
    ),
    re_path(
        r"update-scraper-group-profile-picture/",
        views.UpdateScraperGroupProfilePictureAPIView.as_view(),
    ),
    re_path(
        r"delete-linkfire-url/(?P<linkfireurl_id>[-\w]+)/$",
        views.DeleteLinkfireUrl.as_view(),
    ),
    re_path(
        r"add-linkfire-url/",
        views.AddLinkFireUrlAPIView.as_view(),
    ),
    re_path(
        r"bulk-linkfire-link-setting-update/",
        views.BulkLinkfireLinkSettingUpdateAPIView.as_view(),
    ),
    re_path(
        r"generate-linkfire-link/",
        views.GenerateLinkfirelinkAPIView.as_view(),
    ),
    re_path(
        r"add-linkfire-board/",
        views.CreateLinkfireBoardAPIView.as_view(),
    ),
] + router.urls
