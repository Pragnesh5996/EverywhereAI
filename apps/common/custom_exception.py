from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from apps.error_notifications.models import NotificationLogs


class PlainValidationError(APIException):
    """
    :In PlainValidationError, we will check if the exception being raised is of
    the type dict and then modify the errors format and return that modified errors response
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input."
    default_code = "invalid"

    def __init__(self, detail=None, code=None):
        if not isinstance(detail, dict):
            raise serializers.ValidationError("Invalid Input")
        self.detail = detail


class AmazonS3UploadingException(Exception):
    def __init__(self, message="Amazon s3 uploading issue."):
        self.message = message


class DatabaseRequestException(Exception):
    def __init__(self, message="Could not retrieve data from database"):
        self.message = message


class DatabaseInvalidDataException(Exception):
    def __init__(self, message="Tried to push invalid data to database"):
        self.message = message


class RestrictedPageException(Exception):
    def __init__(
        self, message="The page you tried to post to is restricted for advertising."
    ):
        self.message = message


class SendGridException(Exception):
    def __init__(self, message="Sendgrid mail issue occured."):
        self.message = message


"""
----------------------- FACEBOOK API -----------------------
"""


class FacebookApiUploaderException(Exception):
    def __init__(self, message="Could not upload creative to facebook."):
        self.message = message


class FacebookRequestException(Exception):
    def __init__(self, message="The request you tried was returned with an error."):
        self.message = message


class InitializerContinueException(Exception):
    def __init__(
        self, message="Initializer encountered a problem, continueing to next account"
    ):
        self.message = message


"""
----------------------- TIKTOK API -----------------------
"""


class TiktokApiResponseCodeException(Exception):
    def __init__(self, message="Tiktok api did not return OK message"):
        self.message = message


class TiktokInternalServerException(Exception):
    def __init__(self, message="Tiktok api returned 5xx error"):
        self.message = message


class TiktokApiTimeOutException(Exception):
    def __init__(self, message="Api timed out too many times"):
        self.message = message


class DataTypeStructureException(Exception):
    def __init__(self, message="Data type structure was not correct."):
        self.message = message


class TiktokApiSechulerException(Exception):
    def __init__(self, message="Tiktok api: Could not schedule ad(group)"):
        self.message = message


class TiktokApiUploaderException(Exception):
    def __init__(self, message="Tiktok api: Could not schedule ad(group)"):
        self.message = message


class IllegalAgeFormatException(Exception):
    def __init__(
        self, message="Could not create legal age format from given age range."
    ):
        self.message = message


class APIGetterException(Exception):
    def __init__(self, message="Get function responded with an error."):
        self.message = message


class IDMismatchException(Exception):
    def __init__(self, message="Could not find data matching ID."):
        self.message = message


class InvalidCreativeTypeException(Exception):
    def __init__(
        self,
        message="Encountered unexpected creative type or Recieved invalid creative format.",
    ):
        self.message = message


class ApiNoResponseException(Exception):
    def __init__(self, message="No Api response was found."):
        self.message = message


"""
----------------------- AD OPTIMIZER -----------------------
"""


class NullValueInDatabase(Exception):
    """Raised when a value in the database is NULL when it should not be. Make sure to add the query or location in the message."""

    def __init__(
        self, message="Some value in the Database is NULL where it shouldn't be."
    ):
        self.message = message


class CTRSwingException(Exception):
    """Raised when a large ctr swing has occured."""

    def __init__(self, message="A big ctr swing has occured."):
        self.message = message


"""
----------------------- LINKFIRE API -----------------------
"""


class LinkfireApiResponseCodeException(Exception):
    def __init__(self, message="Linkfire api did not return OK message"):
        self.message = message


class LinkfireApiAccesTokenException(Exception):
    def __init__(self, message="Could not get acces."):
        self.message = message


class LinkfireTooLargeNameException(Exception):
    def __init__(self, message="Name should exceed 999."):
        self.message = message


def handle_error(reason, message):
    """
    Puts an error message in database
    Parameters reason, message (String, String)
    Returns: None
    """
    # notification = {
    #     "reason": reason,
    #     "text_body": message,
    # }
    NotificationLogs.objects.create(
        type_notification=reason,
        notification_data=message,
        notification_sent="No",
    )
