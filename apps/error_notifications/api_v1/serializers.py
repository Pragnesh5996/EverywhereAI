from rest_framework import serializers
from apps.error_notifications.models import NotificationLogs


class NotificationLogsSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for reading error logs information.
    """

    class Meta:
        model = NotificationLogs
        fields = "__all__"
