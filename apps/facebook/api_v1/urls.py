from django.urls import re_path
from rest_framework import routers
from apps.facebook.api_v1 import views

router = routers.SimpleRouter()
router.register("facebook_profiles", views.FacebookProfileViewset)

app_name = "facebook"
urlpatterns = [
    re_path(
        r"connect-facebook/",
        views.ConnectFacebookApiView.as_view(),
    ),
    re_path(
        r"facebook-pages-list/",
        views.FacebookPagesList.as_view(),
    ),
    re_path(
        r"instagram-account-using-business-id/",
        views.InstagramAccountsUsingPageIdAPIView.as_view(),
    ),
] + router.urls
