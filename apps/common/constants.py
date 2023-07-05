class PlatFormType:
    TIKTOK = "Tiktok"
    FACEBOOK = "Facebook"
    SNAPCHAT = "Snap"
    GOOGLE = "Google"
    LINKFIRE = "Linkfire"

    CHOICES = (
        (TIKTOK, "Tiktok"),
        (FACEBOOK, "Facebook"),
        (SNAPCHAT, "Snap"),
        (GOOGLE, "Google"),
        (LINKFIRE, "Linkfire"),
    )


class RoleType:
    ADMIN = "Admin"  # Admin (all permissions)
    CREATOR = "Creator"  # Creator (creative generator only)
    SCHEDULER = (
        "Scheduler"  # Scheduler (creative generator + auto scheduler + auto optimize)
    )


class SocialAccountType:
    NORMAL = 0
    GOOGLE = 1
    FACEBOOK = 2

    CHOICES = (
        (NORMAL, "normal"),
        (GOOGLE, "google"),
        (FACEBOOK, "facebook"),
    )


class GenderType:
    OTHERS = 0
    MALE = 1
    FEMALE = 2

    CHOICES = (
        (OTHERS, "others"),
        (MALE, "male"),
        (FEMALE, "female"),
    )


class AdAccountActiveType:
    NO = 0
    Pending = 1
    Yes = 2

    CHOICES = (
        (NO, "no"),
        (Pending, "pending"),
        (Yes, "yes"),
    )


class CreativeType:
    VIDEO = "Video"
    IMAGE = "Image"
    SPARK = "Spark"

    CHOICES = ((VIDEO, "Video"), (IMAGE, "Image"), (SPARK, "Spark"))


class PlacementType:
    POST = "Post"
    STORY = "Story"
    REELS = "Reels"
    OTHER = "Other"

    CHOICES = ((POST, "Post"), (STORY, "Story"), (REELS, "Reels"), (OTHER, "Other"))


class AdvantageplacementType:
    FACEBOOK_FEED = "Facebook_Feed"
    FACEBOOK_REELS = "Facebook_Reels"
    FACEBOOK_STORY = "Facebook_Story"
    INSTAGRAM_STREAM = "Instagram_Stream"
    INSTAGRAM_REELS = "Instagram_Reels"
    INSTAGRAM_STORY = "Instagram_Story"
    DEFAULT = "Default"
    PLACEMENT_TIKTOK = "Placement_tiktok"
    AUTOMATIC = "Automatic"

    CHOICES = (
        (FACEBOOK_FEED, "Facebook_Feed"),
        (FACEBOOK_REELS, "Facebook_Reels"),
        (FACEBOOK_STORY, "Facebook_Story"),
        (INSTAGRAM_STREAM, "Instagram_Stream"),
        (INSTAGRAM_REELS, "Instagram_Reels"),
        (INSTAGRAM_STORY, "Instagram_Story"),
        (DEFAULT, "Default"),
        (PLACEMENT_TIKTOK, "placement_tiktok"),
        (AUTOMATIC, "Automatic"),
    )


class PublishedContentType:
    COLLECT_VIDEO_ONLY = "collect_video_only"
    COLLECT_VIDEO_AND_POST = "collect_video_and_post"

    CHOICES = (
        (COLLECT_VIDEO_ONLY, "creator_platform"),
        (COLLECT_VIDEO_AND_POST, "collect_video_and_post"),
    )


class ApprovalStatus:
    """
    approval_needed -> creator_post_pending -> post_confirmation_pending -> approved || declined (feedback)
    """

    APPROVAL_NEEDED = "approval_needed"
    CREATOR_POST_PENDING = "creator_post_pending"
    POST_CONFIRMATION_PENDING = "post_confirmation_pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

    CHOICES = (
        (APPROVAL_NEEDED, "approval_needed"),
        (CREATOR_POST_PENDING, "creator_post_pending"),
        (POST_CONFIRMATION_PENDING, "post_confirmation_pending"),
        (ACCEPTED, "accepted"),
        (DECLINED, "declined"),
    )


class MilestoneProgess:
    """
    Completed || InProgress
    """

    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"

    CHOICES = (
        (COMPLETED, "completed"),
        (IN_PROGRESS, "in_progress"),
    )


class PayoutStatus:
    """
    ready_for_payout || paid_out
    """

    READY_FOR_PAYOUT = "ready_for_payout"
    PAID_OUT = "paid_out"
    PENDING = "pending"
    DECLINED = "declined"

    CHOICES = (
        (READY_FOR_PAYOUT, "ready_for_payout"),
        (PAID_OUT, "paid_out"),
        (PENDING, "pending"),
        (DECLINED, "declined"),
    )


class DimensionType:
    VERTICAL = "Vertical"
    HORIZONTAL = "Horizontal"
    SQUARE = "Square"

    CHOICES = (
        (VERTICAL, "Vertical"),
        (HORIZONTAL, "Horizontal"),
        (SQUARE, "Square"),
    )


class MPlatFormType:
    TIKTOK = "Tiktok"
    INSTAGRAM = "Instagram"
    SNAPCHAT = "Snapchat"

    CHOICES = (
        (TIKTOK, "Tiktok"),
        (INSTAGRAM, "Instagram"),
        (SNAPCHAT, "Snapchat"),
    )


class ScraperConnectionType:
    SPOTIFYSCRAPER = 0
    LINKFIRESCRAPER = 1

    CHOICES = ((SPOTIFYSCRAPER, "SpotifyScraper"), (LINKFIRESCRAPER, "LinkfireScraper"))


class ProgressType:
    NOTSTARTED = 0
    INPROGRESS = 1
    FAILED = 2
    SUCCESS = 3

    CHOICES = (
        (NOTSTARTED, "Not Started"),
        (INPROGRESS, "InProgress"),
        (FAILED, "Failed"),
        (SUCCESS, "Success"),
    )


class ConversationEvent:
    TIKTOK = [{
        "ON_WEB_ORDER":"ON_WEB_ORDER",
        "ON_WEB_CART":"ON_WEB_CART",
        "INITIATE_ORDER":"INITIATE_ORDER",
        "ON_WEB_DETAIL":"ON_WEB_DETAIL",
        "SHOPPING":"SHOPPING"}
    ]
    FACEBOOK = [
        {"PURCHASE":"PURCHASE",
        "ADD_TO_CART":"ADD_TO_CART",
        "INITIATE_CHECKOUT":"INITIATE_CHECKOUT",
        "VIEW_CONTENT":"INITIATE_CHECKOUT",
        "ADD_PAYMENT_INFO":"ADD_PAYMENT_INFO",
        "LEAD":"LEAD"}
    ]
    SNAPCHAT = [{
        "PIXEL_PURCHASE":"PIXEL_PURCHASE",
        "PIXEL_ADD_TO_CART":"PIXEL_ADD_TO_CART",
        "PIXEL_PAGE_VIEW":"PIXEL_PAGE_VIEW",
        "PIXEL_SIGNUP":"PIXEL_SIGNUP",
        "STORY_OPENS":"STORY_OPENS",
        "IMPRESSIONS":"IMPRESSIONS",
        "SWIPES":"SWIPES",
        "USES":"USES",
        "VIDEO_VIEWS":"VIDEO_VIEWS",
        "VIDEO_VIEWS_15_SEC":"VIDEO_VIEWS_15_SEC"
    }]


class Marketplace:
    creator_percentage = {"display_name": 25, "profile_picture": 25, "platform": 25}
    brand_percentage = {"brand_name": 34, "brand_description": 33, "brand_logo": 33}
    platforms = ["Instagram", "Tiktok", "Snapchat"]
    milestone_percentage = [10, 37, 77, 100]
    encryption_type = "original"
    social_platform = {"Instagram": None, "Tiktok": None, "Snapchat": None}


class JobStatus:
    ACTIVE = "active"
    CLOSED = "closed"

    CHOICES = (
        (ACTIVE, "active"),
        (CLOSED, "closed"),
    )


class Timeformat:
    ISO8601 = "%Y-%m-%d %H:%M:%S"
    ISO8601DATEFORMAT = "%Y-%m-%d"
    ISO8601DAYEND = "%Y-%m-%d 23:59:59"
    TIMEZONEDESIGNATOR_START = "T00:00:00Z"
    TIMEZONEDESIGNATOR_END = "T23:59:59Z"
    WeekYearFormat = "Week %W (%Y)"
    ISO_8601_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


# FacebookEventMap = {
#     "Purchase": "PURCHASE",
#     "Content View": "VIEW_CONTENT",
#     "Initiated Checkout": "INITIATE_CHECKOUT",
#     "Add to Cart": "ADD_TO_CART",
#     "Add Payment Info": "ADD_PAYMENT_INFO",
#     "Lead": "LEAD",
# }

FacebookEventMap = {
    "PURCHASE": "PURCHASE",
    "VIEW_CONTENT": "VIEW_CONTENT",
    "INITIATED_CHECKOUT": "INITIATED_CHECKOUT",
    "ADD_TO_CART": "ADD_TO_CART",
    "ADD_PAYMENT_INFO": "ADD_PAYMENT_INFO",
    "LEAD": "LEAD",
}

FacebookBidStrategyMap = {
    "Bid": "LOWEST_COST_WITH_BID_CAP",
    "Lowestcost": "LOWEST_COST_WITHOUT_CAP",
}
FacebookPlacementMap = {"Post": ["stream"], "Story": ["story"], "Reels": ["reels"]}

FacebookObjectiveMap = {
    "Traffic": "LINK_CLICKS",
    "App_installs": "APP_INSTALLS",
    "Conversions": "CONVERSIONS",
}

# SnapchatEventMap = {
#     "Purchase": "PIXEL_PURCHASE",
#     "Page View": "PIXEL_PAGE_VIEW",
#     "Sign up": "PIXEL_SIGNUP",
#     "Add to cart": "PIXEL_ADD_TO_CART",
#     "Story Opens": "STORY_OPENS",
#     "Impressions": "IMPRESSIONS",
#     "Swipes / Clicks": "SWIPES",
# }
SnapchatEventMap = {
    "PIXEL_PURCHASE": "PIXEL_PURCHASE",
    "PIXEL_PAGE_VIEW": "PIXEL_PAGE_VIEW",
    "PIXEL_SIGNUP": "PIXEL_SIGNUP",
    "PIXEL_ADD_TO_CART": "PIXEL_ADD_TO_CART",
    "STORY_OPENS": "STORY_OPENS",
    "IMPRESSIONS": "IMPRESSIONS",
    "SWIPES": "SWIPES",
    "VIDEO_VIEWS_15_SEC": "VIDEO_VIEWS_15_SEC",
    "USES": "USES",
    "VIDEO_VIEWS": "VIDEO_VIEWS",
}

SnapchatCreativeTypeMap = {
    "Conversions": "WEB_VIEW",
    "Traffic": "WEB_VIEW",
    "App_installs": "APP_INSTALL",
}

SnapchatCallToActionMap = {"WEB_VIEW": "LISTEN", "APP_INSTALL": "PLAY_GAME"}

SnapchatObjectiveMap = {
    "WEB_VIEW": "Traffic",
    "WEB_CONVERSION": "Conversions",
    "APP_INSTALL": "App_installs",
    "SHOP_VIEW": "shop_view",
}


class StatusType:
    YES = 1
    NO = 0

    CHOICES = (
        (YES, "Yes"),
        (NO, "No"),
    )


TiktokObjectiveMap = {
    "APP_INSTALL": "App_installs",
    "WEB_CONVERSIONS": "Conversions",
    "TRAFFIC": "Traffic",
    "VIDEO_VIEWS": "Video_views",
    "ENGAGEMENT": "Engagement",
    "RF_TRAFFIC": "Rf_traffic",
    "REACH": "Reach",
}
# TiktokEventMap = {
#     "Purchase": "ON_WEB_ORDER",
#     "Content View": "ON_WEB_DETAIL",
#     "Initiated Checkout": "INITIATE_ORDER",
#     "Add to cart": "ON_WEB_CART",
#     "Complete Payment": "SHOPPING",
# }

TiktokEventMap = {
    "ON_WEB_ORDER": "ON_WEB_ORDER",
    "ON_WEB_DETAIL": "ON_WEB_DETAIL",
    "INITIATE_ORDER": "INITIATE_ORDER",
    "ON_WEB_CART": "ON_WEB_CART",
    "SHOPPING": "SHOPPING",
}

BidStrategyMap = {"Bid": "BID_TYPE_CUSTOM", "Lowestcost": "BID_TYPE_NO_BID"}


PlacementTargeting = {
    "Facebook_Feed": ["feed"],
    "Facebook_Reels": ["facebook_reels"],
    "Facebook_Story": ["feed"],
    "Instagram_Stream": ["stream"],
    "Instagram_Reels": ["reels"],
    "Instagram_Story": ["story"],
}


class StripeSubscriptionStatus:
    IN_COMPLETE = "incomplete"
    IN_COMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    FREE_TRIAL = "free trial"


class JobPaymentStatus:
    """
    Completed || Pending
    """

    COMPLETED = "completed"

    CHOICES = ((COMPLETED, "completed"),)


class JobPaymentType:
    """
    Paypal || Card
    """

    PAYPAL = "paypal"
    CARD = "card"

    CHOICES = (
        (PAYPAL, "paypal"),
        (CARD, "card"),
    )


class Webhook_Event_Type:
    Subscription_Created = "customer.subscription.created"
    Subscription_Deleted = "customer.subscription.deleted"
    Subscription_Paused = "customer.subscription.paused"
    Subscription_Updated = "customer.subscription.updated"
    Plan_Created = "plan.created"
    Plan_Deleted = "plan.deleted"
    subscription_renewal = "invoice.upcoming"
    Successfully_paid = "invoice.paid"


class Adspend_Email_Status:
    Active_Status = "active"
