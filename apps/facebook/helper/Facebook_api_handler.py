import os
import time
import random
from datetime import datetime as dt
from datetime import timedelta
import ast
from decimal import Decimal
from SF import settings
from apps.common.constants import (
    PlatFormType,
    AdAccountActiveType,
    FacebookPlacementMap,
    FacebookBidStrategyMap,
    FacebookEventMap,
    FacebookObjectiveMap,
    Timeformat,
    StatusType,
    PlacementTargeting,
)
from apps.common.models import (
    AdAdsets,
    AdCreativeIds,
    AdScheduler,
    Authkey,
    Business,
    AdAccount,
    CustomConversionEvents,
    Language,
    RateLimits,
    AdCampaigns,
    DailyAdspendGenre,
    AdsetInsights,
    Pixels,
    CustomAudiences,
)
import json
import requests
from apps.common.custom_exception import (
    FacebookRequestException,
    DatabaseRequestException,
    RestrictedPageException,
    FacebookApiUploaderException,
)
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adsinsights import AdsInsights
from apps.common import AdPlatform as AP
from apps.facebook.models import (
    FacebookPages,
    FacebookUsers,
    InstagramAccounts,
)
from apps.scraper.models import Settings
from apps.linkfire.models import ScrapeLinkfires
from apps.common.urls_helper import URLHelper
from itertools import groupby

url_hp = URLHelper()


class FacebookAPI(AP.AdPlatform):
    def __init__(self, debug_mode, profile):
        """
        Populates auth key and checks if this key is still valid
        Parameters:
        string: Database connection
        """
        super().__init__(debug_mode)
        self.first_message = True
        self.secret = settings.FACEBOOK_SECRET_ID
        self.app_id = settings.FACEBOOK_APP_ID
        self.profile = profile
        self.access_token = self.get_authkey()
        self.initFacebook()
        self.account = self.is_authorized()
        self.next_page = ""
        self.insight = []
        self.retries = 0

    def initFacebook(self):
        FacebookAdsApi.init(self.app_id, self.secret, self.access_token)

    def handleError(self, reason, message, priority="Low", scheduler_id=None):
        super().handleError(reason, message, priority, scheduler_id)

    def debugPrint(self, message):
        super().debugPrint(message)

    def countryCodeToName(self, country_code):
        """
        Converts country code to full country name
        :param countryCode: country code
        :return: country name
        """
        with open(
            os.path.join(settings.BASE_DIR, "apps/tiktok/files/countries.json"),
            encoding="utf8",
        ) as json_file:
            data = json.load(json_file)
            json_file.close()

            region_list = ["countries", "provinces", "cities"]
            for region in region_list:
                for country in data.get(region):
                    if country["country_code"] == country_code:
                        return country["name"]

            raise Exception(
                f"Country Code could not be matched to country name:, {country_code}"
            )

    def get_authkey(self):
        """
        Fetches authkey from database to populate this parent class
        Returns:
        string: Authorization key
        """
        if authkey := Authkey.objects.filter(profile=self.profile).values(
            "access_token"
        ):
            self.debugPrint(authkey)
            return authkey[0].get("access_token")
        else:
            self.handleError(
                "Facebook Authorization Key Missing",
                f"Authorization Key Missing with profile_id:{self.profile.id}, If you want to use Facebook API, connect your account via the web app.",
            )

    def is_authorized(self):
        """
        Get business account
        Returns: Facebook business object
        """
        try:
            params = {}
            url = f"{url_hp.FACEBOOK_v16_URL}me"
            response = self.get(url, params)
            return response["id"]
        except FacebookRequestException as e:
            # if self.check_valid_token(str(e)):
            #     print(
            #         "[facebook/authorization]this is wrong token please reconnecte in FE"
            #     )
            #     time.sleep(5 * 60)
            #     self.is_authorized()
            # raise FacebookRequestException(f"A Facebook request error occured:\n{e}")
            pass

    def check_valid_token(self, message):
        """
        Check if the token is valid or not
        """
        if (
            message.get("code") == 190
            and message.get("error_subcode") == 460
            and message.get("type") == "OAuthException"
        ):
            return True
        else:
            return False

    def get_campaign(self, account):
        """
        Get all campaigns for the given adAccount
        Account: FB adaccount object (dict)
        """
        params = {
            "fields": "id, name, configured_status, objective, daily_budget",
            "filtering": '[{"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}]',
        }
        if "account_id" in account:
            account_id = account.get("account_id")
        url = f"{url_hp.FACEBOOK_v16_URL}{str(account_id)}/campaigns"

        campaigns = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                campaigns.extend(response.get("data"))
            else:
                self.handleError(
                    reason=f"Something went wrong when trying to get the facebook campaigns for account with ID {account_id}",
                    message=f"{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the campaigns for account with ID {account_id} .\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return campaigns

    def get_accounts(self, toggle_action=None):
        """
        Get all adaccounts from FB
        """
        return AdAccount.objects.filter(
            profile__ad_platform=PlatFormType.FACEBOOK,
            profile=self.profile,
            active=AdAccountActiveType.Pending
            if toggle_action
            else AdAccountActiveType.Yes,
        ).values("account_id", "account_name", "currency", "id")

    def get_single_adaccount(self, account_id):
        """
        Get a single adaccount corresponding with the adaccount ID
        """
        return self.get(url=f"{url_hp.FACEBOOK_v16_URL}{account_id}", params={})

    def get_ad_space_available(self, page_id, account):
        """
        Get the available ad space for the given page_id
        """

        response = self.get(
            url=f"{url_hp.FACEBOOK_v16_URL}{account}/ads_volume",
            params={
                "page_id": page_id,
                "fields": "actor_id,current_account_ads_running_or_in_review_count,limit_on_ads_running_or_in_review,ads_running_or_in_review_count",
            },
        )
        try:
            ad_space_available = response.get("data")[0].get(
                "limit_on_ads_running_or_in_review"
            ) - response.get("data")[0].get("ads_running_or_in_review_count")
        except Exception:
            self.handleError(
                reason="Error in Facebook get_ad_space_available function",
                message=f"Facebook ads_running_or_in_review_count not availble for profile_id: {self.profile.id}, schedule_adaccount_id: {account}, page_id: {page_id}",
            )
        self.debugPrint(
            "Found room to post "
            + str(ad_space_available)
            + " more ads on page with ID "
            + str(page_id)
        )
        return ad_space_available

    # def get_long_access_token(self):
    #     """
    #     Unused method, but useful to quickly get long user access token
    #     """
    #     params = {
    #         "grant_type": "fb_exchange_token",
    #         "client_id": "999439607287204",
    # trunk-ignore(gitleaks/generic-api-key)
    #         "client_secret": "a12363630e2f0d3fa5186acd6e97fcb7",
    #         "fb_exchange_token": "",  # Fill in a short user access token here
    #     }
    #     url = f"{url_hp.FACEBOOK_v16_URL}oauth/access_token"
    #     response = self.get(url, params)
    #     print(response)

    def check_adset_deleted(self, message):
        """
        Check if an adset that is still in the DB was deleted in the UI
        """
        return (
            message.find("'code': 100") != -1
            and message.find("'error_subcode': 1487056") != -1
        )

    def check_temporary_issue(self, message):
        """
        Check if an adset that is still in the DB was deleted in the UI
        """
        return (
            message.find("'code': 2") != -1
            and message.find("'type': 'OAuthException'") != -1
        )

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
        if bid is None and budget is None:
            params = {
                "status": "PAUSED",
            }
        elif bid is None:  # update budget
            budget = int(budget * 100)
            params = {
                "daily_budget": budget,
            }
        elif budget is None:  # update bid
            bid = int(bid * 100)
            params = {
                "bid_amount": bid,
            }
        else:  # update both
            bid = int(bid * 100)  # convert to cents
            budget = int(budget * 100)  # convert to cents
            params = {
                "bid_amount": bid,
                "daily_budget": budget,
            }
        url = f"{url_hp.FACEBOOK_v16_URL}{str(adgroup_id)}"
        try:
            response = self.post(url=url, params=params)
        except FacebookRequestException as e:
            if self.check_adset_deleted(str(e)):
                AdAdsets.objects.filter(
                    ad_platform=PlatFormType.FACEBOOK,
                    adset_id=adgroup_id,
                    campaign_id=campaign_id,
                ).update(active="No", updated_at=dt.now())
                self.handleError(
                    reason=f"{'Error:Update adset with new Bid and/or Budget'}",
                    message=f"Adset {adgroup_id} from campaign {campaign_id} was deleted in the Facebook UI. It has been turned off in the Database.",
                )
                raise FacebookRequestException(
                    f"Adset {adgroup_id} from campaign {campaign_id} was deleted in the Facebook UI. It has been turned off in the Database."
                )
            else:
                raise

        # Error handling
        if "success" not in response:
            errormsg = (
                "Something went wrong in API call to update AdGroup with ID: "
                + str(adgroup_id)
                + " in campaign with ID: "
                + str(campaign_id)
                + ".\nThe error from Facebook API is: "
                + str(response)
                + "\n"
            )
            if bid is not None:
                errormsg += "New bid should be: " + str(bid) + " cents. "
            if budget is not None:
                errormsg += "New budget should be: " + str(budget) + "cents. "
            self.handleError(
                reason=f"{'Facebook updateAdGroup Error'}", message=errormsg
            )
            raise RuntimeError(errormsg)
        if response.get("success") is False:
            errormsg = (
                "API call returned False in function call to update AdGroup with ID: "
                + str(adgroup_id)
                + " in campaign with ID: "
                + str(campaign_id)
                + ". "
            )
            if bid is not None:
                errormsg += "New bid should be: " + str(bid) + "cents. "
            if budget is not None:
                errormsg += "New budget should be: " + str(budget) + "cents. "
            self.handleError(
                reason=f"{'Facebook updateAdGroup Error'}", message=errormsg
            )
            raise RuntimeError(errormsg)

    def get_page_token(self, id):
        """
        Get page token for page with the given ID
        """
        response = self.get(
            url=f"{url_hp.FACEBOOK_v16_URL}{str(id)}",
            params={
                "fields": "name, access_token",
            },
        )
        return response.get("access_token")

    def get_all_pages(self, user_id, account):
        """
        Get all FB pages linked to the account
        """
        pages_database = FacebookPages.objects.filter(
            facebook_user_id=user_id, active="Yes"
        ).values("page_id", "page_token", "page_name")
        pages = []
        for page in pages_database:
            page_id = page.get("page_id")
            page_token = page.get("page_token")
            if page_token is None:
                params = {
                    "fields": "name, access_token",
                }
                url = f"{url_hp.FACEBOOK_v16_URL}{str(user_id)}/accounts"
                response = self.get(url=url, params=params)
                found = False
                while not found:
                    if "data" in response:
                        pages_facebook = response.get("data")
                    else:
                        self.handleError(
                            reason=f"{'pages_facebook error'}", message=response
                        )
                        raise RuntimeError(response)

                    # Match page from DB to page from FB
                    for fb_page in pages_facebook:
                        if fb_page.get("name") == page.get("page_name"):
                            found = True
                            page_id = fb_page.get("id")
                            page_token = fb_page.get("access_token")
                            FacebookPages.objects.filter(
                                facebook_user_id=user_id,
                                page_name=page.get("page_name"),
                            ).update(
                                page_id=page_id,
                                page_token=page_token,
                                updated_at=dt.now(),
                            )
                    # Go to next page if it exists
                    if "paging" in response and "next" in response.get("paging"):
                        url = response.get("paging").get("next")
                        response = self.get(url=url, params=params)
            ad_space_available = self.get_ad_space_available(page_id, account)
            pages.append([page_id, page_token, ad_space_available])
        return pages

    def rate_limit_stats(self, headers):
        """
        Update the rate limits
        """
        bulk_rate_limit_stats_objects = []
        if "x-business-use-case-usage" in headers:
            limit_type = "Business"
            all_limits = ast.literal_eval(headers["x-business-use-case-usage"])
            for i in all_limits:
                limit = all_limits[i][0]
                if "type" in limit:
                    account_id = i
                    subtype = limit["type"]
                    call_count = limit["call_count"]
                    total_cputime = limit["total_cputime"]
                    total_time = limit["total_time"]
                    bulk_rate_limit_stats_objects.append(
                        RateLimits(
                            platform=PlatFormType.FACEBOOK,
                            type=limit_type,
                            subtype=subtype,
                            account_id=account_id,
                            call_count=call_count,
                            total_cputime=total_cputime,
                            total_time=total_time,
                        )
                    )

        if "x-app-usage" in headers:
            limit_type = "App"
            limit = ast.literal_eval(headers["x-app-usage"])
            call_count = limit["call_count"]
            total_cputime = limit["total_cputime"]
            total_time = limit["total_time"]
            bulk_rate_limit_stats_objects.append(
                RateLimits(
                    platform=PlatFormType.FACEBOOK,
                    type=limit_type,
                    call_count=call_count,
                    total_cputime=total_cputime,
                    total_time=total_time,
                )
            )
        if "x-ad-account-usage" in headers:
            limit_type = "AdAccount"
            limit = ast.literal_eval(headers["x-ad-account-usage"])
            call_count = limit["acc_id_util_pct"]
            bulk_rate_limit_stats_objects.append(
                RateLimits(
                    platform=PlatFormType.FACEBOOK,
                    type=limit_type,
                    call_count=call_count,
                )
            )
        RateLimits.objects.bulk_create(bulk_rate_limit_stats_objects)

    def post(self, url, params, scheduler_id=None):
        """
        Do a post request with the given URL and parameters
        """
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        r = requests.post(url, headers=headers, params=params)
        try:
            self.rate_limit_stats(r.headers)
            self.check_rate_limits(r.headers, scheduler_id)
        except Exception as e:
            error_message = f"We Could not check the rate limits for the POST request with the following URL: {r.url}\nThe original error is:\n{e}"
            self.handleError("Could not check rate limits", error_message)
        response = r.json()
        if "error" in response:
            self.handleError(reason=f"Facebook request", message=f"{response}")
            raise FacebookRequestException(
                f"A Facebook request error occured:\n{response}"
            )
        else:
            self.retries = 0
        return response

    def get(self, url, params, scheduler_id=None):
        """
        Do a get request with the given URL and parameters
        """
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.access_token,
        }
        r = requests.get(url, headers=headers, params=params)
        try:
            self.rate_limit_stats(r.headers)
            self.check_rate_limits(r.headers, scheduler_id)
        except Exception as e:
            self.handleError(
                "Could not check rate limits",
                "We could not check the rate limits for the GET request with the following URL:"
                + str(r.url)
                + "\nThe original error is:\n"
                + str(e),
            )
        response = r.json()
        if "error" in response:
            self.handleError(
                reason=f"{'Facebook request error'}",
                message=f"{response.get('error').get('message')}",
            )
            raise FacebookRequestException(response.get("error").get("message"))
        return response

    # def delete(self, url, params, scheduler_id=None):
    #     """
    #     Do a delete request with the given URL and parameters
    #     """
    #     headers = {
    #         "Accept": "application/json",
    #         "Authorization": "Bearer " + str(self.access_token),
    #     }
    #     r = requests.delete(url, headers=headers, params=params)
    #     try:
    #         self.rate_limit_stats(r.headers)
    #         self.check_rate_limits(r.headers, scheduler_id)
    #     except Exception as e:
    #         self.handleError(
    #             "Could not check rate limits",
    #             "We could not check the rate limits for the GET request with the following URL:"
    #             + str(r.url)
    #             + "\nThe original error is:\n"
    #             + str(e),
    #         )
    #     response = r.json()
    #     if "error" in response:
    #         raise FacebookRequestException(
    #             f"A Facebook request error occured:\n{response}"
    #         )
    #     return response

    def schedule_ad_campaign(self, scheduler_id):
        """
        Get values from database for scheduler_id and create an ad campaign
        """
        account_id = self.get_schedule_value(scheduler_id, "adaccount_id")
        account = self.get_single_adaccount(account_id)
        objective_val = self.get_schedule_value(scheduler_id, "objective")
        try:
            objective = FacebookObjectiveMap[objective_val]
        except Exception:
            self.handleError(
                reason="Facebook objective",
                message="The specified objective: "
                + str(objective_val)
                + " has no mapping for Facebook. Please add it to objective_map in constants.py",
            )
            raise ValueError(
                "The specified objective: "
                + str(objective_val)
                + " has no mapping for Facebook. Please add it to objective_map in Facebook_api_handler.py"
            )
        campaign_name = self.create_campaign_name(scheduler_id)
        new_campaign = self.create_ad_campaign(
            account, campaign_name, objective, scheduler_id
        )

        adaccount_id = self.get_schedule_value(scheduler_id, "adaccount_id")
        group_id = self.get_schedule_value(scheduler_id, "scraper_group_id")
        schedule_datetime = self.get_schedule_value(scheduler_id, "scheduled_for")
        campaign_id = new_campaign.get("id")
        AdCampaigns.objects.create(
            automatic="Yes",
            ad_platform=PlatFormType.FACEBOOK,
            advertiserid=adaccount_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            scraper_group_id=group_id,
            active="Yes",
            last_checked=schedule_datetime,
            objective=objective_val,
            api_status="New",
        )
        return new_campaign

    def create_ad_campaign(self, account, campaign_name, objective, scheduler_id=None):
        """
        Creates a new ad campaign
        account (AdAccount): the AdAccount where the ad campaign will be created
        campaign_name (str): name of the ad campaign
        Returns: AdCampaign
        """
        if "id" in account:
            account = account["id"]

        return self.post(
            url=f"{url_hp.FACEBOOK_v16_URL}{str(account)}/campaigns",
            params={
                "name": campaign_name,
                "buying_type": "AUCTION",
                "objective": objective,
                "status": "ACTIVE",
                "special_ad_categories": "[]",
            },
            scheduler_id=scheduler_id,
        )

    def delete_ad_campaign(self, campaign_id):
        """
        Delete campaign with ID: campaign_id
        """
        params = {}
        url = f"{url_hp.FACEBOOK_v16_URL}{campaign_id}"
        response = self.delete(url, params)
        return response

    def create_ad(self, account, name, adset_id, creative_id, scheduler_id=None):
        """
        Creates a new ad

        account (AdAccount): the AdAccount where the ad will be created
        name (str): name of the ad
        adset_id (str): id of the adset where the ad will be created
        creative_id (str): id of the creative which will be used when creating the ad

        Returns: Ad
        """
        if "id" in account:
            account = account["id"]
        return self.post(
            url=f"{url_hp.FACEBOOK_v16_URL}{str(account)}/ads",
            params={
                "name": name,
                "adset_id": adset_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": "ACTIVE",
            },
            scheduler_id=scheduler_id,
        )

    def create_creative(
        self,
        account,
        name,
        landing_page_url,
        caption,
        heading,
        video_thumb_list,
        instagram_id,
        page_id,
        scheduler_id=None,
    ):
        """
        Creates an ad creative and returns the newly created ad creative

        account (AdAccount): the AdAccount where the creative will be created
        name (str): name of the creative
        landing_page_url (str): the landingpage URL of the creative
        caption (str): body of the creative
        heading (str): title of the creative
        video_thumb_list (lst): list of (video_id, thumbnail_url) pairs
        instagram_id (str): ID of the instagram account to post to
        page_id (str): Facebook page to post creative to

        Returns: AdCreative
        """
        schedule_landingpage_url = self.get_creative_value(
            scheduler_id, "landingpage_url"
        )
        if not video_thumb_list:
            raise ValueError("There were no videos found.")
        creative_ids_list = []
        if len(schedule_landingpage_url) == 0:
            for vid, thumb, url, add_heading, add_caption in video_thumb_list:
                video_data = {
                    "video_id": vid,
                    "image_url": thumb,
                    "call_to_action": {"type": "LISTEN_NOW", "value": {"link": url}},
                    "title": heading,
                }
                object_story_spec = json.dumps(
                    {
                        "instagram_actor_id": instagram_id,
                        "page_id": page_id,
                        "video_data": video_data,
                    }
                )
                if "id" in account:
                    account = account["id"]
                response = self.post(
                    url=f"{url_hp.FACEBOOK_v16_URL}{str(account)}/adcreatives",
                    params={
                        "name": name,
                        "object_story_spec": object_story_spec,
                    },
                    scheduler_id=scheduler_id,
                )
                creative_ids_list.append(response)
            return creative_ids_list
        else:
            video = []
            for vid, thumb, url, add_heading, add_caption in video_thumb_list:
                video.append({"video_id": vid, "thumbnail_url": thumb})
            asset_feed_spec = json.dumps(
                {
                    "videos": video,
                    "bodies": [{"text": caption}],
                    "titles": [{"text": heading}],
                    "link_urls": [{"website_url": url}],
                    "ad_formats": ["SINGLE_VIDEO"],
                    "call_to_action_types": ["LISTEN_NOW"],
                }
            )
            object_story_spec = json.dumps(
                {"instagram_actor_id": instagram_id, "page_id": page_id}
            )
            if "id" in account:
                account = account["id"]
            return self.post(
                url=f"{url_hp.FACEBOOK_v16_URL}{str(account)}/adcreatives",
                params={
                    "name": name,
                    "object_story_spec": object_story_spec,
                    "asset_feed_spec": asset_feed_spec,
                },
                scheduler_id=scheduler_id,
            )

    def carousel_create_creative(
        self,
        account,
        name,
        landingPage,
        caption,
        heading,
        video_thumb_list,
        instagram_id,
        page_id,
        scheduler_id=None,
        carousel_card_order=None,
        max_cards_per_carousel=None,
    ):
        """
        Creates an ad creative and returns the newly created ad creative list
        account (AdAccount): the AdAccount where the creative will be created
        name (str): name of the creative
        landingPage (str): the landingpage URL of the creative
        caption (str): body of the creative
        heading (str): title of the creative
        video_thumb_list (lst): list of (video_id, thumbnail_url) pairs
        instagram_id (str): ID of the instagram account to post to
        page_id (str): Facebook page to post creative to

        Returns: AdCreative
        """
        if not video_thumb_list:
            raise ValueError("There were no videos found.")
        creative_ids_list = []
        combine_ads = self.split_list(video_thumb_list, max_cards_per_carousel)
        for ads in combine_ads:
            object_story_spec = {}
            link_data = {}
            link_data = {
                # "link": landingPage,
                "message": name,
                "call_to_action": {"type": "LEARN_MORE"},
                "child_attachments": [
                    {
                        "link": ad[3],
                        "name": ad[5],
                        "description": ad[4],
                        "video_id": ad[0],
                        "picture": ad[1],
                    }
                    if ad[0] is not None
                    else {
                        "description": ad[4],
                        "picture": ad[2],
                        "link": ad[3],
                        "name": ad[5],
                    }
                    for ad in ads
                ],
            }
            object_story_spec = json.dumps(
                {
                    "page_id": page_id,
                    "instagram_actor_id": instagram_id,
                    "link_data": link_data,
                }
            )
            if "id" in account:
                account = account["id"]
            response = self.post(
                url="https://graph.facebook.com/v14.0/" + str(account) + "/adcreatives",
                params={"object_story_spec": object_story_spec},
                scheduler_id=scheduler_id,
            )
            creative_ids_list.append(response)
        return creative_ids_list

    def split_list(self, input_list, num):
        """
        This function takes in a list input_list and an integer num,
        and returns a new list that is created by splitting input_list into chunks of size num.
        The original order of the elements in input_list is preserved in the returned list of chunks.
        """
        return [
            input_list[index : index + num] for index in range(0, len(input_list), num)
        ]

    def get_insights_spend(self, account, date_preset):
        """
        Get adspend data
        """
        account_id = account.get("account_id")
        response = self.get(
            url=f"{url_hp.FACEBOOK_v16_URL}{account_id}/insights",
            params={
                "date_preset": date_preset,
                "level": "adset",
                "time_increment": 1,
                "fields": "adset_id,campaign_id,spend,cpc",
            },
        )
        return response.get("data")

    def get_report_day(self, start_date, end_date):
        """
        Get spend report from FB API
        start_date, end_date (Datetime): should differ either 7 or 28 days. [Tiktok can use different dates, so we use common parameters]
        return: report in the form of a list containing dicts like: {'adgroup_id': '...', 'spend': '...'}
        """
        accounts = self.get_accounts()
        report = []

        days = (end_date - start_date).days
        if days not in (7, 28):
            raise RuntimeError(
                "In get_report_day for Facebook, only the 7 or 28 last days can be checked, so make sure start_date and end_date differ 7 or 28 days in any function that calls it."
            )
        date_preset = "last_{}d".format(days)
        for account in accounts:
            self.next_page = ""
            self.insight = []
            insights = self.get_insights_spend(account, date_preset)
            report = [
                {
                    "adgroup_id": insight.get("adset_id"),
                    "spend": Decimal(insight.get("spend")),
                }
                for insight in insights
            ]
        return report

    def updateDailySpendData(
        self, ad_account_id=None, toggle_action=None, pastdays=None, uid=None
    ):
        # pastdays=28, advertiseraccounts=[], filter_by=all/campaigns
        """
        Update the daily_adspend_genre table
        """
        accounts = self.get_accounts(toggle_action=toggle_action)
        for account in accounts.filter(
            **({"account_id": ad_account_id} if ad_account_id is not None else {})
        ):
            issues_cpc = 0
            issues_spend = 0
            date_preset_list = ["last_28d"] if pastdays else ["last_7d", "today"]
            for date in date_preset_list:
                insights = self.get_insights_spend(account, date)
            adspend_dict = {}
            for insight in insights:
                try:
                    self.update_cpc(insight)
                except Exception:
                    issues_cpc += 1
                try:
                    date = insight.get("date_start")
                    results = AdCampaigns.objects.filter(
                        campaign_id=insight[AdsInsights.Field.campaign_id]
                    ).values_list("campaign_id", "advertiserid")
                    if len(results) != 0:
                        campaign_id = results[0][0]
                        if campaign_id is None:
                            campaign_id = None
                        if (campaign_id, date) in adspend_dict:
                            adspend_dict[(campaign_id, date)]["spend"] += Decimal(
                                insight.get("spend")
                            )
                        else:
                            adspend_dict[(campaign_id, date)] = {}
                            adspend_dict[(campaign_id, date)]["spend"] = Decimal(
                                insight.get("spend")
                            )
                            adspend_dict[(campaign_id, date)]["ad_account"] = results[
                                0
                            ][1]

                except Exception:
                    issues_spend += 1
            if issues_cpc != 0 or issues_spend != 0:
                self.handleError(
                    "[Adspend]",
                    f"For FB account: {account}\nThere were {issues_cpc} issues with retrieving CPC data.\nThere were {issues_spend} issues with retrieving spend data.",
                )

            daily_adspend_genre_bulk_create_objects = []
            daily_adspend_genre_bulk_update_objects = []

            for entry in adspend_dict:
                campaign_id = entry[0]
                date = entry[1]
                account_id = adspend_dict.get(entry).get("ad_account")
                DailyAdspendGenre.objects.filter(
                    account_id=account_id
                ).exists() and DailyAdspendGenre.objects.filter(
                    account_id=account_id
                ).update(
                    ad_account_id=account.get("id")
                )
                added_adspend = DailyAdspendGenre.objects.filter(
                    platform=PlatFormType.FACEBOOK,
                    date=date,
                    ad_account__account_id=account_id,
                    campaign_id=campaign_id,
                ).values("id")
                current_date = dt.now().date()
                if not added_adspend:
                    adaccount = AdAccount.objects.get(account_id=account_id)
                    daily_adspend_genre_bulk_create_objects.append(
                        DailyAdspendGenre(
                            platform=PlatFormType.FACEBOOK,
                            ad_account=adaccount,
                            account_id=account_id,
                            campaign_id=campaign_id,
                            spend=Decimal(str(adspend_dict.get(entry).get("spend"))),
                            date=date,
                            company_uid=uid,
                            ad_account_currency=adaccount.currency,
                        )
                    )
                elif date != current_date or date == current_date:
                    daily_adsspend_genre = DailyAdspendGenre.objects.get(
                        id=added_adspend[0].get("id")
                    )
                    daily_adsspend_genre.spend = Decimal(
                        str(adspend_dict.get(entry).get("spend"))
                    )
                    daily_adsspend_genre.date_updated = dt.now()
                    daily_adsspend_genre.updated_at = dt.now()
                    daily_adspend_genre_bulk_update_objects.append(daily_adsspend_genre)

            DailyAdspendGenre.objects.bulk_create(
                daily_adspend_genre_bulk_create_objects
            )
            DailyAdspendGenre.objects.bulk_update(
                daily_adspend_genre_bulk_update_objects,
                ["spend", "date_updated", "updated_at"],
            )

    def update_cpc(self, insight):
        """
        This method updates the CPC and spend of an adset for a given date
        It checks if the adset insights already exist in the database
        If not, it creates a new entry, else it updates the existing entry.
        """
        campaign_id = insight.get("campaign_id")
        adset_id = insight.get("adset_id")
        date = insight.get("date_start")
        cpc = insight.get("cpc")
        spend = insight.get("spend")
        adset_insights = AdsetInsights.objects.filter(
            platform=PlatFormType.FACEBOOK,
            campaign_id=campaign_id,
            adset_id=adset_id,
            date=date,
        ).values_list("id", "cpc", "spend")

        adset_insights_bulk_create_objects = []
        adset_insights_bulk_update_objects = []
        if not adset_insights:
            adset_insights_bulk_create_objects.append(
                AdsetInsights(
                    platform=PlatFormType.FACEBOOK,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    cpc=cpc,
                    spend=spend,
                    date=dt.now().date(),
                )
            )
        # If value in DB does not match API value, update it to API value
        else:
            cpc_changed = (
                (cpc is None and cpc != adset_insights[0].get("cpc"))
                or (
                    (cpc is not None and adset_insights[0].get("cpc") is not None)
                    and Decimal(cpc) != Decimal(adset_insights[0].get("cpc"))
                )
                or (
                    adset_insights[0].get("cpc") is None
                    and cpc != adset_insights[0].get("cpc")
                )
            )
            spend_changed = (
                (spend is None and spend != adset_insights[0].get("spend"))
                or ((spend is not None and adset_insights[0].get("spend") is not None))
                and Decimal(spend) != Decimal(adset_insights[0].get("spend"))
                or (
                    adset_insights[0].get("spend") is None
                    and spend != adset_insights[0].get("spend")
                )
            )

            if cpc_changed or spend_changed:
                adset_insights = AdsetInsights.objects.get(
                    id=adset_insights[0].get("id")
                )
                adset_insights.cpc = cpc
                adset_insights.spend = spend
                adset_insights.date_updated = dt.now()
                adset_insights.updated_at = dt.now()
                adset_insights_bulk_update_objects.append(adset_insights)

        AdsetInsights.objects.bulk_create(adset_insights_bulk_create_objects)
        AdsetInsights.objects.bulk_update(
            adset_insights_bulk_update_objects,
            ["cpc", "spend", "date_updated", "updated_at"],
        )

    def getLinkfireFromCampaignName(self, name):
        """
        Hardcoded strings that find the Linkfire links from campaign names
        """
        # First check whether the entire website is in the name (which should be the case for campaigns made with this system)
        fullSite = name.rfind("https://fruits.lnk.to/")
        if fullSite != -1:
            url = name[fullSite:]
            return url
        fullSite = name.rfind("https://lnk.to/")
        if fullSite != -1:
            url = name[fullSite:]
            return url

        # Otherwise, check for these strings that were used in older campaigns
        a = name.rfind("2021")
        b = name.rfind("rainw")
        c = name.rfind("jazzw")
        d = name.rfind("jazzfruitsw")
        e = name.rfind("sadlofiw")
        f = name.rfind("lofiplaylistsffb")
        g = name.rfind("strangefruits")

        if a != -1:
            url = name[a:]
        elif b != -1:
            url = name[b:]
        elif c != -1:
            url = name[c:]
        elif d != -1:
            url = name[d:]
        elif e != -1:
            url = name[e:]
        elif f != -1:
            url = name[f:]
        elif g != -1:
            url = name[g:]
        else:
            return None

        # Check if correct link is lnk.to
        # Otherwise check if the correct link is fruits.lnk.to
        # If not, return None
        link = f"https://lnk.to/{url}"
        r = requests.get(link)
        if str(r.status_code) == "404":
            link = "https://fruits.lnk.to/" + url
            r = requests.get(link)
            if str(r.status_code) == "404":
                return None
            else:
                return link
        else:
            return link

    def get_adsets_from_api(self, campaign):
        """
        Get all adsets under the given campaign
        """
        filtering_value = [
            {"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}
        ]
        url = f"{url_hp.FACEBOOK_v16_URL}{str(campaign.get('id'))}/adsets?filtering={filtering_value}"

        adSets = []
        done = False
        while not done:
            response = self.get(
                url=url,
                params={
                    "fields": "id, name, daily_budget, bid_amount, configured_status, targeting, promoted_object",
                },
            )
            if "data" in response:
                adSets.extend(response.get("data"))
            else:
                self.handleError(
                    reason="get_adsets_from_api error",
                    message=f"Something went wrong when trying to get the adsets for campaign with ID {campaign.get('id')}.\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the adsets for campaign with ID {campaign.get('id')}.\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return adSets

    def get_creatives_from_api(self, adset):
        """
        Get all creatives under the given adset
        """
        params = {
            "fields": "id, object_story_spec, asset_feed_spec",
        }
        url = f"{url_hp.FACEBOOK_v16_URL}{str(adset.get('id'))}/adcreatives"

        creatives = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                creatives.extend(response.get("data"))
            else:
                self.handleError(
                    reason="get_creatives_from_api error",
                    message=f"Something went wrong when trying to get the creative for adset with ID {adset.get('id')}.\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the creative for adset with ID {adset.get('id')}.\nOriginal response:\n{response}"
                )

            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return creatives

    def get_ads_from_api(self, adset):
        """
        Get all ads under the given adset
        """
        params = {
            "fields": "id, name, adlabels, configured_status, creative, preview_shareable_link, source_ad, source_ad_id",
        }
        url = f"{url_hp.FACEBOOK_v16_URL}{str(adset.get('id'))}/ads"

        ads = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                ads.extend(response.get("data"))
            else:
                self.handleError(
                    reason="get_ads_from_api error",
                    message=f"Something went wrong when trying to get the ads for adset with ID {adset.get('id')}.\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the ads for adset with ID {adset.get('id')}.\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return ads

    def initializer_adsets(self, campaign):
        """
        Push all adsets under the given campaign to the database
        """
        locationErrors = 0
        tries = 0
        done = False
        campaign_daily_budget = campaign.get("daily_budget")
        while tries < 3 and not done:
            try:
                adsets = self.get_adsets_from_api(campaign)
                done = True
            except Exception:
                tries += 1
                time.sleep(600)

        for adset in adsets:
            if adset.get("configured_status") == "ACTIVE":
                tries = 0
                done = False
                while tries < 3 and not done:
                    try:
                        adcreatives = self.get_creatives_from_api(adset)
                        done = True
                    except Exception:
                        tries += 1
                        self.debugPrint("tries done: ", tries)
                        self.debugPrint("sleeping at creatives...")
                        time.sleep(600)
                url = None
                for cr in adcreatives:
                    try:
                        url = (
                            cr.get("asset_feed_spec")
                            .get("link_urls")[0]
                            .get("website_url")
                        )
                    except Exception:
                        try:
                            url = (
                                cr.get("object_story_spec")
                                .get("video_data")
                                .get("call_to_action")
                                .get("value")
                                .get("link")
                            )
                        except Exception:
                            url = self.getLinkfireFromCampaignName(campaign.get("name"))
                if url is None:
                    self.handleError(
                        "[Initializer/Updater] url not found",
                        "Landingpage for adset: "
                        + adset.get("name")
                        + " was not found. Please check if the url is set correctly in the campaign name, which is: "
                        + campaign.get("name")
                        + ".",
                    )
                    continue
                if "bid_amount" in adset:
                    bid = Decimal(adset.get("bid_amount") / 100)
                else:
                    bid = None
                    self.handleError(
                        "[Initializer/Updater] bid not found",
                        "Bid for adset: "
                        + adset.get("name")
                        + " was not found and was not added to the database entry. Please check if this causes any issues.",
                    )
                try:
                    country = (
                        adset.get("targeting").get("geo_locations").get("countries")
                    )
                    # country = country[0]
                    country=','.join(country)
                    if len(country) != 1:
                        locationErrors += 1
                except Exception:
                    locationErrors += 1
                    country = None
                if country is not None:
                    daily_budget = (
                        campaign_daily_budget
                        if adset.get("daily_budget") is None
                        else adset.get("daily_budget")
                    )
                    last_checked = dt.now() - timedelta(days=1)
                    adsetobj, _ = AdAdsets.objects.update_or_create(
                        campaign_id=campaign.get("id"),
                        adset_id=adset.get("id"),
                        ad_platform=PlatFormType.FACEBOOK,
                        defaults={
                            "adset_name": adset.get("name"),
                            "target_country": country,
                            "landingpage": url,
                            "bid": bid,
                            "budget": daily_budget,
                            "active": "Yes",
                            "last_checked": last_checked,
                        },
                    )
                    if adsetobj.active != "Yes":
                        AdAdsets.objects.filter(
                            adset_id=adset.get("id"), ad_platform=PlatFormType.FACEBOOK
                        ).update(active="Yes", updated_at=dt.now())
                        linkfire_id = adsetobj.linkfire_id
                        if linkfire_id is not None:
                            linkfire = ScrapeLinkfires.objects.filter(
                                id=linkfire_id
                            ).values("is_active")
                            if len(linkfire) != 0:
                                if linkfire[0].get("is_active") == StatusType.NO:
                                    ScrapeLinkfires.objects.filter(
                                        id=linkfire_id
                                    ).update(
                                        is_active=StatusType.YES, updated_at=dt.now()
                                    )
            else:
                results = AdAdsets.objects.filter(
                    adset_id=adset.get("id"), ad_platform=PlatFormType.FACEBOOK
                ).values_list("active")

                if len(results) > 0 and results[0][0] != "No":
                    AdAdsets.objects.filter(
                        adset_id=adset.get("id"), ad_platform=PlatFormType.FACEBOOK
                    ).update(active="No", updated_at=dt.now())

        return locationErrors

    def initializer_campaigns(self, account, api=None):
        """
        Push all campaigns under the given account to the database
        """
        campaigns = self.get_campaign(account)
        locationErrors = 0
        for campaign in campaigns:
            if campaign.get("configured_status") == "ACTIVE":
                try:
                    objective_type = next(
                        (
                            key
                            for key, value in FacebookObjectiveMap.items()
                            if value == campaign["objective"]
                        )
                    )
                except Exception:
                    objective_type = (
                        "Conversions"
                        if campaign["objective"] == "OUTCOME_SALES"
                        else campaign["objective"]
                    )
                AdCampaigns.objects.update_or_create(
                    ad_platform=PlatFormType.FACEBOOK,
                    campaign_id=campaign.get("id"),
                    defaults={
                        "advertiserid": account.get("account_id"),
                        "campaign_name": campaign.get("name"),
                        "scraper_group": None,
                        "active": "Yes",
                        "objective": objective_type,
                    },
                )
                if api != "get-campaign-using-adaccount":
                    locationErrors += self.initializer_adsets(campaign)
            else:
                results = AdCampaigns.objects.filter(
                    campaign_id=campaign.get("id"), ad_platform=PlatFormType.FACEBOOK
                ).values("active")
                if len(results) > 0 and results[0].get("active") != "No":
                    AdCampaigns.objects.filter(
                        campaign_id=campaign.get("id"),
                        ad_platform=PlatFormType.FACEBOOK,
                    ).update(active="No", updated_at=dt.now())
        return locationErrors

    def data_to_file(self):
        """
        Debug function to print all campaign, set and creative data to files
        """
        f = open("all_adsets.txt", "a")
        f.write("START NEW DATA\n")
        accounts = self.get_accounts()
        f.write("__________________________ ACCOUNTS __________________________\n")
        f.write(str(accounts))
        for account in accounts:
            if account.get("account_name") in ["Fruits Gaming", "Test Account (API)"]:
                campaigns = self.get_campaign(account)
                f.write(
                    "__________________________ CAMPAIGNS __________________________\n"
                )
                f.write(str(campaigns))
                for campaign in campaigns:
                    adsets = self.get_adsets_from_api(campaign)
                    f.write(
                        "__________________________ SETS __________________________\n"
                    )
                    f.write(str(adsets))
                    for set in adsets:
                        creatives = self.get_creatives_from_api(set)
                        f.write(
                            "__________________________ CREATIVES __________________________\n"
                        )
                        f.write(str(creatives))
                        ads = self.get_ads_from_api(set)
                        f.write(
                            "__________________________ ADS __________________________\n"
                        )
                        f.write(str(ads))
        f.close()

    def initializer_pixels(self, business_id=None):
        """
        Push all pixels to the database
        """
        if business_id is None:
            businesses = Business.objects.filter(
                profile__ad_platform=PlatFormType.FACEBOOK, profile=self.profile
            ).values("business_id")
        else:
            businesses = [
                {
                    "business_id": business_id,
                }
            ]
        for business in businesses:
            business_id = business.get("business_id")
            params = {}
            url = f"{url_hp.FACEBOOK_v16_URL}{str(business_id)}/owned_pixels"

            response = self.get(url=url, params=params)
            if "data" not in response:
                self.handleError(
                    "[Initializer] Pixels error",
                    "While trying to get the Pixels from Facebook, something went wrong. The original message is:\n"
                    + str(response),
                    "High",
                )
                continue
            done = False
            while not done:
                for pixel in response["data"]:
                    params = {"fields": "name"}
                    url = f'{url_hp.FACEBOOK_v16_URL}{str(pixel["id"])}'

                    res = self.get(url=url, params=params)
                    if "name" not in res:
                        self.handleError(
                            "[Initializer] Pixels error",
                            "While trying to get the name for Pixel "
                            + str(pixel["id"])
                            + " from Facebook, something went wrong. The original message is:\n"
                            + str(res),
                            "High",
                        )
                        continue
                    url = f"{url_hp.FACEBOOK_v16_URL}{str(pixel['id'])}/shared_accounts"
                    params = {"business": business_id}
                    res_acc = self.get(url=url, params=params)
                    if "data" in res_acc:
                        available_ad_account_ids_in_live = []
                        for acc in res_acc["data"]:
                            available_ad_account_ids_in_live.append(acc.get("id"))
                            Pixels.objects.update_or_create(
                                pixel_id=pixel.get("id"),
                                advertiser_id=acc.get("id"),
                                platform=PlatFormType.FACEBOOK,
                                defaults={"name": res.get("name")},
                            )
                        Pixels.objects.filter(pixel_id=pixel.get("id")).exclude(
                            advertiser_id__in=available_ad_account_ids_in_live
                        ).delete()
                    else:
                        self.handleError(
                            "[Initializer] Pixels error",
                            "While trying to get the accounts for Pixel "
                            + str(pixel.get("id"))
                            + " from Facebook, something went wrong. The original message is:\n"
                            + str(res_acc),
                            "High",
                        )
                        continue

                if "paging" in response and "next" in response.get("paging"):
                    url = response.get("paging").get("next")
                    response = self.get(url=url, params=params)
                else:
                    done = True

    def customAudiences_to_database(self, account):
        """
        Push all custom audiences under the given account to the database
        """
        audiences = self.getCustomAudiences(account)
        for audience in audiences:
            CustomAudiences.objects.update_or_create(
                platform=PlatFormType.FACEBOOK,
                account_id=account,
                audience_id=audience.get("id"),
                defaults={
                    "name": audience.get("name"),
                    "description": audience.get("description"),
                },
            )

    def getCustomAudiences(self, accountId):
        """
        Get all custom audiences under the given account ID
        """
        params = {
            "fields": "id, name, description",
        }
        url = f"{url_hp.FACEBOOK_v16_URL}{str(accountId)}/customaudiences"
        audiences = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                audiences.extend(response.get("data"))
            else:
                self.handleError(
                    reason="getCustomAudiences api error",
                    message=f"Something went wrong when trying to get the audiences for account with ID {accountId}.\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the audiences for account with ID {accountId}.\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return audiences

    def customConversionEvents_to_database(self, account_id):
        """
        Push all custom conversion events under the given account to the database
        """
        events = self.getCustomConversionEvents(account_id)
        for event in events:
            CustomConversionEvents.objects.update_or_create(
                platform=PlatFormType.FACEBOOK,
                event_id=event["id"],
                account_id=account_id,
                defaults={
                    "pixel_id": event.get("pixel").get("id"),
                    "name": event.get("name"),
                    "description": event.get("description"),
                    "rules": event.get("rule"),
                },
            )

    def getCustomConversionEvents(self, account_id):
        """
        Get all custom conversion events under the given account ID
        """
        params = {
            "fields": "id, name, description, pixel, rule",
        }
        url = f"{url_hp.FACEBOOK_v16_URL}{str(account_id)}/customconversions"
        events = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                events.extend(response.get("data"))
            else:
                self.handleError(
                    reason="getCustomConversionEvents api error",
                    message=f"Something went wrong when trying to get the custom conversion events for account with ID {account_id}.\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the custom conversion events for account with ID {account_id}.\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return events

    # def intializer_accounts(self, account_id, account_name):
    #     # vars = (account_id,)
    #     # results = self.db.execSQL(
    #     #     """SELECT `account_name`, `genre` FROM facebook_accounts WHERE account_id=%s""",
    #     #     vars,
    #     #     False,
    #     # )
    #     results = FacebookAccounts.objects.filter(account_id=account_id).values_list(
    #         "account_name", "genre"
    #     )
    #     if len(results) > 1:
    #         self.handleError(
    #             f"{'[Initializer] Duplicate account in DB'}",
    #             f"Ad account id {account_id} is found multiple times in the database, please fix this issue",
    #         )
    #         raise InitializerContinueException()
    #     elif len(results) == 0:
    #         self.handleError(
    #             f"{'[Initializer] Account not found in DB'}",
    #             f"Ad account id {account_id} is not in the database, please fix this issue.",
    #             "High",
    #         )
    #         raise InitializerContinueException()
    #     elif (
    #         results[0][0] is None or results[0][0] != account_name
    #     ):  # if name is not in DB, add it to DB
    #         # vars = (account_name, account_id)
    #         # self.db.execSQL(
    #         #     """UPDATE `facebook_accounts` SET `account_name` = %s WHERE account_id  = %s""",
    #         #     vars,
    #         #     True,
    #         # )
    #         FacebookAccounts.objects.filter(account_id=account_id).update(
    #             account_name=account_name
    #         )
    #     if results[0][1] is None:  # if genre is not in DB, send notification
    #         self.handleError(
    #             "[Initializer] Genre not set in DB",
    #             "Ad account name "
    #             + account_name
    #             + " has no genre in the database, please fix this issue.",
    #             "High",
    #         )
    #         # raise InitializerContinueException()
    #     genre = results[0][1]
    #     return genre

    def get_active_adsets_from_api(self, account):
        """
        Get all adsets under the given campaign
        """
        params = {
            "fields": "id, name",
        }
        account_id = account.get("account_id")
        filtering_value = [
            {"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}
        ]
        url = f"{url_hp.FACEBOOK_v16_URL}{str(account_id)}/adsets?filtering={filtering_value}"
        adSets = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                adSets.extend(response.get("data"))
            else:
                self.handleError(
                    reason="get_active_adsets_from_api error",
                    message=f"Something went wrong when trying to get the campaigns for account with ID {account_id} .\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the adsets for account with ID {account_id}.\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return adSets

    def get_active_campaigns_from_api(self, account):
        """
        Get all campaigns for the given adAccount

        Account: FB adaccount object (dict)
        """
        params = {
            "fields": "id, name, configured_status",
        }
        filtering_value = [
            {"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}
        ]
        url = f'{url_hp.FACEBOOK_v16_URL}{str(account.get("account_id"))}/campaigns?filtering={filtering_value}'
        campaigns = []
        done = False
        while not done:
            response = self.get(url=url, params=params)
            if "data" in response:
                campaigns.extend(response.get("data"))
            else:
                self.handleError(
                    reason="get_active_campaigns_from_api error",
                    message=f"Something went wrong when trying to get the campaigns for account with ID {account.get('account_id')} .\nOriginal response:\n{response}",
                )
                raise RuntimeError(
                    f"Something went wrong when trying to get the campaigns for account with ID {account.get('account_id')} .\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response.get("paging"):
                url = response.get("paging").get("next")
            else:
                done = True
        return campaigns

    def get_delete_campaigns_from_api(self, account):
        """
        Get all campaigns for the given adAccount
        Account: FB adaccount object (dict)
        """
        account_id = account.get("account_id")
        filtering_value = [
            {"field": "effective_status", "operator": "IN", "value": ["DELETED"]}
        ]
        url = f"{url_hp.FACEBOOK_v16_URL}{str(account_id)}/campaigns?filtering={filtering_value}"
        campaigns = []
        done = False
        while not done:
            response = self.get(
                url=url,
                params={
                    "fields": "id, name, configured_status",
                },
            )
            if "data" in response:
                campaigns.extend(response["data"])
            else:
                raise RuntimeError(
                    f"Something went wrong when trying to get the campaigns for account with ID {account_id} .\nOriginal response:\n{response}"
                )
            # Go to next page if it exists
            if "paging" in response and "next" in response["paging"]:
                url = response["paging"]["next"]
            else:
                done = True
        return campaigns

    def deactivate_unused_sets(self, account):
        active_adsets_in_facebook = self.get_active_adsets_from_api(account)
        list_of_campaign_id = AdCampaigns.objects.filter(
            advertiserid=account.get("account_id")
        ).values_list("campaign_id", flat=True)
        active_adsets_in_database = AdAdsets.objects.filter(
            campaign_id__in=list_of_campaign_id,
            active="Yes",
            ad_platform=PlatFormType.FACEBOOK,
        ).values_list("adset_id")
        found = False
        updated = 0
        for active_db_adset_index in range(len(active_adsets_in_database)):
            found = any(
                active_adsets_in_facebook[active_facebook_adset_index]["id"]
                == active_adsets_in_database[active_db_adset_index][0]
                for active_facebook_adset_index in range(len(active_adsets_in_facebook))
            )
            if not found:
                AdAdsets.objects.filter(
                    adset_id=active_adsets_in_database[active_db_adset_index][0],
                    ad_platform=PlatFormType.FACEBOOK,
                ).update(active="No", updated_at=dt.now())
                updated += 1
        if updated != 0:
            self.debugPrint(
                "Deactivated ",
                updated,
                " adsets in the database that were disabled in the UI.",
            )

    def deactivate_unused_campaigns(self, account):
        active_campaigns_in_facebook = self.get_active_campaigns_from_api(account)
        active_campaigns_in_database = AdCampaigns.objects.filter(
            advertiserid=account["account_id"],
            active="Yes",
            ad_platform=PlatFormType.FACEBOOK,
        ).values_list("campaign_id")
        found = False
        updated = 0
        for active_db_campaign_index in range(len(active_campaigns_in_database)):
            found = any(
                active_campaigns_in_facebook[active_facebook_campaign_index]["id"]
                == active_campaigns_in_database[active_db_campaign_index][0]
                for active_facebook_campaign_index in range(
                    len(active_campaigns_in_facebook)
                )
            )
            if not found:
                AdCampaigns.objects.filter(
                    campaign_id=active_campaigns_in_database[active_db_campaign_index][
                        0
                    ],
                    ad_platform=PlatFormType.FACEBOOK,
                ).update(active="No", updated_at=dt.now())
                updated += 1
        if updated != 0:
            self.debugPrint(
                "Deactivated ",
                updated,
                " campaigns in the database that were disabled in the UI.",
            )

    def delete_unused_campaigns(self, account):
        delete = 0
        delete_campaigns_api = self.get_delete_campaigns_from_api(account)
        if not delete_campaigns_api:
            self.debugPrint(f"[Campaigns Done] {delete} campaigns delete")
            return None
        self.debugPrint(
            f"[Campaigns] Found to delete {len(delete_campaigns_api)} campaigns..."
        )
        for campaign in range(len(delete_campaigns_api)):
            campaign_id = str(delete_campaigns_api[campaign]["id"])
            try:
                if self.get_count_campaign(campaign_id):
                    AdCampaigns.objects.filter(campaign_id=campaign_id).delete()
                    delete += 1
                else:
                    self.handleError(
                        reason="delete_unused_campaigns fuction issue",
                        message=f"this campaign id {campaign_id} not found in database",
                    )
            except Exception as e:
                raise Exception(str(e))
        self.debugPrint(f"[Delete Campaigns Done] {str(delete)} campaigns Deleted")

    def initializer(self):
        """
        initialises database by getting data on all ads, groups and campaings from the api. Then it pushes all data to database. Prevents duplicats.
        :Param: none
        :return: none
        """
        self.initializing_bussiness_adaccounts()
        ad_accounts = self.get_accounts()
        curtime = dt.now()
        locationErrors = 0
        try:
            self.debugPrint("Initializing pixels")
            self.initializer_pixels()
        except Exception as e:
            self.handleError(
                "[Initializer - Pixels]",
                f"Could not initialize pixels. Original error: {str(e)}",
            )

        for account in ad_accounts:
            account_id = account.get("account_id")
            try:
                self.debugPrint("Deactivating unused adsets")
                self.deactivate_unused_sets(account)
            except Exception as e:
                self.handleError(
                    "[Initializer - Deactivate unused adsets]",
                    f"Could not disable (all) unactive ad_sets. Original error: {str(e)}",
                )
            try:
                self.debugPrint("Deactivating unused adsets")
                self.deactivate_unused_campaigns(account)
            except Exception as e:
                self.handleError(
                    "[Initializer - Deactivate unused campaigns]",
                    f"Could not disable (all) unactive ad_sets. Original error: {str(e)}",
                )
            try:
                self.debugPrint("Initializing custom events")
                self.customConversionEvents_to_database(account_id)
            except Exception as e:
                self.handleError(
                    "[Initializer - Custom conversion events]",
                    f"Could not initialize (all) custom conversion events. Original error: {str(e)}",
                )
            try:
                self.debugPrint("Initializing campaigns")
                locationErrors += self.initializer_campaigns(account)
            except Exception as e:
                self.handleError(
                    "Initializer - Campaigns",
                    f"A fatal error occured while initializing a campaign, adset or ad. Original error: {str(e)}",
                )

            try:
                self.debugPrint("Delete unused campaigns")
                self.delete_unused_campaigns(account)
            except Exception as e:
                self.handleError(
                    "[Initializer - delete unused campaigns]",
                    f"Could not delete (all) unactive campaign. Original error: {str(e)}",
                )

        endtime = dt.now() - curtime
        self.debugPrint(f"Done! Total run took: {endtime}")
        if locationErrors > 0:
            self.handleError(
                "[Initializer] Location Errors",
                "Encountered location errors when pushing data to database. "
                + str(locationErrors)
                + " adgroups had 2 or more locations. These were added to the database, but cannot be optimized.",
            )

    def get_age_minmax(self, age_range):
        """
        Translate the given age_range to a min and max age
        """
        # min_age, max_age = map(int, age_range.split("-"))
        # if min_age > max_age:
        #     min_age, max_age = max_age, min_age
        # return min_age, max_age

        age_ranges = age_range.split(",")
        parsed_ranges = []

        for range_str in age_ranges:
            range_parts = range_str.split("-") if range_str != "55+" else ["55", "65"]
            min_age = range_parts[0]
            max_age = range_parts[1]

            parsed_ranges.append(min_age)
            parsed_ranges.append(max_age)
        min_age, max_age = parsed_ranges[0], parsed_ranges[-1]
        return min_age, max_age

    def checkRestrictedPage(self, error):
        """
        Check if the given error is a 'page restricted' error
        """
        message = error.args[0]
        index_code = message.find('"code": 368')
        return index_code != -1

    def get_video_thumb_list(self, scheduler_id, ad_type):
        """
        Create a list of video_id, thumbnail pairs
        """
        uploadSesId = self.get_schedule_value(scheduler_id, "uploadsesid")
        video_ids = AdCreativeIds.objects.filter(
            uploadsesid=uploadSesId,
            scheduler_id=scheduler_id,
            ad_platform=PlatFormType.FACEBOOK,
        ).values_list(
            "creative_id",
            "thumbnail_url",
            "url",
            "landingpage_url",
            "heading",
            "caption",
        )
        if not video_ids.exists():
            raise DatabaseRequestException(
                f"No video IDs found for uploadSesID: {uploadSesId} and scheduler_id: {scheduler_id}"
            )
        video_thumb_list = []
        if ad_type == "Single":
            for vid in video_ids:
                video_thumb_list.append([vid[0], vid[1], vid[3], vid[4], vid[5]])
        else:
            for vid in video_ids:
                video_thumb_list.append(
                    [vid[0], vid[1], vid[2], vid[3], vid[4], vid[5]]
                )

        return video_thumb_list

    # def get_instagram_id(self, account_id):
    #     """
    #     Get instagram ID for this account_id from the DB
    #     """
    #     try:
    #         # results = InstagramAccounts.objects.filter(ad_account__account_id=account_id)..values_list("instagram_id")
    #         results = FacebookAccounts.objects.filter(
    #             account_id=account_id
    #         ).values_list("instagram_id")
    #         instagram_id = results[0][0] if results else None
    #     except Exception:
    #         self.handleError(
    #             reason="No instagram ID found for adaccount with ID",
    #             message=f"{str(account_id)}, Please add an instagram ID to this account",
    #         )
    #         raise DatabaseRequestException(
    #             "No instagram ID found for adaccount with ID: "
    #             + str(account_id)
    #             + ". Please add an instagram ID to this account"
    #         )
    #     return instagram_id

    def create_ad_group(
        self,
        account,
        campaign_id,
        adgroup_name,
        country,
        schedule_budget,
        schedule_age_min,
        schedule_age_max,
        placement_type,
        schedule_time,
        objective,
        pixel_id,
        custom_event_type,
        application_id,
        object_store_url,
        bid_strategy,
        custom_audiences,
        language_list,
        ad_type,
        automatic_placement,
        selected_placement,
        bid=None,
        scheduler_id=None,
    ):
        """
        Creates a new ad group (=ad set)

        account (AdAccount): the AdAccount where the ad group will be created
        campaign_id (str): id of the ad campaign where the ad group will be created
        adgroup_name (str): name of the ad group
        country (str): country where the ad group will advertise [NOTE: should be country code like "US" or "NL"]
        schedule_budget (int): budget for the ad group in cents
        schedule_age_min, schedule_age_max (int): min/max age to which the ad group will advertise
        placement_type (str): Story, Post or Reels; type of post in instagram which the ad group will use

        Returns: AdGroup
        """
        ### adset is dynamic or non dynamic desided here
        schedule_landingpage_url = self.get_creative_value(
            scheduler_id, "landingpage_url"
        )
        accelerated_spend = self.get_schedule_value(scheduler_id, "accelerated_spend")
        dynamic_creative = (
            True
            if ad_type == "Single" and len(schedule_landingpage_url) != 0
            else False
        )
        bid_strategy = FacebookBidStrategyMap.get(bid_strategy)
        # instagram_position = FacebookPlacementMap.get(placement_type)
        if custom_event_type is not None and not custom_event_type.isnumeric():
            event = FacebookEventMap.get(custom_event_type)

        elif custom_event_type is not None and custom_event_type.isnumeric():
            event = custom_event_type
        else:
            event = None
        custom_audiences_list = (
            [{"id": ca} for ca in custom_audiences.split(",")]
            if custom_audiences not in [None, ""]
            else []
        )

        bid = 1 if bid is None else int(Decimal(bid) * 100)
        schedule_budget = (
            1 if schedule_budget is None else int(Decimal(schedule_budget) * 100)
        )

        targeting_params = {
            "age_min": schedule_age_min,
            "age_max": schedule_age_max,
            "geo_locations": {"countries": country, "location_types": ["home"]},
            "device_platforms": ["mobile", "desktop"],
            # "publisher_platforms": ["instagram"],
            # "instagram_positions": instagram_position,
            # "targeting_optimization": "expansion_all",
            # "flexible_spec": [
            #     {
            #         "interests": [
            #             {
            #                 "id": 6003020834693,
            #                 "name": "Music",
            #             },
            #             {
            #                 "id": 6002969794329,
            #                 "name": "Spotify",
            #             },
            #             {
            #                 "id": 937077532996593,
            #                 "name": "Apple Music",
            #             },
            #             {
            #                 "id": 569202086550452,
            #                 "name": "Amazon Music",
            #             },
            #         ],
            #     },
            # ],
            "excluded_custom_audiences": custom_audiences_list,
        }
        # Set targeting for objectives
        if not automatic_placement:
            publisher_platforms = [
                "instagram"
                if "Instagram" in selected_placement.split("_")
                else "facebook"
            ]
            if publisher_platforms == ["instagram"]:
                instagram_positions = PlacementTargeting.get(selected_placement)
                targeting_params["publisher_platforms"] = publisher_platforms
                targeting_params["instagram_positions"] = instagram_positions
            if publisher_platforms == ["facebook"]:
                facebook_positions = PlacementTargeting.get(selected_placement)
                targeting_params["publisher_platforms"] = publisher_platforms
                targeting_params["facebook_positions"] = facebook_positions

        if objective == "App_installs":
            targeting_params["user_device"] = ["Android_Smartphone", "Android_Tablet"]
            targeting_params["user_os"] = ["Android"]

        if objective == "Conversions":
            billing_event = "IMPRESSIONS"
            optimization_goal = "OFFSITE_CONVERSIONS"
        else:
            billing_event = "LINK_CLICKS"
            optimization_goal = "LINK_CLICKS"
        if len(language_list) != 0:
            targeting_params["locales"] = language_list
        targeting_params = json.dumps(targeting_params)
        params = {
            "name": adgroup_name,
            "campaign_id": campaign_id,
            "status": "ACTIVE",
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "bid_strategy": bid_strategy,
            "is_dynamic_creative": dynamic_creative,
            "targeting": targeting_params,
            "daily_budget": schedule_budget,
            "start_time": schedule_time,
        }

        # Set parameters for bid_strategy
        if bid_strategy == "LOWEST_COST_WITH_BID_CAP":
            params["bid_amount"] = bid
            params["pacing_type"] = (
                "['no_pacing']" if accelerated_spend else "['standard']"
            )
        elif bid_strategy == "LOWEST_COST_WITHOUT_CAP":
            params["pacing_type"] = "['standard']"

        # Set parameters for objective
        if objective == "Conversions":
            if pixel_id is None:
                raise ValueError(
                    "A Pixel ID should be chosen when scheduling a Conversion adset"
                )
            if event is None:
                raise ValueError(
                    "An event should be chosen when scheduling a Conversion adset"
                )
            if not event.isnumeric():
                params["promoted_object"] = json.dumps(
                    {"pixel_id": pixel_id, "custom_event_type": event}
                )
            else:
                rule = CustomConversionEvents.objects.filter(
                    platform=PlatFormType.FACEBOOK, event_id=event
                ).values_list("rules")
                if not rule:
                    raise ValueError(
                        f"No rule found in the database for custom conversion event {event} while scheduling a new adgroup. Please check if the custom made conversion events are fetched properly."
                    )
                params["promoted_object"] = json.dumps(
                    {
                        "pixel_id": pixel_id,
                        "custom_event_type": "OTHER",
                        "pixel_rule": rule[0][0],
                        "custom_conversion_id": event,
                    }
                )
        elif objective == "App_installs":
            if application_id is None:
                raise ValueError(
                    "An Application ID should be chosen when scheduling an App Installs adset"
                )
            if object_store_url is None:
                raise ValueError(
                    "An Object Store Url should be chosen when scheduling an App Installs adset"
                )

            params["promoted_object"] = json.dumps(
                {"application_id": application_id, "object_store_url": object_store_url}
            )

        if "id" in account:
            account = account.get("id")
        url = f"{url_hp.FACEBOOK_v16_URL}{str(account)}/adsets"
        try:
            response = self.post(url=url, params=params, scheduler_id=scheduler_id)
            return response
        except FacebookRequestException as e:
            if self.check_temporary_issue(str(e)):
                self.retries += 1
                if self.retries > 30:
                    self.retries = 0
                    raise FacebookRequestException(
                        f"A Facebook request error occured:\n{str(e)}"
                    )
                time.sleep(60)
                return self.create_ad_group(
                    account,
                    campaign_id,
                    adgroup_name,
                    country,
                    schedule_budget,
                    schedule_age_min,
                    schedule_age_max,
                    placement_type,
                    schedule_time,
                    objective,
                    pixel_id,
                    custom_event_type,
                    application_id,
                    object_store_url,
                    bid_strategy,
                    custom_audiences,
                    language_list,
                    ad_type,
                    automatic_placement,
                    selected_placement,
                    bid,
                    scheduler_id,
                )
            raise FacebookRequestException(
                f"A Facebook request error occured:\n{str(e)}"
            )

    def schedule_single_adset(
        self, scheduler_id, campaign_id, country, name, language_list, ad_type
    ):
        """
        Schedule a single adset
        """
        # Get account
        account_id = self.get_schedule_value(scheduler_id, "adaccount_id")

        # Get age min and max
        schedule_age_range = self.get_schedule_value(scheduler_id, "age_range")
        schedule_age_min, schedule_age_max = self.get_age_minmax(schedule_age_range)
        # Get other variables
        schedule_datetime = self.get_schedule_value(scheduler_id, "scheduled_for")
        placement_type = self.get_schedule_value(scheduler_id, "placement_type")
        bid_strategy = self.get_schedule_value(scheduler_id, "bid_strategy")
        bid = self.get_schedule_value(scheduler_id, "bid")
        budget = (
            self.get_schedule_value(scheduler_id, "budget")
            or self.get_schedule_budget()
        )
        custom_audiences = self.get_schedule_value(scheduler_id, "custom_audiences")

        # Get Advantage + placement variables
        automatic_placement = self.get_schedule_value(
            scheduler_id, "automatic_placement"
        )
        selected_placement = self.get_schedule_value(scheduler_id, "selected_placement")

        # Get objective and set values connected to certain objectives if necessary
        objective = self.get_schedule_value(scheduler_id, "objective")
        pixel_id, event, application_id, object_store_url = None, None, None, None
        if objective == "Conversions":
            pixel_id = self.get_schedule_value(scheduler_id, "pixel_id")
            event = self.get_schedule_value(scheduler_id, "event_type")
        elif objective == "App_installs":
            application_id = self.get_schedule_value(scheduler_id, "application_id")
            object_store_url = self.get_schedule_value(scheduler_id, "landingpage_url")
        return self.create_ad_group(
            account_id,
            campaign_id,
            name,
            country,
            budget,
            schedule_age_min,
            schedule_age_max,
            placement_type,
            schedule_datetime,
            objective,
            pixel_id,
            event,
            application_id,
            object_store_url,
            bid_strategy,
            custom_audiences,
            language_list,
            ad_type,
            automatic_placement,
            selected_placement,
            bid,
            scheduler_id,
        )

    def schedule_creative(
        self,
        scheduler_id,
        video_thumb_list,
        page_id,
        ad_type,
        carousel_card_order=None,
        max_cards_per_carousel=None,
    ):
        """
        Schedule a creative
        """
        # Get Account and Instagram ID
        account_id = self.get_schedule_value(scheduler_id, "adaccount_id")
        account = self.get_single_adaccount(account_id)
        instagram_id = self.get_schedule_value(scheduler_id, "instagram_id")

        # Get other variables
        schedule_landingpage_url = self.get_schedule_value(
            scheduler_id, "landingpage_url"
        )
        schedule_caption = self.get_schedule_value(scheduler_id, "caption")
        schedule_heading = self.get_schedule_value(scheduler_id, "heading")
        group_name = self.get_schedule_value(scheduler_id, "scraper_group__group_name")
        creative_name = group_name
        if ad_type == "Single":
            return self.create_creative(
                account,
                creative_name,
                schedule_landingpage_url,
                schedule_caption,
                schedule_heading,
                video_thumb_list,
                instagram_id,
                page_id,
                scheduler_id,
            )
        else:
            return self.carousel_create_creative(
                account,
                creative_name,
                schedule_landingpage_url,
                schedule_caption,
                schedule_heading,
                video_thumb_list,
                instagram_id,
                page_id,
                scheduler_id,
                carousel_card_order,
                max_cards_per_carousel,
            )

    def schedule_ad(self, scheduler_id, name, adset_id, creative_id):
        """
        Schedule an ad
        """
        account_id = self.get_schedule_value(scheduler_id, "adaccount_id")
        account = self.get_single_adaccount(account_id)

        self.create_ad(account, name, adset_id, creative_id, scheduler_id)

    def schedule_adsets_country(
        self, scheduler_id, page_id, campaign_id, country, language_list
    ):
        # Create a list of video_id, thumbnail pairs
        ad_type = self.get_schedule_value(scheduler_id, "ad_type")
        video_thumb_list = self.get_video_thumb_list(scheduler_id, ad_type)

        # Get other settings
        group_name = self.get_schedule_value(scheduler_id, "scraper_group__group_name")
        placement_type = self.get_schedule_value(scheduler_id, "placement_type")
        extra_name = self.get_schedule_value(scheduler_id, "extra_name")
        schedule_datetime = self.get_schedule_value(scheduler_id, "scheduled_for")
        bid = self.get_schedule_value(scheduler_id, "bid")
        budget = self.get_schedule_value(scheduler_id, "budget")
        ignore_until = self.get_schedule_value(scheduler_id, "ignore_until")
        strategy = self.get_schedule_value(scheduler_id, "strategy")
        max_budget = self.get_schedule_value(scheduler_id, "max_budget")
        automatic_placement = self.get_schedule_value(
            scheduler_id, "automatic_placement"
        )
        selected_placement = self.get_schedule_value(scheduler_id, "selected_placement")
        interests = self.get_schedule_value(scheduler_id, "interests")
        age_range = self.get_schedule_value(scheduler_id, "age_range")
        schedule_landingpage_url = self.get_creative_value(
            scheduler_id, "landingpage_url"
        )
        # Get Carousel related variables
        carousel_card_order = self.get_schedule_value(
            scheduler_id, "carousel_card_order"
        )
        max_cards_per_carousel = self.get_schedule_value(
            scheduler_id, "max_cards_per_carousel"
        )
        country_str = ",".join(country)
        country_name = (
            self.countryCodeToName(country_str)
            if len(country) == 1
            else "Multiple Countries"
        )
        name = f"{group_name} - {selected_placement} - {country_name} - {age_range} - {len(interests) if interests != None else 0}"
        if extra_name is not None:
            name = f"{name} - {extra_name}"
        try:
            newSet = self.schedule_single_adset(
                scheduler_id, campaign_id, country, name, language_list, ad_type
            )
        except Exception as e:
            self.handleError(
                reason="Could not create new ad group",
                message=f"Original error: {str(e)}",
            )
            raise RuntimeError(
                "Could not create new ad group. Original error: \n" + str(e)
            )
        try:
            creative = self.schedule_creative(
                scheduler_id,
                video_thumb_list,
                page_id,
                ad_type,
                carousel_card_order,
                max_cards_per_carousel,
            )
        except Exception as e:
            self.handleError(
                reason="Could not create new ad creative",
                message=f"Original error: {str(e)}",
            )
            raise RuntimeError(
                "Could not create new ad creative. Original error: \n" + str(e)
            )
        try:
            if ad_type == "Single" and len(schedule_landingpage_url) != 0:
                # Normal ads
                self.schedule_ad(scheduler_id, name, newSet["id"], creative["id"])
            else:
                # Carousel ads or Non-dynamic add
                for single_creative in creative:
                    self.schedule_ad(
                        scheduler_id, name, newSet["id"], single_creative["id"]
                    )
        except Exception as e:
            restricted = self.checkRestrictedPage(e)
            if restricted:
                FacebookPages.objects.filter(page_id=page_id).update(
                    active="Restricted", updated_at=dt.now()
                )
                self.handleError(
                    reason="schedule_adsets_country Restricted page error",
                    message="Could not create new ad because the page was restricted. We will try again on another page if possible. Original error: \n"
                    + str(e),
                )
                raise RestrictedPageException(
                    "Could not create new ad because the page was restricted. We will try again on another page if possible. Original error: \n"
                    + str(e)
                )
            else:
                self.handleError(
                    reason="schedule_adsets_country Could not create new ad",
                    message="Could not create new ad. Original error: \n" + str(e),
                )
                raise RuntimeError(
                    "Could not create new ad. Original error: \n" + str(e)
                )
        maturity = "New" if bid is None else "Test"
        budget = budget or self.get_schedule_budget()
        countries = ",".join(country)

        ad_set_obj = AdAdsets.objects.create(
            ad_platform=PlatFormType.FACEBOOK,
            campaign_id=campaign_id,
            adset_id=newSet.get("id"),
            adset_name=name,
            target_country=countries,
            active="Yes",
            last_checked=schedule_datetime,
            bid=bid,
            budget=budget,
            ignore_until=ignore_until,
            maturity=maturity,
            strategy=strategy,
            max_budget=max_budget,
            scheduler_id=scheduler_id,
        )
        video_ids = [vid[0] for vid in video_thumb_list]
        AdCreativeIds.objects.filter(creative_id__in=video_ids).update(
            ad_adset=ad_set_obj, updated_at=dt.now()
        )

    def schedule_adsets(self, scheduler_id, page_id, campaign_id):
        """
        Schedule all adsets for scheduler_id
        """
        schedule_countries = self.get_schedule_value(scheduler_id, "countries").split(
            ","
        )
        bundle_countries = self.get_schedule_value(scheduler_id, "bundle_countries")
        language = self.get_schedule_value(scheduler_id, "language")
        if bundle_countries:
            language_list = self.get_langauge(
                scheduler_id, schedule_countries, bundle_countries, language
            )
            self.schedule_adsets_country(
                scheduler_id, page_id, campaign_id, schedule_countries, language_list
            )
        else:
            for country in schedule_countries:
                language_list = self.get_langauge(
                    scheduler_id, country, bundle_countries, language
                )
                self.schedule_adsets_country(
                    scheduler_id, page_id, campaign_id, [country], language_list
                )

    def get_langauge(self, scheduler_id, schedule_countries, bundle_country, language):
        language_list = []
        if language:
            try:
                if bundle_country:
                    language = Language.objects.get(
                        ad_scheduler_id=scheduler_id
                    ).language_string
                else:
                    language = Language.objects.get(
                        ad_scheduler_id=scheduler_id, country_code=schedule_countries
                    ).language_string
            except Language.DoesNotExist:
                self.debugPrint(
                    f"[scheduler] No language_string found for scheduler_id {scheduler_id}"
                )
                return language_list
            language_list = [int(ln) for ln in language.split(",")] if language else []
        return language_list

    def get_schedule_budget(self):
        """
        Get the test ad budget from the database
        """
        results = Settings.objects.filter(variable="test_ad_budget").values_list(
            "value"
        )
        if results:
            return int(results[0][0])
        else:
            raise ValueError("No test budget found in the database.")

    def order_upload_sessions(self, entries):
        """
        Sort entries by UploadSesId
        eg:
        [(1, x), (2, x), (3, y), (4, z), (5, z), (6, z)] -> [[ (1, x), (2, x)], [(3, y)], [(4, z), (5, z), (6, z)]]
        entries: List of ID, UploadSesId pairs
        return: List of lists of ID, Upload pairs sorted by UploadSesId
        """

        entries = sorted(entries, key=lambda x: x[1])
        return [list(group) for _, group in groupby(entries, key=lambda x: x[1])]

    def get_schedule_value(self, id, databaseColumn):
        """
        Get a single value from the ad_scheduler table with the given ID from the column databaseColumn
        """
        if ad_scheduler := AdScheduler.objects.filter(id=id).values_list(
            databaseColumn
        ):
            return ad_scheduler[0][0]
        raise ValueError(
            f"No value found in the database for id: {id} and column {databaseColumn}"
        )

    def get_creative_value(self, id, databasecolumn):
        """
        Get a single value from the ad_scheduler table with the given ID from the column databaseColumn
        """
        results = AdCreativeIds.objects.filter(scheduler_id=id).values_list(
            databasecolumn, flat=True
        )
        if len(results) == 0:
            return ""
        elif results and all(x == results[0] for x in results):
            return results[0]
        else:
            return ""

    def find_page(self, scheduler_id, pages):
        """
        Find a page and upload the creatives belonging to the scheduler_id. Retry on different pages if necessary

        scheduler_id (int): ID of the item to schedule
        pages: list of (ID, Acces Token) pairs of pages
        """
        uploadSesId = self.get_schedule_value(scheduler_id, "uploadsesid")
        # Get a valid page
        nr_creatives = AdCreativeIds.objects.filter(
            uploadsesid=uploadSesId,
            # ad_scheduler_id=scheduler_id,
            scheduler_id=scheduler_id,
            ad_platform=PlatFormType.FACEBOOK,
            # creative_id=None,
        ).count()
        schedule_countries = self.get_schedule_value(scheduler_id, "countries").split(
            ","
        )
        nr_ads = len(schedule_countries) * nr_creatives
        pages_checked = 0
        nr_pages = len(pages)
        index_pages = random.randint(
            0, nr_pages - 1
        )  # Start on a random page to reduce load on the first page in the list
        enoughRoom = False
        tried_all_pages = False
        while not (tried_all_pages or enoughRoom):
            index_pages += 1
            pages_checked += 1
            if index_pages == nr_pages:
                index_pages = 0
            if pages_checked >= nr_pages:
                tried_all_pages = True
            room_left = pages[index_pages][2] if pages[index_pages][2] is not None else 0
            if room_left >= nr_creatives:
                room_left = room_left - nr_ads
                enoughRoom = True
        if not enoughRoom:
            raise RuntimeError(
                "No page found with enough space for "
                + str(nr_ads)
                + "  ads with scheduler id: "
                + str(scheduler_id)
                + "."
            )
        else:
            return pages[index_pages]

        # return pages[index_pages] if enoughRoom else None

    def create_campaign_name(self, scheduler_id):
        """
        Generate a campaign name according to the schedule data
        """

        group_name = self.get_schedule_value(scheduler_id, "scraper_group__group_name")
        genre_string = (
            group_name.replace("Fruits", "") if "Fruits" in group_name else group_name
        )

        # If the landingpage is a linkfire URL, only take the shorttag. Else take the whole link
        schedule_landingpage_url = self.get_creative_value(
            scheduler_id, "landingpage_url"
        )
        short_tag = schedule_landingpage_url
        if schedule_landingpage_url.rfind("lnk.to") != -1:
            shortTagLocation = schedule_landingpage_url.rfind("/")
            if shortTagLocation != -1:
                short_tag = schedule_landingpage_url[shortTagLocation + 1 :]

        extra_name = self.get_schedule_value(scheduler_id, "extra_name") or ""
        placement_type = self.get_schedule_value(scheduler_id, "placement_type")
        objective = self.get_schedule_value(scheduler_id, "objective")
        date_str = dt.now().strftime(Timeformat.WeekYearFormat)
        return f"{genre_string} - {date_str} [{placement_type}] [{objective}] {extra_name} - {short_tag}"

    def delete_incorrect_campaign(self, campaign_id):
        """
        Delete a campaign that was not correctly completed during scheduling
        """
        result = self.check_campaign_api_status(campaign_id)
        if result == "New":
            try:
                self.delete_ad_campaign(campaign_id)
            except Exception as e:
                self.handleError(
                    "[Scheduler] Campaign could not be deleted.",
                    "We could not delete campaign with ID: "
                    + str(campaign_id)
                    + ". If it still exists, please delete it manually. The original error:\n"
                    + str(e),
                )
            AdCampaigns.objects.filter(campaign_id=campaign_id).delete()

    def check_campaign_api_status(self, campaign_id):
        campaign = (
            AdCampaigns.objects.filter(campaign_id=campaign_id)
            .values("api_status")
            .first()
        )
        return campaign.get("api_status") if campaign else None

    def schedule_entry(self, scheduler_id, pages):
        """
        Schedule one database entry
        """
        self.upload_creatives(scheduler_id)
        completed = "Yes"
        try:
            campaign_id = self.get_schedule_value(scheduler_id, "campaign_id")
            if campaign_id is None:
                newcampaign = self.schedule_ad_campaign(scheduler_id)
                campaign_id = newcampaign.get("id")
        except Exception as e:
            AdScheduler.objects.filter(id=scheduler_id).update(
                completed="Error", campaign_id=None, updated_at=dt.now()
            )
            self.handleError(
                "[Scheduler] Campaign could not be scheduled.",
                "We could not schedule the campaign for schedule session: "
                + str(scheduler_id)
                + ". Please see below for the error and try to fix the issue. The original error:\n"
                + str(e),
                "High",
                scheduler_id,
            )
            return
        try:
            page = self.find_page(scheduler_id, pages)
            self.schedule_adsets(scheduler_id, page[0], campaign_id)
        except RestrictedPageException:
            campaign_id = campaign_id
            completed = "No"
        except Exception as e:
            campaign_id = None
            completed = "Error"
            self.handleError(
                "[Scheduler] Campaign could not be scheduled.",
                "We could not schedule the campaign for schedule session: "
                + str(scheduler_id)
                + ". Please see below for the error and try to fix the issue. The original error:\n"
                + str(e),
                "High",
                scheduler_id,
            )
            self.delete_incorrect_campaign(campaign_id)

        AdScheduler.objects.filter(id=scheduler_id).update(
            completed=completed, campaign_id=campaign_id, updated_at=dt.now()
        )
        ad_scheduler = AdScheduler.objects.filter(id=scheduler_id).values().first()
        if ad_scheduler.get("completed") == "Yes":
            result = self.check_campaign_api_status(campaign_id)
            if result == "New":
                AdCampaigns.objects.filter(campaign_id=campaign_id).update(
                    api_status="Old", updated_at=dt.now()
                )
            adaccount_id = self.get_schedule_value(scheduler_id, "adaccount_id")
            room_left = self.get_ad_space_available(
                page_id=page[0],
                account=adaccount_id,
            )
            page = FacebookPages.objects.get(page_id=page[0])
            page.room_left = room_left
            page.updated_at = dt.now()
            page.save()

    def get_autogenerate_campaign_data(self):
        return (
            AdScheduler.objects.filter(
                platform=PlatFormType.FACEBOOK, completed="No", campaign_id=None
            )
            .values_list(
                "id",
                "campaign_id",
                "scraper_group_id",
                "campaign_name",
                "adaccount_id",
                "objective",
            )
            .exclude("landingpage_url")
        )

    def scheduler(self, ad_scheduler_data_all):
        """
        Schedule all new ads found in the ad_scheduler table in the DB.
        """
        try:
            self.add_new_campaign(ad_scheduler_data_all=ad_scheduler_data_all)
        except Exception as e:
            self.debugPrint(str(e))

        to_schedule = self.order_upload_sessions(ad_scheduler_data_all)
        for schedule in to_schedule:
            # Skip when no landingpage is found, this will be added later and will be scheduled then.
            if schedule[0][2] in [None, "No"]:
                continue
            scheduler_id = schedule[0][0]
            pages = FacebookPages.objects.filter(
                page_id__in=schedule[0][9].split(",")
            ).values_list("page_id", "page_token", "room_left")
            pages_list = [list(data) for data in pages]
            if pages:
                for sched in schedule:
                    self.schedule_entry(sched[0], pages_list)
            else:
                self.handleError(
                    "[Scheduler] No Facebook pages found.",
                    "Critical error! No Facebook pages were found in the database, so no ads can be scheduled on Facebook at the moment!",
                    "High",
                    scheduler_id,
                )
                AdScheduler.objects.filter(
                    id=scheduler_id, platform=PlatFormType.FACEBOOK
                ).update(completed="Error", updated_at=dt.now())

    def upload_creative_video(self, video_url, adaccount_id):
        """
        Upload a creative video with the given URL
        """
        response = self.post(
            url=f"{url_hp.FACEBOOK_v16_URL}{adaccount_id}/advideos",
            params={
                "file_url": video_url,
            },
        )
        id = response.get("id")
        thumb = None
        try:
            for index in range(10):
                if self.check_video_upload_progress(id):
                    thumb = self.get_thumbnail(id)
                    break
                if index == 9:
                    raise FacebookApiUploaderException(
                        "Upload took more than a minute, something might be wrong."
                    )
                else:
                    time.sleep(6)
        except Exception:
            raise FacebookApiUploaderException(
                f"Could not upload creative with video_url:{video_url}Original response:response"
            )
        return id, thumb

    def check_video_upload_progress(self, video_id):
        """
        Check the upload progress of the given video_id
        Return video status
        """
        response = self.get(
            url=f"{url_hp.FACEBOOK_v16_URL}{str(video_id)}",
            params={"fields": "status, live_status"},
        )
        self.debugPrint(response)
        if "status" not in response or "video_status" not in response.get("status"):
            self.handleError(
                reason="Error found while trying to get video status",
                message=str(response),
            )
            raise RuntimeError(
                f"Error found while trying to get video status. Original message: {response}"
            )
        return response.get("status").get("video_status") == "ready"

    def get_thumbnail(self, video_id):
        """
        Get the thumbnail from a FB video with given video_id
        """

        response = self.get(
            url=f"{url_hp.FACEBOOK_v16_URL}{str(video_id)}/thumbnails", params={}
        )
        preferred_url = None
        for url in response.get("data"):
            if url.get("is_preferred"):
                preferred_url = url.get("uri")
        return preferred_url

    def upload_creatives(self, ad_scheduler_id):
        """
        Upload all creatives linked to the given ad_scheduler_id
        """
        uploadsesid = self.get_schedule_value(ad_scheduler_id, "uploadsesid")
        adaccount_id = self.get_schedule_value(ad_scheduler_id, "adaccount_id")
        if ad_creativeids := AdCreativeIds.objects.filter(
            uploadsesid=uploadsesid,
            # ad_scheduler_id=ad_scheduler_id,
            scheduler_id=ad_scheduler_id,
            ad_platform=PlatFormType.FACEBOOK,
        ).values("id", "url", "filename", "user_id", "creative_id", "creative_type"):
            for creative in ad_creativeids:
                if creative.get("creative_id") is not None:  # Skip already uploaded
                    continue
                if creative.get("creative_type").lower() == "video":
                    try:
                        creative_id, thumb_url = self.upload_creative_video(
                            creative.get("url"), adaccount_id
                        )
                        current_date = dt.now()
                        AdCreativeIds.objects.filter(
                            url=creative.get("url"), ad_platform=PlatFormType.FACEBOOK
                        ).update(
                            creative_id=creative_id,
                            thumbnail_url=thumb_url,
                            uploaded_on=current_date,
                            updated_at=current_date,
                        )
                    except (Exception, FacebookApiUploaderException) as e:
                        AdCreativeIds.objects.filter(id=creative.get("id")).update(
                            notes=str(e), updated_at=dt.now()
                        )
                        self.handleError(
                            reason=f"{'Facebook upload creative error'}",
                            message=f"Could not upload creative with ID: {creative.get('id')}. "
                            + str(e),
                        )
                        raise FacebookApiUploaderException(
                            f"Could not upload creative with ID: {creative[0]}. {repr(e)}"
                        )

        else:
            self.handleError(
                reason="No creatives found for Facebook",
                message=f"No creatives found for Facebook with uploadsesid: {uploadsesid} and ad_scheduler_id: {ad_scheduler_id}",
            )

    def check_rate_limits(self, headers, scheduler_id=None):
        """
        Check if we (almost) hit rate limits. If so; wait 10 minutes or until FB estimates we have access again.
        Set ad_scheduler column completed to 'Ratelimit' so the webapp can show the reason of delay.
        """
        waitTime = 10  # Minutes
        max_limit = 90  # Percent of limit reached
        limit_almost_reached = False
        if "x-business-use-case-usage" in headers:
            all_limits = ast.literal_eval(headers["x-business-use-case-usage"])
            for i in all_limits:
                limits = all_limits[i][0]
                if "call_count" in limits:
                    val = limits["call_count"]
                    if val == 100 and "estimated_time_to_regain_access" in limits:
                        limit_almost_reached = True
                        waitTime = limits["estimated_time_to_regain_access"]
                    elif val >= max_limit:
                        limit_almost_reached = True
                if "total_cputime" in limits:
                    val = limits["total_cputime"]
                    if val == 100 and "estimated_time_to_regain_access" in limits:
                        limit_almost_reached = True
                        waitTime = limits["estimated_time_to_regain_access"]
                    elif val >= max_limit:
                        limit_almost_reached = True
                if "total_time" in limits:
                    val = limits["total_time"]
                    if val == 100 and "estimated_time_to_regain_access" in limits:
                        limit_almost_reached = True
                        waitTime = limits["estimated_time_to_regain_access"]
                    elif val >= max_limit:
                        limit_almost_reached = True
        if "x-app-usage" in headers:
            limit = ast.literal_eval(headers["x-app-usage"])
            if "call_count" in limit:
                val = limit["call_count"]
                if val >= max_limit:
                    limit_almost_reached = True
            if "total_cputime" in limit:
                val = limit["total_cputime"]
                if val >= max_limit:
                    limit_almost_reached = True
            if "total_time" in limit:
                val = limit["total_time"]
                if val >= max_limit:
                    limit_almost_reached = True

        if "x-ad-account-usage" in headers:
            limit = ast.literal_eval(headers["x-ad-account-usage"])
            if "acc_id_util_pct" in limit:
                val = limit["acc_id_util_pct"]
                if val >= max_limit:
                    limit_almost_reached = True
        if limit_almost_reached:
            self.debugPrint(
                "Rate limit (almost) reached, sleeping for "
                + str(waitTime)
                + " minutes."
            )
            if scheduler_id is not None:
                AdScheduler.objects.filter(id=scheduler_id).update(
                    completed="Ratelimit", updated_at=dt.now()
                )
            time.sleep(
                waitTime * 60
            )  # Sleep for waitTime minutes if max_limit% or more of call limit reached

    def add_new_campaign(self, ad_scheduler_data_all):
        for scheduler_index in range(len(ad_scheduler_data_all)):
            id_scheduler = ad_scheduler_data_all[scheduler_index][0]
            campaign_id = ad_scheduler_data_all[scheduler_index][3]
            campaign_name = ad_scheduler_data_all[scheduler_index][4]
            adaccount_id = ad_scheduler_data_all[scheduler_index][5]
            schedule_datetime = ad_scheduler_data_all[scheduler_index][6]
            objective_val = ad_scheduler_data_all[scheduler_index][7]
            scraper_group_id = ad_scheduler_data_all[scheduler_index][8]
            try:
                objective = FacebookObjectiveMap[objective_val]
            except Exception:
                self.handleError(
                    reason="add_new_campaign issue",
                    message="The specified objective: "
                    + str(objective_val)
                    + " has no mapping for Facebook. Please add it to objective_map in constants.py",
                )
            if campaign_id is None:
                campaign_name = (
                    self.create_campaign_name(id_scheduler)
                    if campaign_name is None
                    else campaign_name
                )

                create_campaign_response = self.create_ad_campaign(
                    adaccount_id, campaign_name, objective, id_scheduler
                )
                if new_campaign_id := create_campaign_response.get("id"):
                    AdScheduler.objects.filter(id=id_scheduler).update(
                        campaign_id=new_campaign_id,
                        campaign_name=campaign_name,
                        updated_at=dt.now(),
                    )

                    AdCampaigns.objects.create(
                        automatic="Yes",
                        ad_platform=PlatFormType.FACEBOOK,
                        advertiserid=adaccount_id,
                        campaign_id=new_campaign_id,
                        campaign_name=campaign_name,
                        scraper_group_id=scraper_group_id,
                        active="Yes",
                        last_checked=schedule_datetime,
                        objective=objective_val,
                        api_status="New",
                    )

    def get_count_campaign(self, campaign_id):
        return AdCampaigns.objects.filter(
            campaign_id=campaign_id, ad_platform=PlatFormType.FACEBOOK
        ).count()

    def initializing_bussiness_adaccounts(self):
        """
        fetch live data for facebook bussinesses and ad_account,user,pages then all stuff push to database(profile,authkey,bussinesess and adaccount table)
        """
        response = self.get(
            url=f"{url_hp.FACEBOOK_BUSSINESSES_URL}",
            params={"fields": "name,verification_status"},
        )
        if businesses := response.get("data"):
            for business in businesses:
                business_id = business.get("id")
                business_name = business.get("name")
                business, _ = Business.objects.update_or_create(
                    business_id=business_id,
                    defaults={"profile": self.profile, "name": business_name},
                )

                response = self.get(
                    url=f"{url_hp.FACEBOOK_v16_URL}{business_id}/owned_ad_accounts",
                    params={
                        "fields": "account_id,name,account_status,currency,timezone_id"
                    },
                )
                if available_ad_accounts := response.get("data"):
                    for account in available_ad_accounts:
                        with open(
                            os.path.join(
                                settings.BASE_DIR,
                                "apps/common/json/facebook_timezone.json",
                            )
                        ) as f:
                            my_dict = json.load(f)
                            timezone = my_dict.get(f'{account.get("timezone_id")}')
                        f.close()

                        AdAccount.objects.update_or_create(
                            account_id=account.get("id"),
                            defaults={
                                "account_name": account.get("name"),
                                "live_ad_account_status": account.get("account_status"),
                                "profile": self.profile,
                                "business": business,
                                "timezone": timezone,
                                "currency": account.get("currency"),
                            },
                        )
                else:
                    self.handleError(
                        reason=f"we couldn't find any Facebook ad accounts associated with the profile ID {self.profile.id} and business ID {business_id}.",
                        message=response.get("error").get("message")
                        if "error" in response
                        else "ad accounts were not availble",
                    )
        else:
            self.handleError(
                reason=f"Facebook business were not found for this profile_id:{self.profile.id}.",
                message=response.get("error").get("message")
                if "error" in response
                else "business were not availble",
            )

        self.get_facebook_pages()

    def get_facebook_pages(self):
        # if facebook_user := FacebookUsers.objects.filter(profile=self.profile):
        facebook_user = FacebookUsers.objects.filter(profile=self.profile)
        if businesses := Business.objects.filter(profile=self.profile):
            for business in businesses:
                response = self.get(
                    url=f"{url_hp.FACEBOOK_v16_URL}{business.business_id}/owned_pages",
                    params={"fields": "id,name,access_token,is_published"},
                )
                found = False
                while not found:
                    pages_facebook = []
                    if "data" in response:
                        pages_facebook = response.get("data")
                    else:
                        self.handleError(
                            reason=f"Facebook pages not found for this user_id:{business.business_id} and profile_id:{self.profile.id}",
                            message=response.get("error").get("message")
                            if "error" in response
                            else f"Facebook pages not found for this user_id:{business.business_id}",
                        )

                    # store page data to FacebookPages table
                    for fb_page in pages_facebook:
                        page_id = fb_page.get("id")
                        page_token = fb_page.get("access_token")
                        page_name = fb_page.get("name")
                        FacebookPages.objects.update_or_create(
                            page_id=page_id,
                            defaults={
                                "page_name": page_name,
                                "page_token": page_token,
                                "facebook_user_id": facebook_user[0].id,
                                "facebook_business_id": business.id,
                                "is_published": True
                                if fb_page.get("is_published")
                                else False,
                            },
                        )

                    # Go to next page if it exists
                    if "paging" in response and "next" in response.get("paging"):
                        url = response.get("paging").get("next")
                        response = self.get(
                            url=url, params={"fields": "id,name,access_token"}
                        )
                    else:
                        found = True
        self.get_instagram_accounts()

    def get_instagram_accounts(self, business_id=None):
        # facebook_pages = (
        #     FacebookPages.objects.filter(page_id=page_id).values(
        #         "id", "page_id", "page_token"
        #     )
        #     if page_id
        #     else FacebookPages.objects.filter(
        #         facebook_user__profile=self.profile
        #     ).values("id", "page_id", "page_token")
        # )
        # for pages in facebook_pages:
        # if pages.get("page_token") is None:
        #     continue
        businesses = (
            Business.objects.filter(id=business_id)
            if business_id
            else Business.objects.filter(profile=self.profile)
        )
        if businesses:
            for business in businesses:
                url = f"{url_hp.FACEBOOK_v16_URL}{business.business_id}/instagram_accounts"
                try:
                    response = self.get(
                        url=url,
                        params={
                            "fields": "username,profile_pic",
                            "access_token": self.access_token,
                        },
                    )
                except Exception as e:
                    continue
                found = False
                while not found:
                    instagram_accounts = []
                    if "data" in response:
                        instagram_accounts = response.get("data")

                    for instagram in instagram_accounts:
                        instagram_id = instagram.get("id")
                        instagram_name = instagram.get("username")
                        instagram_profile_pic = instagram.get("profile_pic")
                        InstagramAccounts.objects.update_or_create(
                            instagram_account_id=instagram_id,
                            # facebook_page_id=pages.get("id"),
                            facebook_business_id=business.id,
                            defaults={
                                "instagram_account_name": instagram_name,
                                "instagram_profile_pic": instagram_profile_pic,
                            },
                        )

                    # Go to next page if it exists
                    if "paging" in response and "next" in response.get("paging"):
                        url = response.get("paging").get("next")
                        response = self.get(
                            url=url,
                            params={
                                "fields": "username,profile_pic",
                                "access_token": self.access_token,
                            },
                        )
                    else:
                        found = True


def is_valid_facebook_access_token(access_token):
    # credentials_url = f"{url_hp.FACEBOOK_ACCESS_TOKEN_USING_CREDENTIALS_URL}?client_id={settings.FACEBOOK_APP_ID}&client_secret={settings.FACEBOOK_SECRET_ID}&grant_type=client_credentials"
    # credentials_response = requests.get(credentials_url)
    # r = credentials_response.json()
    # debug_token_url = f"{url_hp.FACEBOOK_DEBUG_TOKEN}?input_token={r.get('access_token')}&access_token={self.access_token}"
    # debug_token_response = requests.get(debug_token_url)
    # if debug_token_response.status_code == 200:
    #     debug_token_response = debug_token_response.json()
    #     is_valid = debug_token_response.get("data").get("is_valid")
    #     return {"is_valid": is_valid, "error_message": None}
    # else:
    #     debug_token_response = debug_token_response.json()
    #     error_message = debug_token_response.get("error").get("message")
    #     return {"is_valid": False, "error_message": error_message}
    try:
        response = requests.get(
            f"{url_hp.FACEBOOK_v16_URL}me/?access_token={access_token}&fields=id,first_name,last_name,email"
        )
        res = response.json()
        if response.ok and res.get("id"):
            return {
                "is_valid": True,
                "error_message": None,
                "access_token": access_token,
            }
        else:
            return {
                "is_valid": False,
                "error_message": res.get("message"),
                "access_token": access_token,
            }
    except Exception as e:
        return {
            "is_valid": False,
            "error_message": str(e),
            "access_token": access_token,
        }
