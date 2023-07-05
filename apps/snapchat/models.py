from django.db import models
from apps.common.models import TimeStampModel

# Create your models here.
class SnapApps(TimeStampModel):
    app_name = models.CharField(max_length=450, blank=True, null=True)
    ios_app_id = models.CharField(max_length=95, blank=True, null=True)
    android_app_url = models.CharField(max_length=450, blank=True, null=True)
    icon_url = models.CharField(max_length=450, blank=True, null=True)
    icon_media_id = models.CharField(max_length=450, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "snap_apps"
