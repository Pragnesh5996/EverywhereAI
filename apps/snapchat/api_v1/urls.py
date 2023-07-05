from django.urls import re_path
from rest_framework import routers
from apps.snapchat.api_v1 import views

router = routers.SimpleRouter()
router.register("snap_profiles", views.SnapProfileViewset)

app_name = "snapchat"
urlpatterns = [
    re_path(
        r"connect-snapchat/",
        views.ConnectSnapChatApiView.as_view(),
    ),
] + router.urls
