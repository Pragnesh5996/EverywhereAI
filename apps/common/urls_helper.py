from SF import settings


class URLHelper:
    SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
    FRONTEND_FORGOT_PASSWORD_URL = "http://localhost:3000/reset-password"
    AWS_CREATIVE_BASE_URL = "https://fruitsagency-bucket.s3.eu-west-3.amazonaws.com"

    GOOGLE_ACCESS_TOKEN_USING_CODE_URL = "https://accounts.google.com/o/oauth2/token"
    GOOGLE_SIGNUP_CALLBACK_URL = "http://localhost:3000/register"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
    GOOGLE_AD_PLATFORM_CALLBACK_URL = "http://localhost:3000/platform"

    FACEBOOK_ACCESS_TOKEN_USING_CODE_URL = (
        "https://graph.facebook.com/v2.10/oauth/access_token"
    )
    FACEBOOK_SIGNUP_CALLBACK_URL = "http://localhost:3000/register"
    FACEBOOK_ME_URL = "https://graph.facebook.com/v15.0/me"
    FACEBOOK_AD_PLATFORM_CALLBACK_URL = "http://localhost:3000/platform"
    FACEBOOK_SEARCH_INTREST_URL = "https://graph.facebook.com/v14.0/search"
    FACEBOOK_BUSSINESSES_URL = (
        "https://graph.facebook.com/v14.0/me/businesses?fields=name,verification_status"
    )
    FACEBOOK_ACCESS_TOKEN_USING_CREDENTIALS_URL = (
        "https://graph.facebook.com/oauth/access_token"
    )
    FACEBOOK_DEBUG_TOKEN = "https://graph.facebook.com/debug_token"
    FACEBOOK_v16_URL = "https://graph.facebook.com/v16.0/"
    FACEBOOK_v15_URL = "https://graph.facebook.com/v15.0/"
    FACEBOOK_v14_URL = "https://graph.facebook.com/v14.0/"

    MP_FACEBOOK_REDIRECT_URL = "https://app.everywhere-ai.com/my-creator-info"
    MP_FACEBOOK_ACCESS_TOKEN = "https://graph.facebook.com/v2.10/oauth/access_token"

    SNAPCHAT_ACCESS_TOKEN_USING_CODE_URL = (
        "https://accounts.snapchat.com/login/oauth2/access_token"
    )
    SNAPCHAT_ACCESS_TOKEN_USING_REFRESH_TOKEN_URL = (
        "https://accounts.snapchat.com/login/oauth2/access_token"
    )
    SNAPCHAT_ME_URL = "https://adsapi.snapchat.com/v1/me"
    SNAPCHAT_AD_PLATFORM_CALLBACK_URL = "http://localhost:3000/platform"
    SNAPCHAT_INTREST_URL = "https://adsapi.snapchat.com/v1/targeting/interests/scls"
    SNAPCHAT_ORGANIZATIONS_WITH_AD_ACCOUNTS_URL = (
        "https://adsapi.snapchat.com/v1/me/organizations?with_ad_accounts=true"
    )
    SNAPCHAT_v1_URL = "https://adsapi.snapchat.com/v1"

    LINKFIRE_CONNECT_URL = "https://auth.linkfire.com/identity/connect/token"
    LINKFIRE_BASE_URL = "https://api.linkfire.com/settings/boards/"
    LINKFIRE_BOARDS_URL = "https://api.linkfire.com/settings/boards"

    LINKFIRE_CAMPAIGNS_URL = "https://api.linkfire.com/campaigns/boards/"
    LINKFIRE_MEDIA_SERVICES_URL = (
        "https://api.linkfire.com/settings/mediaservices?pageSize=1000&page="
    )

    # Tiktok Url
    TIKTOK_ACCESS_TOKEN_USING_CODE_URL = (
        "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
    )
    TIKTOK_USERINFO_URL = "https://business-api.tiktok.com/open_api/v1.3/user/info/"
    TIKTOK_RECOMMENED_URL = (
        "https://business-api.tiktok.com/open_api/v1.3/tool/interest_keyword/recommend/"
    )
    TIKTOK_IDENTITY_URL = "https://business-api.tiktok.com/open_api/v1.3/identity/get/"
    TIKTOK_APPLIST_URL = "https://business-api.tiktok.com/open_api/v1.3/app/list/"
    TIKTOK_ADVERTISER_ACCOUNT_URL = (
        "https://business-api.tiktok.com/open_api/v1.3/oauth2/advertiser/get"
    )
    TIKTOK_ADVERTISER_ACCOUNT_INFO_URL = (
        "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
    )
    TIKTOK_UPLOAD_CREATIVE_VIDEO_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/file/video/ad/upload/"
    )
    TIKTOK_UPLOAD_CREATIVE_IMAGE_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/file/image/ad/upload/"
    )
    TIKTOK_CREATE_CAMPAIGN_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/campaign/create/"
    )
    TIKTOK_CREATE_ADGROUP_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/adgroup/create/"
    )
    TIKTOK_ADGROUP_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/adgroup/update/status/"
    )
    TIKTOK_AD_URL = "https://business-api.tiktok.com/open_api/v1.2/ad/create/"
    TIKTOK_AD_GET_URL = "https://business-api.tiktok.com/open_api/v1.2/ad/get/"
    TIKTOK_UPDATE_CAMPAIGN_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/campaign/update/status/"
    )
    TIKTOK_THUMBNAIL_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/file/video/suggestcover/"
    )
    TIKTOK_TT_VIDEO_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/tt_video/authorize/"
    )
    TIKTOK_TT_VIDEO_INFO_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/tt_video/info/"
    )
    TIKTOK_AD_UPDATE_URL = "https://business-api.tiktok.com/open_api/v1.2/ad/update/"
    TIKTOK_ADGROUP_UPDATE_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/adgroup/get/"
    )
    TIKTOK_GET_CAMPAIGN_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/campaign/get/"
    )
    TIKTOK_GET_PIXEL_URL = "https://business-api.tiktok.com/open_api/v1.2/pixel/list/"
    TIKTOK_CUSTOM_AUDIENCE_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/dmp/custom_audience/list/"
    )
    TIKTOK_CUSTOM_AUDIENCE_GET_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/dmp/custom_audience/get/"
    )
    TIKTOK_INTEREST_CATEGORY_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/tools/interest_category/"
    )
    TIKTOK_TARGET_RECOMMEND_TAGS_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/tools/target_recommend_tags/"
    )
    TIKTOK_INTEREST_KEYWORD_URL = "https://business-api.tiktok.com/open_api/v1.2/tools/interest_keyword/recommend/"
    TIKTOK_INTEGRATED_URL = (
        "https://business-api.tiktok.com/open_api/v1.2/reports/integrated/get/"
    )
    MP_TIKTOK_CREATE_TOKEN_USING_CODE_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/creator_token/?business=tt_user"
    MP_TIKTOK_BUSINESS_INFO = (
        "https://business-api.tiktok.com/open_api/v1.3/business/get/"
    )
    MP_TIKTOK_VIEW_COUNT_INFO = (
        "https://business-api.tiktok.com/open_api/v1.3/business/video/list/"
    )
    MP_TIKTOK_REFRESH_TOKEN = "https://open-api.tiktok.com/oauth/refresh_token"

    # Linkfire Scraper URL
    LINKFIRE_SCRAPER_BASE_URL = "https://app.prod.linkfire.co/api/"
    LINKFIRE_SCRAPER_TOKEN_URL = (
        "https://authentication-internal-api.linkfire.com/identity/connect/token"
    )
    LINKFIRE_SCRAPER_BOARDS_URL = "https://app.prod.linkfire.co/api/organisation/boards?filter.isActive=true&sort=-VisitDate"
    FRONTEND_REGISTER_URL = "https://app.everywhere-ai.com"
    VDOCIPHER_URL = "https://dev.vdocipher.com/api"

    DEFAULT_SCAPER_GROUP_PROFILE_PICTURE = "https://fruitsagency-bucket.s3.eu-west-3.amazonaws.com/upload_genre_profile/DefaultProfile.png"

    # Stripe Payment URL
    CHECKOUT_PAYMENT_SUCCESS_URL = (
        "https://app.everywhere-ai.com/account-settings?status=success#your_plan"
    )
    CHECKOUT_PAYMENT_CANCEL_URL = (
        "https://app.everywhere-ai.com/account-settings?status=failure#your_plan"
    )

    CURRANCY_EXCHANEG_RATE = "https://v6.exchangerate-api.com/v6"

    FE_SUBSCRIPTION_PAGE_URL = (
        "https://app.everywhere-ai.com/account-settings#your_plan"
    )

    def __init__(self):
        if settings.ENV == "production":
            self.SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
            self.FRONTEND_FORGOT_PASSWORD_URL = (
                "https://app.everywhere-ai.com/reset-password"
            )
            self.AWS_CREATIVE_BASE_URL = (
                "https://fruitsagency-bucket.s3.eu-west-3.amazonaws.com"
            )

            self.GOOGLE_ACCESS_TOKEN_USING_CODE_URL = (
                "https://accounts.google.com/o/oauth2/token"
            )
            self.GOOGLE_SIGNUP_CALLBACK_URL = "https://app.everywhere-ai.com/register"
            self.GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
            self.GOOGLE_AD_PLATFORM_CALLBACK_URL = (
                "https://app.everywhere-ai.com/platform"
            )

            self.FACEBOOK_ACCESS_TOKEN_USING_CODE_URL = (
                "https://graph.facebook.com/v2.10/oauth/access_token"
            )
            self.FACEBOOK_SIGNUP_CALLBACK_URL = "https://app.everywhere-ai.com/register"
            self.FACEBOOK_ME_URL = "https://graph.facebook.com/v15.0/me"
            self.FACEBOOK_AD_PLATFORM_CALLBACK_URL = (
                "https://app.everywhere-ai.com/platform"
            )
            self.FACEBOOK_SEARCH_INTREST_URL = "https://graph.facebook.com/v14.0/search"
            self.FACEBOOK_BUSSINESSES_URL = (
                "https://graph.facebook.com/v16.0/me/businesses"
            )
            self.FACEBOOK_ACCESS_TOKEN_USING_CREDENTIALS_URL = (
                "https://graph.facebook.com/oauth/access_token"
            )
            self.FACEBOOK_DEBUG_TOKEN = "https://graph.facebook.com/debug_token"
            self.FACEBOOK_v16_URL = "https://graph.facebook.com/v16.0/"
            self.FACEBOOK_v15_URL = "https://graph.facebook.com/v15.0/"
            self.FACEBOOK_v14_URL = "https://graph.facebook.com/v14.0/"
            self.MP_FACEBOOK_REDIRECT_URL = (
                "https://app.everywhere-ai.com/my-creator-info"
            )
            self.MP_FACEBOOK_ACCESS_TOKEN = (
                "https://graph.facebook.com/v2.10/oauth/access_token"
            )

            self.SNAPCHAT_ACCESS_TOKEN_USING_CODE_URL = (
                "https://accounts.snapchat.com/login/oauth2/access_token"
            )
            self.SNAPCHAT_ACCESS_TOKEN_USING_REFRESH_TOKEN_URL = (
                "https://accounts.snapchat.com/login/oauth2/access_token"
            )
            self.SNAPCHAT_ME_URL = "https://adsapi.snapchat.com/v1/me"
            self.SNAPCHAT_AD_PLATFORM_CALLBACK_URL = (
                "https://app.everywhere-ai.com/platform"
            )
            self.SNAPCHAT_INTREST_URL = (
                "https://adsapi.snapchat.com/v1/targeting/interests/scls"
            )
            self.SNAPCHAT_ORGANIZATIONS_WITH_AD_ACCOUNTS_URL = (
                "https://adsapi.snapchat.com/v1/me/organizations?with_ad_accounts=true"
            )
            self.SNAPCHAT_v1_URL = "https://adsapi.snapchat.com/v1"
            self.LINKFIRE_CONNECT_URL = (
                "https://auth.linkfire.com/identity/connect/token"
            )
            self.LINKFIRE_BASE_URL = "https://api.linkfire.com/settings/boards/"
            self.LINKFIRE_BOARDS_URL = "https://api.linkfire.com/settings/boards"

            self.LINKFIRE_CAMPAIGNS_URL = "https://api.linkfire.com/campaigns/boards/"
            self.LINKFIRE_MEDIA_SERVICES_URL = (
                "https://api.linkfire.com/settings/mediaservices?pageSize=1000&page="
            )
            # Linkfire Scraper URL
            self.LINKFIRE_SCRAPER_BASE_URL = "https://app.prod.linkfire.co/api/"
            self.LINKFIRE_SCRAPER_TOKEN_URL = "https://authentication-internal-api.linkfire.com/identity/connect/token"
            self.LINKFIRE_SCRAPER_BOARDS_URL = "https://app.prod.linkfire.co/api/organisation/boards?filter.isActive=true&sort=-VisitDate"

            # Tiktok Url
            self.TIKTOK_ACCESS_TOKEN_USING_CODE_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/oauth2/access_token/"
            )
            self.TIKTOK_USERINFO_URL = (
                "https://business-api.tiktok.com/open_api/v1.3/user/info/"
            )
            self.TIKTOK_RECOMMENED_URL = "https://business-api.tiktok.com/open_api/v1.3/tool/interest_keyword/recommend/"
            self.TIKTOK_IDENTITY_URL = (
                "https://business-api.tiktok.com/open_api/v1.3/identity/get/"
            )
            self.TIKTOK_APPLIST_URL = (
                "https://business-api.tiktok.com/open_api/v1.3/app/list/"
            )
            self.TIKTOK_ADVERTISER_ACCOUNT_URL = (
                "https://business-api.tiktok.com/open_api/v1.3/oauth2/advertiser/get"
            )
            self.TIKTOK_ADVERTISER_ACCOUNT_INFO_URL = (
                "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
            )
            self.TIKTOK_UPLOAD_CREATIVE_VIDEO_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/file/video/ad/upload/"
            )
            self.TIKTOK_UPLOAD_CREATIVE_IMAGE_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/file/image/ad/upload/"
            )
            self.TIKTOK_CREATE_CAMPAIGN_URL = (
                "https://business-api.tiktok.com/open_api/v1.3/campaign/create/"
            )
            self.TIKTOK_CREATE_ADGROUP_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/adgroup/create/"
            )
            self.TIKTOK_ADGROUP_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/adgroup/update/status/"
            )
            self.TIKTOK_AD_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/ad/create/"
            )
            self.TIKTOK_AD_GET_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/ad/get/"
            )
            self.TIKTOK_UPDATE_CAMPAIGN_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/campaign/update/status/"
            )
            self.TIKTOK_THUMBNAIL_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/file/video/suggestcover/"
            )
            self.TIKTOK_TT_VIDEO_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/tt_video/authorize/"
            )
            self.TIKTOK_TT_VIDEO_INFO_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/tt_video/info/"
            )
            self.TIKTOK_AD_UPDATE_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/ad/update/"
            )
            self.TIKTOK_ADGROUP_UPDATE_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/adgroup/get/"
            )
            self.TIKTOK_GET_CAMPAIGN_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/campaign/get/"
            )
            self.TIKTOK_GET_PIXEL_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/pixel/list/"
            )
            self.TIKTOK_CUSTOM_AUDIENCE_URL = "https://business-api.tiktok.com/open_api/v1.2/dmp/custom_audience/list/"
            self.TIKTOK_CUSTOM_AUDIENCE_GET_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/dmp/custom_audience/get/"
            )
            self.TIKTOK_INTEREST_CATEGORY_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/tools/interest_category/"
            )
            self.TIKTOK_TARGET_RECOMMEND_TAGS_URL = "https://business-api.tiktok.com/open_api/v1.2/tools/target_recommend_tags/"
            self.TIKTOK_INTEREST_KEYWORD_URL = "https://business-api.tiktok.com/open_api/v1.2/tools/interest_keyword/recommend/"
            self.TIKTOK_INTEGRATED_URL = (
                "https://business-api.tiktok.com/open_api/v1.2/reports/integrated/get/"
            )
            self.MP_TIKTOK_CREATE_TOKEN_USING_CODE_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/creator_token/?business=tt_user"
            self.MP_TIKTOK_BUSINESS_INFO = (
                "https://business-api.tiktok.com/open_api/v1.3/business/get/"
            )
            self.MP_TIKTOK_VIEW_COUNT_INFO = (
                "https://business-api.tiktok.com/open_api/v1.3/business/video/list/"
            )
            self.MP_TIKTOK_REFRESH_TOKEN = (
                "https://open-api.tiktok.com/oauth/refresh_token"
            )
            # Linkfire Scraper URL
            self.LINKFIRE_SCRAPER_BASE_URL = "https://app.prod.linkfire.co/api/"
            self.LINKFIRE_SCRAPER_TOKEN_URL = "https://authentication-internal-api.linkfire.com/identity/connect/token"
            self.LINKFIRE_SCRAPER_BOARDS_URL = "https://app.prod.linkfire.co/api/organisation/boards?filter.isActive=true&sort=-VisitDate"

            self.FRONTEND_REGISTER_URL = "https://app.everywhere-ai.com/register"
            self.VDOCIPHER_URL = "https://dev.vdocipher.com/api"

            self.DEFAULT_SCAPER_GROUP_PROFILE_PICTURE = "https://fruitsagency-bucket.s3.eu-west-3.amazonaws.com/upload_genre_profile/DefaultProfile.png"

            self.FE_SUBSCRIPTION_PAGE_URL = (
                "https://app.everywhere-ai.com/account-settings#your_plan"
            )
            self.CHECKOUT_PAYMENT_SUCCESS_URL = "https://app.everywhere-ai.com/account-settings?status=success#your_plan"
            self.CHECKOUT_PAYMENT_CANCEL_URL = "https://app.everywhere-ai.com/account-settings?status=failure#your_plan"

            self.CURRANCY_EXCHANEG_RATE = "https://v6.exchangerate-api.com/v6"
