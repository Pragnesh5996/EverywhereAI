import requests
from SF import settings
from apps.common.urls_helper import URLHelper

url_hp = URLHelper()


class SocialAccountOAuth:
    """
    SocialAccountOAuth is a utility class for handling OAuth authentication and authorization flows
    for various social media platforms,including Google, Facebook, Snapchat, and TikTok.
    The class has methods for retrieving access tokens, refresh tokens, and user information from each of the platforms,
    using the provided authorization code and platform-specific client IDs, secrets, and redirect URIs.
    The class also handles HTTP responses and any errors that may occur during the OAuth process.
    """

    def __init__(self, code=None) -> None:
        self.code = code

    def google_login_verification(self, api=None):
        if api == "social-signup":
            redirect_uri = url_hp.GOOGLE_SIGNUP_CALLBACK_URL
        elif api == "google-connect":
            redirect_uri = url_hp.GOOGLE_AD_PLATFORM_CALLBACK_URL
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code": self.code,
        }

        response = requests.post(
            url_hp.GOOGLE_ACCESS_TOKEN_USING_CODE_URL, params=params
        )
        access_token, refresh_token = None, None
        if response.status_code == 200:
            response = response.json()
            access_token, refresh_token = response.get("access_token"), response.get(
                "refresh_token"
            )
            response = requests.get(
                url_hp.GOOGLE_USERINFO_URL,
                params={"access_token": access_token},
            )
        return response, access_token, refresh_token

    def facebook_login_verification(self, api=None):
        if api == "social-signup":
            redirect_uri = url_hp.FACEBOOK_SIGNUP_CALLBACK_URL
        elif api == "facebook-connect":
            redirect_uri = url_hp.FACEBOOK_AD_PLATFORM_CALLBACK_URL
        params = {
            "client_id": settings.FACEBOOK_APP_ID,
            "client_secret": settings.FACEBOOK_SECRET_ID,
            "redirect_uri": redirect_uri,
            "code": self.code,
        }
        response = requests.get(
            url_hp.FACEBOOK_ACCESS_TOKEN_USING_CODE_URL, params=params
        )
        access_token = None
        if response.status_code == 200:
            access_token = response.json().get("access_token")

            params = response.json()
            params.update({"fields": "id,first_name,last_name,email,picture"})
            response = requests.get(url_hp.FACEBOOK_ME_URL, params=params)

        return response, access_token, None

    def snapchat_login_verification(self):
        # use main bussiness account client_id, client_secret, redirect_uri (not use for developer account)
        params = {
            "grant_type": "authorization_code",
            "client_id": settings.SNAPCHAT_CLIENT_ID,
            "client_secret": settings.SNAPCHAT_CLIENT_SECRET_ID,
            "redirect_uri": url_hp.SNAPCHAT_AD_PLATFORM_CALLBACK_URL,
            "code": self.code,
        }
        response = requests.post(
            url_hp.SNAPCHAT_ACCESS_TOKEN_USING_CODE_URL, params=params
        )
        access_token, refresh_token = None, None
        if response.status_code == 200:
            access_token, refresh_token = response.json().get(
                "access_token"
            ), response.json().get("refresh_token")

            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url_hp.SNAPCHAT_ME_URL, headers=headers)

        return response, access_token, refresh_token

    def tiktok_login_verification(self):
        params = {
            "secret": settings.TIKTOK_SECRET_ID,
            "app_id": settings.TIKTOK_APP_ID,
            "auth_code": self.code,
        }
        response = requests.post(
            url_hp.TIKTOK_ACCESS_TOKEN_USING_CODE_URL,
            params=params,
        )
        access_token = response.json().get("data").get("access_token")
        params = {"fields": "email,display_name,avatar_url"}
        headers = {"Access-Token": access_token}
        response = requests.get(
            url_hp.TIKTOK_USERINFO_URL,
            headers=headers,
            params=params,
        )
        return response, access_token, None

    def marketplace_facebook_login_verification(self):
        params = {
            "client_id": settings.MP_FACEBOOK_APP_ID,
            "client_secret": settings.MP_FACEBOOK_SECRET_ID,
            "redirect_uri": url_hp.MP_FACEBOOK_REDIRECT_URL,
            "code": self.code,
        }
        response = requests.get(
            url_hp.FACEBOOK_ACCESS_TOKEN_USING_CODE_URL, params=params
        )
        access_token = None
        if response.status_code == 200:
            access_token = response.json().get("access_token")

            params = response.json()
            params.update({"fields": "id,first_name,last_name,email"})
            response = requests.get(url_hp.FACEBOOK_ME_URL, params=params)

        return response, access_token, None

    def marketplace_tiktok_login_verification(self):

        params = {
            "client_secret": settings.MP_TIKTOK_SECRET_ID,
            "client_id": settings.MP_TIKTOK_APP_ID,
            "grant_type": "authorization_code",
            "auth_code": self.code,
        }
        response = requests.post(
            url_hp.MP_TIKTOK_CREATE_TOKEN_USING_CODE_URL, json=params
        )
        access_token = response.json().get("data").get("access_token")
        creator_id = response.json().get("data").get("creator_id")
        user_params = {
            "business_id": creator_id,
            "fields": '[ "audience_countries", "audience_genders", "followers_count", "display_name", "username", "likes"]',
        }
        headers = {"Access-Token": access_token}
        user_response = requests.get(
            url_hp.MP_TIKTOK_BUSINESS_INFO,
            headers=headers,
            params=user_params,
        )
        return response, user_response
