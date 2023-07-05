from apps.linkfire.models import ScrapeLinkfires, LinkfireData, LinkfireDataServices
from apps.common.models import AdCreativeIds
from apps.error_notifications.models import NotificationLogs
from apps.scraper.models import Settings
import requests
from apps.common.custom_exception import (
    LinkfireApiResponseCodeException,
)
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Q, F
import json
import os
from SF import settings
from apps.common.constants import Timeformat, StatusType
from apps.common.urls_helper import URLHelper

url_hp = URLHelper()


class LinkfireScraper:
    def __init__(self, proifile) -> None:
        self.user = proifile
        self.is_still_authorized = False
        self.authkey = ""
        self.updatevariables()
        self.generate_new_access_token()
        self.page = 0
        self.exportlinkfiredata = []
        self.exportlinkfireservicesdata = []
        self.header = {
            "Content-Type": "application/json",
            "Authorization": self.authkey,
        }

    def handleerror(self, reason, message):
        """
        Puts an error message in database
        Parameters reason, message (String, String)
        Returns: None
        """
        notification = {
            "reason": f"[{reason}] linkfire scraper API",
            "text_body": message,
        }
        NotificationLogs.objects.create(
            type_notification=reason,
            notification_data=notification,
            notification_sent="No",
        )

    def generate_new_access_token(self):
        if not self.is_still_authorized:
            headers = {"content-type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "password",
                "username": self.user["linkfire_username"],
                "password": self.user["linkfire_password"],
                "client_id": "linkfire.js",
                "client_secret": "secretkeyforLinkfire",
                "scope": "linkfire offline_access",
            }
            response = requests.request(
                "POST",
                url_hp.LINKFIRE_SCRAPER_TOKEN_URL,
                headers=headers,
                data=data,
            )
            if response.status_code == 200:
                data = response.json()
                token = data["access_token"]
                access_token = f"Bearer {token}"
                self.is_still_authorized = True
                self.authkey = access_token
                return self.authkey
            else:
                self.is_still_authorized = False
                self.handleerror(
                    "[LinkfireScraper access_token] Could not generate access_token",
                    repr(response.json()),
                )
                raise LinkfireApiResponseCodeException(
                    f"Could not get new LinkfireScraper acces_token from api{str(response.json())}"
                )
        else:
            return self.authkey

    def get_board_id(self):
        headers = self.header
        response = requests.request(
            "GET",
            url_hp.LINKFIRE_SCRAPER_BOARDS_URL,
            headers=headers,
        )
        status_code = response.status_code
        if status_code in [403, 401, 400]:
            self.is_still_authorized = False
            self.generate_new_access_token()
            self.get_board_id()
        elif status_code == 200:
            json_response = response.json()
            board_id = json_response["data"][0]["id"]
            return board_id
        else:
            self.handleerror(
                "[LinkfireScraper board_id] Could not get board_id",
                repr(response.json()),
            )
            return None

    def get_linkid(self, shorttag, board_id):
        headers = self.header
        params = {
            "page[number]": self.page,
            "boardId": board_id,
            "filter[query]": shorttag,
        }
        url = f"{url_hp.LINKFIRE_SCRAPER_BASE_URL}link/boards/{board_id}/links/search"
        response = requests.request("GET", url, headers=headers, params=params)
        status_code = response.status_code
        if status_code in [403, 401, 400]:
            self.is_still_authorized = False
            self.generate_new_access_token()
            self.get_linkid(shorttag, board_id)
        elif status_code == 200:
            json_response = response.json()
            for data in json_response["included"]:
                if data.get("attributes", {}).get("code") == shorttag:
                    linkid = data["id"]
                    return linkid
            if "next" in json_response["links"] and json_response["links"]["next"]:
                self.page += 1
                self.get_linkid(shorttag, board_id)
            else:
                self.page = 0
                return None
        else:
            self.handleerror(
                f"[LinkfireScraper linkid] Could not get linkid for shorttag {shorttag}",
                repr(response.json()),
            )
            return None

    def insights_shorttag(self, board_id, link_id):
        headers = self.header
        params = {
            "boardId": board_id,
        }
        url = f"{url_hp.LINKFIRE_SCRAPER_BASE_URL}link/links/{link_id}"
        response = requests.request("GET", url, headers=headers, params=params)
        status_code = response.status_code
        if status_code in [403, 401, 400]:
            self.is_still_authorized = False
            self.generate_new_access_token()
            self.insights_shorttag(board_id, link_id)
        elif status_code == 200:
            json_response = response.json()
            shorttag_insights = json_response["data"]["attributes"]["name"]
            return shorttag_insights
        else:
            self.handleerror(
                f"[LinkfireScraper insights_shorttag] Could not get insights_shorttag for link_id {link_id}",
                repr(response.json()),
            )
            return None

    def checklinkstoscrape(self):
        """
        First check what linkfires are active according to ad_adsets.
        """
        ScrapeLinkfires.objects.update(is_active=StatusType.NO)
        list_landingpage = (
            AdCreativeIds.objects.filter(
                ad_adset__active="Yes",
                landingpage_url__isnull=False,
                landingpage_url__contains="lnk.to",
            )
            .values_list("landingpage_url", flat=True)
            .distinct()
        )
        ScrapeLinkfires.objects.filter(url__in=list_landingpage).update(
            is_active=StatusType.YES
        )
        last_scraped_interval = datetime.now() - relativedelta(
            hours=int(self.linkfire_scrape_interval)
        )
        response = (
            ScrapeLinkfires.objects.filter(
                Q(is_active=StatusType.YES)
                & (
                    Q(last_scraped__isnull=True)
                    | Q(last_scraped__lte=last_scraped_interval)
                )
            )
            .values_list("shorttag", "id", "insights_shorttag", "board_id", "link_id")
            .order_by("-id")
        )
        return response

    def updatevariables(self):
        response = Settings.objects.all().values_list("variable", "value")

        if not response:
            raise Exception("Please update the variables in the web app")
        self.linkfire_scrape_interval = dict(response).get("linkfire_scrape_interval")
        self.exportlinkfiredata = []
        self.exportlinkfireservicesdata = []
        return settings

    def setlookuplink(self, linkfireurl):
        self.linkfireurl = linkfireurl
        if self.linkfireurl == "":
            # Set inactive and skip
            self.setstatuslinkfire(linkfireurl, StatusType.NO)
            return False
        # Add to database
        today = datetime.now()
        todaydb = today.strftime(Timeformat.ISO8601)
        ScrapeLinkfires.objects.filter(shorttag=self.linkfireurl).update(
            scraped=F("scraped") + 1, last_scraped=todaydb
        )
        return True

    def setstatuslinkfire(self, shorttag, active):
        """
        Function that sets a linkfire status to either active Yes or No based on shorttag
        :param shorttag: corresponds with shorttag in scrape_linkfires
        :param active: Yes/No
        :return: success status
        """
        ScrapeLinkfires.objects.filter(shorttag=shorttag).update(is_active=active)

    def checkexistingdata(self):
        # For every date from now until -7 days, check if we have in database
        datesmissing = []
        for i in range(8):
            today = datetime.now()
            todaystrf = today.strftime(Timeformat.ISO8601DATEFORMAT)
            goback = today - timedelta(i)
            dateto = goback.strftime(Timeformat.ISO8601DATEFORMAT)
            datedb = goback.strftime(Timeformat.ISO8601DAYEND)
            # First check if date to check is today, if so, insert new values because we need every new info every hour or so
            # Only if today != dateto meaning we are looking days in the past: Insert only if there exists no date & tag for this entry
            if todaystrf != dateto:
                # First check if data is already in table, if so, skip this cycle

                scrape_linkfire_list = ScrapeLinkfires.objects.filter(
                    shorttag=self.linkfireurl
                ).values_list("id", flat=True)
                response = LinkfireData.objects.filter(
                    date=datedb, linkfire_id__in=scrape_linkfire_list
                ).values("id")

                if len(response) > 0:
                    # Skip, why? Because this is data not from today and so will not be updated by linkfire, it is past
                    continue
            else:
                # Get latest time from today, if it was less then 1 hr, skip
                last_scraped_interval = datetime.now() - relativedelta(hours=1)
                scrape_linkfire_list = ScrapeLinkfires.objects.filter(
                    shorttag=self.linkfireurl
                ).values_list("id", flat=True)
                response = LinkfireData.objects.filter(
                    date__gte=last_scraped_interval,
                    linkfire_id__in=scrape_linkfire_list,
                ).values("id")

                if len(response) > 0:
                    continue
            datesmissing.append(goback)
        return datesmissing

    def getlocationsdata(
        self, datefrom, dateto, linkfire_id, datedb, board_id, link_id
    ):
        datedbd = datedb
        today = datetime.now()
        today = today.strftime(Timeformat.ISO8601DATEFORMAT)
        headers = self.header
        params = {
            "filter[start]": f"{datefrom}{Timeformat.TIMEZONEDESIGNATOR_START}",
            "filter[end]": f"{dateto}{Timeformat.TIMEZONEDESIGNATOR_END}",
            "page[number]": self.page,
        }
        url = f"{url_hp.LINKFIRE_SCRAPER_BASE_URL}insights/boards/{board_id}/links/{link_id}/countries"
        response = requests.request("GET", url, headers=headers, params=params)
        status_code = response.status_code
        if status_code in [403, 401, 400]:
            self.is_still_authorized = False
            self.generate_new_access_token()
            self.getlocationsdata(
                datefrom, dateto, linkfire_id, datedb, board_id, link_id
            )

        elif status_code == 200:
            json_response = response.json()
            for data in json_response["data"]:
                countrycode = data["attributes"]["isoCode"]
                countryname = self.getcountryname(countrycode)
                visits = data["attributes"]["visits"]
                ctr = data["attributes"]["clickThroughsToVisitsRate"]
                if datefrom != today:
                    datedbd = datedb.strftime(Timeformat.ISO8601DAYEND)
                if visits != 0:
                    self.exportlinkfiredata.append(
                        (linkfire_id, datedbd, countryname, countrycode, visits, ctr)
                    )

            if "next" in json_response["links"]:
                self.page += 1
                self.getlocationsdata(
                    datefrom, dateto, linkfire_id, datedb, board_id, link_id
                )
            else:
                self.page = 0
                self.insertscraperdatabase(
                    self.exportlinkfiredata, table="linkfire_data"
                )
        else:
            self.handleerror(
                "[LinkfireScraper getlocationsdata] Could not get locationsdata",
                repr(response.json()),
            )
            self.page = 0

    def getservicesdata(self, datefrom, dateto, linkfire_id, datedb, board_id, link_id):
        datedbd = datedb
        today = datetime.now()
        today = today.strftime(Timeformat.ISO8601DATEFORMAT)
        headers = self.header
        params = {
            "filter[start]": f"{datefrom}{Timeformat.TIMEZONEDESIGNATOR_START}",
            "filter[end]": f"{dateto}{Timeformat.TIMEZONEDESIGNATOR_END}",
            "page[number]": self.page,
        }
        url = f"{url_hp.LINKFIRE_SCRAPER_BASE_URL}insights/boards/{board_id}/links/{link_id}/services"
        response = requests.request("GET", url, headers=headers, params=params)
        status_code = response.status_code
        if status_code in [403, 401, 400]:
            self.is_still_authorized = False
            self.generate_new_access_token()
            self.getservicesdata(
                datefrom, dateto, linkfire_id, datedb, board_id, link_id
            )

        elif status_code == 200:
            json_response = response.json()
            for data in json_response["data"]:
                servicename = data["attributes"]["serviceTitle"]
                visits = data["attributes"]["clickThroughs"]
                if datefrom != today:
                    datedbd = datedb.strftime(Timeformat.ISO8601DAYEND)
                if visits != 0:
                    self.exportlinkfireservicesdata.append(
                        (linkfire_id, datedbd, servicename, visits)
                    )

            if "next" in json_response["links"]:
                self.page += 1
                self.getservicesdata(
                    datefrom, dateto, linkfire_id, datedb, board_id, link_id
                )
            else:
                self.page = 0
                self.insertscraperdatabase(
                    self.exportlinkfireservicesdata, table="linkfire_data_services"
                )

        else:
            self.handleerror(
                "[LinkfireScraper getlocationsdata] Could not get locationsdata",
                repr(response.json()),
            )
            self.page = 0

    def insertscraperdatabase(self, insertvaluesdb, table):
        if table == "linkfire_data":
            LinkfireData.objects.bulk_create(
                [
                    LinkfireData(
                        linkfire_id=values[0],
                        date=values[1],
                        country=values[2],
                        country_code=values[3],
                        visits=values[4],
                        ctr=values[5],
                    )
                    for values in insertvaluesdb
                ]
            )
            self.exportlinkfiredata = []
        elif table == "linkfire_data_services":
            LinkfireDataServices.objects.bulk_create(
                [
                    LinkfireDataServices(
                        linkfire_id=values[0],
                        date=values[1],
                        mediaservice=values[2],
                        visits=values[3],
                    )
                    for values in insertvaluesdb
                ]
            )
            self.exportlinkfireservicesdata = []
        else:
            pass

    def getcountryname(self, country_code):
        with open(
            os.path.join(
                settings.BASE_DIR,
                "apps/common/json/country_codes.json",
            )
        ) as f:
            my_dict = json.load(f)
        f.close()
        for x in my_dict:
            if x["Name"] == country_code or x["Code"] == country_code:
                return x["Name"]
        return False
