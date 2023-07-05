# Documentation for webdriver wait: https://www.techbeamers.com/selenium-webdriver-waits-python/
import os
import time
from datetime import datetime, timedelta
from SF import settings
from apps.common.models import AdAdsets
from apps.linkfire.models import LinkfireData, LinkfireGeneratedLinks, ScrapeLinkfires
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    TimeoutException,
)
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
import json
import socket
from apps.scraper.models import Settings
from django.db.models import Q
from dateutil.relativedelta import relativedelta
from apps.common.constants import StatusType

"""
----------------------- LINKFIRE SCRAPER ------------------------
"""


class LinkfireScraper:
    linkfireURL = ""
    timeOutLoading = 3  # in min
    linkfire_scrape_interval = 1  # in hours

    def __init__(self):
        self.browser = ""
        # self.db = db
        self.updateVariables()
        # self.updateCountryCodes()
        self.insights_shorttag = ""
        self.timeout_retries = 0
        self.internet_disconnected_time = ""
        self.login_input = "#ember10-input"
        self.password_input = "#ember14-input"

    # def refreshDbConnection(self):
    #     """
    #     Function that closes and reopens the database connection
    #     """
    #     del self.db
    #     self.db = DB.Database('ads')

    def chromeBrowser(self):
        """
        Uses Chrome webbrowser as driver
        :return:
        """
        options = webdriver.ChromeOptions()
        options.add_argument(
            "enable-automation"
        )  # https://stackoverflow.com/a/43840128/1689770
        options.add_argument(
            "--no-sandbox"
        )  # https://stackoverflow.com/a/50725918/1689770
        options.add_argument(
            "--disable-infobars"
        )  # https://stackoverflow.com/a/43840128/1689770
        options.add_argument(
            "--disable-dev-shm-usage"
        )  # https://stackoverflow.com/a/50725918/1689770
        options.add_argument(
            "--disable-browser-side-navigation"
        )  # /https://stackoverflow.com/a/49123152/1689770
        options.add_argument(
            "--disable-gpu"
        )  # https://stackoverflow.com/questions/51959986/how-to-solve-selenium-chromedriver-timed-out-receiving-message-from-renderer-exc
        return webdriver.Chrome(ChromeDriverManager().install(), options=options)

    def firefoxBrowser(self):
        """
        Uses Firefox webbrowser as driver
        Install instructions: https://devenum.com/how-to-open-firefox-browser-in-selenium-python/
        Install : https://github.com/mozilla/geckodriver/releases
        Copy geckodriver.exe to venv/Scripts (together with python.exe)
        Make sure Firefox is installed on system
        :return:
        """
        return webdriver.Firefox()

    def relaunchBrowser(self):
        if self.browser != "":
            self.browser.quit()
        self.browser = self.chromeBrowser()

    def isConnected(self):
        try:
            # connect to the host -- tells us if the host is actually
            # reachable
            sock = socket.create_connection(("www.google.com", 80))
            if sock is not None:
                print("[Internet] Good...")
                sock.close
            return True
        except OSError:
            pass
        return False

    def checkAndwaitForInternet(self):
        if self.isConnected() is False:
            if self.internet_disconnected_time == "":
                today = datetime.now()
                todayDB = today.strftime("%Y-%m-%d %H:%M:%S")
                self.internet_disconnected_time = todayDB
            # We do not have any internet connection. Try again in 2 min
            print(
                "[No internet] No internet connection active, try again in 2 min. Problem occured since {}".format(
                    self.internet_disconnected_time
                )
            )
            time.sleep(2 * 60)
            self.waitForInternet()
            return False
        else:
            self.internet_disconnected_time = ""  # reset
            return True

    def setLookupLink(self, linkfireURL):
        self.linkfireURL = linkfireURL
        if self.linkfireURL == "":
            # Set inactive and skip
            self.setStatusLinkfire(linkfireURL, StatusType.NO)
            return False
        # Add to database
        today = datetime.now()
        todayDB = today.strftime("%Y-%m-%d %H:%M:%S")
        try:
            ScrapeLinkfires.objects.filter(shorttag=self.linkfireURL).update(
                scraped=1, last_scraped=todayDB
            )
            # self.db.execSQL("""UPDATE scrape_linkfires SET scraped=(scraped+1), last_scraped=%s WHERE shorttag=%s""", [todayDB, self.linkfireURL], True)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print("[setLookupLink] Trying again in 15 seconds...")
            time.sleep(15)
            return self.setLookupLink(self.linkfireURL)
        return True

    # Login to linkfire
    def loginLinkfire(self):
        self.relaunchBrowser()

        self.checkAndwaitForInternet()  # Check if internet, if not, hold
        todayStrf = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("[Login] {} - Trying to login".format(todayStrf))
        # Fetch a webpage
        self.browser.get("https://app.linkfire.com/")

        # Accept cookies
        time.sleep(3)
        try:
            accept_cookies = self.browser.find_element(
                By.CSS_SELECTOR, "#onetrust-accept-btn-handler"
            )
            accept_cookies.click()
            print("Accepted cookies")
        except Exception:
            print("No cookie dialog found")

        # Get an element, even if it was created with JS
        try:
            # inputEmail = self.browser.find_element(By.ID, 'ember10-input')
            # inputPW = self.browser.find_element(By.ID, 'ember14-input')
            inputEmail = self.browser.find_element(By.CSS_SELECTOR, self.login_input)
            inputPW = self.browser.find_element(By.CSS_SELECTOR, self.password_input)
            settings = self.updateVariables()
            linkfire_username = settings["linkfire_username"]
            encrypted_linkfire_password = settings["linkfire_password"]
            linkfire_password = self.decrypt(encrypted_linkfire_password)
            inputEmail.send_keys(linkfire_username)
            inputPW.send_keys(linkfire_password)
            time.sleep(2)
            # self.browser.find_element(By.TAG_NAME, 'form').submit()
            # Click enter
            inputPW.send_keys("\ue007")
            # submitBtn = self.browser.find_element(By.CSS_SELECTOR, '[type="submit"]')
            # submitBtn.click()
            time.sleep(5)
        except Exception:
            self.getBackOnTrack(
                "Exception: loginLinkfire() - Trouble finding elements. Trying again in a few seconds"
            )
            return self.loginLinkfire()

    # Check if we are still loggedIn
    def loggedIn(self):
        # Check if there is an element with text contains Sign out
        try:
            self.browser.find_element(By.CSS_SELECTOR, self.login_input)
        except Exception:
            print("[Logged in] We are logged in")
            return True
        print("[Logged out] We are logged out, login required")
        return False

    def updateCountryCodes(self):
        """
        Function to update country codes of rows that have NULL
        """
        try:
            response = (
                LinkfireData.objects.filter(country_code__isnull=True)
                .values("country")
                .distinct()
            )
            # response = self.db.execSQL("""SELECT country FROM linkfire_data WHERE country_code IS NULL GROUP BY country""", [], False)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print("[updateCountryCodes] Trying again in 15 seconds...")
            time.sleep(15)
            return self.updateCountryCodes()
        if len(response) != 0:
            print(
                "[NULL Country_codes] Found {} NULL Country_codes, updating them as we go...".format(
                    str(len(response))
                )
            )
            for res in response:
                country = res[0]
                country_code = self.getCountryCode(country)
                if country_code == 0:  # Skip can't find
                    LinkfireData.objects.filter(country=country).update(
                        country_code="_missing_"
                    )
                    # update = self.db.execSQL("""UPDATE linkfire_data SET country_code=%s WHERE country=%s""",
                    #                          ['_missing_', country], True)
                    continue
                LinkfireData.objects.filter(country=country).update(
                    country_code=country_code
                )
                # update = self.db.execSQL("""UPDATE linkfire_data SET country_code=%s WHERE country=%s""", [country_code, country], True)

    # Function that retrieves up to date database settings/variables
    def updateVariables(self):
        try:
            response = Settings.objects.all().values_list("variable", "value")
            # response = self.db.execSQL("""SELECT variable, value FROM settings""", [], False)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print("[updateVariables] Trying again in 15 seconds...")
            time.sleep(15)
            return self.updateVariables()

        if len(response) == 0:
            raise Exception("Please update the variables in the web app")
        settings = {}
        for x in response:
            variable = x[0]
            value = x[1]
            settings[variable] = value
        self.linkfire_scrape_interval = settings["linkfire_scrape_interval"]
        return settings

    def scanAutoGeneratedLinks(self):
        """
        Reads database linkfire_generated_links where is_scraped = No. Scrape edit page of the url
        check if artwork is present, if not, click on Scan Now, wait and Publish
        :return:
        """
        try:
            response = LinkfireGeneratedLinks.objects.filter(is_scraped="No").values(
                "shorttag", "status"
            )
            # response = self.db.execSQL("""SELECT shorttag, status FROM linkfire_generated_links WHERE is_scraped=%s""", ['No'], False)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print(
                "[scanAutoGeneratedLinks] Trying again in 15 seconds... -- New database session initialized"
            )
            time.sleep(15)
            return self.scanAutoGeneratedLinks()
        if len(response) == 0:
            return
        for row in response:
            shorttag = row[0]
            status = row[1]
            edit_link = (
                "https://app.linkfire.com/#/strange-fruits/" + shorttag + "/edit"
            )
            print("[Visit] Page link " + shorttag)
            self.navigatePage(edit_link)
            time.sleep(5)
            # Check if we are on the right page
            retry_scan = True
            amount_of_retries = 0
            while retry_scan:
                if amount_of_retries > 1:
                    print("[Retry after 10 sec] ...")
                    time.sleep(10)
                is_scraped = "Yes"
                retry_scan = False
                try:
                    WebDriverWait(self.browser, 5).until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, "#linkSource .source-wrapper")
                        )
                    )
                except Exception:
                    retry_scan = True
                    amount_of_retries += 1
                    if amount_of_retries > 100:
                        print(
                            "[Linkfire Scan Issues] Tried to rescan for 10 times, but failed to fetch artwork. Skip"
                        )
                        is_scraped = "ErrorScanning"
                        break
                    print(
                        "[Scanning required. Try {}] for link {} . Click on Scan Now...".format(
                            str(amount_of_retries), shorttag
                        )
                    )
                    scan_btn_found = False
                    while not scan_btn_found:
                        try:
                            scan_btn = WebDriverWait(self.browser, 10).until(
                                EC.visibility_of_element_located(
                                    (By.CSS_SELECTOR, ".rescan-action__rescan_now")
                                )
                            )
                        except Exception:
                            print(
                                "[Rescan btn not found] Retry scan_btn_found loop new in 5 sec"
                            )
                            self.navigatePage(edit_link)
                            time.sleep(5)
                            amount_of_retries += 1
                            if amount_of_retries > 100:
                                print(
                                    "[Linkfire Rescan Issues] Retry scan_btn_found never found. Tried to rescan for 10 times, but failed to fetch artwork. Skip"
                                )
                                is_scraped = "ErrorScanning"
                                break
                            continue
                        scan_btn_found = True
                    if amount_of_retries > 10:
                        break
                    scan_btn.click()
                    time.sleep(3)
                    # Wait until #tilt-wrapper is gone, max 120 sec
                    try:
                        WebDriverWait(self.browser, 120).until(
                            EC.invisibility_of_element_located(
                                (By.CSS_SELECTOR, "#tilt-wrapper")
                            )
                        )
                    except Exception:
                        print(
                            "[Scanning issue] #tilt-wrapper aka scanning screen is still visible after 120 sec.."
                        )
                        is_scraped = "ErrorScanning"

                    if is_scraped != "ErrorScanning":
                        print(
                            "[Scanning complete] First check if scan results are good, if not , try again"
                        )
                        time.sleep(2)
                        try:
                            self.browser.find_element(
                                By.CSS_SELECTOR, "#linkSource .source-wrapper"
                            )
                        except Exception:
                            print("[Scan failed] Try again")
                            continue

                        print("[Scan Success] Click on Publish/Update btn now")
                        retry_scan = False
                        try:
                            publish_btn = WebDriverWait(self.browser, 10).until(
                                EC.visibility_of_element_located(
                                    (
                                        By.CSS_SELECTOR,
                                        '[data-test-selector="publish-edit-link-button"]',
                                    )
                                )
                            )
                        except Exception:
                            print(
                                "[Publish btn not found] Publish button not found. Try update"
                            )
                            # [data-test-selector="update"]
                            try:
                                publish_btn = WebDriverWait(self.browser, 10).until(
                                    EC.visibility_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            '[data-test-selector="update"]',
                                        )
                                    )
                                )
                            except Exception:
                                print(
                                    "[Update btn not found] Publish button not found. Try update"
                                )
                                status = "NoScanningResults"  # Still needs to be published by API
                        if status != "NoScanningResults":
                            publish_btn.click()
                            # If #toast-container .toast-success visible, meaning this link successfully published
                            try:
                                publish_btn = WebDriverWait(self.browser, 20).until(
                                    EC.visibility_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            "#toast-container .toast-success",
                                        )
                                    )
                                )
                            except Exception:
                                print(
                                    "[Not published] No toast-container found, so assuming it wasn't published"
                                )
                                is_scraped = "ErrorScanning"

                            if is_scraped != "ErrorScanning":
                                print(
                                    "[Published] Successfully published link and pushed status to database"
                                )
                                status = "Published"
                                time.sleep(2)
                else:
                    print("[Published] No scan needed")

            LinkfireGeneratedLinks.objects.filter(shorttag=shorttag).update(
                is_scraped=is_scraped, status=status
            )
            # we found #linkSource .source-wrapper meaning this link has an artwork, update db and skip
            # self.db.execSQL("""UPDATE linkfire_generated_links SET `is_scraped`=%s, `status`=%s WHERE shorttag=%s""",
            #                     [is_scraped, status, shorttag], True)

    # Function to check database and check if everything is up to date or needs to be scraped
    def checkLinkstoScrape(self):
        """
        First check what linkfires are active according to ad_adsets.
        """
        try:
            response = ScrapeLinkfires.objects.update(is_active=StatusType.NO)
            # response = self.db.execSQL(
            #     """UPDATE scrape_linkfires SET active=%s""",
            #     ['No'], True)
            #
            list_landingpage = (
                AdAdsets.objects.filter(
                    active="Yes",
                    landingpage__isnull=False,
                    landingpage__contains="lnk.to",
                )
                .values_list("landingpage", flat=True)
                .distinct()
            )
            response = ScrapeLinkfires.objects.filter(url__in=list_landingpage).update(
                is_active=StatusType.YES
            )
            # response = self.db.execSQL("""UPDATE scrape_linkfires SET active=%s WHERE url IN (SELECT landingpage FROM ad_adsets WHERE active='Yes' AND landingpage IS NOT NULL AND landingpage LIKE '%lnk.to%' GROUP BY landingpage);""", ['Yes'], True)
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
                .values_list("shorttag", "id")
                .order_by("-id")
            )
            # response = self.db.execSQL("""SELECT shorttag, id FROM scrape_linkfires WHERE `active`=%s AND (`last_scraped` IS NULL OR  `last_scraped` <= %s - INTERVAL %s HOUR ) ORDER BY id DESC""", ['Yes', now, self.linkfire_scrape_interval], False)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print(
                "[checkLinkstoScrape] Trying again in 15 seconds... -- New database session initialized"
            )
            time.sleep(15)
            return self.checkLinkstoScrape()
        return response

    # function to check if we have past 7 days of data in the database
    # Returns which dates we don't have for fresh new inserted data
    def checkExistingData(self):
        # For every date from now until -7 days, check if we have in database
        datesMissing = []
        for i in range(8):
            today = datetime.now()
            todayStrf = today.strftime("%Y-%m-%d")
            goBack = today - timedelta(i)
            # dateFrom = goBack.strftime("%Y-%m-%d")
            dateTo = goBack.strftime("%Y-%m-%d")
            dateDB = goBack.strftime("%Y-%m-%d 23:59:59")
            # First check if date to check is today, if so, insert new values because we need every new info every hour or so
            # Only if today != dateTo meaning we are looking days in the past: Insert only if there exists no date & tag for this entry
            if todayStrf != dateTo:
                # First check if data is already in table, if so, skip this cycle
                try:
                    scrape_linkfire_list = ScrapeLinkfires.objects.filter(
                        shorttag=self.linkfireURL
                    ).values_list("id", flat=True)
                    response = LinkfireData.objects.filter(
                        date=dateDB, linkfire_id__in=scrape_linkfire_list
                    ).values("id")
                    # response = self.db.execSQL("""SELECT linkfire_data.id as id FROM linkfire_data
                    #                                 INNER JOIN scrape_linkfires ON linkfire_data.linkfire_id = scrape_linkfires.id
                    #                                 WHERE `date`=%s AND `shorttag`=%s""",
                    #                   [dateDB, self.linkfireURL], False)
                except Exception:
                    # Query failed to execute
                    # self.refreshDbConnection()
                    print(
                        "[checkExistingData todayStrf != dateTo] Trying again in 15 seconds..."
                    )
                    time.sleep(15)
                    return self.checkExistingData()
                if len(response) > 0:
                    # Skip, why? Because this is data not from today and so will not be updated by linkfire, it is past
                    print(
                        "[Skip] {} - {} We have the latest data of this date ".format(
                            self.linkfireURL, dateDB
                        )
                    )
                    continue
            else:
                # Get latest time from today, if it was less then 1 hr, skip
                try:
                    last_scraped_interval = datetime.now() - relativedelta(hours=1)
                    scrape_linkfire_list = ScrapeLinkfires.objects.filter(
                        shorttag=self.linkfireURL
                    ).values_list("id", flat=True)
                    response = LinkfireData.objects.filter(
                        date__gte=last_scraped_interval,
                        linkfire_id__in=scrape_linkfire_list,
                    ).values("id")

                    # response = self.db.execSQL("""SELECT linkfire_data.id as id FROM linkfire_data
                    #                      INNER JOIN scrape_linkfires ON linkfire_data.linkfire_id = scrape_linkfires.id
                    #                      WHERE `date`>= now() - INTERVAL %s HOUR AND `shorttag`=%s """,
                    #                     [1, self.linkfireURL], False)
                except Exception:
                    # Query failed to execute
                    # self.refreshDbConnection()
                    print(
                        "[checkExistingData todayStrf == dateTo] Trying again in 15 seconds..."
                    )
                    time.sleep(15)
                    return self.checkLinkstoScrape()
                if len(response) > 0:
                    print(
                        "[Skip] {} - {} Last update was less than 1hr ago.".format(
                            self.linkfireURL, dateDB
                        )
                    )
                    continue
            print("Missing : {}".format(dateDB))
            datesMissing.append(goBack)
        return datesMissing

    def prepareInsightsData(self):
        """
        End goal is to retrieve the insights shorttag from linkfire.
        If the value in the database insights_shorttag is empty, go manual search Linkfire page and get insights link
        If value exists, retrieve from database
        Returns:
        list: List with user info
        """
        try:
            response = ScrapeLinkfires.objects.filter(
                shorttag=self.linkfireURL
            ).values_list("insights_shorttag")
            # response = self.db.execSQL("""SELECT insights_shorttag FROM scrape_linkfires WHERE `shorttag`=%s""",
            #                        [self.linkfireURL], False)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print("[prepareInsightsData] Trying again in 15 seconds...")
            time.sleep(15)
            return self.prepareInsightsData()
        if response[0][0] is None:
            # value is empty
            """--------------------------------  BROWSE LINKS --------------------------------"""
            self.searchPage()
            """ --------------------------------  ENTER CORRECT CARD -------------------------------- """
            cardsFound = self.getInsightsLink()
            if cardsFound == 0:
                # No cards were found, so we cannot check this link, was already reported to database
                return 0
        else:
            self.insights_shorttag = response[0][
                0
            ]  # populate class variable with database value
            return 1

    def searchPage(self, tries=1):
        self.navigatePage(
            "https://app.linkfire.com/#/strange-fruits?searchQuery=" + self.linkfireURL
        )
        # Check if we are on the right page
        try:
            WebDriverWait(self.browser, 30).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.card-content"))
            )
        except Exception:
            if tries >= 3:
                # Skip this one and set on inactive. This is not a valid linkfire
                self.setStatusLinkfire(self.linkfireURL, StatusType.NO)
                return
            tries += 1
            self.getBackOnTrack(
                "[Timeout] searchPage, waited 15 sec but no div.card-content. Try: "
                + str(self.timeout_retries)
            )
            return self.searchPage(tries)

    def getInsightsLink(self):
        # For every .campaign-card search for the div.url and the url there.
        getCampaignCards = self.browser.find_elements(
            By.CSS_SELECTOR, "div.card-content"
        )
        print("Found " + str(len(getCampaignCards)) + " div.card-content divisions")
        if len(getCampaignCards) == 0:
            todayStrf = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.setStatusLinkfire(self.linkfireURL, StatusType.NO)
            print(
                "[Error] {} - Failed to look up link {}".format(
                    todayStrf, self.linkfireURL
                )
            )
            return 0
        found_matching_block = False
        for row in getCampaignCards:
            getUrlBlocks = row.find_element(By.CSS_SELECTOR, "div.url").text.split("/")[
                1
            ]  # only shorttag, without url
            if getUrlBlocks == self.linkfireURL:
                found_matching_block = True
                todayStrf = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(
                    "[Found] {} - Found correct link on browse page. Entering now.. {}".format(
                        todayStrf, self.linkfireURL
                    )
                )
                btnLinkInsights = row.find_element(By.CLASS_NAME, "actions")
                insights_url = btnLinkInsights.find_element(
                    By.CSS_SELECTOR, '[data-test-selector="link-insights"]'
                ).get_attribute("href")

                while "/insights" not in insights_url:
                    time.sleep(1)
                    insights_url = btnLinkInsights.find_element(
                        By.CSS_SELECTOR, '[data-test-selector="link-insights"]'
                    ).get_attribute("href")

                self.insights_shorttag = insights_url.split("/insights")[0].split(
                    "strange-fruits/"
                )[
                    1
                ]  # Save it for later usage

                print("Final : {}".format(self.insights_shorttag))
                # Update database with this shorttag insights
                try:
                    ScrapeLinkfires.objects.filter(shorttag=self.linkfireURL).update(
                        insights_shorttag=self.insights_shorttag
                    )
                    # self.db.execSQL("""UPDATE scrape_linkfires SET `insights_shorttag`=%s WHERE shorttag=%s""",
                    #             [self.insights_shorttag, self.linkfireURL], True)
                except Exception:
                    # Query failed to execute
                    # self.refreshDbConnection()
                    print("[getInsightsLink] Trying again in 15 seconds...")
                    time.sleep(15)
                    return self.getInsightsLink()
                break
        if found_matching_block is False:
            print(
                "Can't find corresponding card on page for shorttag {}".format(
                    self.linkfireURL
                )
            )

        return len(getCampaignCards)

    def enterLocations(self, date_from, date_to):
        # Check current url
        extend_url = (
            "/insights/locations/countries?end="
            + date_from
            + "T23%3A59%3A59Z&granularity=FifteenMinute&start="
            + date_to
            + "T00%3A00%3A00Z&transitionFrom=link-feeds"
        )
        navigate_insights = (
            "https://app.linkfire.com/#/strange-fruits/"
            + self.insights_shorttag
            + extend_url
        )
        # Navigate
        time.sleep(5)
        self.navigatePage(navigate_insights)
        time.sleep(10)
        # Wait until the full table is load, check it by Countries head which appears if table is loaded
        try:
            WebDriverWait(self.browser, 10).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, ".insights table th"), "Countries"
                )
            )
        except (TimeoutException, WebDriverException):
            self.getBackOnTrack(
                "[Timeout] enterLocations() could not find the table with data."
            )
            return self.enterLocations(date_from, date_to)
        # Find Show More button and click on it
        self.clickLoadMoreBtns(reloads=0)

    def getCountryCode(self, country):
        """
        Returns the alpha 2 country code for Spotify country url
        PARAMS:
        country: The full name of the country
        RETURNS:
        country_code: alpha 2 country code
        """
        if country == "Worldwide":
            return country
        # with open("../../s4a_scraper/country_codes.json", "r") as f:

        with open(
            os.path.join(settings.BASE_DIR, "apps/common/json/country_codes.json")
        ) as f:
            my_dict = json.load(f)
        f.close()
        for x in my_dict:
            if x["Name"] == country or x["Code"] == country:
                return x["Code"]
        print(
            "[Country Code ERROR] Could not find country code for country name: {}".format(
                country
            )
        )
        return False

    def getData(self):
        # Full table was loaded, retrieve clicks per country
        try:
            insightsTable = WebDriverWait(self.browser, 30).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.insights-locations")
                )
            )
            time.sleep(6)
            allRows = insightsTable.find_elements(By.CSS_SELECTOR, "tr.source")
        except Exception:
            print(
                "[getData] Timeout. Could not find insights-locations table after 30 sec, so assuming there is no data.."
            )
            allRows = []
        try:
            exportLinkfireData = []
            if len(allRows) == 0:
                todayStrf = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(
                    "[Empty] {} - This link has not enough data yet {}".format(
                        todayStrf, self.linkfireURL
                    )
                )
                return exportLinkfireData
            # it has data..
            todayStrf = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                "[Prepare] {} - Retrieving data from Linkfire page {}".format(
                    todayStrf, self.linkfireURL
                )
            )
            for row in allRows:
                countryName = row.find_element(
                    By.CSS_SELECTOR, "div.country-info h4"
                ).text
                countryCode = self.getCountryCode(countryName)
                visits = row.find_element(
                    By.CSS_SELECTOR, "td:nth-child(3)"
                ).text  # 3,661
                visits = visits.replace(",", "")
                CTR = row.find_element(
                    By.CSS_SELECTOR, "td:nth-child(5)"
                ).text  # 85.43%
                CTR = CTR.replace("%", "")
                if visits != 0:
                    exportLinkfireData.append([countryName, countryCode, visits, CTR])
                # print("[Data] {} - Visits: {} - CTR: {}".format(countryName, visits, CTR))
        except Exception:
            self.getBackOnTrack(
                "[Exception] getData() could not perform steps. Try again"
            )
            return self.getData()
        return exportLinkfireData

    def insertScraperDatabase(self, insert_values_db):
        try:
            linkfireObject = [
                LinkfireData(
                    linkfire_id=val[0],
                    date=val[1],
                    country=val[2],
                    country_code=val[3],
                    visits=val[4],
                    CTR=val[5],
                )
                for val in insert_values_db
            ]
            LinkfireData.objects.bulk_create(linkfireObject)
            # self.db.insertSQL_multi("INSERT INTO linkfire_data (`linkfire_id`,`date`, `country`, `country_code`, `visits`, `CTR`) VALUES (?,?,?,?,?,?)",
            #                         insert_values_db)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print("[insertScraperDatabase] Trying again in 15 seconds...")
            time.sleep(15)
            self.getBackOnTrack(
                "[Exception] Could not conncet to database to insert scraper data"
            )
            return self.insertScraperDatabase(insert_values_db)

    # Click on all Load More btns
    def clickLoadMoreBtns(self, reloads):
        if reloads < 5:
            showMore_btn = self.browser.find_elements(
                By.CSS_SELECTOR, ".ls-button__text"
            )
            if len(showMore_btn) > 0:
                for btn in showMore_btn:
                    try:
                        btn.click()
                    except Exception:
                        self.getBackOnTrack(
                            "[Exception] Could not click btn load more even though it is on page"
                        )
                        return self.clickLoadMoreBtns(0)

                    # Now wait until btns might re-appear again
                    time.sleep(3)
                self.clickLoadMoreBtns(reloads + 1)

    def getBackOnTrack(self, message_user):
        todayStrf = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(todayStrf + ": " + message_user)
        # First check if user is still loggedin
        self.timeout_retries += 1
        # Check if we are still loggedin and login again
        if self.timeout_retries >= 3:
            self.timeout_retries = 0
            # Check if logged in
            loggedIn = self.loggedIn()
            if loggedIn is False:
                self.loginLinkfire()
            else:
                hasInternet = (
                    self.checkAndwaitForInternet()
                )  # Check if internet, if not, hold
                if hasInternet:
                    # It has internet. so we are probably being blocked. Restart the whole scraper
                    self.loginLinkfire()
        # Check if it is actually that annoying popup
        popups = self.browser.find_elements(By.CSS_SELECTOR, ".intercom-post-close")
        if len(popups) > 0:
            # Click on close button
            for close_btn_popup in popups:
                close_btn_popup.click()
        self.browser.refresh()
        time.sleep(2)  # Wait 5 seconds and try again

    def setStatusLinkfire(self, shorttag, active):
        """
        Function that sets a linkfire status to either active Yes or No based on shorttag
        :param shorttag: corresponds with shorttag in scrape_linkfires
        :param active: Yes/No
        :return: success status
        """
        try:
            ScrapeLinkfires.objects.filter(shorttag=shorttag).update(is_active=active)
            # self.db.execSQL("""UPDATE scrape_linkfires SET active=%s WHERE shorttag=%s""",
            #                 [active, shorttag], True)
        except Exception:
            # Query failed to execute
            # self.refreshDbConnection()
            print("[setStatusLinkfire] Trying again in 15 seconds...")
            time.sleep(15)
            return self.setStatusLinkfire(shorttag, active)

    def navigatePage(self, url):
        """
        Navigates to url and checks if we are logged out. If so login again
        :param url:
        :return:
        """
        self.browser.get(url)
        if self.loggedIn() is False:
            self.loginLinkfire()
            return self.navigatePage(url)

    def decrypt(self, password):
        base64_string = password
        base64_bytes = base64_string.encode("ascii")
        sample_string_bytes = base64.b64decode(base64_bytes)
        sample_string = sample_string_bytes.decode("ascii")
        return sample_string
