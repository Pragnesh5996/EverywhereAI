from decimal import Decimal
import json
import os
import time
from datetime import datetime as dt
from datetime import timedelta
from urllib import response
from SF import settings
from apps.common.constants import (
    PlatFormType,
    AdAccountActiveType,
    SnapchatEventMap,
    SnapchatCreativeTypeMap,
    SnapchatCallToActionMap,
    Timeformat,
    SnapchatObjectiveMap,
)
from apps.common.models import (
    AdAccount,
    AdAdsets,
    AdCampaigns,
    AdCreativeIds,
    AdScheduler,
    AdsetInsights,
    Authkey,
    Business,
    CustomAudiences,
    DailyAdspendGenre,
    Pixels,
    Language,
)
from apps.scraper.models import Settings
from apps.linkfire.models import ScrapeLinkfires
import requests
from apps.snapchat.models import SnapApps
from apps.common import AdPlatform as AP
from apps.common.urls_helper import URLHelper
from itertools import groupby

url_hp = URLHelper()


class SnapchatAPI(AP.AdPlatform):
    def __init__(self, debug_mode, profile):
        """
        Populates auth key and checks if this key is still valid
        Parameters:
        string: Database connection
        """
        super().__init__(debug_mode)
        self.client_secret = settings.SNAPCHAT_CLIENT_SECRET_ID
        self.client_id = settings.SNAPCHAT_CLIENT_ID
        self.profile = profile
        self.access_token = self.get_authkey()
        self.microCurrency = 1000000

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
                "Country Code could not be matched to country name:", country_code
            )

    def get_authkey(self):
        """
        Fetches authkey from database to populate this parent class
        Returns:
        string: Authorization key
        """
        authkey = Authkey.objects.filter(profile=self.profile).values("refresh_token")
        if authkey:
            params = {
                "refresh_token": authkey[0].get("refresh_token"),
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
            }
            r = requests.post(
                url_hp.SNAPCHAT_ACCESS_TOKEN_USING_REFRESH_TOKEN_URL, params
            )
            response = r.json()
            return response.get("access_token")

    def post(self, url, params):
        """
        Make a POST request
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.post(url, headers=headers, json=params)
        if r.ok:
            response = r.json()
        elif r.status_code == 401:
            # If unauthorized: get new key and try again
            self.access_token = self.get_authkey()
            headers = {"Authorization": f"Bearer {self.access_token}"}
            r = requests.post(url, headers=headers, json=params)
            if r.ok:
                response = r.json()
            else:
                raise RuntimeError(
                    f"Something went wrong with a request. Original response: {r.text}"
                )
        else:
            raise RuntimeError(
                f"Something went wrong with a request. Original response: {r.text}"
            )
        return response

    # def put(self, url, params):
    #     """
    #     Make a PUT request
    #     """
    #     headers = {"Authorization": f"Bearer {self.access_token}"}
    #     r = requests.put(url, headers=headers, json=params)
    #     if r.ok:
    #         response = r.json()
    #     elif r.status_code == 401:
    #         # If unauthorized: get new key and try again
    #         self.access_token = self.get_authkey()
    #         headers = {"Authorization": f"Bearer {self.access_token}"}
    #         r = requests.put(url, headers=headers, json=params)
    #         if r.ok:
    #             response = r.json()
    #         else:
    #             raise RuntimeError(
    #                 f"Something went wrong with a request. Original response: {r.text}"
    #             )
    #     else:
    #         raise RuntimeError(
    #             f"Something went wrong with a request. Original response: {r.text}"
    #         )
    #     return response

    def get(self, url, params):
        """
        Make a GET request
        """
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        r = requests.get(url, headers=headers, params=params)
        if r.ok:
            response = r.json()
        elif r.status_code == 401:
            # If unauthorized: get new key and try again
            self.access_token = self.get_authkey()
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            r = requests.get(url, headers=headers, params=params)
            if r.ok:
                response = r.json()
            else:
                raise RuntimeError(
                    f"Something went wrong with a request. Original response: {r.text}"
                )
        else:
            raise RuntimeError(
                f"Something went wrong with a request. Original response: {r.text}"
            )
        return response

    def delete(self, url, params):
        """
        Make a DELETE request
        """
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        r = requests.delete(url, headers=headers, params=params)
        if r.ok:
            response = r.json()
        elif r.status_code == 401:
            # If unauthorized: get new key and try again
            self.access_token = self.get_authkey()
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            r = requests.delete(url, headers=headers, params=params)
            if r.ok:
                response = r.json()
            else:
                raise RuntimeError(
                    f"Something went wrong with a request. Original response: {r.text}"
                )
        else:
            raise RuntimeError(
                f"Something went wrong with a request. Original response: {r.text}"
            )
        return response

    def getDates(self, range):
        """
        Get dates in the format Snap wants from today to 'range' days ago
        """
        end_date = dt.now()
        start_date = end_date - timedelta(days=range)
        # Get GMT offset - with DST taken into account
        offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
        offset = offset / 60 / 60 * -1
        # Format dates for Snap requirements
        end_date = f"{end_date.strftime('%Y-%m-%d')}T00:00:00.000+0{int(offset)}:00"
        start_date = f"{start_date.strftime('%Y-%m-%d')}T00:00:00.000+0{int(offset)}:00"
        return start_date, end_date

    def formatDates(self, start_date, end_date):
        """
        Format two Datetime objects in the way Snap wants
        """
        return self.formatDate(start_date), self.formatDate(end_date)

    def formatDate(self, date):
        """
        Format a single Datetime object in the way Snap wants
        # Format dates for Snap requirements
        # date = f"{date}T00:00:00.000+0{int(offset)}:00"
        """
        # Get GMT offset - with DST taken into account
        offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
        offset = offset / 60 / 60 * -1
        date = f"{date}T00:00:00"
        return date

    def formatDateSchedule(self, date_time):
        """
        Format a Datetime object in the way Snap wants for scheduling
        # "2016-08-11T22:03:58.869Z"
        # Format dates for Snap requirements
        """
        return date_time.strftime(Timeformat.ISO_8601_DATE_FORMAT)

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

        results = self.get(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adsquads/{adgroup_id}", params={}
        )
        if (
            "request_status" in results
            and results["request_status"] != "SUCCESS"
            or "request_status" not in results
        ):
            if (
                "debug_message" in results
                and results["debug_message"] == "Resource can not be found"
            ):
                AdAdsets.objects.filter(
                    ad_platform=PlatFormType.SNAPCHAT,
                    adset_id=adgroup_id,
                    campaign_id=campaign_id,
                ).update(active="No", updated_at=dt.now())
                raise RuntimeError(
                    f"Adset {adgroup_id} from campaign {campaign_id} was deleted in the Snapchat UI. It has been turned off in the Database."
                )
            else:
                raise RuntimeError(
                    f"Something went wrong while trying to get the ad {adgroup_id} before updating it. \nOriginal error: \n{results}"
                )
        elif "adsquads" in results and "adsquad" in results["adsquads"][0]:
            adset = results["adsquads"][0]["adsquad"]

        adset.update(
            {"bid_micro": int(bid * self.microCurrency)} if bid is not None else {}
        )
        adset.update(
            {"daily_budget_micro": budget * self.microCurrency}
            if budget is not None
            else {}
        )
        results = self.put(
            url=f"{url_hp.SNAPCHAT_v1_URL}/v1/campaigns/{campaign_id}/adsquads",
            params={"adsquads": [adset]},
        )
        if (
            "request_status" in results
            and results["request_status"] != "SUCCESS"
            or "request_status" not in results
        ):
            errormsg = f"Something went wrong in API call to update AdGroup with ID: {adgroup_id} in campaign with ID: {campaign_id}.\nThe error from Snapchat API is: {response}\n"
            if bid is not None:
                errormsg += "New bid should be: {bid/self.microCurrency}. "
            if budget is not None:
                errormsg += "New budget should be: {budget/self.microCurrency} cents."

    def accounts_to_database(self):
        """
        Get Snap ad accounts and add them to the database (or update them if they already are)
        """
        self.debugPrint("Accounts to database has been called")
        self.initializing_bussiness_adaccounts()
        return AdAccount.objects.filter(
            profile__ad_platform=PlatFormType.SNAPCHAT,
            profile=self.profile,
            active=AdAccountActiveType.Yes,
        ).values("account_id")

    def campaigns_to_database(self, account_id):
        """
        Get campaigns under the given account and add them to the database
        """
        self.debugPrint("Campaigns to database has been called")
        url = f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{account_id}/campaigns"
        last_page = False
        campaigns_in_db = AdCampaigns.objects.filter(
            advertiserid=account_id, ad_platform=PlatFormType.SNAPCHAT
        ).values("campaign_id", "advertiserid")
        available_campaign_list = []
        delete_campaign_list = []
        delete = 0
        while not last_page:
            params = {}
            response = self.get(url=url, params=params)
            if "campaigns" in response:
                for campaign in response["campaigns"]:
                    camp = campaign.get("campaign")
                    if camp["id"] not in available_campaign_list:
                        available_campaign_list.append(camp["id"])
                    if camp.get("status") == "ACTIVE":
                        objective_key = (
                            camp["objective"]
                            if camp["objective"] in list(SnapchatObjectiveMap.keys())
                            else "SHOP_VIEW"
                        )
                        objective = SnapchatObjectiveMap[objective_key]
                        AdCampaigns.objects.update_or_create(
                            ad_platform=PlatFormType.SNAPCHAT,
                            campaign_id=camp.get("id"),
                            defaults={
                                "advertiserid": account_id,
                                "campaign_name": camp.get("name"),
                                "scraper_group": None,
                                "active": "Yes",
                                "objective": objective,
                            },
                        )
                    else:
                        results = AdCampaigns.objects.filter(
                            campaign_id=camp.get("id"),
                            ad_platform=PlatFormType.SNAPCHAT,
                        ).values("active")
                        if results and results[0].get("active") != "No":
                            AdCampaigns.objects.filter(
                                campaign_id=camp.get("id"),
                                ad_platform=PlatFormType.SNAPCHAT,
                            ).update(active="No", updated_at=dt.now())

            if "paging" in response and "next_link" in response.get("paging"):
                url = response.get("paging").get("next_link")
            else:
                last_page = True
        self.debugPrint("Delete Campaigns to database has been called")
        for campaign in campaigns_in_db:
            if campaign.get("campaign_id") not in available_campaign_list:
                delete_campaign_list.append(campaign.get("campaign_id"))
        self.debugPrint(
            f"[Campaigns] Found to delete {delete_campaign_list} campaigns..."
        )
        for campaign_id in delete_campaign_list:
            AdCampaigns.objects.filter(
                campaign_id=campaign_id, advertiserid=account_id
            ).delete()
            delete += 1
        self.debugPrint(f"[Delete Campaigns Done] {str(delete)} campaigns Deleted")

    def adsets_to_database(self, campaign_id):
        """
        Get campaigns under the given account and add them to the database
        """
        self.debugPrint("Adsets to database has been called")
        url = f"{url_hp.SNAPCHAT_v1_URL}/campaigns/{campaign_id}/adsquads"
        last_page = False
        while not last_page:
            params = {}
            response = self.get(url=url, params=params)
            if "adsquads" in response:
                for adsquad in response.get("adsquads"):
                    set = adsquad.get("adsquad")
                    adset_id = set.get("id")
                    if set.get("status") == "ACTIVE":
                        name = set.get("name")
                        try:
                            bid = set.get("bid_micro") / self.microCurrency
                        except KeyError:
                            bid = None
                        budget = set.get("daily_budget_micro") / self.microCurrency

                        # Get countries
                        countries = ""
                        geos = set.get("targeting").get("geos")
                        for country in geos:
                            countries += country.get("country_code").upper() + ","
                        countries = countries[:-1]  # Remove trailing comma
                        '''
                        # Get objective and set in CAMPAIGN
                        objective = None
                        conversion_goals = ['PIXEL_PURCHASE', 'PIXEL_PAGE_VIEW', 'START_CHECKOUT', 'PIXEL_ADD_TO_CART']        
                        if set['optimization_goal'] in conversion_goals:
                            objective = 'Conversions'
                        elif set['optimization_goal'] == 'APP_INSTALLS':
                            objective = 'App_installs'
                        elif set['optimization_goal'] == 'SWIPES':
                            objective = 'Traffic'
                        elif set['optimization_goal'] == 'PIXEL_SIGNUP':
                            objective = 'PIXEL_SIGNUP'
                        else:
                            objective = set['optimization_goal']
                        variables = ("Snap", campaign_id)
                        results = self.db.execSQL("""SELECT objective FROM ad_campaigns WHERE ad_platform=%s AND campaign_id=%s""", variables, False)
                        if len(results) == 0:  
                            raise RuntimeError(f"No campaign found with id {campaign_id} while trying to update its objective")
                        if results[0][0] == None:
                            variables = (objective, campaign_id, "Snap")
                            self.db.execSQL("""UPDATE `ad_campaigns` SET `objective` = %s WHERE campaign_id = %s AND ad_platform = %s;""", variables, True)
                        elif results[0][0] != objective:
                            raise RuntimeError(f"Campaign {campaign_id} has two different objectives: {results[0][0]} and {objective}")
                        '''

                        # Get linkfire URL
                        ad_url = f"{url_hp.SNAPCHAT_v1_URL}/adsquads/{adset_id}/ads"
                        ad_params = {}
                        ad_response = self.get(url=ad_url, params=ad_params)
                        ads = ad_response.get("ads")
                        if len(ads) == 0:
                            self.handleError(
                                "No ads found",
                                f"No ads were found for Snap adset with id {adset_id}.",
                            )
                            continue
                        try:
                            creative_id = (
                                ads[0].get("ad").get("creative_id")
                            )  # URL is the same for all ads in 1 adset
                            cr_url = f"{url_hp.SNAPCHAT_v1_URL}/creatives/{creative_id}"
                            cr_params = {}
                            cr_response = self.get(url=cr_url, params=cr_params)
                        except Exception as e:
                            self.handleError(
                                "No ads found",
                                f"Could not get creative for adset with ID {adset_id}. \nOriginal error:\n{str(e)}\n\nOriginal response:\ncr_response",
                            )
                            continue
                        try:
                            linkfire_url = (
                                cr_response.get("creatives")[0]
                                .get("creative")
                                .get("web_view_properties")
                                .get("url")
                            )
                        except KeyError:
                            linkfire_url = None

                        adset, _ = AdAdsets.objects.update_or_create(
                            adset_id=adset_id,
                            campaign_id=campaign_id,
                            ad_platform=PlatFormType.SNAPCHAT,
                            defaults={
                                "adset_name": name,
                                "target_country": countries,
                                "landingpage": linkfire_url,
                                "bid": bid,
                                "budget": budget,
                                "active": "Yes",
                            },
                        )
                        # AdCreativeIds.objects.filter()
                        # linkfire_id = adset.linkfire_id
                        # if linkfire_id is not None:
                        #     linkfire = ScrapeLinkfires.objects.filter(
                        #         id=linkfire_id
                        #     ).values("is_active")

                        #     if linkfire:
                        #         if linkfire[0].get("is_active") == StatusType.NO:
                        #             ScrapeLinkfires.objects.filter(
                        #                 id=linkfire_id
                        #             ).update(
                        #                 is_active=StatusType.YES, updated_at=dt.now()
                        #             )
                    else:
                        results = AdAdsets.objects.filter(
                            adset_id=adset_id, ad_platform=PlatFormType.SNAPCHAT
                        ).values("active")

                        if results and results[0].get("active") != "No":
                            AdAdsets.objects.filter(
                                adset_id=adset_id, ad_platform=PlatFormType.SNAPCHAT
                            ).update(active="No", updated_at=dt.now())

            if "paging" in response and "next_link" in response.get("paging"):
                url = response.get("paging").get("next_link")
            else:
                last_page = True
        return response

    def pixels_to_database(self, account_id):
        """
        Get Pixels under the given account and add them to the database
        """
        self.debugPrint("Pixels to database has been called")
        url = f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{account_id}/pixels"
        last_page = False
        while not last_page:
            params = {}
            response = self.get(url=url, params=params)
            for pixel in response.get("pixels"):
                Pixels.objects.update_or_create(
                    pixel_id=pixel.get("pixel").get("id"),
                    advertiser_id=account_id,
                    platform=PlatFormType.SNAPCHAT,
                    defaults={
                        "name": pixel.get("pixel").get("name"),
                    },
                )
            if "paging" in response and "next_link" in response.get("paging"):
                url = response.get("paging").get("next_link")
            else:
                last_page = True

    def audiences_to_database(self, account_id):
        """
        Get Custom Audiences under the given account and add them to the database
        """
        self.debugPrint("Audiences to database has been called")
        url = f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{account_id}/segments"
        last_page = False
        while not last_page:
            params = {}
            response = self.get(url=url, params=params)
            for segment in response.get("segments"):
                CustomAudiences.objects.update_or_create(
                    audience_id=segment.get("segment").get("id"),
                    account_id=account_id,
                    platform=PlatFormType.SNAPCHAT,
                    defaults={
                        "name": segment.get("segment").get("name"),
                        "description": segment.get("segment").get("description"),
                    },
                )
            if "paging" in response and "next_link" in response["paging"]:
                url = response.get("paging").get("next_link")
            else:
                last_page = True

    def initializer(self):
        """
        Initialize and update Snap advertising data.
        """
        self.debugPrint("Initializer has been called")
        ad_accounts = self.accounts_to_database()

        for account in ad_accounts:
            account_id = account.get("account_id")
            self.campaigns_to_database(account_id)
            self.pixels_to_database(account_id)
            self.audiences_to_database(account_id)

        campaigns = AdCampaigns.objects.filter(
            ad_platform=PlatFormType.SNAPCHAT
        ).values("campaign_id")
        for campaign in campaigns:
            campaign_id = campaign.get("campaign_id")
            try:
                self.adsets_to_database(campaign_id)
            except Exception as e:
                self.handleError(
                    "[Initializer - adsets]",
                    f"Something went wrong while adding an adset to the database. Original error: {str(e)}",
                )

    def get_insights_spend(self, start_date, end_date, adset_id):
        """
        Get spend data for adset
        """
        self.debugPrint("get_insights_spend has been called")
        start_date, end_date = self.formatDates(start_date, end_date)
        response = self.get(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adsquads/{adset_id}/stats",
            params={
                "granularity": "DAY",
                "start_time": start_date,
                "end_time": end_date,
            },
        )
        insights = (
            response.get("timeseries_stats")[0].get("timeseries_stat").get("timeseries")
        )
        report = [
            {
                "adgroup_id": adset_id,
                "spend": Decimal(ins.get("stats").get("spend") / self.microCurrency),
                "date": start_date,
            }
            for ins in insights
        ]
        return report

    def get_report_day(self, start_date, end_date):
        """
        Get spend report from API

        start_date (Datetime): start date of the report
        end_date (Datetime): end date of the report

        return: report in the form of a list containing dicts like: {'adgroup_id': '...', 'spend': '...'}
        """
        report = []
        results = AdAdsets.objects.filter(
            ad_platform=PlatFormType.SNAPCHAT
        ).values_list("adset_id")
        for set in results:
            report += self.get_insights_spend(start_date, end_date, set[0])
        return report

    def get_insights_spend_campaign(self, start_date, end_date, campaign_id):
        """
        Get spend data for campaign
        """
        self.debugPrint("get_insights_spend_campaign has been called")
        url = f"{url_hp.SNAPCHAT_v1_URL}/campaigns/{campaign_id}/stats"
        start_date, end_date = self.formatDates(start_date, end_date)
        params = {
            "granularity": "DAY",
            "start_time": start_date,
            "end_time": end_date,
        }
        response = self.get(url=url, params=params)
        insights = (
            response.get("timeseries_stats")[0].get("timeseries_stat").get("timeseries")
        )
        report = [
            {
                "campaign_id": campaign_id,
                "spend": Decimal(ins.get("stats").get("spend") / self.microCurrency),
                "date": ins["start_time"],
            }
            for ins in insights
        ]
        return report

    def updateDailySpendData(self, ad_account_id=None, pastdays=None, uid=None):
        """
        Update the daily_adspend_genre table
        """
        self.debugPrint("Update daily spend data has been called")
        try:
            self.update_cpc(ad_account_id=ad_account_id)  # Update CPC as well
        except Exception as e:
            self.handleError(
                "Update Spend Data",
                f"There was an issue while updating the CPC.\nOriginal error: {str(e)}",
            )
        report = []
        delta = 28 if pastdays == "last_28d" else 7
        start_date = str(dt.now().date() - timedelta(days=delta))
        end_date = str(dt.now().date() + timedelta(days=1))
        results = AdCampaigns.objects.filter(ad_platform=PlatFormType.SNAPCHAT).values(
            "campaign_id"
        )
        for set in results.filter(
            **({"advertiserid": ad_account_id} if ad_account_id is not None else {})
        ):
            report += self.get_insights_spend_campaign(
                start_date, end_date, set.get("campaign_id")
            )
        date_dict = {}
        for rep in report:
            i = rep.get("date").find("T")
            date = rep.get("date")[:i]
            results = AdCampaigns.objects.filter(
                ad_platform=PlatFormType.SNAPCHAT, campaign_id=rep["campaign_id"]
            ).values("scraper_group_id", "advertiserid", "campaign_id")

            if len(results) != 0:
                campaign_id = results[0].get("campaign_id")
                if campaign_id is None:
                    campaign_id = None
                if (campaign_id, date) in date_dict:
                    date_dict[(campaign_id, date)]["spend"] += Decimal(rep.get("spend"))
                else:
                    date_dict[(campaign_id, date)] = {}
                    date_dict[(campaign_id, date)]["spend"] = Decimal(rep.get("spend"))
                    date_dict[(campaign_id, date)]["ad_account"] = results[0].get(
                        "advertiserid"
                    )
        daily_adspend_genre_bulk_create_objects = []
        daily_adspend_genre_bulk_update_objects = []

        for rep, value in date_dict.items():
            campaign_id = rep[0]
            date = rep[1]
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
                platform=PlatFormType.SNAPCHAT,
                campaign_id=campaign_id,
                ad_account__account_id=account_id,
                date=date,
            ).values("id")

            current_date = dt.now().date()
            if not daily_adspend_genre:
                daily_adspend_genre_bulk_create_objects.append(
                    DailyAdspendGenre(
                        platform=PlatFormType.SNAPCHAT,
                        spend=Decimal(str(value.get("spend"))),
                        date=date,
                        campaign_id=campaign_id,
                        ad_account=adaccount,
                        account_id=account_id,
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

    def get_cpc_adset(self, start_date, end_date, adset_id):
        """
        Get spend data for campaign
        """
        self.debugPrint("get_insights_spend_campaign has been called")
        start_date, end_date = self.formatDates(start_date, end_date)
        response = self.get(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adsquads/{adset_id}/stats",
            params={
                "fields": "swipes,spend",
                "granularity": "DAY",
                "start_time": start_date,
                "end_time": end_date,
            },
        )
        insights = (
            response.get("timeseries_stats")[0].get("timeseries_stat").get("timeseries")
        )
        report = []
        for ins in insights:
            spend = ins.get("stats").get("spend") / self.microCurrency
            clicks = ins.get("stats").get("swipes")
            if clicks != 0:
                cpc = spend / clicks
            else:
                cpc = 0
            report.append(
                {
                    "adset_id": adset_id,
                    "spend": round(Decimal(spend), 2),
                    "cpc": round(Decimal(cpc), 8),
                    "date": ins.get("start_time"),
                }
            )
        return report

    def update_cpc(self, ad_account_id=None):
        report = []
        end_date = str(dt.now().date())
        start_date = str(dt.now().date() - timedelta(days=7))
        if ad_account_id:
            campaigns_ids_list = AdCampaigns.objects.filter(
                ad_platform=PlatFormType.SNAPCHAT, advertiserid=ad_account_id
            ).values_list("campaign_id", flat=True)

            adsets = AdAdsets.objects.filter(
                ad_platform=PlatFormType.SNAPCHAT, campaign_id__in=campaigns_ids_list
            ).values("adset_id", "campaign_id")
        else:
            adsets = AdAdsets.objects.filter(ad_platform=PlatFormType.SNAPCHAT).values(
                "adset_id", "campaign_id"
            )

        for adset in adsets:
            report += self.get_cpc_adset(start_date, end_date, adset.get("adset_id"))
            for rep in report:
                campaign_id = adset.get("campaign_id")
                adset_id = rep.get("adset_id")
                date = dt.strptime(rep.get("date").split("T")[0], "%Y-%m-%d")
                cpc = rep.get("cpc")
                spend = rep.get("spend")
                adset_insights = AdsetInsights.objects.filter(
                    platform=PlatFormType.SNAPCHAT,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    date=date,
                ).values("id", "cpc", "spend")

                if not adset_insights:
                    AdsetInsights.objects.create(
                        platform=PlatFormType.SNAPCHAT,
                        campaign_id=campaign_id,
                        adset_id=adset_id,
                        cpc=cpc,
                        spend=spend,
                        date=date,
                    )
                # If value in DB does not match API value, update it to API value
                else:
                    cpc_changed = (
                        cpc is None and cpc != adset_insights[0].get("cpc")
                    ) or (
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
                        AdsetInsights.objects.filter(
                            id=adset_insights[0].get("id")
                        ).update(
                            cpc=cpc,
                            spend=spend,
                            date_updated=dt.now(),
                            updated_at=dt.now(),
                        )

    def get_schedule_value(self, id, databaseColumn):
        """
        Get a single value from the database from the 'ad_scheduler' table. This method is to make methods that use it more legible.
        id: ID of the row to schedule
        databaseColumn: Name of the database column to take the required value from
        """

        if ad_scheduler := AdScheduler.objects.filter(id=id).values_list(
            databaseColumn
        ):
            return ad_scheduler[0][0]

        raise ValueError(
            "No value found in the database for id: "
            + str(id)
            + " and column "
            + str(databaseColumn)
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

    def upload_creatives(self, scheduler_id):
        """
        Upload all creatives linked to the scheduler_id
        """
        uploadSesId = self.get_schedule_value(scheduler_id, "uploadsesid")
        adaccount_id = self.get_schedule_value(scheduler_id, "adaccount_id")

        ad_creatives_ids = AdCreativeIds.objects.filter(
            uploadsesid=uploadSesId,
            scheduler_id=scheduler_id,
            ad_platform=PlatFormType.SNAPCHAT,
            creative_id=None,
        ).values("id", "url", "filename", "creative_id")

        for data in ad_creatives_ids:
            id = data.get("id")
            video_url = data.get("url")
            filename = data.get("filename")
            response = self.post(
                url=f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{adaccount_id}/media",
                params={
                    "media": [
                        {
                            "name": filename,
                            "type": "VIDEO",
                            "ad_account_id": adaccount_id,
                        }
                    ]
                },
            )
            if (
                "media" in response
                and "media" in response.get("media")[0]
                and "id" in response.get("media")[0].get("media")
            ):
                media_id = response.get("media")[0].get("media").get("id")
                try:
                    self.upload_video(media_id, video_url)
                    date = dt.now()
                    AdCreativeIds.objects.filter(
                        url=video_url, ad_platform=PlatFormType.SNAPCHAT
                    ).update(creative_id=media_id, uploaded_on=date, updated_at=date)
                    self.debugPrint("Uploaded creative video")

                except Exception as e:
                    AdCreativeIds.objects.filter(id=id).update(
                        notes=str(e), updated_at=dt.now()
                    )
                    raise RuntimeError(
                        f"Could not upload creative with ID: {id}. " + str(e)
                    )

    def upload_video(self, id, video_url):
        """
        Upload a single video by downloading it to disk, then uploading it to Snapchat (Snapchat API does not allow upload from a URL directly)
        """
        res = requests.get(video_url)
        video = res.content
        open("temp_video.mp4", "wb").write(video)
        response = requests.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/media/{id}/upload",
            files={
                "file": open("temp_video.mp4", "br"),
                "filename": "uploaded_vid.mp4",
            },
            headers={"Accept": "*/*", "Authorization": f"Bearer {self.access_token}"},
        )
        if not response.ok:
            raise Exception(
                f"Could not upload creative video. Original error: {response.json()}"
            )

    def upload_app_icon(self, adaccount_id, icon_url):
        """
        Upload an app icon
        """

        response = self.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{adaccount_id}/media",
            params={
                "media": [
                    {
                        "name": "app_icon",
                        "type": "IMAGE",
                        "ad_account_id": adaccount_id,
                    }
                ]
            },
        )
        if (
            "media" in response
            and "media" in response.get("media")[0]
            and "id" in response.get("media")[0].get("media")
        ):
            media_id = response.get("media")[0].get("media").get("id")
            try:
                self.upload_image(media_id, icon_url)
                self.debugPrint("Uploaded creative img")
                return media_id
            except Exception as e:
                raise RuntimeError(
                    f"Could not upload creative with URL: {icon_url}. " + str(e)
                )

    def upload_image(self, id, img_url):
        """
        Upload image by downloading it to disk, then uploading it to Snapchat (Snapchat API does not allow upload from a URL directly)
        """
        res = requests.get(img_url)
        img = res.content
        open("temp_icon.png", "wb").write(img)
        response = requests.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/media/{id}/upload",
            files={"file": open("temp_icon.png", "br"), "filename": "app_icon.png"},
            headers={"Accept": "*/*", "Authorization": f"Bearer {self.access_token}"},
        )
        if not response.ok:
            raise Exception(
                f"Could not upload creative video. Original error: {response.json()}"
            )

    def create_adset_name(self, scheduler_id, country):
        """ "
        Generate a campaign name according to the schedule data
        """
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
        objective = self.get_schedule_value(scheduler_id, "objective")
        country_str = ",".join(country)
        country_name = (
            self.countryCodeToName(country_str)
            if len(country) == 1
            else "Multiple Countries"
        )

        date_str = dt.now().strftime(Timeformat.WeekYearFormat)
        return f"[{country_name}] - {date_str} [{objective}] {extra_name} - {short_tag}"

    def create_adset(
        self,
        campaign_id,
        name,
        country,
        schedule_budget,
        schedule_age_min,
        schedule_age_max,
        schedule_datetime,
        bid_strategy,
        custom_audiences,
        bid,
        objective,
        opt_goal,
        pixel_id,
        accelerated_spend,
        language_string,
    ):
        """
        Create an adset with the given parameters. Make sure the parameters are in the form Snap expects.

        Pixel ID can be None if objective is not PIXEL_SIGNUP
        """
        countries = [{"country_code": c.lower()} for c in country]
        targeting = {
            "geos": countries,
            "demographics": [
                {"min_age": schedule_age_min, "max_age": schedule_age_max}
            ],
            "enable_targeting_expansion": "False",
        }

        if language_string is not None and len(language_string) != 0:
            language_list = language_string.split(",")
            targeting["demographics"][0]["languages"] = language_list

        if custom_audiences is not None:
            audiences = custom_audiences.split(",")
            if len(audiences) > 1:
                raise RuntimeError("Snap cannot have more than 1 custom audience")
            targeting["segments"] = [
                {"segment_id": audiences, "operation": "EXCLUDE"}
            ]  # custom_audiences in place of the ID  ## TODO

        adsquad = [
            {
                "campaign_id": campaign_id,
                "name": name,
                "type": "SNAP_ADS",
                "placement_v2": {"config": "AUTOMATIC"},
                "optimization_goal": opt_goal,
                "bid_micro": bid,
                "daily_budget_micro": schedule_budget,
                "bid_strategy": "LOWEST_COST_WITH_MAX_BID",
                "billing_event": "IMPRESSION",  # "No matter what Optimization Goal is selected, the Billing Event will still be IMPRESSION. This may change in the future." - API docs: https://marketingapi.snapchat.com/docs/#squad-optimization-goals
                "targeting": targeting,
                "status": "ACTIVE",
                "start_time": schedule_datetime,
            }
        ]
        if objective in ["Conversions", "PIXEL_SIGNUP"]:
            if pixel_id is None:
                raise RuntimeError(
                    f"Please add a pixel if you want to use the objective {objective}"
                )
            else:
                adsquad[0]["pixel_id"] = pixel_id
        optimization_goal_list = [
            "PIXEL_PURCHASE",
            "PIXEL_PAGE_VIEW",
            "PIXEL_SIGNUP",
            "IMPRESSIONS",
            "USES",
            "SWIPES",
            "VIDEO_VIEWS",
            "VIDEO_VIEWS_15_SEC",
            "STORY_OPENS",
            "PIXEL_ADD_TO_CART",
        ]
        if accelerated_spend:
            if (
                adsquad[0].get("bid_strategy") == "LOWEST_COST_WITH_MAX_BID"
                and adsquad[0].get("bid_micro") is not None
                and adsquad[0].get("optimization_goal") in optimization_goal_list
            ):
                adsquad[0]["pacing_type"] = "ACCELERATED"
            else:
                adsquad[0]["pacing_type"] = "STANDARD"
        else:
            adsquad[0]["pacing_type"] = "STANDARD"
        response = self.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/campaigns/{campaign_id}/adsquads",
            params={
                "adsquads": adsquad,
            },
        )
        if (
            "adsquads" in response
            and "adsquad" in response.get("adsquads")[0]
            and "id" in response.get("adsquads")[0].get("adsquad")
        ):
            return response.get("adsquads")[0].get("adsquad").get("id")
        else:
            raise RuntimeError(f"An error occured: {response}")

    def get_age_minmax(self, age_range):
        """ "
        Extract the min and max age range from the age range from the database
        """
        # min_age, max_age = map(int, age_range.split("-"))
        # if min_age > max_age:
        #     min_age, max_age = max_age, min_age
        # return min_age, max_age

        age_ranges = age_range.split(",")
        parsed_ranges = []

        for range_str in age_ranges:
            range_parts = range_str.split("-") if range_str != "45+" else ["49", "49"]
            min_age = range_parts[0] 
            max_age = range_parts[1]

            parsed_ranges.append(min_age)
            parsed_ranges.append(max_age)
        min_age, max_age = parsed_ranges[0], parsed_ranges[-1]
        return min_age, max_age

    def schedule_single_adset(
        self, scheduler_id, campaign_id, country, language_string
    ):
        """
        Schedule a single adset with the given scheduler id for the given country in the given campaign
        """
        schedule_age_range = self.get_schedule_value(scheduler_id, "age_range")
        schedule_age_min, schedule_age_max = self.get_age_minmax(schedule_age_range)
        scheduled_for = self.get_schedule_value(scheduler_id, "scheduled_for")
        schedule_datetime = self.formatDateSchedule(scheduled_for)

        # Get optimization goal / objective and check if it is the same as the campaign objective in the database
        event = self.get_schedule_value(scheduler_id, "event_type")
        objective = self.get_schedule_value(scheduler_id, "objective")
        accelerated_spend = self.get_schedule_value(scheduler_id, "accelerated_spend")
        placement = self.get_schedule_value(scheduler_id, "automatic_placement")

        campaign_objective = AdCampaigns.objects.filter(
            campaign_id=campaign_id, ad_platform=PlatFormType.SNAPCHAT
        ).values("objective")

        if campaign_objective[0].get("objective") != objective:
            raise RuntimeError(
                f"Campaign objective ({campaign_objective}) and and adset objective ({objective}) do not match. Please make sure these match when scheduling."
            )
        try:
            if objective == "Traffic":
                opt_goal = "SWIPES"
            elif objective == "App_installs":
                opt_goal = "APP_INSTALLS"
            elif objective == "Conversions":
                opt_goal = SnapchatEventMap[event]
        except Exception as e:
            raise RuntimeError(
                f"The objective {objective} has not been implemented for Snap. Please do so in Snapchat_api_handler.py {str(e)}"
            )

        name = self.create_adset_name(scheduler_id, country)
        # Get bid and budget -> cast DB value to Decimal for multiplication, then cast to int (Decimal cannot be used in JSON)
        schedule_budget = int(Decimal(self.get_schedule_budget()) * self.microCurrency)
        bid = self.get_schedule_value(scheduler_id, "bid") or Decimal("0.01")
        schedule_bid = int(Decimal(bid) * self.microCurrency)
        bid_strategy = self.get_schedule_value(scheduler_id, "bid_strategy")  # ?
        custom_audiences = self.get_schedule_value(scheduler_id, "custom_audiences")
        pixel_id = self.get_schedule_value(scheduler_id, "pixel_id")

        return self.create_adset(
            campaign_id,
            name,
            country,
            schedule_budget,
            schedule_age_min,
            schedule_age_max,
            schedule_datetime,
            bid_strategy,
            custom_audiences,
            schedule_bid,
            objective,
            opt_goal,
            pixel_id,
            accelerated_spend,
            language_string,
        )

    def schedule_single_creative(
        self,
        adaccount_id,
        video_id,
        name,
        headline,
        creative_type,
        call_to_action,
        link_url,
        app_data,
        # profile_id,
    ):
        """ "
        Schedule a single creative with the given data. Make sure the parameters are in the form Snap expects
        """
        creative = [
            {
                "ad_account_id": adaccount_id,
                "top_snap_media_id": video_id,
                "name": name,
                "type": creative_type,
                "call_to_action": call_to_action,
                "brand_name": "Fruits Music",
                "headline": headline,
                "shareable": True,
            }
        ]

        if creative_type == "WEB_VIEW":
            if link_url is None:
                raise RuntimeError(
                    "If the creative type is WEB_VIEW, please add an URL to link to the ad."
                )
            creative[0]["web_view_properties"] = {
                "url": link_url,
                "block_preload": True,
            }
        elif creative_type == "APP_INSTALL":
            creative[0]["app_install_properties"] = app_data

        # if profile_id is not None:
        #     creative[0]["profile_properties"] = {"profile_id": profile_id}

        response = self.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{adaccount_id}/creatives",
            params={
                "creatives": creative,
            },
        )
        if (
            "creatives" in response
            and "creative" in response.get("creatives")[0]
            and "id" in response.get("creatives")[0].get("creative")
        ):
            return response.get("creatives")[0].get("creative").get("id")
        else:
            raise RuntimeError(
                f"Call to create creative went wrong. Original message: {response}"
            )

    def schedule_creatives(self, scheduler_id):
        """ "
        Schedule creatives for the given scheduler_id
        """
        uploadSesId = self.get_schedule_value(scheduler_id, "uploadsesid")
        adaccount_id = self.get_schedule_value(scheduler_id, "adaccount_id")
        link_url = self.get_schedule_value(scheduler_id, "landingpage_url")
        headline = self.get_schedule_value(scheduler_id, "heading")
        objective = self.get_schedule_value(scheduler_id, "objective")
        # profile_id = self.get_schedule_value(scheduler_id, "snap_profile_id")

        if objective == "App_installs":
            app_id = self.get_schedule_value(scheduler_id, "application_id")
            snap_apps = SnapApps.objects.filter(id=app_id).values(
                "app_name", "ios_app_id", "android_app_url", "icon_url", "icon_media_id"
            )
            if snap_apps:
                raise RuntimeError(
                    f"There was no app found with id {app_id} which was added to schedule session with id {scheduler_id}. Please make sure the app exists in the webapp."
                )
            app_name = snap_apps[0].get("app_name")
            app_data = {"app_name": app_name}
            if snap_apps[0].get("ios_app_id") is not None:
                ios_app_id = snap_apps[0].get("ios_app_id")
                app_data["ios_app_id"] = ios_app_id
            if snap_apps[0].get("android_app_url") is not None:
                android_app_url = snap_apps[0].get("android_app_url")
                app_data["android_app_url"] = android_app_url
            if (
                snap_apps[0].get("ios_app_id") is None
                and snap_apps[0].get("android_app_url") is None
            ):
                raise RuntimeError(
                    f"The app with id {app_id} and name {app_name} has no iOs id and no Android URL, please add at least one of these in the web app before scheduling."
                )
            if snap_apps[0].get("android_app_url") is None:
                icon_url = snap_apps[0].get("icon_url")
                icon_media_id = self.upload_app_icon(adaccount_id, icon_url)
                SnapApps.objects.filter(id=app_id).update(
                    icon_media_id=icon_media_id, updated_at=dt.now()
                )
                self.debugPrint("App icon uploaded")
            else:
                icon_media_id = snap_apps[0].get("icon_media_id")
            app_data["icon_media_id"] = icon_media_id
        else:
            app_data = None

        try:
            creative_type = SnapchatCreativeTypeMap[objective]
        except Exception:
            raise RuntimeError(
                f"The objective {objective} was not found. Please try another option or add {objective} to SnapchatCreativeTypeMap in Snapchat_api_handler.py if you want to use it."
            )
        try:
            call_to_action = SnapchatCallToActionMap[creative_type]
        except Exception:
            raise RuntimeError(
                f"The creative type {creative_type} was not found. Please add it to SnapchatCallToActionMap in Snapchat_api_handler.py if you want to use it."
            )

        ad_creatives_ids = AdCreativeIds.objects.filter(
            uploadsesid=uploadSesId,
            scheduler_id=scheduler_id,
            ad_platform=PlatFormType.SNAPCHAT,
        ).values("creative_id", "landingpage_url")
        creative_ids = []
        for vid in ad_creatives_ids:
            if vid.get("creative_id") is None:
                raise RuntimeError(
                    "Video should be uploaded before scheduling a creative with that video"
                )
            else:
                creative_ids.append(
                    self.schedule_single_creative(
                        adaccount_id=adaccount_id,
                        video_id=vid.get("creative_id"),
                        name="BrandName",
                        headline=headline,
                        creative_type=creative_type,
                        call_to_action=call_to_action,
                        link_url=vid.get("landingpage_url"),
                        app_data=app_data,
                        # profile_id=profile_id,
                    )
                )
        return creative_ids

    def schedule_ad(self, scheduler_id, adset_id, name, creative, objective):
        """ "
        Schedule a single ad with the given data. Make sure the parameters are in the form Snap expects
        """
        ad = [
            {
                "ad_squad_id": adset_id,
                "creative_id": creative,
                "name": name,
                "status": "ACTIVE",
            }
        ]

        # NOTE: difference between App_installs (with 's') and APP_INSTALL (without 's') is correct
        ad[0]["type"] = (
            "APP_INSTALL" if objective == "App_installs" else "REMOTE_WEBPAGE"
        )
        response = self.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adsquads/{adset_id}/ads",
            params={
                "ads": ad,
            },
        )
        if not (
            "request_status" in response
            and response.get("request_status") == "SUCCESS"
            and "ads" in response
            and "sub_request_status" in response.get("ads")[0]
            and response.get("ads")[0].get("sub_request_status") == "SUCCESS"
        ):
            raise RuntimeError(
                f"Something went wrong while scheduling an ad. Original response: {response}"
            )

    def delete_adset(self, adset_id):
        """
        Delete adset with the given id
        """
        res = self.delete(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adsquads/{adset_id}", params={}
        )
        if (
            "request_status" in res
            and res.get("request_status") == "ERROR"
            or "request_status" not in res
        ):
            raise RuntimeError(res)

    def delete_campaign_id(self, campaign_id):
        """
        Delete a campaign that was not correctly completed during scheduling
        """
        result = self.check_campaign_api_status(campaign_id)
        if result == "New":
            try:
                res = self.delete(
                    url=f"{url_hp.SNAPCHAT_v1_URL}/campaigns/{campaign_id}", params={}
                )
                if (
                    "request_status" in res
                    and res["request_status"] == "ERROR"
                    or "request_status" not in res
                ):
                    raise RuntimeError(res)
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

    def schedule_adsets_country(self, scheduler_id, country, language_string):
        campaign_id = self.get_schedule_value(scheduler_id, "campaign_id")
        campaign_name = self.get_schedule_value(scheduler_id, "campaign_name")
        schedule_landingpage_url = self.get_schedule_value(
            scheduler_id, "landingpage_url"
        )
        schedule_datetime = self.get_schedule_value(scheduler_id, "scheduled_for")
        bid = self.get_schedule_value(scheduler_id, "bid")
        budget = self.get_schedule_budget()
        ignore_until = self.get_schedule_value(scheduler_id, "ignore_until")
        objective = self.get_schedule_value(scheduler_id, "objective")
        strategy = self.get_schedule_value(scheduler_id, "strategy")
        max_budget = self.get_schedule_value(scheduler_id, "max_budget")
        adaccount_id = self.get_schedule_value(scheduler_id, "adaccount_id")
        scraper_group_id = self.get_schedule_value(scheduler_id, "scraper_group_id")
        uploadSesId = self.get_schedule_value(scheduler_id, "uploadsesid")
        try:
            if campaign_id is None:
                if campaign_name is None:
                    campaign_name = self.create_campaign_name(scheduler_id)
                campaign_id = self.create_new_campaign(
                    adaccount_id=adaccount_id,
                    campaign_name=campaign_name,
                    scheduled_for=schedule_datetime,
                    objective=objective,
                    scraper_group_id=scraper_group_id,
                )
                AdScheduler.objects.filter(id=scheduler_id).update(
                    campaign_id=campaign_id,
                    campaign_name=campaign_name,
                    updated_at=dt.now(),
                )
        except Exception as e:
            raise RuntimeError(
                "Could not create new campaign. Original error: \n" + str(e)
            )
        res = AdCampaigns.objects.filter(
            campaign_id=campaign_id, ad_platform=PlatFormType.SNAPCHAT
        ).values("objective")
        if len(res) == 0:
            raise RuntimeError("Campaign not found in DB")
        else:
            campaign_objective = res[0].get("objective")
        if campaign_objective != objective:
            raise RuntimeError(
                f"Campaign objective ({campaign_objective}) and and adset objective ({objective}) do not match. Please make sure these match when scheduling."
            )

        try:
            newSet = self.schedule_single_adset(
                scheduler_id, campaign_id, country, language_string
            )
            self.debugPrint("Adset created")
        except Exception as e:
            raise RuntimeError(
                "Could not create new ad group. Original error: \n" + str(e)
            )
        try:
            creatives = self.schedule_creatives(scheduler_id)
        except Exception as e:
            raise RuntimeError(
                "Could not create new ad creative. Original error: \n" + str(e)
            )
        for i, cr in enumerate(creatives, start=1):
            try:
                name = "["
                for c in country:
                    name += f"{c}, "
                name = f"{name[:-2]}]"
                name += f" {i}"
                self.schedule_ad(scheduler_id, newSet, name, cr, objective)
                self.debugPrint("Ad created")
            except Exception as e:
                try:
                    self.delete_adset(newSet)
                    self.debugPrint("ERROR WHILE SCHEDULING. Adset deleted")
                except Exception as ex:
                    raise RuntimeError(
                        f"Could not create new ad. Original error: \n{str(e)}\n\nThe adset could not be deleted, please do so manually. Original error: {str(ex)}"
                    )
                raise RuntimeError(
                    "Could not create new ad. Original error: \n" + str(e)
                )
        adSetName = self.create_adset_name(scheduler_id, country)
        maturity = "New" if bid is None else "Test"
        budget = budget or self.get_schedule_budget()
        countries = ",".join(country)
        ad_set_obj = AdAdsets.objects.create(
            ad_platform=PlatFormType.SNAPCHAT,
            campaign_id=campaign_id,
            adset_id=newSet,
            adset_name=adSetName,
            target_country=countries,
            landingpage=schedule_landingpage_url,
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
        AdCreativeIds.objects.filter(
            uploadsesid=uploadSesId,
            scheduler_id=scheduler_id,
            ad_platform=PlatFormType.SNAPCHAT,
        ).update(ad_adset=ad_set_obj, updated_at=dt.now())

    def schedule_adsets(self, scheduler_id):
        """
        Schedule adsets with the given scheduler_id
        """
        schedule_countries = self.get_schedule_value(scheduler_id, "countries").split(
            ","
        )
        bundle_countries = self.get_schedule_value(scheduler_id, "bundle_countries")
        language = self.get_schedule_value(scheduler_id, "language")
        if bundle_countries:
            language_string = self.get_langauge(
                scheduler_id, schedule_countries, bundle_countries, language
            )
            self.schedule_adsets_country(
                scheduler_id, schedule_countries, language_string
            )
        else:
            for country in schedule_countries:
                language_string = self.get_langauge(
                    scheduler_id, country, bundle_countries, language
                )
                self.schedule_adsets_country(scheduler_id, [country], language_string)

    def get_langauge(self, scheduler_id, schedule_countries, bundle_country, language):
        language_list = None
        if language:
            try:
                if bundle_country:
                    language_list = Language.objects.get(
                        ad_scheduler_id=scheduler_id
                    ).language_string
                else:
                    language_list = Language.objects.get(
                        ad_scheduler_id=scheduler_id, country_code=schedule_countries
                    ).language_string
            except Language.DoesNotExist:
                self.debugPrint(
                    f"[scheduler] No language_string found for scheduler_id {scheduler_id}"
                )
                return language_list
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

    def get_autogenerate_campaign_data(self):
        return (
            AdScheduler.objects.filter(
                platform=PlatFormType.SNAPCHAT, completed="No", campaign_id=None
            )
            .exclude(landingpage_url=None)
            .values_list(
                "id",
                "campaign_id",
                "scraper_group_id",
                "campaign_name",
                "adaccount_id",
                "scheduled_for",
                "objective",
            )
        )

    def scheduler(self, ad_scheduler_data_all):
        """
        Schedule all new ads found in the ad_scheduler table in the DB.
        """
        try:
            # check_for_campaign = self.get_autogenerate_campaign_data()
            self.add_new_campaign(ad_scheduler_data_all)
        except Exception as e:
            self.debugPrint(f"[Scheduler] Could not create new campaign {str(e)}")

        to_schedule = self.order_upload_sessions(ad_scheduler_data_all)
        i = 0
        for schedule in to_schedule:
            i += 1
            self.debugPrint(f"Scheduling {i} of {len(to_schedule)}")
            # Skip when no landingpage is found, this will be added later and will be scheduled then.
            if schedule[0][2] is None:
                continue
            for sched in schedule:
                scheduler_id = sched[0]
                check_vars = ("Yes", scheduler_id)
                try:
                    self.upload_creatives(scheduler_id)
                    self.schedule_adsets(scheduler_id)
                except Exception as e:
                    self.handleError(
                        "[Scheduler] Campaign could not be scheduled.",
                        f"We could not schedule the campaign for schedule session: {scheduler_id}. Please see below for the error and try to fix the issue. The original error:\n{str(e)}",
                        "High",
                        scheduler_id,
                    )
                    check_vars = ("Error", scheduler_id)
                    campaign_id = self.get_schedule_value(scheduler_id, "campaign_id")
                    result = self.check_campaign_api_status(campaign_id)
                    if result == "New":
                        self.debugPrint(
                            f"[Scheduler] This is a new campaign {campaign_id} delete process start."
                        )
                        self.delete_campaign_id(campaign_id)
                        AdScheduler.objects.filter(id=scheduler_id).update(
                            campaign_id=None, updated_at=dt.now()
                        )
                AdScheduler.objects.filter(id=scheduler_id).update(
                    completed=check_vars[0], updated_at=dt.now()
                )
                if check_vars[0] == "Yes":
                    campaign_id = self.get_schedule_value(scheduler_id, "campaign_id")
                    result = self.check_campaign_api_status(campaign_id)
                    if result == "New":
                        AdCampaigns.objects.filter(campaign_id=campaign_id).update(
                            api_status="Old", updated_at=dt.now()
                        )
        if i >= 0:
            self.debugPrint("Done scheduling")

    def add_new_campaign(self, ad_scheduler_data_all):
        for scheduler_index in range(len(ad_scheduler_data_all)):
            id_scheduler = ad_scheduler_data_all[scheduler_index][0]
            campaign_id = ad_scheduler_data_all[scheduler_index][3]
            campaign_name = ad_scheduler_data_all[scheduler_index][4]
            adaccount_id = ad_scheduler_data_all[scheduler_index][5]
            scheduled_for = ad_scheduler_data_all[scheduler_index][6]
            objective = ad_scheduler_data_all[scheduler_index][7]
            scraper_group_id = ad_scheduler_data_all[scheduler_index][8]

            if campaign_id in [None, ""]:
                if campaign_name is None:
                    campaign_name = self.create_campaign_name(id_scheduler)
                response = self.create_new_campaign(
                    adaccount_id=adaccount_id,
                    campaign_name=campaign_name,
                    scheduled_for=scheduled_for,
                    objective=objective,
                    scraper_group_id=scraper_group_id,
                )
                new_campaign_id = response
                AdScheduler.objects.filter(id=id_scheduler).update(
                    campaign_id=new_campaign_id,
                    campaign_name=campaign_name,
                    updated_at=dt.now(),
                )

    def create_campaign_name(self, scheduler_id):
        """ "
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

    objective_map_reversed = {v: k for k, v in SnapchatObjectiveMap.items()}

    def create_new_campaign(
        self, adaccount_id, campaign_name, scheduled_for, objective, scraper_group_id
    ):
        schedule_datetime = self.formatDateSchedule(scheduled_for)
        objective_type = self.objective_map_reversed.get(objective)
        response = self.post(
            url=f"{url_hp.SNAPCHAT_v1_URL}/adaccounts/{adaccount_id}/campaigns",
            params={
                "campaigns": [
                    {
                        "name": campaign_name,
                        "ad_account_id": adaccount_id,
                        "status": "ACTIVE",
                        "start_time": schedule_datetime,
                        "objective": objective_type,
                    }
                ]
            },
        )
        if response.get("request_status") == "SUCCESS":
            new_campaign_id = response.get("campaigns")[0].get("campaign").get("id")
            try:
                AdCampaigns.objects.create(
                    ad_platform=PlatFormType.SNAPCHAT,
                    advertiserid=adaccount_id,
                    campaign_id=new_campaign_id,
                    campaign_name=campaign_name,
                    active="Yes",
                    objective=objective,
                    api_status="New",
                    scraper_group_id=scraper_group_id,
                )
            except Exception as e:
                self.debugPrint("Campaigns not uploaded in db")
                self.handleError(
                    "[Scheduler Campaign insert] Campaign could not be inserted.",
                    f"We could not inserted the campaign for adaccount_id : {adaccount_id}. Please see below for the error and try to fix the issue. The original error:\n{str(e)}",
                    "High",
                )
            return new_campaign_id
        else:
            raise RuntimeError(f"An error occured: {response}")

    def initializing_bussiness_adaccounts(self):
        """
        fetch live data for snap organizations and ad_account , then all stuff push to database
        """
        if self.access_token:
            response = self.get(
                url=url_hp.SNAPCHAT_ORGANIZATIONS_WITH_AD_ACCOUNTS_URL, params={}
            )
            if organizations := response.get("organizations"):
                for data in organizations:
                    organization_id = data.get("organization").get("id")
                    organization_name = data.get("organization").get("name")
                    business, _ = Business.objects.update_or_create(
                        organization_id=organization_id,
                        defaults={"profile": self.profile, "name": organization_name},
                    )

                    if available_ad_accounts := data.get("organization").get(
                        "ad_accounts"
                    ):
                        for account in available_ad_accounts:
                            AdAccount.objects.update_or_create(
                                account_id=account.get("id"),
                                defaults={
                                    "account_name": account.get("name"),
                                    "live_ad_account_status": account.get("status"),
                                    "profile": self.profile,
                                    "business": business,
                                    "timezone": account.get("timezone"),
                                    "currency": account.get("currency"),
                                },
                            )
                    else:
                        self.handleError(
                            reason=f"Snap ad accounts were not found for this profile_id:{self.profile.id}.",
                            message=response,
                        )
            else:
                self.handleError(
                    reason=f"Snap organization were not found for this profile_id:{self.profile.id}.",
                    message=response,
                )
