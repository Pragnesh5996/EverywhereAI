from rest_framework.authentication import TokenAuthentication
from rest_framework.viewsets import ModelViewSet
from apps.error_notifications.models import NotificationLogs
from apps.error_notifications.api_v1.serializers import NotificationLogsSerializer
from rest_framework import filters
from apps.common.paginations import PageNumberPagination10


class ErrorLogsViewset(ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = NotificationLogs.objects.all()
    serializer_class = NotificationLogsSerializer
    pagination_class = PageNumberPagination10
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = [
        "id",
        "type_notification",
        "linkfire_data_id",
        "scheduler_id",
        "notified_emails",
        "reason",
        "linkfire_insights_now",
        "linkfire_insights_before",
        "notification_data",
        "viewed",
        "viewed_by",
        "email_sent",
        "email_log_output",
        "notification_sent_on",
        "email_read_on",
        "notification_sent",
        "priority",
    ]
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = super(ErrorLogsViewset, self).get_queryset()
        return queryset


class ErorrMessage:
    def get_message(self, id):
        notification = (
            NotificationLogs.objects.filter(scheduler_id=id)
            .values("notification_data", "id")
            .order_by("-id")
            .first()
        )
        if notification:
            errormessage = notification.get("notification_data")
            if "'error_user_msg'" in errormessage:
                start_index = errormessage.find("'error_user_msg'")
                end_index = errormessage.find("',", start_index)
                substring = errormessage[start_index + 18 : end_index - 1]
                errormessage = substring.strip("").replace("'", "")
            elif "'message'" in errormessage:
                start_index = errormessage.find("'message'")
                end_index = errormessage.find("',", start_index)
                substring = errormessage[start_index + 12 : end_index]
                errormessage = substring.strip("").replace("'", "")
            else:
                errormessage = errormessage.replace("\n", "")
        else:
            errormessage = "The error message is inaccessible."
        final_result = errormessage
        return final_result
