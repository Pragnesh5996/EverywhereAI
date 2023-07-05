from django.urls import re_path
from rest_framework import routers
from apps.error_notifications.api_v1 import views

router = routers.SimpleRouter()
router.register("error-logs", views.ErrorLogsViewset)

app_name = "error_notifications"
urlpatterns = [] + router.urls
