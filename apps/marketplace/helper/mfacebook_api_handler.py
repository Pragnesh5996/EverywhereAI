from SF import settings
from apps.common.urls_helper import URLHelper
from apps.marketplace.models import SocialAuthkey, SocialBusiness, SocialProfile
from apps.common.constants import MPlatFormType
import requests

url_hp = URLHelper()


class MFacebookAPI:
    def __init__(self, user, access_token, refresh_token, profile):
        """
        Populates auth key and checks if this key is still valid
        Parameters:
        string: Database connection
        """
        self.secret = settings.MP_FACEBOOK_SECRET_ID
        self.app_id = settings.MP_FACEBOOK_APP_ID
        self.user = user
        self.profile = profile
        self.access_token = access_token
        self.refresh_token = refresh_token

    def get_business_id(self):
        """
        fetch live data for facebook bussinesses and ad_account,user,pages then all stuff push to database(profile,authkey,bussinesess and adaccount table)
        """
        r = requests.get(
            url=f"{url_hp.FACEBOOK_v16_URL}me/accounts",
            params={"access_token": self.access_token},
        )
        response = r.json()

        if page_data := response.get("data"):
            if page_id := page_data[0].get("id"):
                br = requests.get(
                    url=f"{url_hp.FACEBOOK_v16_URL}{page_id}",
                    params={
                        "fields": "instagram_business_account",
                        "access_token": self.access_token,
                    },
                )
                business_response = br.json()
                business_account = business_response.get("instagram_business_account", None)
                if business_account is not None:
                    if business_id := business_account.get("id", None):
                        r = requests.get(
                            url=f"{url_hp.FACEBOOK_v16_URL}/{business_id}",
                            params={
                                "fields": "username",
                                "access_token": self.access_token,
                            },
                        )
                        username = r.json()
                        SocialInstagramData = SocialProfile.objects.filter(user=self.user, platforms=MPlatFormType.INSTAGRAM)
                        if not SocialInstagramData:
                            profile, _ = SocialProfile.objects.update_or_create(
                                platforms=MPlatFormType.INSTAGRAM,
                                user_id=self.user,
                                defaults={
                                    "first_name": self.profile.get("first_name"),
                                    "last_name": self.profile.get("last_name"),
                                    "username":  username.get("username"),
                                },
                            )
                            SocialAuthkey.objects.update_or_create(
                                profile=profile,
                                defaults={
                                    "access_token": self.access_token,
                                    "refresh_token": self.refresh_token,
                                },
                            )
                            SocialBusiness.objects.update_or_create(
                                profile=profile,
                                defaults={"fb_page_id": page_id, "business_id": business_id},
                            )
                            return (
                                False,
                                "You have successfully connected your Facebook account.",
                            )
                        else:
                            return (
                                True,
                                "You have already connected your Facebook account.",
                            )
                    else:
                        raise Exception (
                            "It looks like this account is not a business account. Please select a Facebook business account to connect to the Creator Marketplace or go to Facebook to convert your account to a business account.",
                        )
                else:
                    raise Exception(
                        "Something went wrong while connecting your Instagram account. Please try again.",
                    )
        else:
            raise Exception (
                "Something went wrong while connecting your Facebook account. Please try again.",
            )


class MFacebookMediaId:
    def __init__(self, social_post_link, user_id):

        self.social_post_link = social_post_link
        self.user = user_id
        self.profile = self.get_profile()
        self.access_token = self.get_authkey()
        self.business_id = self.get_business_id()

    def get_profile(self):
        """
        Fetches profile_id from database to get business_id
        Returns:
        string: profile_id
        """
        try:
            return SocialProfile.objects.get(user=self.user).id
        except Exception:
            raise Exception("Instagram is not integrate with this creator.")

    def get_business_id(self):
        """
        Fetches business from database through profile_id
        Returns:
        string: business_id
        """
        try:
            return SocialBusiness.objects.get(profile=self.profile).business_id
        except Exception:
            raise Exception("Business id is not exist.")

    def get_authkey(self):
        """
        Fetches authkey from database to populate this parent class
        Returns:
        string: Authorization key
        """
        try:
            return SocialAuthkey.objects.get(profile=self.profile).access_token
        except Exception:
            raise Exception("Auth key is not exist.")

    def get_media_id(self):

        r = requests.get(
            url=f"{url_hp.FACEBOOK_v16_URL}{self.business_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,shortcode,permalink",
                "access_token": self.access_token,
            },
        )
        response = r.json()
        media_id = None
        for item in response["data"]:
            if item["shortcode"] == self.social_post_link.split("/")[4]:
                media_id = item["id"]
        return media_id if media_id else None
