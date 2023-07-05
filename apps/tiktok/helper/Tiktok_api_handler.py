import time
import datetime
import re
from datetime import timedelta
import os
import random
from decimal import Decimal
import json
import requests
import collections
from django.db.models import Q
from six import string_types
from six.moves.urllib.parse import urlencode, urlunparse
from SF import settings
from SF.settings import BASE_DIR
from apps.common.constants import PlatFormType, AdAccountActiveType
from datetime import datetime as dt
from apps.common.models import (
    AdAccount,
    AdScheduler,
    Authkey,
    AdCreativeIds,
    AdAdsets,
    AdCampaigns,
    CustomConversionEvents,
    DailyAdspendGenre,
    Pixels,
    CustomAudiences,
    AdsetInsights,
    Language,
    Day_Parting,
    Profile,
)
from apps.scraper.models import Settings
from apps.common import AdPlatform as AP
from apps.common.custom_exception import (
    DatabaseInvalidDataException,
    DataTypeStructureException,
    TiktokApiResponseCodeException,
    TiktokInternalServerException,
    APIGetterException,
    DatabaseRequestException,
    IDMismatchException,
)
from dateutil import parser
from apps.common.urls_helper import URLHelper
import pytz
from apps.common.constants import TiktokObjectiveMap, TiktokEventMap, BidStrategyMap

url_hp = URLHelper()


class TikTokAPI(AP.AdPlatform):
    def __init__(self, debug_mode, profile):
        """
        Populates auth key and checks if this key is still valid
        Parameters:
        string: Database connection
        """
        super().__init__(debug_mode)
        self.first_message = True
        self.secret = settings.TIKTOK_SECRET_ID
        self.app_id = settings.TIKTOK_APP_ID
        self.profile = profile
        self.access_token = self.get_authkey()
        is_still_authorized = self.is_authorized()
        if is_still_authorized is False:
            raise Exception(
                "Authorization key for TikTok is outdated. Initiate new one with web app"
            )
        self.retries = 0
        self.hardcoded_thumbnail = ["ad-site-i18n-sg/202201275d0dfd2bfd0472084437ab7a"]
        self.my_args_note = ""

    def handleError(self, reason, message, priority="Low", scheduler_id=None):
        if "JSONDecodeError" in message:
            message += self.my_args_note
        super().handleError(reason, message, priority, scheduler_id)

    def debugPrint(self, message):
        super().debugPrint(message)

    def handleNotes(self, reason, message, id):
        subject = f"[{reason}] Tiktok API."
        notification = '{"reason":' + subject + ', "text_body":' + message + "}"
        AdCreativeIds.objects.filter(id=id).update(
            notes=notification, updated_at=dt.now()
        )

    def get_authkey(self):
        """
        Fetches authkey from database to populate this parent class
        Returns:
        string: Authorization key
        """
        response = Authkey.objects.filter(profile=self.profile).values("access_token")
        if response is None:
            if self.first_message:
                self.handleError(
                    "Tiktok Authorization Key Missing",
                    "If you want to use Tiktok API, connect your account via the web app.",
                )
                self.first_message = False
            self.debugPrint(
                "[Tiktok] Sleep. No Authorization code found. Checking back in 1 min..."
            )
            time.sleep(60)
            return self.get_authkey()
        self.first_message = True
        return response[0].get("access_token")

    def is_authorized(self):
        """
        Performs a simple fetch for advertiser ids, if fails return not authorized
        Returns:
        boolean: Authorization status
        """
        userinfo = self.get_userinfo()
        return userinfo.get("code") == 0

    def get_advertiserIds(self, toggle_action=None, is_run_initializer=False):
        """
        Fetches active advertiser ids from the database table
        Returns:
        array: with advertiser ids
        """
        if is_run_initializer:
            self.initializing_bussiness_adaccounts()
        return AdAccount.objects.filter(
            active=AdAccountActiveType.Pending
            if toggle_action
            else AdAccountActiveType.Yes,
            profile__ad_platform=PlatFormType.TIKTOK,
            profile=self.profile,
        )

    def get_userinfo(self):
        """
        API call to retrieve user info
        Returns:
        list: List with user info
        """
        my_args = "{}"
        response = self.get(url=url_hp.TIKTOK_USERINFO_URL, params=my_args)
        return response

    def change_key(self, name):
        """
        Changes access_token.
        Returns none
        Param: name of email linked to access token
        """
        # if 'lofi' in name:
        # data masked saved in database
        #    name = 'l***i@strangefruits.net'
        # elif 'esra' in name:
        #    name = 'e***a@strangefruits.net'
        profile = Profile.objects.get(email=name)
        authkey = Authkey.objects.get(profile=profile)

        if not authkey:
            if self.first_message:
                self.handleError(
                    "Tiktok Authorization Key Missing",
                    "If you want to use Tiktok API, connect your account "
                    + str(name)
                    + " via the web app.",
                )
                self.first_message = False
            self.debugPrint(
                "[Tiktok] Sleep. No Authorization code found "
                + str(name)
                + ". Checking back in 1 min..."
            )
            time.sleep(60)
        self.first_message = True

        access_token = authkey.access_token
        if access_token != self.access_token:
            self.debugPrint("[access_token] Changing access token to " + str(name))
            self.access_token = access_token
            is_still_authorized = self.is_authorized()
            if is_still_authorized is False:
                if self.first_message:
                    self.handleError(
                        "Tiktok Authorization Key Missing",
                        "If you want to use Tiktok API, connect your account "
                        + str(name)
                        + " via the web app.",
                    )
                    self.first_message = False
                self.debugPrint(
                    "[Tiktok] Sleep. No Authorization code found "
                    + str(name)
                    + ". Checking back in 1 min..."
                )
                time.sleep(60)
            self.first_message = True

    def check_input(self, content):  # values to check:
        """
        Checks variables for illegal values. Only checks known (hardcoded) values
        :Param: list of tuples [(Variable name, Value)]
        :return: Exception or 0 (no Exception) or 1 when one or more country code exceptions were found.
        """
        statusvalues = [
            "CAMPAIGN_STATUS_DELETE",
            "CAMPAIGN_STATUS_ADVERTISER_AUDIT_DENY",
            "CAMPAIGN_STATUS_ADVERTISER_AUDIT",
            "ADVERTISER_CONTRACT_PENDING",
            "CAMPAIGN_STATUS_BUDGET_EXCEED",
            "CAMPAIGN_STATUS_DISABLE",
            "CAMPAIGN_STATUS_ENABLE",
            "CAMPAIGN_STATUS_ALL",
            "CAMPAIGN_STATUS_NOT_DELETE",
            "ADGROUP_STATUS_DELETE",
            "ADGROUP_STATUS_CAMPAIGN_DELETE",
            "ADGROUP_STATUS_ADVERTISER_AUDIT_DENY",
            "ADGROUP_STATUS_ADVERTISER_AUDIT",
            "ADVERTISER_CONTRACT_PENDING",
            "ADGROUP_STATUS_CAMPAIGN_EXCEED",
            "ADGROUP_STATUS_BUDGET_EXCEED",
            "ADGROUP_STATUS_BALANCE_EXCEED",
            "ADGROUP_STATUS_AUDIT_DENY",
            "ADGROUP_STATUS_REAUDIT",
            "ADGROUP_STATUS_AUDIT",
            "ADGROUP_STATUS_CREATE",
            "ADGROUP_STATUS_NOT_START",
            "ADGROUP_STATUS_TIME_DONE",
            "ADGROUP_STATUS_CAMPAIGN_DISABLE",
            "ADGROUP_STATUS_DISABLE",
            "ADGROUP_STATUS_DELIVERY_OK",
            "ADGROUP_STATUS_SHADOW_ADGROUP_REAUDIT",
            "ADGROUP_STATUS_ALL",
            "ADGROUP_STATUS_NOT_DELETE",
            "ADGROUP_STATUS_PRE_ONLINE",
            "ADGROUP_STATUS_PARTIAL_AUDIT_AND_DELIVERY_OK",
            "ENABLE",
            "DISABLE",
        ]
        errors = 0
        locationerror = False
        msg = ""
        for content_index in range(len(content)):
            if len(content[content_index]) > 2:
                errors += 1
                msg += f"Error {errors}: Could not read content, tuple contains too many values.\n"

            if content[content_index][0] == "location":  # TODO
                if len(content[content_index][1]) == 0:
                    errors += 0
                    msg += f"Error{errors}: Variable country: No values found.\n"
                elif content[content_index][1] == "":
                    errors += 0
                    msg += f"Error{errors}: Variable country: Country can't be NULL.\n"
            elif content[content_index][0] == "campaign_id":
                if content[content_index][1] == "":
                    errors += 0
                    msg += f"Error{errors}: campaign_id: campaign_id can't be empty.\n"
            elif content[content_index][0] == "adgroup_id":
                if content[content_index][1] == "":
                    errors += 0
                    msg += f"Error {errors}: adgroup_id can't be empty.\n"
            elif content[content_index][0] == "adgroup_name":
                if content[content_index][1] == "":
                    errors += 0
                    msg += f"Error {errors}: adgroup_name can't be empty.\n"
            elif content[content_index][0] == "opt_status":
                if content[content_index][1] == "":
                    errors += 0
                    msg += f"Error {errors}: opt_status can't be empty.\n"

                if content[content_index][1] not in statusvalues:
                    errors += 0
                    msg += f"Error {errors}: active can only be opt_status values (see TikTok API Enumeration), not: {content[content_index][1]}.\n"

            elif content[content_index][0] == "ad_platform":
                allowed_platforms = ["Tiktok", "Facebook", "Snapchat"]
                if content[content_index][1] not in allowed_platforms:
                    errors += 0
                    msg += f"Error {errors}: ad_platform can only be Tiktok, Facebook, or Snapchat, not: {content[content_index][0]}.\n"

            elif (
                content[content_index][0] == "genre"
            ):  # TODO, uitkizen welke genres wel/niet kunnen?
                if content[content_index][1] == "":
                    errors += 0
                    msg += f"Error {errors}: Genre can't be empty.\n"
            elif (
                content[content_index][0] == "landing_page_url"
                and not content[content_index][1]
            ):
                errors += 0
                msg += f"Error {errors}: landing_page_url can't be empty.\n"

            elif content[content_index][0] == "campaign_name":
                if content[content_index][1] == "":
                    errors += 0
                    msg += f"Error {errors}: campaign_name: campaign_name can't be empty.\n "
            elif content[content_index][0] == "bid":
                if content[content_index][1] < 0:
                    errors += 0
                    msg += f"Error {errors}: bid: bid can't be lower than 0.\n "
            elif content[content_index][0] == "budget":
                if content[content_index][1] < 0:
                    errors += 0
                    msg += f"Error {errors}: budget: budget can't be lower than 0.\n "
            else:
                errors += 0
                msg += (
                    f"Error{errors}: Unknown variable {content[content_index][0]} .\n"
                )
        if errors > 0 and not (errors == 1 and locationerror):
            raise DatabaseInvalidDataException(msg)
        if (
            errors == 1 and locationerror
        ):  # don't handle each individual location error due to database overflow, rather add them up in one error
            return 1
        return 0

    def check_response(self, response):
        """
        Checks api response for unexpected data to prevent crashes. With bad connections the api can send unexpected responses.
        Returns: None or raises exception
        parameter: Response from api with page_info
        """
        if str(type(response)) != "<class 'dict'>":
            raise DataTypeStructureException(
                f"response should be a dict, not {type(response)}: {response}"
            )
        if not (
            "message" in response.keys()
            and "data" in response.keys()
            and "code" in response.keys()
            and "request_id" in response.keys()
        ):
            raise DataTypeStructureException(
                "keys should be dict_keys(['message', 'code', 'data', 'request_id']), not : "
                + str(response.keys())
                + " response: "
                + str(response)
            )
        if response["code"] == 0:
            if str(type(response["data"])) != "<class 'dict'>":
                raise DataTypeStructureException(
                    "response['data'] should be <class 'dict'>, not : "
                    + str(type(response["data"]))
                    + " response: "
                    + str(response)
                )
            if not (
                "page_info" in response["data"].keys()
                and "list" in response["data"].keys()
            ):
                raise DataTypeStructureException(
                    "response['data'].keys() should be dict_keys(['page_info', 'list']), not : "
                    + str(response["data"].keys())
                    + " response: "
                    + str(response)
                )
            if str(type(response["data"]["page_info"])) != "<class 'dict'>":
                raise DataTypeStructureException(
                    "response['data']['page_info'] should be <class 'dict'>, not : "
                    + str(type(response["data"]["page_info"]))
                    + " response: "
                    + str(response)
                )

            if not (
                "total_number" in response["data"]["page_info"].keys()
                and "page" in response["data"]["page_info"].keys()
                and "page_size" in response["data"]["page_info"].keys()
                and "total_page" in response["data"]["page_info"].keys()
            ):
                raise DataTypeStructureException(
                    "response['data']['page_info'].keys() should be <class 'dict'>, not : "
                    + str(response["data"]["page_info"].keys())
                    + " response: "
                    + str(response)
                )
            if (
                str(type(response["data"]["page_info"]["total_page"]))
                != "<class 'int'>"
            ):
                raise DataTypeStructureException(
                    "response['data']['page_info']['total_page'] should be <class 'int'>, not : "
                    + str(type(response["data"]["page_info"]["total_page"]))
                    + " response: "
                    + str(response)
                )

    def printStatus(self, page, pages_total):
        """
        Helper function to keep track of progress when using pages. Only used for debugging.
        """
        if self.debug_mode:
            percent = int((page * 100) / pages_total)
            divisor = (
                pages_total + (25 - (pages_total % 25))
            ) / 25  # should be divisable by 25 (every 4% update)
            if pages_total < 50:
                if page % 2 == 0:
                    print(
                        "[Get Progress] Read ",
                        page,
                        "/",
                        pages_total,
                        " pages.",
                        percent,
                        "%",
                    )
            else:
                if page % divisor == 0:
                    print(
                        "[Get Progress] Read ",
                        page,
                        "/",
                        pages_total,
                        " pages.",
                        percent,
                        "%",
                    )

    def recalculate_Pages(self, page, page_size, total_items):
        """
        Recalculates pageSize when a time out occurs. If the page size changes current page should scale with it.
        parameters: CurrentPage, pageSize, total items
        returns: CurrentPage, pageSize, total items [new]
        """
        self.debugPrint("[progress] Recalculating pages.")
        if total_items > 0 and page_size > 1:
            newsize = int(page_size / 2)
            newpage = page * 2
            newtotal = int(total_items / newsize)
            if total_items % newsize != 0:
                newtotal += 1
            if page_size % 2 == 0:
                newpage -= 1
            if self.debug_mode:
                print("[Progress] new current page: ", newpage)
                print("[Progress] new page size: ", newsize)
                print("[Progress] new total pages: ", newtotal)
                print("[Progress] current progress: ", newpage, "/", newtotal)
            return newpage, newsize, newtotal
        elif page_size == 1:
            self.debugPrint("[progress] Minimal page size reached.")
            return page, page_size, total_items
        else:
            self.debugPrint("[progress] Could not recalculate pages.")
            return page, page_size, 1

    def get_active_ads(self, id):
        """
        Helper function, mostly used to mock for testing to test database call.
        """
        list_of_campaign_id = AdCampaigns.objects.filter(advertiserid=id).values_list(
            "campaign_id", flat=True
        )
        active_ads = AdAdsets.objects.filter(
            campaign_id__in=list_of_campaign_id, active="Yes"
        ).values_list("adset_id", "campaign_id")
        return active_ads

    def create_batch(self, id):
        active_adsets = self.get_active_ads(id=id)
        if len(active_adsets) == 0:
            self.debugPrint("no active ads found")
            return 0, collections.defaultdict(list), 0
        # Build array with max 100 adset_ids per iteration
        active_adset_ids = collections.defaultdict(list)
        total_active_adsets = len(active_adsets)  # 176
        i = 0
        page = 0
        for adset in active_adsets:
            active_adset_ids[page].append(adset[0][0])  # Append the adset_id
            i += 1
            if i / 100 >= (page + 1):
                page += 1
        # Final array: active_adset_ids[0] = array of length 100, active_adset_ids[1] = array of length x....
        return page, active_adset_ids, total_active_adsets

    def get_ads(self, is_run_initializer=False):
        """
        API call to retrieve all ads per advertiser id account.
        Parameters: None
        Returns: A list with responses per advertiser Per page. If no ads were found returns []
        """
        fields = json.dumps(["adgroup_id", "landing_page_url", "status"])
        page_size = 1000
        response = []
        results = self.get_advertiserIds(is_run_initializer=is_run_initializer)
        for obj in results:
            self.debugPrint("getting ads for advertiser ID: " + str(obj.account_id))
            page, active_adset_ids, total_active_adsets = self.create_batch(
                obj.account_id
            )
            self.debugPrint(
                "[Active Adsets] Found {} active adsets. Created {} batches of each max 100 active adset ids. Iterating over them...".format(
                    str(len(active_adset_ids)), str(len(active_adset_ids))
                )
            )
            for k, list_active_adset_ids in active_adset_ids.items():
                pagetotalset = False
                page = 1
                pages_read = 0
                pages_total = 1
                timeout = 0
                total_items = 0
                trys = 5
                while page - 1 < pages_total:
                    if timeout >= trys:
                        # raise TiktokApiTimeOutException(responseTemp)
                        break
                    advertiser_id = obj.account_id  # Fetched from database
                    my_args = json.dumps(
                        {
                            "advertiser_id": advertiser_id,
                            "fields": fields,
                            "page_size": page_size,
                            "page": page,
                            "filtering": {"adgroup_ids": list_active_adset_ids},
                        }
                    )

                    responsetemp = self.get(
                        url=url_hp.TIKTOK_AD_GET_URL, params=my_args
                    )
                    try:
                        self.check_response(
                            responsetemp
                        )  # todo, this is now redundant as we check for internal server errors within the get() and post() functions?
                    except DataTypeStructureException as e:
                        timeout += 1
                        page, page_size, pages_total = self.recalculate_Pages(
                            page=page, page_size=page_size, total_items=total_items
                        )
                        if timeout == trys:
                            self.handleError("[get_ads] TypeError", e.message, "High")
                        self.debugPrint(e.message)
                        continue
                    # if (
                    #     responseTemp["code"] == 40001
                    # ):  # only check for code if datastructure is correct
                    #     raise TiktokApiResponseCodeException(responseTemp)
                    if responsetemp.get("code") != 0:
                        page, page_size, pages_total = self.recalculate_Pages(
                            page=page, page_size=page_size, total_items=total_items
                        )
                        time.sleep(1)
                        timeout += 1
                        self.debugPrint("[get ads] code did not return 0")
                        continue
                    if responsetemp.get("code") == 0:
                        response.append(responsetemp)
                    if (
                        pagetotalset is False
                    ):  # Only on first loop set page total, or when page_size changes
                        pages_total = (
                            responsetemp.get("data").get("page_info").get("total_page")
                        )  # Data structure should always be correct after check_response
                        total_items = (
                            responsetemp.get("data")
                            .get("page_info")
                            .get("total_number")
                        )
                        pagetotalset = True
                    self.debugPrint(
                        "[Ads pages] Batch {}/{}. Ad Page {}/{}. Total ads: {}".format(
                            str(k + 1),
                            str(len(active_adset_ids)),
                            str(page),
                            str(pages_total),
                            str(total_items),
                        )
                    )
                    if timeout > trys:
                        # raise TiktokApiTimeOutException(responseTemp)
                        break
                    pages_read += 1
                    page += 1
        return response

    def get_ad(self, advertiser_id, ad_id):
        """
        Returns specific fields of GET ads based on filtering value
        :param advertiser_id: id of advertiser
        :param ad_id: id of specific ad
        :param filtering: json string indicating fields to return
        :return: json response
        """
        my_args = json.dumps(
            {"advertiser_id": advertiser_id, "filtering": {"ad_ids": ad_id}}
        )

        try:
            response = self.get(url=url_hp.TIKTOK_AD_GET_URL, params=my_args)
        except Exception as e:
            self.debugPrint(e)
            return

        if response.get("code") == 40001:
            raise TiktokApiResponseCodeException(response)
        elif response.get("code") == 40002:
            print(response)

        return response

    def get_adgroups(
        self, ad_account_id=None, toggle_action=None, is_run_initializer=False
    ):
        """
        API call to retrieve all adgroups per advertiser id account.
        Parameters: None
        Returns: A list with responses per advertiser Per page. If no adgroups were found returns []
        """
        results = self.get_advertiserIds(
            toggle_action=toggle_action, is_run_initializer=is_run_initializer
        )
        fields = json.dumps(
            [
                "location",
                "campaign_name",
                "campaign_id",
                "adgroup_name",
                "opt_status",
                "budget",
                "bid",
                "advertiser_id",
            ]
        )
        response = []
        campaings_found = 0
        current = 0
        for obj in results.filter(
            **({"account_id": ad_account_id} if ad_account_id is not None else {})
        ):
            self.debugPrint(
                "[get_adgroups] Getting adgroups for advertiser: " + str(obj.account_id)
            )
            pagetotalset = False
            timeout = 0
            trys = 5
            page_size = 1000
            page = 1
            pages_read = 0
            pages_total = 1
            total_items = 0
            while page - 1 < pages_total:
                if timeout >= trys:
                    break
                    # raise TiktokApiTimeOutException(responsetemp)
                advertiser_id = obj.account_id  # Fetched from database
                my_args = json.dumps(
                    {
                        "advertiser_id": advertiser_id,
                        "fields": fields,
                        "page_size": page_size,
                        "page": page,
                    }
                )

                responsetemp = self.get(
                    url=url_hp.TIKTOK_ADGROUP_UPDATE_URL, params=my_args
                )
                try:
                    self.check_response(responsetemp)
                except DataTypeStructureException as e:
                    timeout += 1
                    page, page_size, pages_total = self.recalculate_Pages(
                        page=page, page_size=page_size, total_items=total_items
                    )
                    if timeout == trys:
                        self.handleError("[get_adgroups] TypeError ", e.message, "High")
                    self.debugPrint(e.message)
                    continue
                # if (
                #     responsetemp["code"] == 40001
                # ):  # only check for code if datastructure is correct
                #     raise TiktokApiResponseCodeException(responseTemp)
                if responsetemp.get("code") != 0:
                    page, page_size, pages_total = self.recalculate_Pages(
                        page=page, page_size=page_size, total_items=total_items
                    )
                    time.sleep(1)
                    timeout += 1
                    self.debugPrint("[get adgroups] code did not return 0")
                    continue
                if responsetemp.get("code") == 0:
                    response.append(responsetemp)
                if (
                    pagetotalset is False
                ):  # Only on first loop set page total, or when page_size changes
                    pages_total = (
                        responsetemp.get("data").get("page_info").get("total_page")
                    )  # Data structure should always be correct after check_response
                    total_items = (
                        responsetemp.get("data").get("page_info").get("total_number")
                    )
                    pagetotalset = True
                self.printStatus(page=page, pages_total=pages_total)
                pages_read += 1
                page += 1
            current = 0
            for response_index in range(len(response)):
                current += len(response[response_index]["data"]["list"])
            self.debugPrint(
                "Found "
                + str(current - campaings_found)
                + " adgroups for advertiser : "
                + str(obj.account_id)
            )
            campaings_found += current
        return response

    def get_campaign(
        self,
        primary_status=False,
        ad_account_id=None,
        toggle_action=None,
        is_run_initializer=False,
    ):
        """
        API call to retrieve all adcampaigns per advertiser id account.
        Parameters: None
        Returns: A list with responses per advertiser Per page. If no adCampaigns were found returns []
        """
        results = self.get_advertiserIds(
            toggle_action=toggle_action, is_run_initializer=is_run_initializer
        )
        campaings_found = 0
        current = 0
        response = []
        for obj in results.filter(
            **({"account_id": ad_account_id} if ad_account_id is not None else {})
        ):
            self.debugPrint(
                "[get_campaign] Getting campaigns for advertiser: "
                + str(obj.account_id)
            )
            page_size = 1000
            page = 1
            pages_read = 0
            pages_total = 1
            total_items = 0
            pagetotalset = False
            timeout = 0
            trys = 5
            while page - 1 < pages_total:
                if timeout >= trys:
                    break
                    # raise TiktokApiTimeOutException(responseTemp)
                advertiser_id = obj.account_id  # Fetched from database
                filtering = {}
                if primary_status:
                    filtering["primary_status"] = "STATUS_DELETE"

                my_args = json.dumps(
                    {
                        "advertiser_id": advertiser_id,
                        "page_size": page_size,
                        "page": page,
                        "filtering": filtering,
                    }
                )
                responsetemp = self.get(
                    url=url_hp.TIKTOK_GET_CAMPAIGN_URL, params=my_args
                )
                try:
                    self.check_response(responsetemp)
                except DataTypeStructureException as e:
                    timeout += 1
                    page, page_size, pages_total = self.recalculate_Pages(
                        page=page, page_size=page_size, total_items=total_items
                    )
                    if timeout == trys:
                        self.handleError("[get_campaign] TypeError", e.message, "High")
                    self.debugPrint(e.message)
                    continue
                # if (
                #     responseTemp["code"] == 40001
                # ):  # only check for code if datastructure is correct
                #     raise TiktokApiResponseCodeException(responseTemp)
                if responsetemp.get("code") != 0:
                    page, page_size, pages_total = self.recalculate_Pages(
                        page=page, page_size=page_size, total_items=total_items
                    )
                    time.sleep(1)
                    timeout += 1
                    self.debugPrint("[get adgroups] code did not return 0")
                    continue
                response.append(responsetemp)
                if (
                    pagetotalset is False
                ):  # Only on first loop set page total, or when page_size changes
                    pages_total = (
                        responsetemp.get("data").get("page_info").get("total_page")
                    )  # Data structure should always be correct after check_response
                    total_items = (
                        responsetemp.get("data").get("page_info").get("total_number")
                    )
                    pagetotalset = True
                self.printStatus(page=page, pages_total=pages_total)  # if Debug is true
                pages_read += 1
                page += 1
            current = 0
            for response_index in range(len(response)):
                current += len(response[response_index]["data"]["list"])
            self.debugPrint(
                "Found "
                + str(current - campaings_found)
                + " campaingns for advertiser : "
                + str(obj.account_id)
            )
            campaings_found += current
        return response

    def post(self, url, params):
        """
        Send POST request
        :param json_str: Args in JSON format
        :return: Response in JSON format
        """
        # url = self.build_url(url)
        try:
            args = json.loads(params)
        except Exception as e:
            self.debugPrint(
                f"[JSONDecodeError]response is not valid JSON ,response args:{args}",
                str(e),
            )
        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
        rsp = requests.post(url, headers=headers, json=args)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[5[0-9][0-9]\]>")
        if re.search(pattern, str(rsp)):
            self.debugPrint(rsp.json())
            raise TiktokInternalServerException(rsp.json())
        try:
            # self.retries = 0
            json_response = rsp.json()
            return json_response
        except Exception as e:
            self.debugPrint(
                f"[response]response is not valid JSON retry count:{self.retries},response:{rsp}",
                str(e),
            )
            self.handleError(
                "[Tiktok Post request issue]",
                f" Please see below for the error and try to fix the issue.{rsp}. The original error{str(e)}",
            )
            return rsp.json()

    def get(self, url, params):
        """
        Send GET request
        :param json_str: Args in JSON format
        :return: Response in JSON format
        """
        args = json.loads(params)
        query_string = urlencode(
            {
                k: v if isinstance(v, string_types) else json.dumps(v)
                for k, v in args.items()
            }
        )

        headers = {
            "Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
        rsp = requests.get(url, headers=headers, params=query_string)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[5[0-9][0-9]\]>")
        if not re.search(pattern, str(rsp)):
            return rsp.json()

    def activate_adgroup(self, adgroup_id, advertiser_id):
        """
        Helper function that sets adGroup status to ENABLE after the adgroup is created
        parameters: Adgroup_ID
        return: Response message from api
        """

        opt_status = "ENABLE"
        response = []
        my_args = json.dumps(
            {
                "advertiser_id": advertiser_id,
                "adgroup_ids": [adgroup_id],
                "opt_status": opt_status,
            }
        )
        responsetemp = self.post(url=url_hp.TIKTOK_ADGROUP_URL, params=my_args)
        if responsetemp["code"] != 0:  # only check for code if datastructure is correct
            raise TiktokApiResponseCodeException(responsetemp)
        response.append(responsetemp)
        return response

    def create_ad_campaign(self, campaign_name):
        """
        Creates ad campaign
        :Param str: campaign_name, created with data from database
        """

        results = self.get_advertiserIds()

        budget_mode = "BUDGET_MODE_INFINITE"  # Fetched from database Uiteindelijk wordt dit uit database gehaald
        objective_type = "TRAFFIC"  # Fetched from database Uiteindelijk wordt dit uit database gehaald
        # Args in JSON format
        response = []
        for obj in results:
            advertiser_id = int(obj.account_id)
            my_args = json.dumps(
                {
                    "advertiser_id": advertiser_id,
                    "budget_mode": budget_mode,
                    "objective_type": objective_type,
                    "campaign_name": campaign_name,
                }
            )
            responsetemp = self.post(
                url=url_hp.TIKTOK_CREATE_CAMPAIGN_URL, params=my_args
            )
            if responsetemp.get("code") == 0:
                response.append(responsetemp)
        return response

    objective_map_reversed = {v: k for k, v in TiktokObjectiveMap.items()}

    def create_ad_group_conversions(
        self,
        advertiser_id,
        campaign_id,
        adgroup_name,
        location,
        schedule_type,
        schedule_start_time,
        budget,
        bid,
        is_comment_disable,
        video_download,
        creative_material_mode,
        Age,
        pixel_id,
        external_action_raw,
        custom_audience,
        bid_strategy_raw,
        accelerated_spend,
        dayparting_string,
        language_string,
        objective,
    ):
        self.debugPrint("[create ad_group] Attempting to create conversions adgroup")

        placement_type = "PLACEMENT_TYPE_NORMAL"  # Plsacement: manual, only TikTok -> normal = manual?
        external_type = "WEBSITE"
        budget_mode = "BUDGET_MODE_DAY"
        optimize_goal = "CONVERT" if objective == "Conversions" else "CLICK"
        pacing = "PACING_MODE_SMOOTH"
        billing_event = "OCPM" if objective == "Conversions" else "CPC"
        placement = "PLACEMENT_TIKTOK"
        language_list = None

        if accelerated_spend:
            pacing = "PACING_MODE_FAST"
        else:
            pacing = "PACING_MODE_SMOOTH"
        try:
            bid_strategy = BidStrategyMap[bid_strategy_raw]
        except Exception:
            raise ValueError(
                f"The given bid strategy {bid_strategy_raw}is incorrect, it should be Bid or Lowestcost"
            )
        # Set custom conversion event
        if  objective =='Traffic' or  external_action_raw == None:
                external_action = None
        elif (
            not external_action_raw.isnumeric()
            and external_action_raw in TiktokEventMap
        ):
            try:
                external_action = TiktokEventMap[external_action_raw]
            except Exception:
                raise ValueError(
                    "The given event type "
                    + str(external_action_raw)
                    + " is incorrect."
                )
        else:
            custom_event_types = CustomConversionEvents.objects.filter(
                platform=PlatFormType.FACEBOOK, event_id=external_action_raw
            ).values_list("external_action")
            if len(custom_event_types) != 0:
                external_action = custom_event_types[0][0]
            else:
                raise ValueError(
                    "The given event type "
                    + str(external_action_raw)
                    + " is incorrect."
                )
        if language_string is not None and len(language_string) != 0:
            language_list = language_string[0][0].split(",")
        response = []
        my_args = {
            "advertiser_id": advertiser_id,
            "placement_type": placement_type,
            "external_type": external_type,
            "budget_mode": budget_mode,
            "optimize_goal": optimize_goal,
            "billing_event": billing_event,
            "placement": [placement],
            "campaign_id": campaign_id,
            "adgroup_name": adgroup_name,
            "location": location,
            "schedule_type": schedule_type,
            "schedule_start_time": str(schedule_start_time),
            "bid_type": bid_strategy,
            "budget": str(budget),
            "is_comment_disable": is_comment_disable,
            "video_download": video_download,
            "age": Age,
            "pixel_id": int(pixel_id),
            "pacing": pacing,
        }
        if custom_audience:
            my_args["excluded_audience"] = custom_audience

        if bid_strategy_raw == "Bid":
            if objective == "Conversions":
               my_args["conversion_bid"] = str(bid)
            else :
               my_args["bid"] = str(bid)

        if dayparting_string is not None:
            my_args["dayparting"] = dayparting_string[0][0]

        if language_list is not None:
            my_args["languages"] = language_list

        if external_action != None and objective == 'Conversions':
            my_args["external_action"] = external_action

        my_args = json.dumps(my_args)
        responsetemp = self.post(url=url_hp.TIKTOK_CREATE_ADGROUP_URL, params=my_args)
        response.append(responsetemp)

        if (
            responsetemp["code"] == 40002
            and "already exists" in responsetemp["message"]
        ):  # Potential: Ad group name already exists. Please try another one
            self.debugPrint(responsetemp)
            self.retries += 1
            if self.retries > 5:
                self.retries = 0
                raise TiktokApiResponseCodeException(responsetemp)
            print(
                "[Renaming adgroup] And try again. Tries: {}/5".format(
                    str(self.retries)
                )
            )
            return self.create_ad_group_conversions(
                advertiser_id=advertiser_id,
                campaign_id=campaign_id,
                adgroup_name=adgroup_name + " (" + str(self.retries) + ")",
                location=location,
                schedule_type=schedule_type,
                schedule_start_time=schedule_start_time,
                budget=budget,
                bid=bid,
                is_comment_disable=is_comment_disable,
                video_download=video_download,
                creative_material_mode=creative_material_mode,
                Age=Age,
                pixel_id=pixel_id,
                external_action_raw=external_action_raw,
                custom_audience=custom_audience,
                bid_strategy_raw=bid_strategy_raw,
                accelerated_spend=accelerated_spend,
                dayparting_string=dayparting_string,
                language_string=language_string,
                objective = objective,
            )

        elif responsetemp["code"] != 0:
            self.debugPrint(responsetemp)
            raise TiktokApiResponseCodeException(responsetemp)
        return response

    def create_ad_group(
        self,
        advertiser_id,
        campaign_id,
        adgroup_name,
        location,
        schedule_type,
        schedule_start_time,
        budget,
        bid,
        is_comment_disable,
        video_download,
        creative_material_mode,
        Age,
        custom_audience,
        bid_strategy_raw,
        accelerated_spend,
        dayparting_string,
        language_string,
    ):
        """
        Creates adgroup
        :Param: campaign_id, adgroup_name, location, schedule_type, schedule_start_time, budget, bid, is_comment_disable, video_download, creative_material_mode, Age. All are retrieved from database
        :return: json that contains adgroup id
        """
        self.debugPrint(
            "[create ad_group] Attempting to create traffic adgroup inside campaign_id: {}".format(
                str(campaign_id)
            )
        )
        placement_type = "PLACEMENT_TYPE_NORMAL"
        external_type = "WEBSITE"
        budget_mode = "BUDGET_MODE_DAY"
        optimize_goal = "CLICK"
        # pacing = "PACING_MODE_FAST"
        billing_event = "CPC"
        placement = "PLACEMENT_TIKTOK"
        try:
            bid_strategy = BidStrategyMap[bid_strategy_raw]
        except Exception:
            raise ValueError(
                f"The given bid strategy{bid_strategy_raw}is incorrect, it should be Bid or Lowestcost"
            )
        if accelerated_spend:
            pacing = "PACING_MODE_FAST"
        else:
            pacing = "PACING_MODE_SMOOTH"
        language_list = None
        if language_string is not None and len(language_string) != 0:
            language_list = language_string[0][0].split(",")
        response = []
        args_dict = {
            "advertiser_id": advertiser_id,
            "placement_type": placement_type,
            "external_type": external_type,
            "budget_mode": budget_mode,
            "optimize_goal": optimize_goal,
            "billing_event": billing_event,
            "placement": [placement],
            "campaign_id": campaign_id,
            "adgroup_name": adgroup_name,
            "location": location,
            "schedule_type": schedule_type,
            "schedule_start_time": str(schedule_start_time),
            "bid_type": bid_strategy,
            "budget": str(budget),
            "is_comment_disable": is_comment_disable,
            "video_download": video_download,
            "age": Age,
            "pacing": pacing,
        }

        if custom_audience:
            args_dict["excluded_audience"] = custom_audience

        if bid_strategy_raw == "Bid":
            args_dict["bid"] = str(bid)

        if dayparting_string is not None:
            args_dict["dayparting"] = dayparting_string

        if language_list is not None:
            args_dict["languages"] = language_list

        my_args = json.dumps(args_dict)
        responsetemp = self.post(url=url_hp.TIKTOK_CREATE_ADGROUP_URL, params=my_args)
        response.append(responsetemp)
        if (
            responsetemp["code"] == 40002
            and "already exists" in responsetemp["message"]
        ):  # Potential: Ad group name already exists. Please try another one
            self.debugPrint(responsetemp)
            self.retries += 1
            if (
                responsetemp["code"] == 40002
                and "already exists" in responsetemp["message"]
            ):  # Potential: Ad group name already exists. Please try another one
                self.debugPrint(responsetemp)
                self.retries += 1
                if self.retries > 5:
                    self.retries = 0
                    raise TiktokApiResponseCodeException(responsetemp)
                print(
                    "[Renaming adgroup] And try again. Tries: {}/5".format(
                        str(self.retries)
                    )
                )
                return self.create_ad_group(
                    advertiser_id=advertiser_id,
                    campaign_id=campaign_id,
                    adgroup_name=adgroup_name + " (" + str(self.retries) + ")",
                    location=location,
                    schedule_type=schedule_type,
                    schedule_start_time=schedule_start_time,
                    budget=budget,
                    bid=bid,
                    is_comment_disable=is_comment_disable,
                    video_download=video_download,
                    creative_material_mode=creative_material_mode,
                    Age=Age,
                    custom_audience=custom_audience,
                    bid_strategy_raw=bid_strategy_raw,
                    accelerated_spend=accelerated_spend,
                    dayparting_string=dayparting_string,
                    language_string=language_string,
                )
        elif responsetemp["code"] != 0:
            self.debugPrint(responsetemp)
            raise TiktokApiResponseCodeException(responsetemp)
        return response

    def create_app_install_campaign(
        self,
        advertiser_id,
        campaign_id,
        adgroup_name,
        location,
        schedule_type,
        schedule_start_time,
        budget,
        bid,
        creative_material_mode,
        custom_audience,
        identity_type,
        identity_id,
        operation_system,
        bid_strategy_raw,
        accelerated_spend,
        dayparting_string,
        language_string,
    ):
        """
        Creates adgroup
        :Param: campaign_id, adgroup_name, location, schedule_type, schedule_start_time, budget, bid, is_comment_disable, video_download, creative_material_mode, Age. All are retrieved from database
        :return: json that contains adgroup id
        """
        self.debugPrint(
            "[create ad_group] Attempting to create traffic adgroup inside campaign_id: {}".format(
                str(campaign_id)
            )
        )
        placement_type = "PLACEMENT_TYPE_NORMAL"
        external_type = "APP_IOS"
        budget_mode = "BUDGET_MODE_DAY"
        optimize_goal = "INSTALL"
        billing_event = "OCPM"
        ios_target_device = "IOS14_PLUS"
        ios_osv = "14.0"
        placement = "PLACEMENT_TIKTOK"
        if accelerated_spend:
            pacing = "PACING_MODE_FAST"
        else:
            pacing = "PACING_MODE_SMOOTH"

        try:
            bid_strategy = BidStrategyMap[bid_strategy_raw]
        except:
            raise ValueError(
                f"The given bid strategy{bid_strategy_raw}is incorrect, it should be Bid or Lowestcost"
            )
        language_list = None
        if language_string is not None and len(language_string) != 0:
            language_list = language_string[0][0].split(",")
        response = []
        my_args = {
            "advertiser_id": advertiser_id,
            "placement_type": placement_type,
            "external_type": external_type,
            "budget_mode": budget_mode,
            "optimize_goal": optimize_goal,
            "billing_event": billing_event,
            "placement": [placement],
            "campaign_id": campaign_id,
            "adgroup_name": adgroup_name,
            "location": location,
            "schedule_type": schedule_type,
            "schedule_start_time": str(schedule_start_time),
            "ios_target_device": ios_target_device,
            "ios_osv": ios_osv,
            "identity_type": identity_type,
            "identity_id": identity_id,
            "budget": str(budget),
            "pacing": pacing,
            "conversion_bid": str(bid),
            "operation_system": operation_system,
        }
        if custom_audience != []:
            my_args["excluded_audience"] = json.dumps(custom_audience)
        if bid_strategy_raw == "Bid":
            my_args["bid"] == bid
        if dayparting_string is not None:
            my_args["dayparting"] == dayparting_string
        if language_list is not None:
            my_args["languages"] == language_list
        responsetemp = self.post(url=url_hp.TIKTOK_CREATE_ADGROUP_URL, params=my_args)
        response.append(responsetemp)

        if (
            responsetemp["code"] == 40002
            and "already exists" in responsetemp["message"]
        ):  # Potential: Ad group name already exists. Please try another one
            self.debugPrint(responsetemp)
            self.retries += 1
            if self.retries > 5:
                self.retries = 0
                raise TiktokApiResponseCodeException(responsetemp)
            print(
                "[Renaming adgroup] And try again. Tries: {}/5".format(
                    str(self.retries)
                )
            )
            return self.create_app_install_campaign(
                advertiser_id=advertiser_id,
                campaign_id=campaign_id,
                adgroup_name=adgroup_name + " (" + str(self.retries) + ")",
                location=location,
                schedule_type=schedule_type,
                schedule_start_time=schedule_start_time,
                budget=budget,
                bid=bid,
                creative_material_mode=creative_material_mode,
                custom_audience=custom_audience,
                identity_type=identity_type,
                identity_id=identity_id,
                operation_system=operation_system,
                bid_strategy_raw=bid_strategy_raw,
                accelerated_spend=accelerated_spend,
                dayparting_string=dayparting_string,
                language_string=language_string,
            )
        elif (
            responsetemp["code"] == 40111
        ):  # The maximum number of successful calls has been exceeded
            self.handleError(
                "quota reached",
                f"quota reached for app id {self.app_id}",
                "High",
                self.app_id,
            )
            self.debugPrint(f"quota reached for app id {self.app_id}")
        elif responsetemp["code"] != 0 and responsetemp["code"] != 40111:
            self.debugPrint(responsetemp)
            raise TiktokApiResponseCodeException(responsetemp)
        return response

    def create_spark_ad(
        self,
        ad_name,
        ad_text,
        landing_page_url,
        adgroup_id,
        tiktok_item_id,
        ad_format,
        advertiser_id,
    ):
        """
        Creates an ad. requires creatives: Video and thumbnail
        :param: ad_name, ad_text, landing_page_url, adgroup_id, tiktok_item_id, ad_format. All are retrieved from database.
        :return: Server response in json_str format
        """
        call_to_action = "LISTEN_NOW"
        response = []
        my_dict = {
            "advertiser_id": advertiser_id,
            "creatives": [
                {
                    "tiktok_item_id": tiktok_item_id,
                    "call_to_action": call_to_action,
                    "ad_format": ad_format,
                    "ad_name": ad_name,
                    "landing_page_url": landing_page_url,
                    "ad_text": ad_text,
                }
            ],
            "adgroup_id": adgroup_id,
            "dark_post_status": "ON",
        }

        my_args = json.dumps(my_dict)
        responsetemp = self.post(url=url_hp.TIKTOK_AD_URL, params=my_args)
        response.append(responsetemp)
        if responsetemp["code"] != 0:
            raise TiktokApiResponseCodeException(responsetemp)
        return response

    def create_image_ad(
        self, ad_name, ad_text, landing_page_url, adgroup_id, image_ids
    ):
        """
        Unused function, old.
        """
        return (
            []
        )  # This function has not been tested and is unfinished. This is a template for future application
        ad_format = "SINGLE_IMAGE"
        call_to_action = "LISTEN_NOW"
        results = self.get_advertiserIds()
        response = []
        for x in results:
            advertiser_id = x.account_id  # Fetched from database
            my_args = (
                '{"advertiser_id": "%s", "adgroup_id": "%s", "creatives": [{"call_to_action": "%s", "ad_text": "%s", "image_ids": %s, "landing_page_url": "%s", "ad_name": "%s", "ad_format": "%s"}]}'
                % (
                    advertiser_id,
                    adgroup_id,
                    call_to_action,
                    ad_text,
                    image_ids,
                    landing_page_url,
                    ad_name,
                    ad_format,
                )
            )
            responseTemp = self.post("/open_api/v1.2/ad/create/", my_args)

            # if responseTemp["code"] != 0:
            #     self.debugPrint(responseTemp)
            #     raise TiktokApiResponseCodeException(responseTemp)
            if responseTemp.get("code") == 0:
                response.append(responseTemp)
        return response

    def get_thumbnail_url_from_frame(self, advertiser_id, video_id):

        my_dict = {
            "advertiser_id": advertiser_id,
            "video_id": video_id,
        }

        my_args = json.dumps(my_dict)
        response = []
        response = self.get(url=url_hp.TIKTOK_THUMBNAIL_URL, params=my_args)
        url = ""
        if response.get("code") != 0:
            self.debugPrint(response)
            self.debugPrint(
                "Could not create thumbnail for video. Fallback to hardcoded black thumbnail"
            )
            return self.hardcoded_thumbnail
        else:
            url = response.get("data").get("list")[0].get("url")
            AdCreativeIds.objects.filter(
                creative_id=video_id, ad_platform=PlatFormType.TIKTOK
            ).update(thumbnail_url=url)
            response = self.upload_creative_image(
                image_url=url,
                file_name="thumbnail" + self.generateRandomString(length=10),
                advertiser_id=advertiser_id,
            )
            if response[0]["code"] != 0:
                self.debugPrint(response)
                raise TiktokApiResponseCodeException(response)
            else:
                return response[0]["data"]["image_id"]

    def create_video_ad(
        self,
        ad_name,
        ad_text,
        landing_page_url,
        adgroup_id,
        image_ids,
        video_id,
        display_name,
        identity_id,
        advertiser_id,
        identity_type,
        music_sharing,
        stitch_duet,
    ):  # video id str, image id [str]
        """
        Creates a video ad with data from database and api.
        :param: ad_name, ad_text, landing_page_url, adgroup_id,image_ids, video_id, display_name, identity_id. All are retrieved from database.
        :return: Server response in json_str format
        """
        self.debugPrint("[Scheduler/CreateAd/Video] Start")
        call_to_action = "LISTEN_NOW"
        response = []
        thumbnail = []
        ad_format = "SINGLE_VIDEO"
        music_sharing = False if music_sharing else True
        stitch_duet = "ENABLE" if stitch_duet else "DISABLE"
        try:
            thumbnail.append(self.get_thumbnail_url_from_frame(advertiser_id, video_id))
            thumbnail = json.dumps(thumbnail)
        except Exception as e:
            self.debugPrint("Could not get thumbnail" + str(e))
            self.handleError(
                "[Scheduler/create_video_ad] Could not fetch thumbnail from api.",
                str(e) + "adname: " + ad_name,
                "High",
            )
        if thumbnail != []:
            image_ids = thumbnail
        my_args = {
            "advertiser_id": advertiser_id,
            "adgroup_id": adgroup_id,
            "creatives": [
                {
                    "call_to_action": call_to_action,
                    "ad_text": ad_text,
                    "video_id": video_id,
                    "image_ids": image_ids,
                    "landing_page_url": landing_page_url,
                    "ad_name": ad_name,
                    "ad_format": ad_format,
                    "display_name": display_name,
                    "identity_id": identity_id,
                    "identity_type": identity_type,
                    "dark_post_status": "ON",
                }
            ],
        }
        if not music_sharing:
            my_args["creatives"][0].update(
                {
                    "promotional_music_disabled": str(music_sharing).lower(),
                    "item_duet_status": stitch_duet,
                    "item_stitch_status": stitch_duet,
                }
            )
        my_args = json.dumps(my_args)
        responsetemp = self.post(url=url_hp.TIKTOK_AD_URL, params=my_args)
        response.append(responsetemp)
        if responsetemp["code"] == 0:
            self.retries = 0
        elif responsetemp["code"] != 0:
            self.debugPrint(responsetemp)
            if responsetemp["code"] >= 50000:  # INTERNAL ERROR, Try again later
                self.retries += 1
                if self.retries > 5:
                    self.retries = 0
                    raise TiktokInternalServerException(responsetemp)
                self.debugPrint(
                    "[Internal Retry] Got an internal error. Will try again in 20 sec, max 5 times"
                )
                time.sleep(20)
                return self.create_video_ad(
                    ad_name,
                    ad_text,
                    landing_page_url,
                    adgroup_id,
                    image_ids,
                    video_id,
                    display_name,
                    identity_id,
                    advertiser_id,
                    identity_type,
                    music_sharing,
                    stitch_duet,
                )
            elif responsetemp["code"] == 40002:
                if responsetemp["message"] == "Enter a valid identity ID":
                    errormsg = (
                        "[Failed to create videos Tiktok] Identity ID "
                        + str(identity_id)
                        + " not known user with access token: "
                        + str(self.access_token)
                        + ". How to fix: Go to Tiktok Business Manager > Tiktok Accounts > Link Tiktok account"
                    )
                    self.debugPrint(errormsg)
                    raise TiktokApiResponseCodeException(errormsg)
                if (
                    responsetemp["message"]
                    == "creatives.0.image_ids.0: Not a valid string."
                ):
                    self.retries += 1
                    if self.retries > 30:
                        self.retries = 0
                        raise TiktokInternalServerException(responsetemp)
                    time.sleep(60)
                    return self.create_video_ad(
                        ad_name,
                        ad_text,
                        landing_page_url,
                        adgroup_id,
                        image_ids,
                        video_id,
                        display_name,
                        identity_id,
                        advertiser_id,
                        identity_type,
                        music_sharing,
                        stitch_duet,
                    )
            raise TiktokApiResponseCodeException(responsetemp)
        return response

    def apply_authorisation_code(self, authkey):
        """
        Authorizes a spark ad so it can be created
        :param: authkey. All are retrieved from database.
        :return: Server response in json_str format
        """
        self.debugPrint("[authorisation] Authorizating sparkad")
        results = self.get_advertiserIds()
        responsetemp = []
        for data in results:
            advertiser_id = data.account_id
            my_args = json.dumps({"advertiser_id": advertiser_id, "auth_code": authkey})
            responsetemp.append(
                self.post(url=url_hp.TIKTOK_TT_VIDEO_URL, params=my_args)
            )
        return responsetemp

    def get_spark_ad_code(self, auth_code):
        """
        Gets spark ad auth_code.
        :Param int: auth_code used to retrieve spark ad code
        :return: Server response in json_str format
        """
        results = self.get_advertiserIds()

        response = []
        for obj in results:
            advertiser_id = obj.account_id  # Fetched from database
            my_dict = {"advertiser_id": advertiser_id, "auth_code": auth_code}
            my_args = json.dumps(my_dict)
            responsetemp = self.get(url=url_hp.TIKTOK_TT_VIDEO_INFO_URL, params=my_args)

            if responsetemp.get("code") == 0:
                self.retries = 0
                response.append(responsetemp)
            elif responsetemp.get("code") != 0:
                if responsetemp.get("code") >= 50000:  # INTERNAL ERROR, Try again later
                    self.retries += 1
                    if self.retries < 6:
                        # self.retries = 0
                        # raise TiktokInternalServerException(responseTemp)
                        self.debugPrint(
                            "[Internal Retry] Got an internal error. Will try again in 20 sec, max 5 times"
                        )
                        time.sleep(20)
                        return self.get_spark_ad_code(auth_code)
                    else:
                        self.retries = 0
                # raise TiktokApiResponseCodeException(responseTemp)
                self.debugPrint(responsetemp)
        return response

    def extract_report_data(self, basic_report):
        """
        Extracts 'spend' from basic report and calculates the sum of spend per adgroup_id
        :param json: Args in JSON format, only basicReport from tiktok API with data_level "AUCTION_ADGROUP"
        :return: list with adgroup id and total spend per id in a dict
        """
        index = 0
        response = []
        found = False
        if str(type(basic_report)) != "<class 'list'>":
            raise DataTypeStructureException(
                "basicReport type should be <class 'list'>, not : "
                + str(type(basic_report))
            )
        if str(type(basic_report[0])) != "<class 'dict'>":
            raise DataTypeStructureException(
                "basicReport[0] type should be <class 'dict'>, not : "
                + str(type(basic_report[0]))
            )
        if not (
            "message" in basic_report[0].keys()
            and "data" in basic_report[0].keys()
            and "code" in basic_report[0].keys()
            and "request_id" in basic_report[0].keys()
        ):
            raise DataTypeStructureException(
                "basicReport[0] keys should be dict_keys(['message', 'code', 'data', 'request_id']), not : "
                + str(basic_report[0].keys())
            )
        if str(type(basic_report[0]["data"])) != "<class 'dict'>":
            raise DataTypeStructureException(
                "basicReport[0]['data'] type should be <class 'dict'>, not : "
                + str(type(basic_report[0]["data"]))
            )
        if not (
            "page_info" in basic_report[0]["data"].keys()
            and "list" in basic_report[0]["data"].keys()
        ):
            raise DataTypeStructureException(
                "basicReport[0]['data'] keys should be dict_keys(['page_info', 'list']), not : "
                + str(basic_report[0]["data"].keys())
            )
        if str(type(basic_report[0]["data"]["list"])) != "<class 'list'>":
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'] type should be <class 'list'>, not : "
                + str(type(basic_report[0]["data"]["list"]))
            )
        if basic_report[0]["data"]["list"] == []:
            return []
        if str(type(basic_report[0]["data"]["list"][0])) != "<class 'dict'>":
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'][0] type should be <class 'dict'>, not : "
                + str(type(basic_report[0]["data"]["list"][0]))
            )
        if not (
            "metrics" in basic_report[0]["data"]["list"][0].keys()
            and "dimensions" in basic_report[0]["data"]["list"][0].keys()
        ):
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'][0] keys should be dict_keys(['metrics', 'dimensions']), not : "
                + str(basic_report[0]["data"]["list"][0].keys())
            )
        if (
            str(type(basic_report[0]["data"]["list"][0]["dimensions"]))
            != "<class 'dict'>"
        ):
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'][0]['dimensions'] type should be <class 'dict'>, not : "
                + str(type(basic_report[0]["data"]["list"][0]["dimensions"]))
            )
        if not (
            "stat_time_day" in basic_report[0]["data"]["list"][0]["dimensions"].keys()
            and "adgroup_id" in basic_report[0]["data"]["list"][0]["dimensions"].keys()
        ):
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'][0]['dimensions'] keys should be dict_keys(['stat_time_day', 'adgroup_id']), not : "
                + str(basic_report[0]["data"]["list"][0]["dimensions"].keys())
            )
        if str(type(basic_report[0]["data"]["list"][0]["metrics"])) != "<class 'dict'>":
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'][0]['metrics'] type should be <class 'dict'>, not : "
                + str(type(basic_report[0]["data"]["list"][0]["metrics"]))
            )
        if not (
            "cpc" in basic_report[0]["data"]["list"][0]["metrics"].keys()
            and "spend" in basic_report[0]["data"]["list"][0]["metrics"].keys()
        ):
            raise DataTypeStructureException(
                "basicReport[0]['data']['list'][0]['metrics'] keys should be dict_keys(['cpc', 'spend']), not : "
                + str(basic_report[0]["data"]["list"][0]["metrics"].keys())
            )
        for basicreport_index in range(len(basic_report)):
            for list_index in range(
                len(basic_report[basicreport_index]["data"]["list"])
            ):
                found = False
                for k in range(len(response)):
                    if (
                        basic_report[basicreport_index]["data"]["list"][list_index][
                            "dimensions"
                        ]["adgroup_id"]
                        == response[k]["adgroup_id"]
                    ):
                        if (
                            basic_report[basicreport_index]["data"]["list"][list_index][
                                "dimensions"
                            ]["stat_time_day"]
                            == response[k]["date"]
                        ):
                            found = True
                            index = k
                if not found:
                    response.append(
                        {
                            "adgroup_id": basic_report[basicreport_index]["data"][
                                "list"
                            ][list_index]["dimensions"]["adgroup_id"],
                            "spend": Decimal(
                                basic_report[basicreport_index]["data"]["list"][
                                    list_index
                                ]["metrics"]["spend"]
                            ),
                            "cpc": Decimal(
                                basic_report[basicreport_index]["data"]["list"][
                                    list_index
                                ]["metrics"]["cpc"]
                            ),
                            "date": basic_report[basicreport_index]["data"]["list"][
                                list_index
                            ]["dimensions"]["stat_time_day"],
                        }
                    )
                else:
                    response[index]["spend"] += Decimal(
                        basic_report[basicreport_index]["data"]["list"][list_index][
                            "metrics"
                        ]["spend"]
                    )
        if len(response) > 0:
            return response
        return []

    def get_report_day(
        self, start_date, end_date, ad_account_id=None, toggle_action=None
    ):
        """
        requests a Basic report from the tiktok API
        :Param int, json_str: report_time_range defines from how far back data should be retrieved (max 30). param_args will be passed to tiktok api
        :Return: Json that contains Basic report
        :function call args: my_args = ", \"start_date\": \"%s\", \"end_date\": \"%s\"}" % (start_date, end_date)
        """
        results = self.get_advertiserIds(toggle_action=toggle_action)
        report_type = "BASIC"
        data_level = "AUCTION_ADGROUP"
        dimensions_list = ["adgroup_id", "stat_time_day"]
        dimensions = dimensions_list
        metrics_list = ["spend", "cpc"]
        metrics = metrics_list
        stat_time_day = str(datetime.datetime.now())
        response = []
        page_size = 1000
        for obj in results.filter(
            **({"account_id": ad_account_id} if ad_account_id is not None else {})
        ):
            self.debugPrint(
                "[get_report_day] getting report for advertiser_id: "
                + (str(obj.account_id))
            )
            page = 1
            pages_read = 0
            pages_total = 1
            while pages_read < pages_total:
                advertiser_id = obj.account_id
                my_dict = {
                    "advertiser_id": advertiser_id,
                    "report_type": report_type,
                    "dimensions": dimensions,
                    "metrics": metrics,
                    "stat_time_day": stat_time_day,
                    "page_size": page_size,
                    "page": page,
                    "data_level": data_level,
                    "start_date": start_date,
                    "end_date": end_date,
                }
                my_args = json.dumps(my_dict)
                responsetemp = self.get(
                    url=url_hp.TIKTOK_INTEGRATED_URL, params=my_args
                )
                if responsetemp.get("code") == 0:
                    self.retries = 0
                    if pages_read == 0:
                        pages_total = responsetemp["data"]["page_info"]["total_page"]
                    response.append(responsetemp)
                    pages_read += 1
                    page += 1

                elif responsetemp.get("code") != 0:
                    if (
                        responsetemp.get("code") >= 50000
                    ):  # INTERNAL ERROR, Try again later
                        self.retries += 1
                        if self.retries < 6:
                            # raise TiktokInternalServerException(responsetemp)
                            self.debugPrint(
                                "[Internal Retry] Got an internal error. Will try again in 20 sec, max 5 times"
                            )
                            time.sleep(20)
                            continue  # skips this loop and tries loop again, because we haven't increased any pages yet
                        else:
                            self.retries = 0
                    # raise TiktokApiResponseCodeException(responsetemp)

        try:
            return self.extract_report_data(response)
        except DataTypeStructureException as e:
            self.handleError("[get_report_day] TypeError", e.message, "High")
            self.debugPrint(e.message)
            return []

    def updateDailySpendData(
        self, ad_account_id=None, toggle_action=None, pastdays=None, uid=None
    ):
        delta = 28 if pastdays == "last_28d" else 6
        start_date = str(dt.now().date() - timedelta(days=delta))
        end_date = str(dt.now().date())

        basic_report = self.get_report_day(
            start_date,
            end_date,
            ad_account_id=ad_account_id,
            toggle_action=toggle_action,
        )
        date_dict = {}
        issues_cpc = 0
        for report in basic_report:
            date = report.get("date")
            adset = AdAdsets.objects.filter(
                adset_id=report["adgroup_id"], ad_platform=PlatFormType.TIKTOK
            )
            if adset:
                results = AdCampaigns.objects.filter(
                    campaign_id=adset[0].campaign_id
                ).values("campaign_id", "scraper_group_id", "advertiserid")
            else:
                results = None
            if results is None:
                continue
            if len(results) != 0:
                try:
                    self.update_cpc(report, results[0].get("campaign_id"))
                except Exception:
                    issues_cpc += 1
                campaign_id = results[0].get("campaign_id")
                if campaign_id is None:
                    campaign_id = None
                if (campaign_id, date) in date_dict:
                    date_dict[(campaign_id, date)]["spend"] += Decimal(report["spend"])
                else:
                    date_dict[(campaign_id, date)] = {}
                    date_dict[(campaign_id, date)]["spend"] = Decimal(report["spend"])
                    date_dict[(campaign_id, date)]["ad_account"] = results[0].get(
                        "advertiserid"
                    )

        if issues_cpc != 0:
            self.handleError(
                "[Adspend]",
                f"For Tiktok :\nThere were {issues_cpc} issues with retrieving CPC data.",
            )
        daily_adspend_genre_bulk_create_objects = []
        daily_adspend_genre_bulk_update_objects = []


        for entry, value in date_dict.items():
            campaign_id = entry[0]
            date = str(parser.parse(entry[1]).date())
            account_id = value.get("ad_account")
            adaccount = AdAccount.objects.get(account_id=account_id)
            DailyAdspendGenre.objects.filter(
                account_id=account_id
            ).exists() and DailyAdspendGenre.objects.filter(
                account_id=account_id
            ).update(
                ad_account_id=adaccount.id
            )
            daily_adspend_genre = DailyAdspendGenre.objects.filter(
                platform=PlatFormType.TIKTOK,
                campaign_id=campaign_id,
                ad_account__account_id=account_id,
                date=date,
            ).values("id")

            current_date = dt.now().date()
            if not daily_adspend_genre:
                daily_adspend_genre_bulk_create_objects.append(
                    DailyAdspendGenre(
                        platform=PlatFormType.TIKTOK,
                        spend=Decimal(str(value.get("spend"))),
                        campaign_id=campaign_id,
                        ad_account=adaccount,
                        account_id=account_id,
                        date=date,
                        company_uid=uid,
                        ad_account_currency=adaccount.currency,
                    )
                )
            elif date != current_date or date == current_date:
                daily_adsspend_genre = DailyAdspendGenre.objects.get(
                    id=daily_adspend_genre[0].get("id")
                )
                daily_adsspend_genre.spend = Decimal(str(value.get("spend")))
                daily_adsspend_genre.date_updated = dt.now()
                daily_adsspend_genre.updated_at = dt.now()
                daily_adspend_genre_bulk_update_objects.append(daily_adsspend_genre)

        DailyAdspendGenre.objects.bulk_create(daily_adspend_genre_bulk_create_objects)
        DailyAdspendGenre.objects.bulk_update(
            daily_adspend_genre_bulk_update_objects,
            ["spend", "date_updated", "updated_at"],
        )

    def update_cpc(self, insight, campaign_id):
        adset_id = insight.get("adgroup_id")
        date = insight.get("date").split()[0]
        cpc = insight.get("cpc", None)
        spend = insight.get("spend", None)
        adset_insights = AdsetInsights.objects.filter(
            platform=PlatFormType.TIKTOK,
            campaign_id=campaign_id,
            adset_id=adset_id,
            date=date,
        ).values("id", "cpc", "spend")

        adset_insights_bulk_create_objects = []
        adset_insights_bulk_update_objects = []
        if not adset_insights:
            adset_insights_bulk_create_objects.append(
                AdsetInsights(
                    platform=PlatFormType.TIKTOK,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    cpc=cpc,
                    spend=spend,
                    date=date,
                )
            )
        # If value in DB does not match API value, update it to API value
        else:
            cpc_changed = (cpc is None and cpc != adset_insights[0].get("cpc")) or (
                cpc is not None
                and Decimal(cpc) != Decimal(adset_insights[0].get("cpc"))
            )
            spend_changed = (
                spend is None and spend != adset_insights[0].get("spend")
            ) or (
                spend is not None
                and Decimal(spend) != Decimal(adset_insights[0].get("spend"))
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

    def update_ad_dark_post_status(self, advertiser_id, payload):
        """
        Specific function that enables DARK_POST_STATUS to ON
        :param advertiser_id: id of advertiser
        :param payload:
        :return:

        minimal payload requirements:
        {
            "advertiser_id": 6854124174642774022,
            "adgroup_id": "1727474759449649",
            "creatives": [{
                "identity_type": "TT_USER",
                "landing_page_url": "https://fruits.lnk.to/2022lofisleepw11-016",
                "identity_id": "743afd35-9de0-418b-9dd6-650119af5a3c",
                "dark_post_status": "ON",
                "ad_id": 1727474800018450,
                "ad_name": "Ad - 2394",
                "ad_text": "Listen Now! Lofi beats to sleep/relax/chill to playlist on Spotify, Apple Music, etc",
                "ad_format": "SINGLE_VIDEO",
                "video_id": "v10033g50000c92p1mjc77ufsgbot88g",
                "image_ids": ["ad-site-i18n-sg/202201275d0dfd2bfd0472084437ab7a"],
                "call_to_action": "LISTEN_NOW"
            }]
        }
        """
        try:
            response = self.post(url=url_hp.TIKTOK_AD_UPDATE_URL, params=payload)
        except Exception:
            return False
        if response.get("code") == 40002 and "valid identity" in response["message"]:
            return True
        elif response.get("code") != 0:
            print(response)
        else:
            return True

    def remove_ad_campaign(self, campaign_ids):
        """
        FUNCTION ONLY MADE FOR TESTING
        """
        return ["This function is currently disabled!"]
        results = self.get_advertiserIds()
        opt_status = "DELETE"
        response = []
        for obj in results:
            advertiser_id = obj.account_id
            my_args = json.dumps(
                {
                    "advertiser_id": advertiser_id,
                    "opt_status": opt_status,
                    "campaign_ids": campaign_ids,
                }
            )
            responseTemp = self.post("/open_api/v1.2/campaign/update/status/", my_args)
            response.append(responseTemp)
            if responseTemp.get("code") != 0:
                raise TiktokApiResponseCodeException(responseTemp)
        return response

    def remove_ad_group(self, adgroup_ids):
        """
        FUNCTION ONLY MADE FOR TESTING
        """
        return ["This function is currently disabled!"]
        results = self.get_advertiserIds()
        opt_status = "DELETE"
        response = []
        for obj in results:
            advertiser_id = obj.account_id
            my_args = {
                "advertiser_id": advertiser_id,
                "opt_status": opt_status,
                "adgroup_ids": [adgroup_ids],
            }
            responseTemp = self.post("/open_api/v1.2/adgroup/update/status/", my_args)
            response.append(responseTemp)
            if responseTemp.get("code") != 0:
                raise TiktokApiResponseCodeException(responseTemp)
        return response

    def remove_ad(self, ad_ids):
        """
        FUNCTION ONLY MADE FOR TESTING
        """
        return ["This function is currently disabled!"]
        results = self.get_advertiserIds()
        response = []
        opt_status = "DELETE"
        for obj in results:
            advertiser_id = obj.account_id
            my_args = json.dumps(
                {
                    "advertiser_id": advertiser_id,
                    "opt_status": opt_status,
                    "ad_ids": ad_ids,
                }
            )
            responseTemp = self.post("/open_api/v1.2/ad/update/status/", my_args)
            response.append(responseTemp)
            if responseTemp.get("code") != 0:
                raise TiktokApiResponseCodeException(responseTemp)
        return response

    def deactive_group(self, adgroup_ids, advertiser_id):
        """ """
        temp = []
        # page_size = 100
        try:
            advertiser_id = int(advertiser_id)
            for adgroup_ids_index in range(len(adgroup_ids)):
                temp.append(adgroup_ids[adgroup_ids_index][0])
            adgroup_ids = temp
            response = []
            fields = json.dumps(["adgroup_id"])
            my_dict = {
                "advertiser_id": advertiser_id,
                "fields": fields,
                "filtering": {
                    "adgroup_ids": adgroup_ids,
                },
            }

            my_args = json.dumps(my_dict)
            response = self.get(url=url_hp.TIKTOK_ADGROUP_UPDATE_URL, params=my_args)
            if response.get("code") != 0:
                response["advertiser_id"] = str(advertiser_id)
                raise TiktokApiResponseCodeException(response)
            if response["data"]["page_info"]["total_number"] != len(adgroup_ids):
                return response
        except TiktokApiResponseCodeException:
            pass
        except Exception:
            pass
            # raise Exception(
            #     "Could not correctly convert "
            #     + str(type(advertiser_id))
            #     + "to INT for advertiser_id : "
            #     + str(advertiser_id)
            # )
        return []

    def deactive_campaign(self, campaign_ids, advertiser_id):
        """ """
        temp = []
        page_size = 100
        try:
            advertiser_id = int(advertiser_id)
            for campaign_ids_index in range(len(campaign_ids)):
                temp.append(campaign_ids[campaign_ids_index][0])
            campaign_ids = temp
            response = []
            fields = json.dumps(["campaign_id"])
            my_dict = {
                "advertiser_id": advertiser_id,
                "page_size": page_size,
                "fields": fields,
                "filtering": {
                    "campaign_ids": campaign_ids,
                },
            }

            my_args = json.dumps(my_dict)
            response = self.get(url=url_hp.TIKTOK_GET_CAMPAIGN_URL, params=my_args)
            if response.get("code") != 0:
                response["advertiser_id"] = str(advertiser_id)
                raise TiktokApiResponseCodeException(response)
            if response.get("data").get("page_info").get("total_number") != len(
                campaign_ids
            ):
                return response
        except TiktokApiResponseCodeException:
            pass
        except Exception:
            pass
            # raise Exception(
            #     "Could not correctly convert "
            #     + str(type(advertiser_id))
            #     + "to INT for advertiser_id : "
            #     + str(advertiser_id)
            # )

        return []

    def deactivate_unused(self):
        """
        This function gets active ad_groups and checks if they still exist in the tiktok api. no -> set unactive, yes -> do nothing
        """

        self.debugPrint("[Deactivate unused] Start")
        # active_campaigns = self.db.execSQL(
        #     """SELECT `campaign_id`, `advertiserID` FROM `ad_campaigns` WHERE `active` = 'yes' AND `ad_platform` = 'Tiktok'""",
        #     (),
        #     False,
        # )
        active_campaigns = AdCampaigns.objects.filter(
            active="yes", ad_platform=PlatFormType.TIKTOK
        ).values_list("campaign_id", "advertiserid")
        unique_advertiser_ids = []
        batches = []
        found = False
        changed = 0
        self.debugPrint("[Deactivate/campaign] Start")
        for i in range(len(active_campaigns)):
            unique_advertiser_ids.append(active_campaigns[i][1])
        unique_advertiser_ids = list(set(unique_advertiser_ids))
        for i in range(
            len(active_campaigns)
        ):  # create batches of max length 100 (api wont accept more) and one collumn per advertiser_id
            found = False
            for j in range(len(batches)):
                if batches[j][0][1] == active_campaigns[i][1] and len(batches[j]) < 100:
                    batches[j].append((active_campaigns[i][0], active_campaigns[i][1]))
                    found = True
            if not found:
                batches.append([(active_campaigns[i][0], active_campaigns[i][1])])
        for i in range(len(batches)):  # for each collumn, check if they exist in api
            try:
                response = self.deactive_campaign(
                    batches[i], batches[i][0][1]
                )  # if all exist, return [], continue, response contains id's of all existing id's, deavtivate all id's not in that list.
            except Exception as e:
                self.debugPrint("could not get campaigns from api")
                self.handleError(
                    "[deavtivate/campaigns] could not get campaigns from api", str(e)
                )
                continue
            if response == []:
                continue
            found_ids = []
            for j in range(len(response["data"]["list"])):
                found_ids.append(response["data"]["list"][j]["campaign_id"])
            for j in range(len(batches[i])):
                if batches[i][j][0] not in found_ids:
                    changed += 1
                    # variables = ("No", batches[i][j][0])
                    # self.db.insertSQL(
                    #     """UPDATE `ad_campaigns` SET `active` = %s WHERE campaign_id = %s;""",
                    #     variables,
                    # )
                    AdCampaigns.objects.filter(campaign_id=batches[i][j][0]).update(
                        active="No", updated_at=dt.now()
                    )
        self.debugPrint("updated: " + str(changed) + " campaigns")
        batches = []
        changed = 0
        lock_index = 0

        self.debugPrint("[Deactivate/group] Start")
        for i in range(
            len(unique_advertiser_ids)
        ):  # same as with ad_campaigns, except for that ad_set table does not contain advertiserID, so advertiserID must be fetched with campaign id.
            active_groups = self.get_active_ads(id=unique_advertiser_ids[i])
            lock_index = len(batches)
            for j in range(len(active_groups)):
                found = False
                for k in range(lock_index, len(batches)):
                    if len(batches[k]) < 100:
                        batches[k].append(active_groups[j])
                        found = True
                if not found:
                    batches.append([active_groups[j]])
        for i in range(len(batches)):
            # advert_id = self.db.execSQL(
            #     """SELECT `advertiserID` FROM `ad_campaigns` WHERE `campaign_id` = %s;""",
            #     (batches[i][0][1],),
            #     False,
            # )[0][0]
            advert_id = AdCampaigns.objects.get(
                campaign_id=batches[i][0][1]
            ).advertiserid
            try:
                response = self.deactive_group(batches[i], advert_id)
            except Exception as e:
                self.debugPrint("could not get groups from api")
                self.handleError(
                    "[deavtivate/groups] could not get groups from api", str(e)
                )
                continue
            if response == []:
                continue
            found_ids = []
            for j in range(len(response["data"]["list"])):
                found_ids.append(response["data"]["list"][j]["adgroup_id"])
            for j in range(len(batches[i])):
                if batches[i][j][0] not in found_ids:
                    changed += 1
                    # variables = ("No", batches[i][j][0])
                    # self.db.insertSQL(
                    #     """UPDATE `ad_adsets` SET `active` = %s WHERE adset_id = %s;""",
                    #     variables,
                    # )
                    AdAdsets.objects.filter(adset_id=batches[i][j][0]).update(
                        active="No", updated_at=dt.now()
                    )

        self.debugPrint("updated: " + str(changed) + " adgroups")
        self.debugPrint("[Deactivate] Done")

    def get_count_campaign(self, campaign_id):
        return AdCampaigns.objects.filter(
            campaign_id=campaign_id, ad_platform=PlatFormType.TIKTOK
        ).count()

    def initializer_campaigns(
        self, ad_account_id=None, toggle_action=None, is_run_initializer=False
    ):
        genre = None
        ad_platform = PlatFormType.TIKTOK
        updated, inserted, total_campaigns_found, locationerrors = 0, 0, 0, 0
        allcampaigns = []
        try:
            allcampaigns = self.get_campaign(
                ad_account_id=ad_account_id,
                toggle_action=toggle_action,
                is_run_initializer=is_run_initializer,
            )
        except Exception as e:
            self.debugPrint(str(e))
            # raise APIGetterException(e)
        if len(allcampaigns) == 0:
            return None

        for index in range(len(allcampaigns)):  # set campaign data
            for count in range(len(allcampaigns[index]["data"]["list"])):
                total_campaigns_found += 1
            self.debugPrint(
                "[Campaigns] Found {} campaigns...".format(str(total_campaigns_found))
            )
        for campaigns_index in range(len(allcampaigns)):  # set campaign data
            for list_index in range(len(allcampaigns[campaigns_index]["data"]["list"])):
                campaign_name = allcampaigns[campaigns_index]["data"]["list"][
                    list_index
                ]["campaign_name"]
                campaign_id = str(
                    allcampaigns[campaigns_index]["data"]["list"][list_index][
                        "campaign_id"
                    ]
                )
                advertiser_id = str(
                    allcampaigns[campaigns_index]["data"]["list"][list_index][
                        "advertiser_id"
                    ]
                )
                opt_status = allcampaigns[campaigns_index]["data"]["list"][list_index][
                    "opt_status"
                ]
                try:
                    objective_type = TiktokObjectiveMap[
                        allcampaigns[campaigns_index]["data"]["list"][list_index][
                            "objective_type"
                        ]
                    ]
                except Exception:
                    objective_type = allcampaigns[campaigns_index]["data"]["list"][
                        list_index
                    ]["objective_type"]
                    self.handleError(
                        "[initialize/campaigns]",
                        " objective type : "
                        + str(objective_type)
                        + " has no valid mapping. This should be adjusted in the code",
                        "high",
                        campaign_id,
                    )
                try:
                    check_variables = [
                        ("ad_platform", ad_platform),
                        ("campaign_id", campaign_id),
                        ("campaign_name", campaign_name),
                        ("genre", genre),
                        ("opt_status", opt_status),
                    ]
                    locationerrors += self.check_input(
                        content=check_variables
                    )  # always returns 0 because no locations are checked (this is how it should work)
                    opt_status = "Yes" if opt_status == "ENABLE" else "No"
                    AdCampaigns.objects.update_or_create(
                        ad_platform=PlatFormType.TIKTOK,
                        campaign_id=campaign_id,
                        defaults={
                            "advertiserid": advertiser_id,
                            "campaign_name": campaign_name,
                            "scraper_group": None,
                            "active": opt_status,
                            "objective": objective_type,
                        },
                    )
                except DatabaseInvalidDataException:
                    # self.handleError("[initializer/get_campaign] Invalid data given to database.",str(e) + " campaign_id: " + str(campaign_id), "Low")
                    continue
                except Exception:
                    pass
        self.debugPrint(
            "[Campaigns Done] {} campaigns updated, {} campaigns inserted".format(
                str(updated), str(inserted)
            )
        )

    def initializer_delete_campaigns(self):
        delete, total_campaigns_found = 0, 0
        try:
            allcampaigns = self.get_campaign(primary_status=True)
        except Exception as e:
            self.debugPrint(str(e))
            raise APIGetterException(e)
        if len(allcampaigns) == 0:
            self.debugPrint("[Campaigns Done] {} campaigns delete".format(str(delete)))
            return None
        for campaign in range(len(allcampaigns)):  # set campaign data
            for count in range(len(allcampaigns[campaign]["data"]["list"])):
                total_campaigns_found += 1
            self.debugPrint(
                "[Campaigns] Found to delete {} campaigns...".format(
                    str(total_campaigns_found)
                )
            )
        for campaign_index in range(len(allcampaigns)):  # set campaign data
            for list_index in range(len(allcampaigns[campaign_index]["data"]["list"])):
                campaign_id = str(
                    allcampaigns[campaign_index]["data"]["list"][list_index][
                        "campaign_id"
                    ]
                )
                try:
                    if self.get_count_campaign(campaign_id):
                        AdCampaigns.objects.filter(campaign_id=campaign_id).delete()
                        delete += 1
                except Exception as e:
                    raise Exception(str(e))
        self.debugPrint(
            "[Delete Campaigns Done] {} campaigns Deleted".format(str(delete))
        )

    def get_count_groups(self, adgroup_id):
        return AdAdsets.objects.filter(
            adset_id=adgroup_id, ad_platform=PlatFormType.TIKTOK
        ).count()

    def initializer_groups(
        self, ad_account_id=None, toggle_action=None, is_run_initializer=False
    ):
        updated, inserted, locationerrors, total_adgroups_found, counter = 0, 0, 0, 0, 0
        adGroups = self.get_adgroups(
            ad_account_id=ad_account_id,
            toggle_action=toggle_action,
            is_run_initializer=is_run_initializer,
        )
        if len(adGroups) == 0:
            self.debugPrint(
                "[Adgroups Done] {} adgroups updated, {} adgroups inserted".format(
                    str(updated), str(inserted)
                )
            )
            return None
        for index in range(len(adGroups)):
            for count in range(len(adGroups[index]["data"]["list"])):
                total_adgroups_found += 1
        self.debugPrint(
            "[Adgroups] Found {} adgroups...".format(str(total_adgroups_found))
        )
        for index in range(len(adGroups)):
            for list_index in range(len(adGroups[index]["data"]["list"])):
                counter += 1
                if counter % 500 == 0:  # Progress
                    self.debugPrint(
                        "[Adgroups Progress] Adgroup {}/{}".format(
                            str(counter), str(total_adgroups_found)
                        )
                    )
                budget = adGroups[index]["data"]["list"][list_index]["budget"]
                bid = adGroups[index]["data"]["list"][list_index]["bid"]
                adgroup_id = str(
                    adGroups[index]["data"]["list"][list_index]["adgroup_id"]
                )
                adgroup_name = adGroups[index]["data"]["list"][list_index][
                    "adgroup_name"
                ]
                location = adGroups[index]["data"]["list"][list_index]["location"]
                campaign_id = str(
                    adGroups[index]["data"]["list"][list_index]["campaign_id"]
                )
                opt_status = adGroups[index]["data"]["list"][list_index]["opt_status"]
                check_variables = [
                    ("campaign_id", campaign_id),
                    ("adgroup_id", adgroup_id),
                    ("adgroup_name", adgroup_name),
                    ("location", location),
                    ("opt_status", opt_status),
                    ("bid", bid),
                    ("budget", budget),
                ]
                try:
                    if self.check_input(content=check_variables) == 1:
                        locationerrors += 1
                        continue
                except DatabaseInvalidDataException as e:
                    self.handleError(
                        "[initializer/get_adgroups] Invalid data given to database.",
                        str(e) + " adgroup_id: " + str(adgroup_id),
                        "High",
                    )
                    continue
                except Exception as e:
                    raise Exception(str(e))
                try:
                    location_list = []
                    for id in location:
                        code = self.countryIDToCode(countryId=id)
                        if code:
                            location_list.append(code)
                    location = ",".join(location_list)
                except Exception as e:
                    self.handleError(
                        "[initializer/get_adgroups] Invalid country code.",
                        str(e)
                        + "location code:"
                        + str(location[0])
                        + " adgroup_id: "
                        + str(adgroup_id),
                        "High",
                    )
                    continue
                opt_status = "Yes" if opt_status == "ENABLE" else "No"
                last_checked = datetime.datetime.now() - timedelta(days=1)
                try:
                    AdAdsets.objects.update_or_create(
                        adset_id=adgroup_id,
                        campaign_id=campaign_id,
                        ad_platform=PlatFormType.TIKTOK,
                        defaults={
                            "adset_name": adgroup_name,
                            "target_country": location,
                            "bid": bid,
                            "budget": budget,
                            "active": opt_status,
                            "last_checked": last_checked,
                        },
                    )
                except DatabaseRequestException as e:
                    self.handleError(
                        "[initializer/get_adgroups] Could not create entry or update value",
                        e.message,
                        "High",
                    )
                except Exception:
                    pass
                    # raise Exception(str(e))

    def get_landing_page(self, adgroup_id):
        response = AdAdsets.objects.filter(adset_id=adgroup_id).values_list(
            "landingpage"
        )
        return response

    def initializer_ads(self, is_run_initializer=False):
        counter = 0
        total_ads_found = 0
        allAds = self.get_ads(is_run_initializer=is_run_initializer)

        for index in range(len(allAds)):
            for count in range(len(allAds[index]["data"]["list"])):
                total_ads_found += 1
        if total_ads_found == 0:
            return None
        updated_landingpage = 0
        for add_index in range(len(allAds)):
            for list_index in range(len(allAds[add_index]["data"]["list"])):
                counter += 1
                adgroup_id = str(
                    allAds[add_index]["data"]["list"][list_index]["adgroup_id"]
                )
                landing_page_url = allAds[add_index]["data"]["list"][list_index][
                    "landing_page_url"
                ]
                # variables = (landing_page_url, adgroup_id)
                check_variables = [
                    ("landing_page_url", landing_page_url),
                    ("adgroup_id", adgroup_id),
                ]
                try:
                    self.check_input(content=check_variables)
                    response = self.get_landing_page(adgroup_id)
                    if len(response) == 0:
                        continue
                    if response:
                        if (
                            response[0][0] != landing_page_url
                        ):  # only update if url is different

                            AdAdsets.objects.filter(adset_id=adgroup_id).update(
                                landingpage=landing_page_url, updated_at=dt.now()
                            )
                            updated_landingpage += 1
                except DatabaseInvalidDataException:
                    # self.handleError("[initializer/get_ads] Invalid data given to database.", str(e) + " adgroup_id: " + str(adgroup_id), "High")
                    continue

                except DatabaseRequestException as e:
                    self.handleError(
                        "[initializer/get_ads] Error inserting landing_page_url in Database",
                        str(e)
                        + " adgroup_id: "
                        + str(adgroup_id)
                        + " adgroup ID: "
                        + str(adgroup_id),
                        "High",
                    )
                except Exception:
                    pass
                    # raise Exception(str(e))

    def initializer(self):
        """
        initialises database by getting data on all ads, groups and campaings from the api. Then it pushes all data to database. Prevents duplicats.
        :Param: none
        :return: none
        """
        self.initializing_bussiness_adaccounts()
        try:
            self.initializer_campaigns()
        except Exception as e:
            self.handleError(
                "[initializer/get_campaign] Could not get (all) campaigns from tiktok Api.",
                str(e),
                "High",
            )

        try:
            self.initializer_groups()
        except Exception as e:
            self.handleError(
                "[initializer/get_adgroups] Could not get (all) adGroups from tiktok Api.",
                str(e),
                "High",
            )

        try:
            self.initializer_ads()
        except Exception as e:
            self.handleError(
                "[initializer/get_ads] Could not get (all) ads from tiktok Api.",
                str(e),
                "High",
            )
        try:
            self.initializer_pixels()
        except Exception as e:
            self.handleError(
                "[initializer/pixels] Could not get (all) pixel from tiktok Api.",
                str(e),
                "High",
            )
        try:
            self.initialize_audience_data()
        except Exception as e:
            self.handleError(
                "[initializer/audience] Could not get (all) audiences from tiktok Api.",
                str(e),
                "High",
            )
        try:
            self.deactivate_unused()
        except Exception as e:
            self.handleError(
                "[initializer/deactive] Could not deactivate groups/campaingns.",
                str(e),
                "High",
            )
        try:
            self.remove_unused_audiences_preprocess()
        except Exception as e:
            self.handleError(
                "[initializer/audiences/remove] Could not remove all required audiences.",
                str(e),
                "High",
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
        # advertiser_id = self.db.execSQL(
        #     """SELECT `advertiserID` FROM `ad_campaigns` WHERE `ad_platform` = %s AND `campaign_id` = %s""",
        #     ("Tiktok", campaign_id),
        #     False,
        # )[0][0]
        advertiser_id = AdCampaigns.objects.get(
            ad_plateform=PlatFormType.TIKTOK, campaign_id=campaign_id
        ).advertiserid
        response = []
        if bid is None and budget is None:
            self.debugPrint(
                "[updateAdGroup] No bid and budget found, deactivating adgroup."
            )
            return []

        data = {
            "advertiser_id": advertiser_id,
            "adgroup_id": adgroup_id,
        }
        if bid:
            data["bid"] = bid
        if budget:
            data["budget"] = budget

        my_args = json.dumps(data)
        responsetemp = self.post(url=url_hp.TIKTOK_ADGROUP_UPDATE_URL, params=my_args)
        if responsetemp["code"] == 0:
            self.retries = 0
            response.append(responsetemp)
        elif responsetemp.get("code") != 0:
            if responsetemp.get("code") >= 50000:  # INTERNAL ERROR, Try again later
                self.retries += 1
                if self.retries < 6:
                    # self.retries = 0
                    # raise TiktokInternalServerException(responsetemp)
                    self.debugPrint(
                        "[Internal Retry] Got an internal error. Will try again in 20 sec, max 5 times"
                    )
                    time.sleep(20)
                    return self.updateAdGroup(bid, budget, adgroup_id, campaign_id)
                else:
                    self.retries = 0
            # Check if ad is deleted, then delete from database
            if (
                responsetemp.get("code") == 40002
                and responsetemp.get("message") == "Ad deleted"
            ):
                self.debugPrint(
                    "[Fix: Ad deleted] Trying to update ad that is deleted in UI. Delete from database."
                )
                try:
                    AdAdsets.objects.filter(adset_id=adgroup_id).delete()
                except Exception:
                    self.debugPrint(
                        "Could not delete entry with adgroup_id : {}".format(
                            str(adgroup_id)
                        )
                    )
                    pass
            # raise TiktokApiResponseCodeException(responseTemp)

        return response

    def create_legal_age_format(self, age):
        response = []
        for age in age.split(","):
            if age == "55+":
                response.append("AGE_55_100")
                continue
            low = int(age.split("-")[0])
            high = int(age.split("-")[1])
            validAge = False
            increments = [13, 18, 25, 35, 45, 55, 101]
            increments_string = [
                "AGE_13_17",
                "AGE_18_24",
                "AGE_25_34",
                "AGE_35_44",
                "AGE_45_54",
                "AGE_55_100",
            ]
            if low >= high:
                return []
            if low not in increments:
                return []
            if high + 1 not in increments:
                return []
            for index in range(len(increments_string)):
                if increments[index] == low:
                    validAge = True
                if increments[index] - 1 == high:
                    break
                if validAge:
                    response.append(increments_string[index])
            # if response == []:
            #     raise IllegalAgeFormatException(
            #         "Could not create legal age range from ", +str(age) + "."
            #     )
        return response

    def url_to_tag(self, url):
        tag = ""
        if str(type(url)) != "<class 'str'>" or len(url) == 0:
            return tag
        url_split = url.split("/")
        tag = url_split[-1]
        return tag

    def genre_to_tag(self, genre):
        tag = ""
        if str(type(genre)) != "<class 'str'>" or len(genre) == 0:
            return tag
        if "Fruits" in genre:
            genrestring = genre.replace("Fruits", "")
        else:
            genrestring = genre
        return genrestring

    def get_campaign_data(self, ad_scheduler_instance_id):
        response = (
            AdScheduler.objects.filter(id=ad_scheduler_instance_id)
            .values_list(
                "id",
                "campaign_id",
                "countries",
                "age_range",
                "budget",
                "landingpage_url",
                "caption",
                "scheduled_for",
                "type_post",
                "scraper_group_id",
                "extra_name",
                "objective",
                "pixel_id",
                "event_type",
                "bid",
                "custom_audiences",
                "authkey_email_user",
                "tiktok_identity_type",
                "tiktok_identity_id",
                "bid_strategy",
                "strategy",
                "max_budget",
                "app_platform",
                "adaccount_id",
                "dayparting",
                "language",
                "campaign_name",
            )
            .exclude(landingpage_url=None)
        )
        return response

    def get_budget(self):
        try:
            budget = Settings.objects.filter(variable="test_ad_budget").values_list(
                "value"
            )
            return budget[0][0]
        except Exception as e:
            self.handleError(
                "Error in Settings table",
                "budget has not been set in the Settings table. Original error: "
                + str(e),
            )

    def update_completed_to_error(self, id_scheduler, adgroup_id, advertiser_id):
        AdScheduler.objects.filter(id=id_scheduler).update(
            completed="Error", updated_at=dt.now()
        )
        self.delete_adgroup_id(adgroup_id=adgroup_id, advertiser_id=advertiser_id)

    def scheduler_preprocessor(self, ad_scheduler_data_all, id_batches):
        """
        Prepares data for scheduling
        Returns:
        ad_scheduler_data_all -> Contains all scheduler data. This data will be spread over batches.
        id_batches -> contains all scheduler data per advertiserID id_batches[0] contains all scheduler data of the 1st advertiserID, id_batches[1] the data of the 2nd, end so on. len(id_batches) === len(unique_advertiser_ids)
        """

        all_advertiser_ids = []
        ad_scheduler_data_all_list_copy = []
        for index in range(len(ad_scheduler_data_all)):
            # print(ad_scheduler_data_all[i])
            ad_scheduler_data_all_list_copy.append(
                list(ad_scheduler_data_all[index])
            )  # convert from tupple to list
            advertiser_id = AdScheduler.objects.filter(
                id=ad_scheduler_data_all[index][0]
            ).values("adaccount_id")
            _advertiser_id = advertiser_id[0].get("adaccount_id")
            if _advertiser_id is None or 0 or len(_advertiser_id) == 0:
                # continue
                raise IDMismatchException(
                    "Could not find advertiser_id for campaign: "
                    + str(ad_scheduler_data_all[index][1])
                )
            ad_scheduler_data_all_list_copy[index].append(
                advertiser_id[0].get("adaccount_id")
            )  # add advertiserID
            all_advertiser_ids.append(
                advertiser_id[0].get("adaccount_id")
            )  # keep track of advertiserID in seperate list
        all_advertiser_ids = list(
            set(all_advertiser_ids)
        )  # filter for unique advertiserIDs
        for count in range(len(all_advertiser_ids)):
            id_batches.append([])  # create list with length of unique advertiser ids
        for data_index in range(len(ad_scheduler_data_all_list_copy)):
            for id_index in range(len(all_advertiser_ids)):
                if str(ad_scheduler_data_all_list_copy[data_index][-1]) == str(
                    all_advertiser_ids[id_index]
                ):  # if advertiserID in all data is same as unique advertiser id in that batch, put it in that batch.
                    id_batches[id_index].append(
                        ad_scheduler_data_all_list_copy[data_index]
                    )
                    break  # advertiser id found, go to next
        return ad_scheduler_data_all_list_copy, id_batches

    def get_genre(self, campaign_id, id_scheduler):
        try:
            group_name = AdScheduler.objects.filter(id=id_scheduler).values_list(
                "scraper_group__group_name"
            )
            if not group_name:
                raise IDMismatchException(
                    "Could not find group for campaign: " + str(campaign_id)
                )  # if no group was found, ads can't be scheduled. continue to next ad_campaign
            return group_name[0][0]
        except Exception as e:
            self.handleError(
                "[scheduler/adgroup] Could not get group from database.",
                "Scheduler ID:" + str(id_scheduler) + " message: " + str(e),
                "High",
                id_scheduler,
            )
            raise IDMismatchException(
                "Could not find group for campaign: " + str(campaign_id)
            )

    def preprocess_creative(self, id_scheduler):
        data = AdCreativeIds.objects.filter(
            Q(scheduler_id=id_scheduler)
            & (
                (~Q(creative_id=None) & Q(uploaded_on=None))
                | (Q(creative_id=None) & ~Q(uploaded_on=None))
            )
        )
        if data:
            ids = [obj.id for obj in data]
            AdCreativeIds.objects.filter(id__in=ids).update(
                notes="ad_creative missing upload date or creative_id. Both need to be present or NULL to schedule. Skipping entry",
                updated_at=dt.now(),
            )
            for obj in data:
                self.debugPrint(
                    f"ad_creative missing upload date or creative_id. Both need to be present or NULL to schedule. Skipping entry. See notes at id = {obj.id}"
                )

    def get_autogenerate_campaign_data(self):
        return AdScheduler.objects.filter(
            platform=PlatFormType.TIKTOK,
            completed="No",
            campaign_id=None,
            landingpage_url=None,
        ).values_list(
            "campaign_id",
            "scraper_group_id",
            "campaign_name",
            "adaccount_id",
            "objective",
        )

    def scheduler(self, ad_scheduler_data_all):
        """
        Schedules ads with data from database. See inline comments
        """
        audience_list = []
        identity_available = True  # keep track of wether identity_id is available for creative ads, not needed for spark ads
        image_ids = json.dumps(self.hardcoded_thumbnail)  # Hardcoded thumbnail
        schedule_exception = (
            False  # if at some point true, change database value to 'error'
        )
        self.debugPrint("[scheduler] Requesting data from database...")
        id_batches = []
        bid = Decimal(str(0.1))

        # autogenerate campaign code start
        try:
            self.add_new_campaign(ad_scheduler_data_all=ad_scheduler_data_all)
        except Exception as e:
            self.debugPrint(str(e))
        # autogenerate campaign code stop
        ad_scheduler_data_all, id_batches = self.scheduler_preprocessor(
            ad_scheduler_data_all, id_batches
        )
        for n in range(len(id_batches)):
            self.debugPrint(
                "[scheduler] Start scheduling "
                + str(len(ad_scheduler_data_all))
                + " entrie(s)."
            )
            ad_scheduler_data = id_batches[
                n
            ]  # for the remainder of the loop we will work with ad_scheduler_data. This is all data for 1 advertiser_id
            if not ad_scheduler_data:
                self.debugPrint("[scheduler] No adgroups found to schedule.")
                continue
            for scheduler_index in range(
                len(ad_scheduler_data)
            ):  # indexing: n = advertiser, i = campaign, j = adgroup, k = ad
                response = []
                ad_data = []
                identity_id = []
                audience_list = []
                response = []
                extra_name = ""
                schedule_exception = False
                missing_all_creatives = True
                ad_skipped = False
                id_scheduler = ad_scheduler_data[scheduler_index][0]
                # campaign_id = ad_scheduler_data[scheduler_index][1]
                countries_all = ad_scheduler_data[scheduler_index][2]
                age_range = ad_scheduler_data[scheduler_index][3]
                budget = ad_scheduler_data[scheduler_index][4]
                landingpage_url = ad_scheduler_data[scheduler_index][5]
                caption = ad_scheduler_data[scheduler_index][6]
                scheduled_for = ad_scheduler_data[scheduler_index][7]
                # type_post = ad_scheduler_data[scheduler_index][8]  # todo, dit doet niks?
                group_id = ad_scheduler_data[scheduler_index][9]
                extra_name = ad_scheduler_data[scheduler_index][10]
                objective = ad_scheduler_data[scheduler_index][11]
                pixel_id = ad_scheduler_data[scheduler_index][12]
                event_type = ad_scheduler_data[scheduler_index][13]
                bid = ad_scheduler_data[scheduler_index][14]
                custom_audiences = ad_scheduler_data[scheduler_index][15]
                authkey_email_user = ad_scheduler_data[scheduler_index][16]
                tiktok_identity_type = ad_scheduler_data[scheduler_index][17]
                tiktok_identity_id = ad_scheduler_data[scheduler_index][18]
                bid_strategy = ad_scheduler_data[scheduler_index][19]
                strategy = ad_scheduler_data[scheduler_index][20]
                max_budget = ad_scheduler_data[scheduler_index][21]
                app_platform = (
                    ad_scheduler_data[scheduler_index][22]
                    if ad_scheduler_data[scheduler_index][22] is not None
                    else ""
                )  # if None then send empty string
                advertiser_id = ad_scheduler_data[scheduler_index][
                    23
                ]  # added after get. So always last element
                dayparting = ad_scheduler_data[scheduler_index][24]
                language = ad_scheduler_data[scheduler_index][25]
                music_sharing = ad_scheduler_data[scheduler_index][27]
                stitch_duet = ad_scheduler_data[scheduler_index][28]
                campaign_id = self.get_schedule_value(id_scheduler, "campaign_id")
                countries = countries_all.split(",")
                scheduled_for_time = scheduled_for
                identity_id = tiktok_identity_id
                # check for valid identity_id
                if identity_id is not None:
                    identity_available = True
                else:
                    identity_available = False
                # check for valid extra name
                if extra_name is not None:
                    extra_name = " - " + extra_name
                else:
                    extra_name = ""
                # check for valid extra name
                if bid is not None:
                    bid = Decimal(str(ad_scheduler_data[scheduler_index][14]))
                    maturity = "Test"
                    bid_db = bid
                else:
                    maturity = "New"
                    bid = Decimal("0.1")
                    bid_db = None
                if budget is None:
                    budget = Decimal(self.get_budget())
                else:
                    budget = Decimal(str(budget))
                # prepare custom audiences
                if custom_audiences is not None and custom_audiences != "":
                    audience_list = str(custom_audiences).split(",")
                    for k in range(len(audience_list)):
                        audience_list[k] = int(audience_list[k])
                # check if in past, then update to now
                if scheduled_for_time < datetime.datetime.now():
                    self.debugPrint(
                        "[Schedule time fixed] Was in the past, updated to now"
                    )
                    scheduled_for_time = datetime.datetime.now()
                self.preprocess_creative(
                    id_scheduler
                )  # this function makes sure that always creative_id and uploaded_on are either NULL or filled. And prevents the one from being NULL while the other is not NULL
                self.upload_creatives(id_scheduler, advertiser_id)
                try:
                    group_name = self.get_genre(campaign_id, id_scheduler)
                except IDMismatchException as e:  # error already handled in function
                    self.handleError(
                        "[scheduler/adgroup] Could not get group from database.",
                        "Scheduler ID:" + str(id_scheduler) + " message: " + str(e),
                        "High",
                        id_scheduler,
                    )
                    continue
                # Check whether all creatives were uploaded , if not, skip creating adgroup
                try:
                    count_non_uploaded = AdCreativeIds.objects.filter(
                        scheduler_id=id_scheduler, uploaded_on=None
                    ).count()
                except Exception:
                    self.debugPrint(
                        "[scheduler/adgroup] Could not get successfully created creatives from database."
                    )
                if count_non_uploaded > 0:
                    self.handleError(
                        "Tiktok Scheduler",
                        "There were "
                        + str(count_non_uploaded)
                        + " creatives not uploaded for scheduler id "
                        + str(id_scheduler),
                    )
                    continue
                # make sure correct key is selected. If key can't be selected succesfully, move on to next campaign
                try:
                    self.change_key(name=authkey_email_user)
                except Exception as e:
                    self.debugPrint(
                        "[Scheduler/access_token] Could not get new access token."
                    )
                    self.handleError(
                        "[scheduler/access_token] Could not get new access token. ",
                        "Scheduler ID: " + str(id_scheduler) + " message: " + str(e),
                        "High",
                        id_scheduler,
                    )
                    continue

                accelerated_spend = self.get_schedule_value(
                    id_scheduler, "accelerated_spend"
                )
                bundle_countries = self.get_schedule_value(
                    id_scheduler, "bundle_countries"
                )
                country_list = countries
                for j in range(len(country_list)):
                    dayparting_string = None
                    language_string = None
                    if (
                        bundle_countries
                    ):  # if bundle_countries is True then complete loop hear and take countries = ['DE','GB','US']
                        if j + 1 != len(country_list):
                            continue
                        countries = country_list
                        country_name = "Multiple Countries"
                        if dayparting:
                            try:
                                dayparting_string = Day_Parting.objects.filter(
                                    ad_scheduler_id=id_scheduler
                                ).values_list("dayparting_string")
                                if not dayparting_string:
                                    self.debugPrint(
                                        "[scheduler] No dayparting_string found for schedular_id"
                                        + str(id_scheduler)
                                    )
                            except Exception:
                                raise DatabaseRequestException(
                                    "Could not get data from database"
                                )
                        if language:
                            try:
                                language_string = Language.objects.filter(
                                    ad_scheduler_id=id_scheduler
                                ).values_list("language_string")
                                if not language_string:
                                    self.debugPrint(
                                        "[scheduler] No language_string found for schedular_id"
                                        + str(id_scheduler)
                                    )
                            except Exception:
                                raise DatabaseRequestException(
                                    "Could not get data from database"
                                )
                    else:
                        countries = country_list[
                            j
                        ]  # if bundle_countries is No then create adgroup for every country countries[j] = 'DE'
                        country_name = self.countryCodeToName(country_code=countries)
                        if dayparting:
                            try:
                                dayparting_string = Day_Parting.objects.filter(
                                    ad_scheduler_id=id_scheduler, country_code=countries
                                ).values_list("dayparting_string")
                                if len(dayparting_string) == 0:
                                    self.debugPrint(
                                        "[scheduler] No dayparting_string found for schedular_id"
                                        + str(id_scheduler)
                                    )
                            except Exception:
                                raise DatabaseRequestException(
                                    "Could not get data from database"
                                )
                        if language:
                            try:
                                language_string = Language.objects.filter(
                                    ad_scheduler_id=id_scheduler, country_code=countries
                                ).values_list("language_string")
                                if len(language_string) == 0:
                                    self.debugPrint(
                                        "[scheduler] No language_string found for schedular_id"
                                        + str(id_scheduler)
                                    )
                            except Exception:
                                raise DatabaseRequestException(
                                    "Could not get data from database"
                                )

                    self.debugPrint(
                        "[scheduler/ad_group] Entry "
                        + str(scheduler_index + 1)
                        + " / "
                        + str(len(ad_scheduler_data))
                        + ". Country "
                        + str(j + 1)
                        + "/"
                        + str(len(countries))
                    )
                    # Try to create an adgroup On fail skip adgroup and move to next adgroup. Set database variable to "error" to prevent further trys.
                    try:
                        # preparename
                        landingpage_url = self.get_creative_value(
                            id=id_scheduler, databasecolumn="landingpage_url"
                        )
                        name = (
                            str(id_scheduler)
                            + " - "
                            + self.genre_to_tag(group_name)
                            + " - Scheduler "
                            + str(datetime.datetime.now().strftime("%Y"))
                            + " Week "
                            + str(int(scheduled_for.strftime("%W")))
                            + " - "
                            + country_name
                            + ""
                            + extra_name
                            + " - "
                            + self.url_to_tag(landingpage_url)
                        )
                        adgroup_id = None
                        # create adgroup:
                        if objective == "Traffic" and pixel_id is None:  #
                            response = self.create_ad_group(
                                advertiser_id=advertiser_id,
                                campaign_id=campaign_id,
                                adgroup_name=name,
                                location=self.countryCodeToId(
                                    countryCode=countries,
                                    bundle_countries=bundle_countries,
                                ),
                                schedule_type="SCHEDULE_FROM_NOW",
                                schedule_start_time=scheduled_for_time,
                                budget=budget,
                                bid=bid,
                                is_comment_disable=0,
                                video_download="PREVENT_DOWNLOAD",
                                creative_material_mode="DYNAMIC",
                                Age=json.dumps(self.create_legal_age_format(age_range)),
                                custom_audience=audience_list,
                                bid_strategy_raw=bid_strategy,
                                accelerated_spend=accelerated_spend,
                                dayparting_string=dayparting_string,
                                language_string=language_string,
                            )

                        elif objective == "Conversions" or (
                            objective == "Traffic" and pixel_id is not None
                        ):  # todo, this is a specific condition. Could maybe just be else. unless there are plans for future objectives.
                            response = self.create_ad_group_conversions(
                                advertiser_id=advertiser_id,
                                campaign_id=campaign_id,
                                adgroup_name=name,
                                location=self.countryCodeToId(
                                    countryCode=countries,
                                    bundle_countries=bundle_countries,
                                ),
                                schedule_type="SCHEDULE_FROM_NOW",
                                schedule_start_time=scheduled_for_time,
                                budget=budget,
                                bid=bid,
                                is_comment_disable=0,
                                video_download="PREVENT_DOWNLOAD",
                                creative_material_mode="DYNAMIC",
                                Age=json.dumps(self.create_legal_age_format(age_range)),
                                pixel_id=pixel_id,
                                external_action_raw=event_type,
                                custom_audience=audience_list,
                                bid_strategy_raw=bid_strategy,
                                accelerated_spend=accelerated_spend,
                                dayparting_string=dayparting_string,
                                language_string=language_string,
                                objective = objective,
                            )
                        elif objective == "APP_INSTALLS" and pixel_id is None:  #
                            response = self.create_app_install_campaign(
                                advertiser_id=advertiser_id,
                                campaign_id=campaign_id,
                                adgroup_name=name,
                                location=self.countryCodeToId(countryCode=countries),
                                schedule_type="SCHEDULE_FROM_NOW",
                                schedule_start_time=scheduled_for_time,
                                budget=budget,
                                bid=bid,
                                creative_material_mode="DYNAMIC",
                                custom_audience=audience_list,
                                identity_type=tiktok_identity_type,
                                identity_id=tiktok_identity_id,
                                operation_system=[app_platform.upper()],
                                bid_strategy_raw=bid_strategy,
                                accelerated_spend=accelerated_spend,
                                dayparting_string=dayparting_string,
                                language_string=language_string,
                            )
                        else:
                            raise Exception(
                                "[Scheduler]"
                                + str(objective)
                                + " is not a valid objective."
                            )
                        adgroup_id = response[0]["data"]["adgroup_id"]
                    except Exception as e:
                        schedule_exception = True
                        self.handleError(
                            "[scheduler/ad_group] Adgroup could not be created",
                            "Scheduler ID: "
                            + str(id_scheduler)
                            + " message: "
                            + str(e)
                            + " response: "
                            + str(response),
                            "High",
                            id_scheduler,
                        )
                        self.debugPrint(
                            "[scheduler/ad_group] Adgroup could not be created Skipping country and logging error..."
                            + str(e)
                        )
                        self.update_completed_to_error(
                            id_scheduler, adgroup_id, advertiser_id
                        )
                        continue
                    try:
                        if bundle_countries:
                            countries = ",".join([str(i) for i in countries])
                        else:
                            countries = countries
                        ad_set_obj = AdAdsets.objects.create(
                            ad_platform=PlatFormType.TIKTOK,
                            campaign_id=campaign_id,
                            adset_id=adgroup_id,
                            adset_name=name,
                            target_country=countries,
                            active="Yes",
                            last_checked=scheduled_for,
                            bid=bid_db,
                            budget=budget,
                            maturity=maturity,
                            strategy=strategy,
                            max_budget=max_budget,
                            scheduler_id=id_scheduler,
                        )
                    except Exception:
                        schedule_exception = True
                        self.handleError(
                            "[scheduler/adgroup] Could not push adgroup_data to database.",
                            " Scheduler ID: " + str(id_scheduler),
                            "High",
                            id_scheduler,
                        )
                        self.debugPrint(
                            "[scheduler/ad_group] Could not push adgroup_data to database. "
                        )
                        self.update_completed_to_error(
                            id_scheduler, adgroup_id, advertiser_id
                        )
                        continue
                    # if above statement failed code underneath will not be executed. If succeeded, adgroup needs to be activated to schedule ads.
                    try:
                        response = self.activate_adgroup(
                            adgroup_id=adgroup_id, advertiser_id=advertiser_id
                        )
                    except Exception as e:
                        schedule_exception = True
                        self.handleError(
                            "[scheduler/ad_group] Adgroup could not be activated",
                            "Scheduler ID: "
                            + str(id_scheduler)
                            + " message: "
                            + str(e)
                            + " response: "
                            + str(response),
                            "High",
                            id_scheduler,
                        )
                        self.debugPrint(
                            "[scheduler/ad_group] could not active adgroup ID: "
                            + str(id_scheduler)
                            + ". Country: "
                            + countries
                            + " Skipping country and logging error..."
                            + str(e)
                        )
                        self.update_completed_to_error(
                            id_scheduler, adgroup_id, advertiser_id
                        )
                        continue

                    # if above code succeeded, proceed to next step, get all creative data for the ads and start scheduling.
                    try:
                        ad_data = AdCreativeIds.objects.filter(
                            scheduler_id=id_scheduler
                        ).values_list(
                            "id",
                            "creative_id",
                            "creative_type",
                            "notes",
                            "landingpage_url",
                            "caption",
                            "heading",
                        )
                    except Exception:
                        self.debugPrint(
                            "[scheduler/ad] Could not get ad_data from database."
                        )
                        self.handleError(
                            "[scheduler/ad] Could not get ad_data from database.",
                            " Scheduler ID: " + str(id_scheduler),
                            "High",
                            id_scheduler,
                        )
                        ad_data = []
                        schedule_exception = True
                    if len(ad_data) == 0 and self.debug_mode:
                        self.debugPrint("[scheduler/ad] No ads found to schedule")
                    for ad_data_index in range(len(ad_data)):
                        """
                        Before edditing this code read the following:
                        The logic presented in the code below migth seem convuluted, but follows the following rules:
                        -When an adgroup uploads all ads without error it should me marked as completed = Yes
                        -When an adgroup uploads no ads because all creatives are missing it should be marked as:
                            -completed = Error if any of the creatives for that set has a note, meaning that something went wrong during uploading of that creative
                            -completed = No if all creatives are missing and all Notes are NULL. This is because the creatives could still be added in a later cycle. The scheduler will then reupload
                        -When an adgroup schedules one or more ads, but not all ads, it should be markes as completed = Error
                        """
                        ad_data_id = ad_data[ad_data_index][0]
                        creative_id = ad_data[ad_data_index][1]
                        creative_type = ad_data[ad_data_index][2]
                        notes = ad_data[ad_data_index][3]
                        landingpage_url = ad_data[ad_data_index][4]
                        add_caption = ad_data[ad_data_index][5]
                        ad_heading = ad_data[ad_data_index][6]
                        if ad_data_index == 0:  # print on first loop
                            self.debugPrint(
                                "[scheduler/ad] scheduling "
                                + str(len(ad_data))
                                + " ads. '+'  = DB opperation, 'x'  = succes, '-' = fail:"
                            )
                        if (
                            creative_type != "Spark" and identity_available is False
                        ):  # if no identity was found, and video_ads are being scheduled, stop scheduling, go to next adgroup.
                            schedule_exception = True
                            self.handleError(
                                "[scheduler/ad] Could not schedule non-spark ad(s) because identity is missing for group_name "
                                + str(group_name),
                                "Scheduler ID: " + str(id_scheduler),
                                "High",
                                id_scheduler,
                            )
                            self.debugPrint(
                                "[scheduler/ad] Could not schedule non-spark ad(s) because identity is missing for group_name "
                                + (group_name)
                            )
                            break
                        try:
                            response = []
                            # spark ads don't need to retrieve creatives. creative ID is expected to be present, if not throw generic api_code_Exception
                            if creative_type == "Spark":
                                response = self.create_spark_ad(
                                    ad_name="ad - " + str(ad_data_id),
                                    ad_text=caption,
                                    landing_page_url=landingpage_url,
                                    adgroup_id=adgroup_id,
                                    tiktok_item_id=creative_id,
                                    ad_format="SINGLE_VIDEO",
                                    advertiser_id=advertiser_id,
                                )
                                missing_all_creatives = False
                            # video ads do need to retrieve creatives. Additional errorhandling is put in place.
                            elif creative_type == "Video":
                                if creative_id is None:  # missing a creative ID
                                    ad_skipped = True
                                    if (
                                        notes is not None
                                    ):  # if any note is not NULL that means a creative had an error. Setting missing_all_creatives to false will prevent a reupload
                                        missing_all_creatives = False
                                    if (
                                        missing_all_creatives is False
                                    ):  # if in one group one creative id is missing but all others are present, it will schedule half the group. It should always schedule all or nothing, so throw error
                                        self.debugPrint(
                                            "[scheduler/ad] Inconsistent amount of missing creatives."
                                        )
                                        schedule_exception = True
                                        self.handleError(
                                            "[scheduler/ad] Some creatives in this group were missing, but some were not. Creating error to prevent repetition of ad uploads.",
                                            "Scheduler ID: " + str(id_scheduler),
                                            "High",
                                            id_scheduler,
                                        )
                                    self.debugPrint(
                                        "[scheduler/ad] No creative ID was found. Skipping entry"
                                    )
                                    continue
                                else:
                                    # missing_all_creatives = False  # at least one ad is going to be scheduled, if any other creative is missing, do not mark for reupload.
                                    if ad_skipped:
                                        self.debugPrint(
                                            "[scheduler/ad] Inconsistent amount of missing creatives."
                                        )
                                        schedule_exception = True
                                        self.handleError(
                                            "[scheduler/ad] Some creatives in this group were missing, but some were not. Creating error to prevent repetition of ad uploads.",
                                            "Scheduler ID: " + str(id_scheduler),
                                            "High",
                                            id_scheduler,
                                        )
                                    self.create_video_ad(
                                        "Ad - " + str(ad_data_id),
                                        caption,
                                        landingpage_url,
                                        adgroup_id,
                                        image_ids,
                                        creative_id,
                                        "display_name",
                                        identity_id,
                                        advertiser_id,
                                        tiktok_identity_type,
                                        music_sharing,
                                        stitch_duet,
                                    )
                                    missing_all_creatives = False
                            # image ads or not implemented yet.
                            elif creative_type == "Image":
                                schedule_exception = True
                                self.handleError(
                                    "[Scheduler/Ad/Image] This function is not implemented",
                                    "",
                                )
                            else:
                                self.handleError(
                                    "[scheduler/ad] Got creative_type: "
                                    + creative_type
                                    + " which is invalid.",
                                    "Scheduler ID: " + str(id_scheduler),
                                    "High",
                                    id_scheduler,
                                )
                                self.debugPrint(
                                    "[scheduler/ad] Got creative_type: "
                                    + creative_type
                                    + " which is invalid."
                                )
                            self.debugPrint("x")
                            AdCreativeIds.objects.filter(
                                creative_id=creative_id
                            ).update(ad_adset=ad_set_obj, updated_at=dt.now())
                        except Exception as e:
                            schedule_exception = True
                            self.handleError(
                                "[scheduler/ad] Could not create ad.",
                                "Scheduler ID: "
                                + str(id_scheduler)
                                + " message: "
                                + str(e)
                                + " response: "
                                + str(response),
                                "High",
                                id_scheduler,
                            )
                            self.debugPrint("-")
                            self.debugPrint(str(e))
                # finalize with error handling in j loop
                if (
                    schedule_exception is False and missing_all_creatives is False
                ):  # if no ads were skipped and no errors occurd, mark down yes
                    AdScheduler.objects.filter(id=id_scheduler).update(
                        completed="Yes", updated_at=dt.now()
                    )
                    result = self.check_campaign_api_status(campaign_id=campaign_id)
                    if result == "New":
                        AdCampaigns.objects.filter(campaign_id=campaign_id).update(
                            api_status="Old", updated_at=dt.now()
                        )
                elif (
                    schedule_exception
                ):  # If *all* creatives were missing without causing an exception, leave value on 'No'
                    AdScheduler.objects.filter(id=id_scheduler).update(
                        completed="Error", updated_at=dt.now()
                    )
                    self.delete_adgroup_id(
                        adgroup_id=adgroup_id, advertiser_id=advertiser_id
                    )

                    result = self.check_campaign_api_status(campaign_id=campaign_id)
                    if result == "New":
                        self.debugPrint(
                            "[Scheduler] This is a new campaign {campaign_id} delete process start."
                        )
                        self.delete_campaign_id(
                            campaign_id=campaign_id, advertiser_id=advertiser_id
                        )
                        AdScheduler.objects.filter(id=id_scheduler).update(
                            campaign_id=None, updated_at=dt.now()
                        )
                    if schedule_exception:
                        self.debugPrint(
                            "[Scheduler] Encountered one or more errors during scheduling."
                        )
                    elif identity_available is False:
                        self.debugPrint(
                            "[Scheduler] Missing Tiktok identity for group_name "
                            + group_name
                        )  # todo, impossible statement?
                # If *all* creatives were missing without causing an exception, leave value on 'no'
        self.debugPrint("[Scheduler] Completed")

    def upload_creative_image(self, image_url, file_name, advertiser_id):
        """
        Creates an ad. requires creatives: Video and thumbnail
        :param json_str, int: param_args contains arguments that will be passed to api. authcode is required to get a video code (spark ad)
        :return: Server response in json_str format
        :function call args: my_args = ",\"ad_name\": \"%s\",\"landing_page_url\": \"%s\",\"ad_text\": \"%s\", \"display_name\": \"%s\"}],\"adgroup_id\": \"%s\"}" % (ad_name, landing_page_url, ad_text, display_name, adgroup_id)
        """
        upload_type = "UPLOAD_BY_URL"
        response = []
        my_args = json.dumps(
            {
                "advertiser_id": advertiser_id,
                "image_url": image_url,
                "upload_type": upload_type,
                "file_name": file_name,
            }
        )
        responsetemp = self.post(
            url=url_hp.TIKTOK_UPLOAD_CREATIVE_IMAGE_URL, params=my_args
        )
        if responsetemp["code"] != 0:
            raise TiktokApiResponseCodeException(responsetemp)
        response.append(responsetemp)
        return response

    def upload_creative_video(self, creative_id, video_url, file_name, advertiser_id):
        """
        Creates an ad. requires creatives: Video and thumbnail
        :param json_str, int: param_args contains arguments that will be passed to api. authcode is required to get a video code (spark ad)
        :return: Server response in json_str format
        :function call args: my_args = ",\"ad_name\": \"%s\",\"landing_page_url\": \"%s\",\"ad_text\": \"%s\", \"display_name\": \"%s\"}],\"adgroup_id\": \"%s\"}" % (ad_name, landing_page_url, ad_text, display_name, adgroup_id)
        """
        upload_type = "UPLOAD_BY_URL"
        response = []
        my_args = json.dumps(
            {
                "advertiser_id": advertiser_id,
                "video_url": video_url,
                "upload_type": upload_type,
                "file_name": file_name,
            }
        )
        self.my_args_note = my_args  # additional debugging
        responsetemp = self.post(
            url=url_hp.TIKTOK_UPLOAD_CREATIVE_VIDEO_URL, params=my_args
        )
        if responsetemp.get("code") != 0:
            # If ERROR = Duplicated material name. Edit name and try again
            if responsetemp.get("code") == 40911 or responsetemp["code"] == 51004:
                extrastring = self.generateRandomString(length=10)
                file_name = str(extrastring) + " " + file_name
                self.debugPrint(
                    "[Duplicate] Duplicate name found for video. Trying again with name: {}".format(
                        str(file_name)
                    )
                )
                AdCreativeIds.objects.filter(id=creative_id).update(
                    filename=file_name, updated_at=dt.now()
                )
                return self.upload_creative_video(
                    creative_id, video_url, file_name, advertiser_id
                )
            raise TiktokApiResponseCodeException(responsetemp)

        if responsetemp.get("code") == 0:
            response.append(responsetemp)
        return response

    def get_creative_data(self, id_adscheduler):
        return AdCreativeIds.objects.filter(
            creative_id=None,
            ad_platform=PlatFormType.TIKTOK,
            scheduler_id=id_adscheduler,
        ).values_list("id", "filename", "url", "creative_type", "notes")

    def upload_creatives(self, id_adscheduler, advertiser_id):
        creativedata = self.get_creative_data(id_adscheduler)
        response = []
        if not creativedata:
            return
        for index in range(len(creativedata)):
            response = []
            creative_id = creativedata[index][0]
            filename = creativedata[index][1]
            video_url = creativedata[index][2]
            creative_type = creativedata[index][3]
            try:
                if creative_type == "Video":
                    response.append(
                        self.upload_creative_video(
                            creative_id,
                            video_url,
                            filename,
                            advertiser_id,
                        )
                    )
                    try:
                        AdCreativeIds.objects.filter(id=creative_id).update(
                            creative_id=response[0][0]["data"][0]["video_id"],
                            uploaded_on=datetime.datetime.now(),
                            updated_at=dt.now(),
                        )
                    except Exception as e:
                        self.debugPrint(str(e))
                        self.handleError(
                            "UploadCreatives",
                            "Could not update database. " + str(e),
                            "High",
                            id_adscheduler,
                        )
                elif creative_type == "Image":
                    response.append(
                        self.upload_creative_image(
                            image_url=video_url,
                            file_name=filename,
                            advertiser_id=advertiser_id,
                        )
                    )
                    try:
                        AdCreativeIds.objects.filter(id=creative_id).update(
                            creative_id=response[0][0]["data"][0]["image_id"],
                            uploaded_on=datetime.datetime.now(),
                            updated_at=dt.now(),
                        )
                    except Exception as e:
                        self.debugPrint(str(e))
                        self.handleError(
                            "UploadCreatives",
                            "Could not update database. " + str(e),
                            "High",
                            id_adscheduler,
                        )
            except Exception as e:
                self.debugPrint(str(e))
                self.handleError(
                    "[Uploader] Could not upload creative. ",
                    str(e),
                    "High",
                    id_adscheduler,
                )
                self.handleNotes(
                    "[Uploader] Could not upload creative. ",
                    "Response/Exception: " + str(e),
                    creative_id,
                )

    def initializer_pixels(self, advertiser_id=None, is_run_initializer=False):
        self.debugPrint("[Initilazer/pixel] start")
        response = self.get_pixel_data(
            advertiser_id=advertiser_id, is_run_initializer=is_run_initializer
        )
        for index in range(len(response)):
            for pixel_index in range(len(response[index]["data"]["pixels"])):
                pixel_id = str(
                    response[index]["data"]["pixels"][pixel_index]["pixel_id"]
                )
                pixel_name = response[index]["data"]["pixels"][pixel_index][
                    "pixel_name"
                ]
                advertiser_id = str(response[index]["data"]["advertiser_id"])
                Pixels.objects.update_or_create(
                    advertiser_id=advertiser_id,
                    pixel_id=pixel_id,
                    platform=PlatFormType.TIKTOK,
                    defaults={"name": pixel_name},
                )
                for event_index in range(
                    len(response[index]["data"]["pixels"][pixel_index]["events"])
                ):
                    event_id = response[index]["data"]["pixels"][pixel_index]["events"][
                        event_index
                    ]["event_id"]
                    event_name = response[index]["data"]["pixels"][pixel_index][
                        "events"
                    ][event_index]["name"]
                    external_action = response[index]["data"]["pixels"][pixel_index][
                        "events"
                    ][event_index]["event_type"]
                    if (
                        response[index]["data"]["pixels"][pixel_index]["events"][
                            event_index
                        ]["name"]
                        != ""
                        and response[index]["data"]["pixels"][pixel_index]["events"][
                            event_index
                        ]["event_id"]
                        != 0
                    ):
                        CustomConversionEvents.objects.update_or_create(
                            platform=PlatFormType.TIKTOK,
                            account_id=advertiser_id,
                            event_id=event_id,
                            pixel_id=pixel_id,
                            description=None,
                            rules=None,
                            defaults={
                                "name": event_name,
                                "external_action": external_action,
                            },
                        )

    def get_pixel_data(self, advertiser_id=None, is_run_initializer=False):
        """
        requests a Basic report from the tiktok API
        :Param int, json_str: report_time_range defines from how far back data should be retrieved (max 30). param_args will be passed to tiktok api
        :Return: Json that contains Basic report
        :function call args: my_args = ", \"start_date\": \"%s\", \"end_date\": \"%s\"}" % (start_date, end_date)
        """
        results = self.get_advertiserIds(is_run_initializer=is_run_initializer)
        response = []
        # page_size = 10
        for obj in results.filter(
            **({"account_id": advertiser_id} if advertiser_id is not None else {})
        ):
            self.debugPrint(
                "[get_pixel] getting pixel for advertiser_id: " + (str(obj.account_id))
            )
            page = 1
            pages_read = 0
            pages_total = 1
            while pages_read < pages_total:
                advertiser_id = obj.account_id
                my_args = json.dumps({"advertiser_id": advertiser_id})
                responsetemp = self.get(url=url_hp.TIKTOK_GET_PIXEL_URL, params=my_args)
                # if responsetemp["code"] != 0:
                #     raise TiktokApiResponseCodeException(responsetemp)
                if responsetemp.get("code") == 0:
                    responsetemp["data"]["advertiser_id"] = obj.account_id
                    if pages_read == 0:
                        pages_total = (
                            responsetemp.get("data").get("page_info").get("total_page")
                        )
                    response.append(responsetemp)
                    pages_read += 1
                    page += 1
        return response

    def initialize_audience_data(self, account_id=None, is_run_initializer=False):
        self.debugPrint("[get_audience_data] Start")
        try:
            audience_data = self.get_audience_data(
                account_id=account_id, is_run_initializer=is_run_initializer
            )
            for index in range(len(audience_data)):
                if len(audience_data[index]["data"]["list"]) > 0:
                    advertiser_id = str(
                        audience_data[index]["data"]["list"][0]["advertiser_id"]
                    )
                for list_index in range(len(audience_data[index]["data"]["list"])):
                    audience_id = str(
                        audience_data[index]["data"]["list"][list_index]["audience_id"]
                    )
                    name = audience_data[index]["data"]["list"][list_index]["name"]
                    CustomAudiences.objects.update_or_create(
                        platform=PlatFormType.TIKTOK,
                        audience_id=audience_id,
                        defaults={"name": name, "account_id": advertiser_id},
                    )
        except Exception as e:
            self.debugPrint(str(e))

    def remove_unused_audiences_preprocess(self):
        audience_data = CustomAudiences.objects.filter(
            platform=PlatFormType.TIKTOK
        ).values_list("account_id", "audience_id")
        found = False
        batches = []
        unique_advertiser_ids = []
        changed = 0
        for index in range(len(audience_data)):
            unique_advertiser_ids.append(audience_data[index][0])
        unique_advertiser_ids = list(set(unique_advertiser_ids))
        for data_index in range(
            len(audience_data)
        ):  # create batches of max length 100 (api wont accept more) and one collumn per advertiser_id
            found = False
            for batch_index in range(len(batches)):
                if (
                    batches[batch_index][0][0] == audience_data[data_index][0]
                    and len(batches[batch_index]) < 100
                ):
                    batches[batch_index].append(audience_data[data_index])
                    found = True
            if not found:
                batches.append([audience_data[data_index]])
        for index in range(
            len(batches)
        ):  # for each collumn, check if they exist in api
            try:
                response = self.remove_unused_audiences(
                    audience_ids=batches[index], advertiser_id=batches[index][0][0]
                )  # if all exist, return [], continue, response contains id's of all existing id's, deavtivate all id's not in that list.
            except Exception as e:
                self.debugPrint("could not get campaigns from api")
                self.handleError(
                    "[deavtivate/campaigns] could not get campaigns from api", str(e)
                )
                continue
            if response == []:
                continue
            found_ids = []
            for list_index in range(len(response["data"]["list"])):
                found_ids.append(
                    response["data"]["list"][list_index]["audience_details"][
                        "audience_id"
                    ]
                )
            for batch_index in range(len(batches[index])):
                if int(batches[index][batch_index][1]) not in found_ids:
                    changed += 1
                    # variables = (batches[i][j][1],)
                    # self.db.execSQL(
                    #     """DELETE FROM `custom_audiences` WHERE `audience_id` = %s;""",
                    #     variables,
                    #     False,
                    # )
                    CustomAudiences.objects.filter(
                        audience_id=batches[index][batch_index][1]
                    ).delete()
        self.debugPrint("removed " + str(changed) + " entries.")

    def remove_unused_audiences(self, audience_ids, advertiser_id):
        response = []
        # page_size = 10
        self.debugPrint(
            "[deactivate/audience] getting audience for advertiser_id: "
            + str(advertiser_id)
        )
        temp = []
        for i in range(len(audience_ids)):
            temp.append(audience_ids[i][1])
        audience_ids = temp
        my_args = json.dumps(
            {"advertiser_id": advertiser_id, "custom_audience_ids": audience_ids}
        )
        response = self.get(url=url_hp.TIKTOK_CUSTOM_AUDIENCE_GET_URL, params=my_args)
        # if response["code"] != 0:
        #     raise TiktokApiResponseCodeException(response)
        if response.get("code") == 0:
            if len(response.get("data").get("list")) != len(audience_ids):
                return response
        return []

    def get_audience_data(self, account_id=None, is_run_initializer=False):
        """
        requests a Basic report from the tiktok API
        :Param int, json_str: report_time_range defines from how far back data should be retrieved (max 30). param_args will be passed to tiktok api
        :Return: Json that contains Basic report
        :function call args: my_args = ", \"start_date\": \"%s\", \"end_date\": \"%s\"}" % (start_date, end_date)
        """
        results = self.get_advertiserIds(is_run_initializer=is_run_initializer)
        response = []
        # page_size = 10
        for obj in results.filter(
            **({"account_id": account_id} if account_id is not None else {})
        ):
            page = 1
            pages_read = 0
            pages_total = 1
            while pages_read < pages_total:
                advertiser_id = obj.account_id
                my_args = json.dumps({"advertiser_id": advertiser_id})
                responseTemp = self.get(
                    url=url_hp.TIKTOK_CUSTOM_AUDIENCE_URL, params=my_args
                )
                # if responseTemp["code"] != 0:
                #     raise TiktokApiResponseCodeException(responseTemp)
                if responseTemp.get("code") == 0:
                    if len(responseTemp.get("data").get("list")) > 0:
                        responseTemp["data"]["list"][0][
                            "advertiser_id"
                        ] = obj.account_id
                    if pages_read == 0:
                        pages_total = (
                            responseTemp.get("data").get("page_info").get("total_page")
                        )
                    response.append(responseTemp)
                    pages_read += 1
                    page += 1
        return response

    def get_all_interests(self):  # FUNCTION FOR TESTING TODO
        results = self.get_advertiserIds()
        response = []
        version = 1
        # page_size = 10
        for obj in results:
            advertiser_id = obj.account_id
            my_args = json.dumps({"advertiser_id": advertiser_id, "version": version})
            responseTemp = self.get(
                url=url_hp.TIKTOK_INTEREST_CATEGORY_URL, params=my_args
            )
            # if responseTemp["code"] != 0:
            #     raise TiktokApiResponseCodeException(responseTemp)
            if responseTemp.get("code") == 0:
                response.append(responseTemp)
        return response

    def init_interests(self):  # FUNCTION FOR TESTING TODO
        response = self.get_all_interests()
        for index in range(len(response)):
            for data in range(len(response[index]["data"]["interest_categories"])):
                # print(response[i]['data']['interest_categories'][j]['level'])
                name = response[index]["data"]["interest_categories"][data]["name"]
                level = response[index]["data"]["interest_categories"][data]["level"]
                interest_id = response[index]["data"]["interest_categories"][data]["id"]
                # variables = (name, interest_id, level)
                # self.db.insertSQL(
                #     """INSERT INTO custom_interests (name, interest_id, level) VALUES (%s, %s, %s)""",
                #     variables,
                # )
                CustomAudiences.objects.create(
                    name=name, interest_id=interest_id, level=level
                )
        print("end")

    def get_interest_suggestion(self):  # FUNCTION FOR TESTING TODO
        results = self.get_advertiserIds()
        response = []
        region_code = json.dumps(["NL"])
        # page_size = 10
        for obj in results:
            advertiser_id = obj.account_id
            my_args = '{"advertiser_id": "%s", "region_code": %s}' % (
                advertiser_id,
                region_code,
            )
            responsetemp = self.post(
                url=url_hp.TIKTOK_TARGET_RECOMMEND_TAGS_URL, params=my_args
            )
            # if responsetemp["code"] != 0:
            #     raise TiktokApiResponseCodeException(responseTemp)
            if responsetemp.get("code") == 0:
                response.append(responsetemp)
        return response

    def get_interest_suggestion_by_keyword(self):  # FUNCTION FOR TESTING TODO
        results = self.get_advertiserIds()
        response = []
        key_words = json.dumps(["Jazz"])
        # page_size = 10
        for obj in results:
            advertiser_id = obj.account_id
            my_args = '{"advertiser_id": "%s", "keywords": %s}' % (
                advertiser_id,
                key_words,
            )
            responsetemp = self.get(
                url=url_hp.TIKTOK_INTEREST_KEYWORD_URL, params=my_args
            )
            # if responsetemp["code"] != 0:
            #     raise TiktokApiResponseCodeException(responsetemp)
            if responsetemp.get("code") == 0:
                response.append(responsetemp)
        return response

    def build_url(self, path, query=""):
        """
        Build request URL
        :param path: Request path
        :param query: Querystring
        :return: Request URL
        """
        if False:  # TODO REMOVE
            print("WARNING, CURRENTLY ON SANDBOX URL")
            scheme, netloc = "https", "sandbox-ads.tiktok.com"
        else:
            # print("Currently on business api")
            scheme, netloc = "https", "business-api.tiktok.com"

        return urlunparse((scheme, netloc, path, "", query, ""))

    def TikTok_Authorize(self):
        # Authorization url: https://ads.tiktok.com/marketing_api/auth?app_id=6979236567743201281&state=your_custom_params&redirect_uri=https%3A%2F%2Fads.strangefruits.net%2Ftiktok&rid=acacvjew94i
        return False

    # def TikTok_CampaignInfo(self, id):
    #     # [API] Sleep = 1706540187124754

    #     PATH = "/open_api/v1.2/campaign/get/"
    #     advertiser_id = ADVERTISER_ID
    #     campaign_ids_list = list(id)
    #     campaign_ids = json.dumps(campaign_ids_list)
    #     primary_status = "CAMPAIGN_STATUS_ENABLE"
    #     page = 1
    #     page_size = 1000

    #     # Args in JSON format
    #     my_args = (
    #         '{"advertiser_id": "%s", "filtering": {"status": "%s", "campaign_name": "%s", "objective_type": "%s", "campaign_ids": %s, "primary_status": "%s"}, "page": "%s", "page_size": "%s"}'
    #         % (
    #             advertiser_id,
    #             status,
    #             campaign_name,
    #             objective_type,
    #             campaign_ids,
    #             primary_status,
    #             page,
    #             page_size,
    #         )
    #     )
    #     print(get(my_args, PATH))

    def countryIDToCode(self, countryId):
        with open(
            os.path.join(BASE_DIR, "apps/tiktok/files/countries.json"), encoding="utf8"
        ) as json_file:
            data = json.load(json_file)
            json_file.close()
            for country in data["countries"]:
                if country["id"] == countryId:
                    return country["country_code"]
            for country in data["provinces"]:
                if country["id"] == countryId:
                    return country["country_code"]
            for country in data["cities"]:
                if country["id"] == countryId:
                    return country["country_code"]
            return None
            # raise Exception(
            #     "Country ID could not be matched to country code:", countryId
            # )

    # def countryCodeToId(self, countryCode):
    #     with open(
    #         os.path.join(BASE_DIR, "apps/tiktok/files/countries.json"), encoding="utf8"
    #     ) as json_file:
    #         data = json.load(json_file)
    #         json_file.close()
    #         for country in data["countries"]:
    #             if country["country_code"] == countryCode:
    #                 return country["id"]
    # raise Exception(
    #     "Country code could not be matched to country ID:", countryCode
    # )
    def countryCodeToId(self, countryCode, bundle_countries=False):
        with open(
            os.path.join(BASE_DIR, "apps/tiktok/files/countries.json"), encoding="utf8"
        ) as json_file:
            data = json.load(json_file)
            json_file.close()
            country_id = []
            if bundle_countries:
                for country in data["countries"]:
                    for x in countryCode:
                        if x == country["country_code"]:
                            country_id.append(country["id"])
                return country_id

            else:
                for country in data["countries"]:
                    if country["country_code"] == countryCode:
                        country_id.append(country["id"])
                        return country_id
                raise Exception(
                    "Country code could not be matched to country ID:", countryCode
                )

    def countryCodeToName(self, country_code):
        """
        Converts country code to full country name
        :param countryCode: country code
        :return: country name
        """
        with open(
            os.path.join(BASE_DIR, "apps/tiktok/files/countries.json"), encoding="utf8"
        ) as json_file:
            data = json.load(json_file)
            json_file.close()
            for country in data["countries"]:
                if country["country_code"] == country_code:
                    return country["name"]
            for country in data["provinces"]:
                if country["country_code"] == country_code:
                    return country["name"]
            for country in data["cities"]:
                if country["country_code"] == country_code:
                    return country["name"]

            raise Exception(
                "Country Code could not be matched to country name:", country_code
            )

    def generateRandomString(self, length):
        """
        Returns random string of length `length`
        Used to avoid duplicate upload names
        """
        random_string = ""

        for _ in range(length):
            # Considering only upper and lowercase letters
            random_integer = random.randint(97, 97 + 26 - 1)
            flip_bit = random.randint(0, 1)
            # Convert to lowercase if the flip bit is on
            random_integer = random_integer - 32 if flip_bit == 1 else random_integer
            # Keep appending random characters using chr(x)
            random_string += chr(random_integer)
        return random_string

    def delete_adgroup_id(self, adgroup_id, advertiser_id):
        try:
            if adgroup_id:
                opt_status = "DELETE"
                my_args = json.dumps(
                    {
                        "advertiser_id": advertiser_id,
                        "adgroup_ids": [adgroup_id],
                        "opt_status": opt_status,
                    }
                )

                responsetemp = self.post(url=url_hp.TIKTOK_ADGROUP_URL, params=my_args)
                if responsetemp["code"] != 0:
                    raise TiktokApiResponseCodeException(responsetemp)

        except TiktokApiResponseCodeException as e:
            self.handleError(
                "[Scheduler] adgroup could not be deleted.",
                "We could not delete adgroup with ID: "
                + str(adgroup_id)
                + ". If it still exists, please delete it manually. The original error:\n"
                + str(e),
            )
        AdAdsets.objects.filter(adset_id=adgroup_id).delete()

    def delete_campaign_id(self, campaign_id, advertiser_id):
        """
        Delete a campaign that was not correctly completed during scheduling
        """
        result = self.check_campaign_api_status(campaign_id=campaign_id)
        if result == "New":
            try:
                opt_status = "DELETE"
                my_args = json.dumps(
                    {
                        "advertiser_id": advertiser_id,
                        "opt_status": opt_status,
                        "campaign_ids": campaign_id,
                    }
                )
                responsetemp = self.post(
                    url=url_hp.TIKTOK_UPDATE_CAMPAIGN_URL, params=my_args
                )
                if responsetemp["code"] != 0:
                    raise TiktokApiResponseCodeException(responsetemp)
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
        campaign = AdCampaigns.objects.filter(campaign_id=campaign_id).values_list(
            "api_status"
        )
        return campaign[0][0]

    def add_new_campaign(self, ad_scheduler_data_all):
        for index in range(len(ad_scheduler_data_all)):
            id_scheduler = ad_scheduler_data_all[index][0]
            campaign_id = ad_scheduler_data_all[index][1]
            group_id = ad_scheduler_data_all[index][9]
            extra_name = ad_scheduler_data_all[index][10]
            objective = ad_scheduler_data_all[index][11]
            adaccount_id = ad_scheduler_data_all[index][23]
            campaign_name = ad_scheduler_data_all[index][26]
            group_name = ad_scheduler_data_all[index][29]
            placement_type = ad_scheduler_data_all[index][30]

            if campaign_id is None:
                if campaign_name is None:
                    campaign_name = self.create_campaign_name(
                        scheduler_id=id_scheduler,
                        extra_name=extra_name,
                        objective=objective,
                        group_name=group_name,
                        placement_type=placement_type,
                    )
                response = self.create_new_campaign(
                    adaccount_id=adaccount_id,
                    campaign_name=campaign_name,
                    objective=objective,
                    group_id=group_id,
                )
                if response:
                    new_campaign_id = response["data"]["campaign_id"]
                    AdScheduler.objects.filter(id=id_scheduler).update(
                        campaign_id=new_campaign_id,
                        campaign_name=campaign_name,
                        updated_at=dt.now(),
                    )

    def get_schedule_value(self, id, databasecolumn):
        """
        Get a single value from the ad_scheduler table with the given ID from the column databaseColumn
        """
        if ad_scheduler := AdScheduler.objects.filter(id=id).values_list(
            databasecolumn
        ):
            return ad_scheduler[0][0]

        raise ValueError(
            "No value found in the database for id: "
            + str(id)
            + " and column "
            + str(databasecolumn)
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

    def create_campaign_name(
        self, scheduler_id, extra_name, objective, group_name, placement_type
    ):
        """ "
        Generate a campaign name according to the schedule data
        """
        date = datetime.datetime.now()
        weeknr = date.strftime("%W")
        year = date.strftime("%Y")

        if "Fruits" in group_name:
            genrestring = group_name.replace("Fruits", "")
        else:
            genrestring = group_name
        # If the landingpage is a linkfire URL, only take the shorttag. Else take the whole link
        schedule_landingpage_url = self.get_creative_value(
            id=scheduler_id, databasecolumn="landingpage_url"
        )
        shorttag = schedule_landingpage_url
        if schedule_landingpage_url.rfind("lnk.to") != -1:
            shorttaglocation = schedule_landingpage_url.rfind("/")
            if shorttaglocation != -1:
                shorttag = schedule_landingpage_url[shorttaglocation + 1 :]

        if extra_name is None:
            extra_name = ""

        campaign_name = f"{genrestring} - Week {weeknr} ({year}) [{placement_type}] [{objective}] {extra_name} - {shorttag}"
        return campaign_name

    def create_new_campaign(self, adaccount_id, campaign_name, objective, group_id):
        try:
            objective_type = self.objective_map_reversed[objective]
        except Exception:
            self.handleError(
                "[ERROR Create New Campaign]",
                " Objective type : "
                + str(objective)
                + " has no valid mapping. This should be adjusted in the code",
                "high",
            )
            return

        budget_mode = "BUDGET_MODE_INFINITE"  # Fetched from database Uiteindelijk wordt dit uit database gehaald

        advertiser_id = adaccount_id
        my_args = json.dumps(
            {
                "advertiser_id": advertiser_id,
                "budget_mode": budget_mode,
                "objective_type": objective_type,
                "campaign_name": campaign_name,
            }
        )
        responsetemp = self.post(url=url_hp.TIKTOK_CREATE_CAMPAIGN_URL, params=my_args)

        if responsetemp.get("code") != 0:
            if (
                responsetemp["code"] == 40002
                and "Campaign name already exists" in responsetemp["message"]
            ):
                # Campaign with this name already exists, GET campaign id and return
                campaign_id_search = AdCampaigns.objects.filter(
                    ad_platform=PlatFormType.TIKTOK, campaign_name=campaign_name
                ).values_list("campaign_id")
                if len(campaign_id_search) != 0:
                    campaign_id = campaign_id_search[0][0]
                    responsetemp["data"]["campaign_id"] = campaign_id
                    return responsetemp
                self.debugPrint(
                    "[Campaign name already exists, retry again with random string]: "
                    + campaign_name
                )
                extrastring = self.generateRandomString(length=4)
                campaign_name = f"{campaign_name} {extrastring}"

                return self.create_new_campaign(
                    adaccount_id=adaccount_id,
                    campaign_name=campaign_name,
                    objective=objective,
                    group_id=group_id,
                )
            self.debugPrint(responsetemp)
            raise TiktokApiResponseCodeException(responsetemp)
        if responsetemp.get("code") == 0:
            campaign_id = responsetemp.get("data").get("campaign_id")
            try:
                AdCampaigns.objects.create(
                    ad_platform=PlatFormType.TIKTOK,
                    advertiserid=adaccount_id,
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    active="Yes",
                    objective=objective,
                    api_status="New",
                    scraper_group_id=group_id,
                )
            except Exception:
                self.handleError(
                    "[ERROR Insert New Campaign]",
                    f" Objective type : {objective}",
                    "high",
                )

            return responsetemp

    def initializing_bussiness_adaccounts(self):
        """
        fetch live data for tiktok ad_accounts ,then all stuff push to database Adaccount tables
        """
        if self.access_token:
            params = json.dumps(
                {
                    "app_id": settings.TIKTOK_APP_ID,
                    "secret": settings.TIKTOK_SECRET_ID,
                }
            )
            response = self.get(
                url=url_hp.TIKTOK_ADVERTISER_ACCOUNT_URL,
                params=params,
            )
            if available_ad_accounts := response.get("data").get("list"):
                for account in available_ad_accounts:
                    params = json.dumps(
                        {
                            "advertiser_ids": [account.get("advertiser_id")],
                            "fields": [
                                "company",
                                "status",
                                "description",
                                "display_timezone",
                                "currency",
                            ],
                        }
                    )
                    responseinfo = self.get(
                        url=url_hp.TIKTOK_ADVERTISER_ACCOUNT_INFO_URL,
                        params=params,
                    )
                    r = responseinfo.get("data").get("list")[0]
                    if r.get("display_timezone") not in pytz.all_timezones:
                        utc_offset_str = None
                    else:
                        timezone = pytz.timezone(r.get("display_timezone"))
                        offset_second = timezone.utcoffset(dt.now()).total_seconds()
                        utc_offset_str = "{:+03d}:00".format(int(offset_second / 3600))
                    AdAccount.objects.update_or_create(
                        account_id=account.get("advertiser_id"),
                        defaults={
                            "account_name": account.get("advertiser_name"),
                            "live_ad_account_status": r.get("status"),
                            "profile": self.profile,
                            "business": None,
                            "timezone": r.get("display_timezone"),
                            "currency": r.get("currency"),
                            "utc_offset": utc_offset_str,
                        },
                    )
            else:
                self.handleError(
                    reason=f"Tiktok ad accounts were not found for this profile_id:{self.profile.id}.",
                    message=response,
                )


def is_valid_tiktok_access_token(access_token):
    try:
        response = requests.get(
            url_hp.TIKTOK_USERINFO_URL,
            headers={"Access-Token": access_token},
        )
        res = response.json()
        if response.status_code == 200 and res.get("code") == 0:
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
