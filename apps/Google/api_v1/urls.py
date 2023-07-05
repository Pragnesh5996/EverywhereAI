from django.urls import re_path
from rest_framework import routers
from apps.Google.api_v1 import views

router = routers.SimpleRouter()
router.register("google_profiles", views.GoogleProfileViewset)

app_name = "Google"
urlpatterns = [
    re_path(
        r"connect-google/",
        views.ConnectGoogleApiView.as_view(),
    ),
] + router.urls
