from django.urls import re_path
from rest_framework import routers
from apps.tiktok.api_v1 import views

router = routers.SimpleRouter()
router.register("tiktok_profiles", views.TiktokProfileViewset)

app_name = "tiktok"
urlpatterns = [
    re_path(
        r"connect-tiktok/",
        views.ConnectTiktokApiView.as_view(),
    )
] + router.urls
