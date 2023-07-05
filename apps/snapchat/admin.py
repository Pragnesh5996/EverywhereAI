from django.contrib import admin
from django.contrib.admin.decorators import register
from apps.snapchat import models

# Register your models here.
@register(models.SnapApps)
class SnapAppsAdmin(admin.ModelAdmin):
    list_display = (
        "app_name",
        "ios_app_id",
        "android_app_url",
        "icon_url",
        "icon_media_id",
    )
