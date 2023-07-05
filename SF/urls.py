"""SF URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import re_path, include
from apps.common.api_v1.views import TestWebhookAPIView

api_v1_urls = [
    re_path("accounts/", include("apps.accounts.api_v1.urls", namespace="v1-accounts")),
    re_path("facebook/", include("apps.facebook.api_v1.urls", namespace="v1-facebook")),
    re_path("linkfire/", include("apps.linkfire.api_v1.urls", namespace="v1-linkfire")),
    re_path("snapchat/", include("apps.snapchat.api_v1.urls", namespace="v1-snapchat")),
    re_path("tiktok/", include("apps.tiktok.api_v1.urls", namespace="v1-tiktok")),
    re_path("common/", include("apps.common.api_v1.urls", namespace="v1-common")),
    re_path(
        "marketplace/",
        include("apps.marketplace.api_v1.urls", namespace="v1-marketplace"),
    ),
    re_path(
        "error_notifications/",
        include(
            "apps.error_notifications.api_v1.urls", namespace="v1-error_notifications"
        ),
    ),
    re_path("Google/", include("apps.Google.api_v1.urls", namespace="v1-Google")),
    re_path("payment/", include("apps.payment.api_v1.urls", namespace="v1-payment")),
    re_path(
        "webhook/",
        include("apps.payment.webhook.urls", namespace="v1-payment-webhook"),
    ),
]

urlpatterns = [
    re_path("admin/", admin.site.urls),
    re_path("api/v1/", include(api_v1_urls)),
    re_path("webhook/", TestWebhookAPIView.as_view()),
]
