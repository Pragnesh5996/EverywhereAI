import requests
import re
import json
import datetime
import time
from apps.linkfire.models import (
    LinkfireBoards,
    LinkfireGeneratedLinks,
    LinkfireLinkSettings,
    LinkfireMediaservices,
    LinkfireUrl,
)
from apps.common.models import (
    AdScheduler,
    Authkey,
    Profile,
    AdCreativeIds,
)
from django.db.models import Q
from apps.common.constants import PlatFormType, StatusType
from apps.error_notifications.models import NotificationLogs
from apps.common.custom_exception import (
    DatabaseRequestException,
    LinkfireApiResponseCodeException,
    LinkfireApiAccesTokenException,
    LinkfireTooLargeNameException,
)
from apps.common.urls_helper import URLHelper

url_hp = URLHelper()


class LinkfireApi:
    def __init__(self, debug_mode):
        """
        Populates auth key and checks if this key is still valid
        Parameters:
        string: Database connection
        """
        self.generated = False
        self.debug = debug_mode
        self.mediaservices_list = []
        self.page = 0
        self.client_secret = self.get_client_secret()
        self.access_token = self.get_authkey()
        self.header = {
            "Api-Version": "v1.0",
            "Content-Type": "application/json",
            "Authorization": self.access_token,
        }
        is_still_authorized = self.is_authorized()
        if is_still_authorized is False:
            self.debugprint(
                "[Init] access_token is outdated, attempting to generate new token..."
            )
            if not self.generated:
                self.access_token = self.generate_new_access_token()
                is_still_authorized = self.is_authorized()
                if is_still_authorized is False:
                    raise LinkfireApiAccesTokenException(
                        "Could not generate and/or authorize access_token."
                    )
                else:
                    self.debugprint("[access_token] verified.")
            else:
                raise LinkfireApiAccesTokenException(
                    "Could not generate and/or authorize access_token."
                )
        else:
            self.debugprint("[access_token] verified.")
        self.generated = False
        self.board_id = self.get_board_id_database()
        if not self.verify_board_id():
            if not self.generated:
                self.debugprint(
                    "[board_id] Could not verify board id, attempting to get new one from api."
                )
                self.board_id = self.get_board_id_api()
                if not self.verify_board_id():
                    raise LinkfireApiAccesTokenException("could not verify board_id")
                else:
                    self.debugprint("[board_id] verified.")
        else:
            self.debugprint("[board_id] verified.")

    def debugprint(self, message):
        if self.debug:
            print(message)

    def handleerror(self, reason, message):
        """
        Puts an error message in database
        Parameters reason, message (String, String)
        Returns: None
        """
        subject = f"[{reason}] linkfire API."
        notification = '{"reason":' + subject + ', "text_body":' + message + "}"
        NotificationLogs.objects.create(
            type_notification=reason,
            notification_data=notification,
            notification_sent="No",
        )

    def get_client_secret(self):
        response = Authkey.objects.filter(
            profile__ad_platform=PlatFormType.LINKFIRE,
            profile__is_active=StatusType.YES,
        ).values_list("access_token", flat=True)

        if not response or not response[0]:
            message = "Could not find client secret, please add it manually to database. Exiting..."
            self.debugprint(message)
            raise LinkfireApiAccesTokenException(
                "Could not fetch client secret from database."
            )
        return response[0]

    def get_authkey(self):
        response = Authkey.objects.filter(
            profile__ad_platform=PlatFormType.LINKFIRE,
            profile__is_active=StatusType.YES,
        ).values_list("refresh_token", flat=True)
        try:
            if not response or not response[0]:
                self.debugprint(
                    "No authorization key was found for Linkfire in database. Attempting to generate new one."
                )
                return self.generate_new_access_token()
        except Exception as e:
            raise LinkfireApiAccesTokenException(
                "Could not find any values for 'Linkfire' in database. Full error: "
                + str(e)
            )
        return response[0]

    def is_authorized(self):
        if not self.access_token:
            return False
        headers = self.header
        parameters = {}
        response = self.get(url_hp.LINKFIRE_BOARDS_URL, headers, parameters)
        status_code = response["status_code"]
        if status_code == 200:
            return True
        elif status_code == 401:
            return False
        raise LinkfireApiAccesTokenException(
            f"unexpected API response. Got {response.status_code}"
        )

    def generate_new_access_token(self):
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": "Strange_Fruits_API",
            "scope": "public.api",
            "client_secret": self.client_secret,
        }
        response = requests.request(
            "POST",
            url_hp.LINKFIRE_CONNECT_URL,
            headers=headers,
            data=data,
        )
        status_code = response.status_code
        if status_code == 200:
            r = response.json()
            access_token = f"{r.get('token_type')} {r.get('access_token')}"
            Authkey.objects.filter(
                profile__ad_platform=PlatFormType.LINKFIRE,
                profile__is_active=StatusType.YES,
            ).update(refresh_token=access_token, updated_at=datetime.datetime.now())
            self.generated = True
            return access_token
        raise LinkfireApiResponseCodeException(
            f"Could not get new acces_token from api{str(response)}"
        )

    def get_board_id_api(self):
        headers = self.header
        parameters = {}
        response = self.get(url_hp.LINKFIRE_BOARDS_URL, headers, parameters)
        status_code = response["status_code"]
        if status_code == 200:
            r = response.json()
            board_data = r.get("data")
            if board_data and len(board_data) == 1:
                name = board_data[0].get("name")
                board_id = board_data[0].get("id")
                profile = Profile.objects.filter(
                    ad_platform=PlatFormType.LINKFIRE, is_active=StatusType.YES
                ).first()
                linkfire_bord, created = LinkfireBoards.objects.get_or_create(
                    board_id=board_id
                )
                linkfire_bord.name = name
                linkfire_bord.profile = profile
                linkfire_bord.save()
                return board_id
        else:
            raise LinkfireApiAccesTokenException(
                "Could not get board_id from api " + str(response.__dict__)
            )

    def get_board_id_database(self):
        response = LinkfireBoards.objects.filter(
            profile__is_active=StatusType.YES
        ).values_list("board_id", flat=True)
        try:
            if not response or not response[0]:
                return self.get_board_id_api()
        except Exception as e:
            raise LinkfireApiAccesTokenException(
                "Could not find any values for 'Linkfire' in database. Full error: "
                + str(e)
            )
        return response[0]

    def verify_board_id(self):
        if not self.board_id:
            return False
        headers = self.header
        parameters = {}
        url = self.createlink(url_hp.LINKFIRE_BASE_URL, "/domains")
        response = self.get(url, headers, parameters)
        status_code = response["status_code"]
        if status_code == 200:
            return True
        elif status_code == 401:
            return False
        raise Exception(f"unexpected API response. Got {response.status_code}")

    def createlink(self, base, extension):
        return base + self.board_id + extension

    def createcampaignlink(self, base, extension, linkid, extension2):
        return base + self.board_id + extension + linkid + extension2

    def get(self, url, headers, data=None):
        response = requests.request("GET", url, headers=headers, data=data)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[4[0-9]1\]>")
        if re.search(pattern, str(response)):
            if response.__dict__["reason"] == "Unauthorized":
                try:
                    self.debugprint(
                        "[GET] Authorization failed, attempting to generate new key and retry."
                    )
                    self.access_token = self.generate_new_access_token()
                    headers["Authorization"] = self.access_token
                except Exception as e:
                    raise LinkfireApiAccesTokenException(str(e))
                response = requests.request("GET", url, headers=headers, data=data)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[2[0-9][0-9]\]>")
        if re.search(pattern, str(response)):
            return response.__dict__
        raise LinkfireApiResponseCodeException(response.__dict__)

    def post(self, url, headers, data=None):
        response = requests.request("POST", url, headers=headers, data=data)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[4[0-9]1\]>")
        if re.search(pattern, str(response)):
            if response.__dict__["reason"] == "Unauthorized":
                try:
                    self.debugprint(
                        "[POST] Authorization failed, attempting to generate new key and retry."
                    )
                    self.access_token = self.generate_new_access_token()
                    headers["Authorization"] = self.access_token
                except Exception as e:
                    raise LinkfireApiAccesTokenException(str(e))
                response = requests.request("POST", url, headers=headers, data=data)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[2[0-9][0-9]\]>")
        if re.search(pattern, str(response)):
            return response.__dict__
        raise LinkfireApiResponseCodeException(response.__dict__)

    def put(self, url, headers, data=None):
        response = requests.request("PUT", url, headers=headers, data=data)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[4[0-9]1\]>")
        if re.search(pattern, str(response)):
            if response.__dict__["reason"] == "Unauthorized":
                try:
                    self.debugprint(
                        "[PUT] Authorization failed, attempting to generate new key and retry."
                    )
                    self.access_token = self.generate_new_access_token()
                    headers["Authorization"] = self.access_token
                except Exception as e:
                    raise LinkfireApiAccesTokenException(str(e))
                response = requests.request("PUT", url, headers=headers, data=data)
        # trunk-ignore(flake8/W605)
        pattern = re.compile("<Response \[2[0-9][0-9]\]>")
        if re.search(pattern, str(response)):
            return response.__dict__
        raise LinkfireApiResponseCodeException(response.__dict__)

    def name_fallback(self, genre, n):
        self.debugprint(
            "[create_link] Warning, desync between api and DB, falling back on api based name generation."
        )
        headers = self.header
        name = ""
        num_int = n
        num = str(num_int)
        str_num = ""
        for i in range(3 - len(num)):
            str_num += "0"
        str_num += num
        genre_short = genre.lower().split("fruits")[0].strip()
        if genre_short == "strange":
            genre_short = "dance"
        if genre_short == "deep house":
            genre_short = "house"
        name = (
            str(datetime.datetime.now().strftime("%Y"))
            + genre_short
            + "w"
            + str(datetime.datetime.now().strftime("%W"))
            + "-"
            + str_num
        )
        name = name.replace(" ", "")
        name = name.lower()
        response = self.get(
            self.createlink(url_hp.LINKFIRE_CAMPAIGNS_URL, "/links?code=" + name),
            headers,
        )
        while json.loads(response["_content"].decode())["totalItemsCount"] > 0:
            num_int += 1
            if num_int > 999:
                raise LinkfireTooLargeNameException()
            num = str(num_int)
            str_num = ""
            for i in range(3 - len(num)):
                str_num += "0"
            str_num += num
            name = (
                str(datetime.datetime.now().strftime("%Y"))
                + genre_short
                + "w"
                + str(datetime.datetime.now().strftime("%W"))
                + "-"
                + str_num
            )
            name = name.replace(" ", "")
            name = name.lower()
            response = self.get(
                self.createlink(url_hp.LINKFIRE_CAMPAIGNS_URL, "/links?code=" + name),
                headers,
            )
        return name, num_int

    def generate_name(self, genre, n):
        self.debugprint("[generate name] start")
        genre_short = genre.lower().split("fruits")[0].strip()
        if genre_short == "strange":
            genre_short = "dance"
        if genre_short == "deep house":
            genre_short = "house"
        shorttitle = (
            str(datetime.datetime.now().strftime("%Y"))
            + genre_short
            + "w"
            + str(datetime.datetime.now().strftime("%W"))
            + "-"
        )
        name = ""
        num_int = n
        num = str(num_int)
        str_num = ""
        for i in range(3 - len(num)):
            str_num += "0"
        str_num += num
        name = (
            str(datetime.datetime.now().strftime("%Y"))
            + genre_short
            + "w"
            + str(datetime.datetime.now().strftime("%W"))
            + "-"
            + str_num
        )
        name = name.replace(" ", "")
        name = name.lower()
        headers = self.header
        response = self.get(
            self.createlink(url_hp.LINKFIRE_CAMPAIGNS_URL, "/links?code=" + name),
            headers,
        )
        if json.loads(response["_content"].decode())["totalItemsCount"] > 0:
            self.debugprint("[createlink] " + name + " is taken, generating new name.")
            namestaken = (
                AdCreativeIds.objects.filter(landingpage_url__contains=shorttitle)
                .values_list("landingpage_url")
                .order_by("-landingpage_url")[:1]
            )
            if len(namestaken) > 0:
                max = int(namestaken[0][0].split("-")[-1])
            else:
                return self.name_fallback(genre, n)
            if max < num_int:
                return self.name_fallback(genre, n)
        else:
            self.debugprint("[createlink] name is valid")
            return name, n
        num_int = max + 1
        num = str(num_int)
        str_num = ""
        for i in range(3 - len(num)):
            str_num += "0"
        str_num += num
        current_time = datetime.datetime.now()
        name = f"{current_time.strftime('%Y')}{genre_short}w{current_time.strftime('%W')}-{str_num}"
        return self.generate_name(genre, num_int)

    def update_database_link(self, linkid, linkstatus):
        """
        Updates status of linkfire generated by api
        """
        LinkfireGeneratedLinks.objects.filter(link_id=linkid).update(
            status=linkstatus, is_scraped="No", updated_at=datetime.datetime.now()
        )

    def add_to_database_link(
        self,
        board_id,
        linkid,
        landing_page_url,
        shorttag,
        linkfire_status,
        adscheduler_id,
        scraper_group_id,
    ):
        """
        Adds generated link to database to keep track of generated urls
        """
        board_object_id = LinkfireBoards.objects.filter(board_id=board_id).values_list(
            "id", flat=True
        )[0]
        LinkfireGeneratedLinks.objects.create(
            ad_scheduler_id=adscheduler_id,
            link_id=linkid,
            domain=landing_page_url,
            shorttag=shorttag,
            status=linkfire_status,
            linkfire_board_id=board_object_id,
            scraper_group_id=scraper_group_id,
        )

    def get_campaign(self, linkid, board_id=-1):
        """
        Returns array with data of linkfire id
        https://api.linkfire.com/campaigns/boards/{boardId}/links/{linkid}
        """
        if board_id == -1:
            # Default = self.board_id
            board_id = self.board_id
        headers = {
            "Accept": "application/json",
            "Api-Version": "v1.0",
            "Authorization": self.access_token,
        }
        return self.get(
            url_hp.LINKFIRE_CAMPAIGNS_URL + board_id + "/links/" + linkid,
            headers,
        )

    def update_campaign(self, linkid, response_get, board_id=-1):
        """
        PUT call to overwrite/update data of linkId by response_get
        https://api.linkfire.com/campaigns/boards/{boardId}/links/{linkId}
        """
        if board_id == -1:
            board_id = self.board_id
        headers = {
            "Accept": "application/json",
            "Api-Version": "v1.0",
            "Content-Type": "text/json",
            "Authorization": self.access_token,
        }
        return self.put(
            url_hp.LINKFIRE_CAMPAIGNS_URL + board_id + "/links/" + linkid,
            headers,
            response_get,
        )

    def create_campaign(
        self,
        spotify_base_url,
        service_destinations,
        service_urls,
        service_ctas,
        sortorder,
        baseurl,
        text,
        subtext,
        genre,
        artwork,
        n,
        genre_name,
    ):
        self.debugprint("[createlink] Attempting to create link")

        title, n = self.generate_name(genre_name, n)
        baseurl = spotify_base_url
        headers = self.header
        services = []
        for service_index in range(len(service_destinations)):
            url_list = []
            url_list = self.get_urls(service_destinations[service_index], genre)
            for url_index in range(len(url_list)):
                if len(services) == 0:
                    services.append(
                        {
                            "mediaServices": [
                                {
                                    "mediaServiceId": service_destinations[
                                        service_index
                                    ]["mediaServiceIds"],
                                    "url": url_list[url_index][0],
                                    "sortOrder": int(sortorder[service_index]),
                                    "enabled": False
                                    if url_list[url_index][1] != "DEFAULT"
                                    and url_list[url_index][1] != "No"
                                    else True,
                                }
                            ],
                            "title": "Listen & Follow",
                            "isoCode": url_list[url_index][1]
                            if url_list[url_index][1] != "DEFAULT"
                            and url_list[url_index][1] != "No"
                            else "all",
                            "subTitle": "Choose music service",
                            "sampleBehaviour": "PlayNothing",
                        }
                    )
                    if service_ctas[service_index] is not None:
                        services[url_index]["mediaServices"][0].update(
                            {"buttonText": service_ctas[service_index]}
                        )
                else:
                    for services_iteration_index in range(len(services)):
                        found = "No"
                        if (
                            services[services_iteration_index]["isoCode"]
                            == url_list[url_index][1]
                            if url_list[url_index][1] != "DEFAULT"
                            and url_list[url_index][1] != "No"
                            else "all"
                        ):
                            found = "Yes"
                            services[services_iteration_index]["mediaServices"].append(
                                {
                                    "mediaServiceId": service_destinations[
                                        service_index
                                    ]["mediaServiceIds"],
                                    "url": url_list[url_index][0],
                                    "sortOrder": int(sortorder[service_index]),
                                    "enabled": False
                                    if url_list[url_index][1] != "DEFAULT"
                                    and url_list[url_index][1] != "No"
                                    else True,
                                }
                            )
                            if service_ctas[service_index] is not None:
                                services[services_iteration_index]["mediaServices"][
                                    -1
                                ].update({"buttonText": service_ctas[service_index]})
                            break
                    if found == "No":
                        services.append(
                            {
                                "mediaServices": [
                                    {
                                        "mediaServiceId": service_destinations[
                                            service_index
                                        ]["mediaServiceIds"],
                                        "url": url_list[url_index][0],
                                        "sortOrder": int(sortorder[service_index]),
                                        "enabled": False
                                        if url_list[url_index][1] != "DEFAULT"
                                        and url_list[url_index][1] != "No"
                                        else True,
                                    }
                                ],
                                "title": "Listen & Follow",
                                "isoCode": url_list[url_index][1]
                                if url_list[url_index][1] != "DEFAULT"
                                and url_list[url_index][1] != "No"
                                else "all",
                                "subTitle": "Choose music service",
                                "sampleBehaviour": "PlayNothing",
                            }
                        )
                        if service_ctas[service_index] is not None:
                            services[-1]["mediaServices"][-1].update(
                                {"buttonText": service_ctas[service_index]}
                            )
        payload = json.dumps(
            {
                "title": title,
                "destination Url": "Strange_Fruits_API",
                "baseUrl": baseurl,
                "status": "Published",
                "skipSearch": True,
                "sampleBehaviour": "PlayNothing",
                "image": artwork,
                "code": title,
                "locales": services,
            }
        )
        response = []
        response = self.post(
            self.createlink(url_hp.LINKFIRE_CAMPAIGNS_URL, "/links"),
            headers,
            payload,
        )
        return response, n

    def get_urls(self, mediaserviceid, genre):
        if (
            mediaserviceid["default_url"] == "No"
            and mediaserviceid["territory_url"] == "No"
        ):
            response = LinkfireLinkSettings.objects.filter(
                Q(scraper_group_id=genre)
                & Q(mediaserviceid=mediaserviceid["mediaServiceIds"])
                & ~Q(url__exact="")
            ).values_list("url", "default_url")
            return response
        return LinkfireUrl.objects.filter(
            Q(scraper_group_id=genre)
            & Q(mediaServiceId=mediaserviceid["mediaServiceIds"])
            & ~Q(url__exact="")
        ).values_list("url", "isoCode")

    def get_scanning_status(self, campaign_id):
        headers = {
            "Api-Version": "v1.0",
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": self.access_token,
        }
        # 404 response = No scan status found. Meaning scanning was done a long time ago
        response = requests.request(
            "GET",
            url_hp.LINKFIRE_CAMPAIGNS_URL
            + self.board_id
            + "/links/"
            + campaign_id
            + "/scan/status",
            headers=headers,
        )
        if str(response) == "<Response [404]>":
            try:
                response_get = self.get_campaign(campaign_id)
                response_get = json.loads(response_get["_content"].decode())
            except Exception as e:
                self.debugprint(str(e))
                self.handleerror(
                    "[get_scanning_status] Invalid response get_campaign ", str(e)
                )
            linkstatus = response_get["data"]["status"]
            iscomplete = not response_get["data"]["isScanning"]

        else:
            response = response.__dict__
            linkstatus = json.loads(response["_content"].decode())["data"]["linkStatus"]
            iscomplete = json.loads(response["_content"].decode())["data"]["isComplete"]
        return linkstatus, iscomplete

    def get_scheduler_data(self, scheduler_id=None):
        try:
            if scheduler_id is None:
                response = (
                    AdScheduler.objects.filter(
                        landingpage_url="No",
                        objective__in=["Traffic", "Conversions"],
                    )
                    .order_by("platform")
                    .values_list("id", "scraper_group_id", "scraper_group__group_name")
                )
            else:
                response = (
                    AdScheduler.objects.filter(
                        id=scheduler_id,
                        landingpage_url="No",
                        objective__in=["Traffic", "Conversions"],
                    )
                    .order_by("platform")
                    .values_list("id", "scraper_group_id", "scraper_group__group_name")
                )
        except Exception:
            raise DatabaseRequestException("Could not get data from database")
        return response

    def generate_missing_urls(self, scheduler_id=None):
        ad_scheduler_data = self.get_scheduler_data(scheduler_id)
        if len(ad_scheduler_data) == 0:
            self.debugprint(
                "[Linkfire generator] No url's were missing, ending generation process."
            )
            return
        linkfire_settings = []
        genre = ""
        mediaserviceids = []
        sortorder = []
        mediaurls = []
        mediactas = []
        heading = []
        caption = []
        response = []
        n = 1  # name suffix
        for schedule_index in range(len(ad_scheduler_data)):
            try:
                AdScheduler.objects.filter(
                    id=ad_scheduler_data[schedule_index][0]
                ).update(completed="Pending", updated_at=datetime.datetime.now())
            except Exception:
                continue
            if schedule_index == 0:
                genre = ad_scheduler_data[schedule_index][1]
                genre_name = ad_scheduler_data[schedule_index][2]
                linkfire_settings = (
                    LinkfireLinkSettings.objects.filter(
                        Q(scraper_group_id=genre)
                        & (
                            (Q(default_url="Yes") | Q(territory_url="Yes"))
                            | (
                                (Q(default_url="No") & Q(territory_url="No"))
                                & (Q(url__isnull=False) & ~Q(url=""))
                            )
                        )
                    )
                    .order_by("sortorder")
                    .values_list(
                        "sortorder",
                        "mediaserviceid",
                        "url",
                        "heading",
                        "caption",
                        "scraper_group_id",
                        "artwork",
                        "customctatext",
                        "default_url",
                        "territory_url",
                    )
                )
                if linkfire_settings == []:
                    self.handleerror(
                        "generate_missing_urls",
                        "No linkfireSettings found for "
                        + genre
                        + ", please set them in database",
                    )
                    continue
                mediaserviceids = []
                sortorder = []
                mediaurls = []
                mediactas = []
                spotify_base_url = ""
                heading = linkfire_settings[0][3]
                caption = linkfire_settings[0][4]
                artwork = linkfire_settings[0][6]
                countorder = 0
                for linkfire_index in range(len(linkfire_settings)):
                    sortorder.append(countorder)
                    countorder = countorder + 1
                    mediaserviceids.append(
                        {
                            "mediaServiceIds": linkfire_settings[linkfire_index][1],
                            "default_url": linkfire_settings[linkfire_index][8],
                            "territory_url": linkfire_settings[linkfire_index][9],
                        }
                    )
                    mediaurls.append(linkfire_settings[linkfire_index][2])
                    mediactas.append(linkfire_settings[linkfire_index][7])
                    if spotify_base_url == "":
                        if (
                            linkfire_settings[linkfire_index][1]
                            == "7a586f9f-9e2d-4383-83cc-b2aa5bd1798d"
                        ):  # spotify
                            spotify_base_url = linkfire_settings[linkfire_index][2]
                        if (
                            linkfire_settings[linkfire_index][1]
                            == "8f82cc1c-a2c3-4438-8a29-285983518182"
                        ):  # apple
                            spotify_base_url = linkfire_settings[linkfire_index][2]
                        if (
                            linkfire_settings[linkfire_index][1]
                            == "18976FD2-4365-49B5-86BC-F1E93D8465DB"
                        ):  # Amazon
                            spotify_base_url = linkfire_settings[linkfire_index][2]

            elif (
                genre != ad_scheduler_data[schedule_index][1]
            ):  # only do a database call if a new genre is found. don't do this check when i == 0 to prevent index error.
                n = 1
                genre = ad_scheduler_data[schedule_index][1]
                genre_name = ad_scheduler_data[schedule_index][2]
                linkfire_settings = (
                    LinkfireLinkSettings.objects.filter(
                        Q(scraper_group_id=genre)
                        & (
                            (Q(default_url="Yes") | Q(territory_url="Yes"))
                            | (
                                (Q(default_url="No") & Q(territory_url="No"))
                                & (Q(url__isnull=False) & ~Q(url=""))
                            )
                        )
                    )
                    .order_by("sortorder")
                    .values_list(
                        "sortorder",
                        "mediaserviceid",
                        "url",
                        "heading",
                        "caption",
                        "scraper_group_id",
                        "artwork",
                        "customctatext",
                        "default_url",
                        "territory_url",
                    )
                )

                if linkfire_settings == []:
                    self.handleerror(
                        "generate_missing_urls",
                        "No linkfireSettings found for "
                        + genre
                        + ", please set them in database",
                    )
                    continue

                mediaserviceids = []
                sortorder = []
                mediaurls = []
                mediactas = []
                spotify_base_url = ""

                heading = linkfire_settings[0][3]
                caption = linkfire_settings[0][4]
                artwork = linkfire_settings[0][6]
                countorder = 0
                for linkfire_index in range(len(linkfire_settings)):
                    sortorder.append(countorder)
                    countorder = countorder + 1
                    mediaserviceids.append(
                        {
                            "mediaServiceIds": linkfire_settings[linkfire_index][1],
                            "default_url": linkfire_settings[linkfire_index][8],
                            "territory_url": linkfire_settings[linkfire_index][9],
                        }
                    )
                    mediaurls.append(linkfire_settings[linkfire_index][2])
                    mediactas.append(linkfire_settings[linkfire_index][7])
                    if spotify_base_url == "":
                        if (
                            linkfire_settings[linkfire_index][1]
                            == "7a586f9f-9e2d-4383-83cc-b2aa5bd1798d"
                        ):  # spotify
                            spotify_base_url = linkfire_settings[linkfire_index][2]
                        if (
                            linkfire_settings[linkfire_index][1]
                            == "8f82cc1c-a2c3-4438-8a29-285983518182"
                        ):  # apple
                            spotify_base_url = linkfire_settings[linkfire_index][2]
                        if (
                            linkfire_settings[linkfire_index][1]
                            == "18976FD2-4365-49B5-86BC-F1E93D8465DB"
                        ):  # Amazon
                            spotify_base_url = linkfire_settings[linkfire_index][2]
            if linkfire_settings == []:
                continue
            # Step 1: Create campaign
            try:
                response, n = self.create_campaign(
                    spotify_base_url,
                    mediaserviceids,
                    mediaurls,
                    mediactas,
                    sortorder,
                    mediaurls[0],
                    heading,
                    caption,
                    genre,
                    artwork,
                    n,
                    genre_name,
                )  # hardcoded
                n += 1
            except Exception as e:
                AdScheduler.objects.filter(
                    id=ad_scheduler_data[schedule_index][0]
                ).update(completed="Error", updated_at=datetime.datetime.now())
                self.handleerror(
                    "[createlink] Exception occurd during link creation ad_scheduler id : "
                    + str(ad_scheduler_data[schedule_index][0]),
                    str(e),
                )
                continue
            # Get some variables
            response_decoded = json.loads(response["_content"].decode())
            linkid = response_decoded["data"]["id"]
            landing_page_url = response_decoded["data"]["url"]
            shorttag = response_decoded["data"]["code"]
            linkfire_status = response_decoded["data"]["status"]

            # Add to database -- Check later to update status to Published
            # We will later loop on this database table and update status accordingly
            self.add_to_database_link(
                self.board_id,
                linkid,
                landing_page_url,
                shorttag,
                linkfire_status,
                ad_scheduler_data[schedule_index][0],
                ad_scheduler_data[schedule_index][1],
            )

            try:
                AdScheduler.objects.filter(
                    id=ad_scheduler_data[schedule_index][0]
                ).update(landingpage_url="Yes", updated_at=datetime.datetime.now())
                AdCreativeIds.objects.filter(
                    scheduler_id=ad_scheduler_data[schedule_index][0]
                ).update(
                    landingpage_url=landing_page_url,
                )
            except Exception as e:
                self.handleerror(
                    "[createlink] Could not update landingpage_url in database", str(e)
                )
            # Wait until this link is fully scanned.
            iscomplete = False
            while not iscomplete:
                linkstatus, iscomplete = self.get_scanning_status(linkid)
                if iscomplete:
                    if linkstatus == "NoScanningResults":
                        self.update_database_link(linkid, linkstatus)
                    elif linkstatus == "Published":
                        try:
                            AdScheduler.objects.filter(
                                id=ad_scheduler_data[schedule_index][0]
                            ).update(completed="No", updated_at=datetime.datetime.now())
                        except Exception as e:
                            self.handleerror(
                                "[createlink] Could not update completed status in database",
                                str(e),
                            )
                        break
                    elif linkstatus == "Pending":
                        break
                time.sleep(10)

    def resolve_pending_status(self):
        """
        Fetches database table linkfire_generated_links, checks for status != 'Published' and update status in db
        """
        response = (
            LinkfireGeneratedLinks.objects.all()
            .exclude(status="Published")
            .values_list(
                "id",
                "linkfire_board_id",
                "link_id",
                "status",
                "shorttag",
                "ad_scheduler_id",
            )
        )
        for response_index in range(len(response)):
            id_db = response[response_index][0]
            board_id = response[response_index][1]
            link_id = response[response_index][2]
            status_db = response[response_index][3]
            shorttag = response[response_index][4]
            ad_scheduler_id = response[response_index][5]
            self.debugprint(
                "[Update Status] Found `Pending` status. Trying to publish. Linkfire: {}".format(
                    str(shorttag)
                )
            )
            # Get campaign info
            try:
                response_get = self.get_campaign(link_id, board_id)
                response_get = json.loads(response_get["_content"].decode())
            except Exception as e:
                self.debugprint(str(e))
                self.handleerror(
                    "[resolve_pending_status] Invalid response get_campaign ", str(e)
                )
            linkfire_status = response_get["data"]["status"]
            landingpage_url = response_get["data"]["url"]
            if linkfire_status == "Pending":
                # Publish it with PUT req
                # First delete properties tags and images as they are handled incorrectly in backend Linkfire
                try:
                    del response_get["data"]["tags"]
                    del response_get["data"]["images"]
                except Exception:
                    self.debugprint(
                        "[Delete properties] Warning, could not find `tags` or `images`. Is normal."
                    )
                # Change status to Published
                response_get["data"]["status"] = "Published"
                try:
                    response_update = self.update_campaign(
                        link_id, json.dumps(response_get["data"]), board_id
                    )
                    response_update = json.loads(response_update["_content"].decode())
                except Exception as e:
                    self.debugprint(str(e))
                    self.handleerror(
                        "[resolve_pending_status, update_campaign] Could not update PUT campaign ",
                        str(e),
                    )
                linkfire_status = response_update["data"]["status"]

            if linkfire_status != status_db:
                # Update table
                try:
                    LinkfireGeneratedLinks.objects.filter(id=id_db).update(
                        status=linkfire_status, updated_at=datetime.datetime.now()
                    )
                    AdScheduler.objects.filter(
                        id=ad_scheduler_id, completed="Pending"
                    ).update(completed="No", updated_at=datetime.datetime.now())
                except Exception as e:
                    self.debugprint(str(e))
                    self.handleerror(
                        "[resolve_pending_status, insert_db] Could not update linkfire status in database ",
                        str(e),
                    )
            else:
                # Link probably doesn't exist anymore, delete entry
                LinkfireGeneratedLinks.objects.filter(id=id_db).delete()

    def get_media_services(self):
        try:

            headers = self.header
            parameters = {}
            url = url_hp.LINKFIRE_MEDIA_SERVICES_URL + str(self.page)
            response = []
            response = self.get(url, headers, parameters)
            status_code = response["status_code"]
            if status_code in [403, 401, 400]:
                self.generate_new_access_token()
                self.get_media_services()

            elif (
                status_code == 200
                and "data" in json.loads(response["_content"].decode())
                and len(json.loads(response["_content"].decode())["data"]) != 0
            ):
                response_data = json.loads(response["_content"].decode())["data"]
                self.page += 1
                for value in response_data:
                    mediaservice_id = value["id"]
                    buttontype = value["buttonType"]
                    name = value["name"]
                    description = value["description"]
                    self.mediaservices_list.append(
                        (mediaservice_id, buttontype, name, description)
                    )
                self.get_media_services()
            return self.mediaservices_list
        except Exception as e:
            self.debugprint(str(e))

    def mediaservices(self):
        mediaservices_list = self.get_media_services()
        if len(mediaservices_list) > 0:
            response = LinkfireBoards.objects.filter(
                board_id=self.board_id
            ).values_list("id", flat=True)
            board_id_match = response[0]
            ### delete all content form linkfire_mediaservices table ####
            LinkfireMediaservices.objects.all().delete()
            linkfire_media_service_object = []
            for single_tupple in mediaservices_list:
                linkfire_media_service_object.append(
                    LinkfireMediaservices(
                        mediaservice_id=single_tupple[0],
                        buttontype=single_tupple[1],
                        name=single_tupple[2],
                        description=single_tupple[3],
                        linkfire_board_id=board_id_match,
                    )
                )
            LinkfireMediaservices.objects.bulk_create(linkfire_media_service_object)
