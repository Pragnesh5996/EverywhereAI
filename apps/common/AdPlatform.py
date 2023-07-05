from abc import ABC, abstractmethod
from apps.error_notifications.models import NotificationLogs
from datetime import datetime as dt


class AdPlatform(ABC):
    @abstractmethod
    def __init__(self, debug_mode):
        """
        Populates auth key and checks if this key is still valid
        Parameters:
        string: Database connection
        """
        self.debug_mode = debug_mode

    def handleError(self, reason, message, priority="Low", scheduler_id=None):
        subject = reason
        self.debugPrint(f"Error: {message}")
        if priority == "Low":
            NotificationLogs.objects.create(
                type_notification=subject,
                notification_data=message,
                email_sent="No",
                scheduler_id=scheduler_id,
                notification_sent_on=dt.now(),
            )
        else:
            NotificationLogs.objects.create(
                type_notification=subject,
                notification_data=message,
                email_sent="No",
                priority=priority,
                scheduler_id=scheduler_id,
                notification_sent_on=dt.now(),
            )

    def debugPrint(self, message):
        now = dt.now()
        now = now.strftime("%d %b %H:%M:%S")
        if self.debug_mode:
            print(f"{now}: {message}")

    @abstractmethod
    def initializer(self):
        """
        initialises database by getting data on all ads, groups and campaings from the api. Then it pushes all data to database. Prevents duplicates.
        """
        pass

    def scheduler(self):
        """
        Schedules new adsets found in ad_scheduler table in database
        """
        pass

    def get_report_day(self, start_date, end_date):
        """
        Get spend report from API

        start_date (Datetime): start date of the report
        end_date (Datetime): end date of the report

        return: report in the form of a list containing dicts like: {'adgroup_id': '...', 'spend': '...'}

        """
        pass

    def updateAdGroup(self, bid, budget, adgroup_id, campaign_id):
        """
        Update adset with new Bid and/or Budget

        bid (Decimal): new bid. None if it should not be changed
        budget (Decimal): new budget. None if it should not be changed
        adgroup_id (str): ID of adgroup to update
        campaign_id: ID of campaign the adgroup belongs to

        If both budget and bid are Null, the adset should be turned off/paused

        return: -

        """
        pass
