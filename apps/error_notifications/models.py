from django.db import models
from apps.common.models import TimeStampModel

# Create your models here.


class NotificationLogs(TimeStampModel):
    type_notification = models.TextField(blank=True, null=True)
    linkfire_data_id = models.BigIntegerField(blank=True, null=True)
    scheduler_id = models.BigIntegerField(blank=True, null=True)
    notified_emails = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    linkfire_insights_now = models.TextField(blank=True, null=True)
    linkfire_insights_before = models.TextField(blank=True, null=True)
    notification_data = models.TextField(blank=True, null=True)
    viewed = models.CharField(max_length=45, blank=True, null=True)
    viewed_by = models.CharField(max_length=95, blank=True, null=True)
    email_sent = models.CharField(max_length=45, blank=True, null=True)
    email_log_output = models.TextField(blank=True, null=True)
    notification_sent_on = models.DateTimeField(blank=True, null=True)
    email_read_on = models.DateTimeField(blank=True, null=True)
    notification_sent = models.CharField(max_length=45, blank=True, null=True)
    priority = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "notification_logs"
