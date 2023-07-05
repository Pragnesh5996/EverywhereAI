from datetime import datetime as dt
from datetime import timedelta
import time
from decimal import Decimal
import requests
from abc import ABC
from apps.common.Optimizer import Optimizer as op
from apps.common.constants import PlatFormType, StatusType
from apps.tiktok.helper import Tiktok_api_handler as tt
from apps.facebook.helper import Facebook_api_handler as fb
from apps.snapchat.helper import Snapchat_api_handler as sc
from apps.common.models import (
    AdCampaigns,
    AdsetInsights,
    AdAdsets,
    SpendData,
    AdLogs,
    ScraperGroup,
    ProfitMargins,
)
from apps.scraper.models import (
    Settings,
    Spotify1DayData,
    Spotify28DaysData,
    SpotifyPlaylistData,
    SpotifyPayoutData,
)
from django.db.models import Max
from django.db.models.functions import TruncDate
from apps.linkfire.models import ScrapeLinkfires, LinkfireData
from apps.common.custom_exception import NullValueInDatabase
from apps.error_notifications.models import NotificationLogs


class AdOptimizer:
    def __init__(self, adPlatform, debug_mode, profile):
        self.adPlatform = adPlatform
        self.debug_mode = debug_mode
        self.lastCheckedHourDiff = dt.now()
        self.lastCheckedConversionRate = dt.now()
        self.lastRefreshDatabase = dt.now()
        self.secondDiff = None
        self.dollarToEuro = None
        self.testAdBudget = None
        self.adMinimalSpendDays = None
        self.adMinimalSpendEuro = None
        self.minScalingCtr = None
        self.testEndedVisits = None
        self.testEndedDays = None
        self.scaleBudget = None
        self.ctrSwingVisits = None
        self.ctrSwingPercentageOptimiser = None
        self.scheduleCtr = None
        self.daysMovingAverage = None
        self.profile = profile
        self.dsp = "Spotify"
        self.adPlatformConn = None
        if adPlatform == PlatFormType.TIKTOK:
            self.adPlatformConn = tt.TikTokAPI(debug_mode, self.profile)
        elif adPlatform == PlatFormType.FACEBOOK:
            self.adPlatformConn = fb.FacebookAPI(debug_mode, self.profile)
        elif adPlatform == PlatFormType.SNAPCHAT:
            self.adPlatformConn = sc.SnapchatAPI(debug_mode, self.profile)

        try:
            self.settings()
        except Exception as e:
            self.handleError(
                "Error in settings",
                "This error occured while starting the optimizer for this adplatform, the original message is: "
                + repr(e),
                "High",
            )

    def handleError(self, reason, message, priority="Low"):
        """
        Send an error message to the database, which will be picked up to be emailed

        reason (str): The (short) reason for the error, will be set as part of the email subject [example: "Spend value not found"]
        message (str): The message body of the email. Detailed description of the error, include the location and exact values where an error occured

        Returns: -
        """
        try:
            self.adPlatformConn.handleError(reason, message, priority)
        except Exception:
            scheduler_id = None
            subject = "[" + reason + "] "
            if priority == "Low":
                NotificationLogs.objects.create(
                    type_notification=subject,
                    notification_data=message,
                    email_sent="No",
                    scheduler_id=scheduler_id,
                )
            else:
                NotificationLogs.objects.create(
                    type_notification=subject,
                    notification_data=message,
                    email_sent="No",
                    priority=priority,
                    scheduler_id=scheduler_id,
                )

    def debugPrint(self, message):
        try:
            self.adPlatformConn.debugPrint(message)
        except Exception:
            if self.debug_mode:
                print(message)

    def updateSpendDataDays(self, days):
        """
        Instert into the spend_data table the sum of the past {days} of spend data per genre per country

        Returns: -
        """
        end_date = dt.now().date()
        start_date = dt.now().date() - timedelta(days=days)
        basicReport = self.adPlatformConn.get_report_day(start_date, end_date)
        countryDict = {}
        for report in basicReport:
            adset = AdAdsets.objects.filter(
                adset_id=report["adgroup_id"], ad_platform=self.adPlatform
            ).values_list("campaign_id", "target_country")
            if len(adset) != 0:
                campaign = AdCampaigns.objects.filter(
                    campaign_id=adset[0][0]
                ).values_list("scraper_group_id")
                scraper_group_id = campaign[0][0]
                country = adset[0][1]
                # skip adsets with multiple countries
                if len(country) > 2:
                    continue
                if scraper_group_id is None or scraper_group_id == "NULL":
                    continue
                if (scraper_group_id, country) in countryDict:
                    countryDict[(scraper_group_id, country)] += report["spend"]
                else:
                    countryDict[(scraper_group_id, country)] = report["spend"]
        bulk_update_spend_data_objects = []
        for countryEntry in countryDict:
            bulk_update_spend_data_objects.append(
                SpendData(
                    ad_platform=self.adPlatform,
                    scraper_group_id=countryEntry[0],
                    country=countryEntry[1],
                    spend=int(countryDict[countryEntry]),
                    data_days=days,
                    date_updated=dt.now(),
                )
            )
        SpendData.objects.bulk_create(bulk_update_spend_data_objects)

    def updateSpendData(self):
        """
        Get the data on the amount of money spend from the API from the pas X days, where X is the amount of days we check (found in the settings table).
        With this, calculate the totals and add it to the database

        Returns: -
        """
        self.updateSpendDataDays(7)
        self.updateSpendDataDays(28)

    def settings(self):
        """
        Update the general settings of the optimizer with values taken from the database.

        Returns: -
        """
        # set dollarToEuro
        try:
            results = Settings.objects.filter(
                variable="dollar_euro_conversion"
            ).values_list("value")
            self.dollarToEuro = Decimal(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "dollar_euro_conversion has not been set in the Settings table. Original error: "
                + repr(e)
            )

        # set optimization interval
        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='optimize_interval_hours'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(
                variable="optimize_interval_hours"
            ).values_list("value")
            self.secondDiff = int(results[0][0]) * 3600

        except Exception as e:
            raise NullValueInDatabase(
                "optimize_interval_hours has not been set in the Settings table. Original error: "
                + repr(e)
            )

        # settings
        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='test_ad_budget'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(variable="test_ad_budget").values_list(
                "value"
            )
            self.testAdBudget = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "test_ad_budget has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='ad_minimal_spend_days'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(
                variable="ad_minimal_spend_days"
            ).values_list("value")
            self.adMinimalSpendDays = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "ad_minimal_spend_days has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='ad_minimal_spend_euro'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(
                variable="ad_minimal_spend_euro"
            ).values_list("value")
            self.adMinimalSpendEuro = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "ad_minimal_spend_euro has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='min_ctr_for_scaling'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(
                variable="min_ctr_for_scaling"
            ).values_list("value")
            self.minScalingCtr = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "min_ctr_for_scaling has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='testEnded_visits'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(variable="testEnded_visits").values_list(
                "value"
            )
            self.testEndedVisits = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "testEnded_visits has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='testEnded_days'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(variable="testEnded_days").values_list(
                "value"
            )
            self.testEndedDays = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "testEnded_days has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='ctrSwing_visits'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(variable="ctrSwing_visits").values_list(
                "value"
            )
            self.ctrSwingVisits = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "ctrSwing_visits has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='ctrSwing_percentage_optimiser'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(
                variable="ctrSwing_percentage_optimiser"
            ).values_list("value")
            self.ctrSwingPercentageOptimiser = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "ctrSwing_percentage_optimiser has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='schedule_ctr'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(variable="schedule_ctr").values_list(
                "value"
            )
            self.scheduleCtr = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "schedule_ctr has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='days_moving_average'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(
                variable="days_moving_average"
            ).values_list("value")
            self.daysMovingAverage = int(results[0][0])

        except Exception as e:
            raise NullValueInDatabase(
                "days_moving_average has not been set in the Settings table. Original error: "
                + repr(e)
            )

        try:
            if self.adPlatform == "Tiktok":
                # results = self.db.execSQL(
                #     """SELECT value FROM settings WHERE variable='tiktok_scale_budget'""",
                #     (),
                #     False,
                # )
                results = Settings.objects.filter(
                    variable="tiktok_scale_budget"
                ).values_list("value")
                self.scaleBudget = int(results[0][0])
            if self.adPlatform == "Facebook":
                results = Settings.objects.filter(
                    variable="facebook_scale_budget"
                ).values_list("value")
                self.scaleBudget = int(results[0][0])
        except Exception as e:
            raise NullValueInDatabase(
                "[ADPLATFORM]_scale_budget has not been set in the Settings table. Original error: "
                + repr(e)
            )

    def setConversion(self):
        """
        Set the conversion rate USD:EUR with an API call an updates the value in the database.

        Returns: -
        """
        self.debugPrint("setConversion has been called")
        url = "https://v6.exchangerate-api.com/v6/d09c40c5fbe9bf61b7cfc352/latest/USD"
        response = requests.get(url)
        data = response.json()
        self.dollarToEuro = data["conversion_rates"]["EUR"]
        Settings.objects.filter(variable="dollar_euro_conversion").update(
            value=self.dollarToEuro, updated_at=dt.now()
        )

    # def optimizeAdsLoop(self):
    #     """
    #     Checks whether settings needs to be updated and which method has to be called to handle adsets.

    #     Update settings if time passed is more than interval on which ads are checked.
    #     Update conversion rate once per day.
    #     Get all adcampaigns and all corresponding adsets. Then for each check which method has to handle it (new, test or existing).

    #     Returns: -
    #     """
    #     time.sleep(
    #         3
    #     )  # Buffer between loops -- TODO bug; DB time verschilt iets van Python time, waardoor je een een underflow op timeDiff.days en daardoor een overflow op timeDiff.seconds krijgt. Fix dit een keer netjes
    #     dateTimeNow = dt.now()

    #     # If reset_minutes have passed, refresh DB connection
    #     # self.checkRefreshDB(dateTimeNow)

    #     # If optimize_interval_hours have passed, update settings and optimization interval
    #     self.checkUpdateSettings(dateTimeNow)

    #     # If a day has passed, update conversion rate USD:EUR and spend data for all countries
    #     self.checkUpdateDaily(dateTimeNow)

    #     # Optimize campaigns
    #     self.optimizeCampaigns()

    def optimizeCampaigns(self):
        """
        Optimize campaigns
        """
        campaigns = AdCampaigns.objects.filter(
            ad_platform=self.adPlatform, active="Yes", automatic="Yes"
        ).values_list(
            "campaign_id",
            "scraper_group_id",
            "campaign_name",
            "last_checked",
            "objective",
            "active",
        )
        for camp in campaigns:
            campaign_id = camp[0]
            genre = camp[1]
            if genre is None or genre == "NULL":
                if camp[3]:
                    timeDiff = dt.now() - camp[3]
                    if timeDiff.days >= 1 or timeDiff.seconds > self.secondDiff:
                        # campaignVars = (campaign_id, self.adPlatform)
                        # self.db.execSQL(
                        #     """UPDATE ad_campaigns SET last_checked = DEFAULT WHERE campaign_id=%s AND ad_platform=%s""",
                        #     campaignVars,
                        #     True,
                        # )
                        AdCampaigns.objects.filter(
                            campaign_id=campaign_id, ad_platform=self.adPlatform
                        ).update(last_checked=dt.now(), updated_at=dt.now())
                        message = (
                            "Genre is not set for campaign_id: "
                            + str(campaign_id)
                            + " with name: "
                            + camp[2]
                            + ". Please set the genre in the web application as soon as possible!"
                        )
                        self.handleError("Genre not set", message, "High")
                    continue
            if camp[4] != "Traffic" and camp[4] != "Conversions":
                continue  # Only optimize Traffic campaigns
            if camp[5] != "Yes":
                continue  # Only optimize active campaigns
            # campaignVars = (campaign_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_campaigns SET last_checked = DEFAULT WHERE campaign_id=%s AND ad_platform=%s""",
            #     campaignVars,
            #     True,
            # )
            AdCampaigns.objects.filter(
                campaign_id=campaign_id, ad_platform=self.adPlatform
            ).update(last_checked=dt.now(), updated_at=dt.now())

            # adSetVars = (camp[0], "Yes", self.adPlatform)
            # adSets = self.db.exec SQL(
            #     """SELECT adset_id, target_country, last_checked, linkfire_id, budget, bid, landingPage, ignore_until, manual_change_updated, manual_change_reason FROM ad_adsets WHERE campaign_id=%s AND active = %s AND ad_platform=%s""",
            #     adSetVars,
            #     False,
            # )
            adSets = AdAdsets.objects.filter(
                campaign_id=camp[0], active="Yes", ad_platform=self.adPlatform
            ).values_list(
                "adset_id",
                "target_country",
                "last_checked",
                "linkfire_id",
                "budget",
                "bid",
                "landingpage",
                "ignore_until",
                "manual_change_updated",
                "manual_change_reason",
            )
            print("adSets", adSets)
            for set in adSets:
                # justScaled = False
                adset_id = set[0]
                if camp[4] == "Traffic" or camp[4] == "Conversions":
                    settings = self.settings_dict()
                    adSet = AdSetTraffic(
                        campaign_id,
                        adset_id,
                        self.adPlatformConn,
                        self.adPlatform,
                        settings,
                    )
                else:
                    continue
                try:
                    adSet.optimize()
                except Exception as e:
                    self.handleError(
                        "Optimizer error", f"error for adset id :{adset_id}" + str(e)
                    )

    # def checkUpdateSettings(self, dateTimeNow):
    #     """
    #     if optimize_interval_hours have passed, update settings and optimization interval
    #     """
    #     timeDiff = dateTimeNow - self.lastCheckedHourDiff
    #     if timeDiff.days >= 1 or timeDiff.seconds > self.secondDiff:
    #         self.lastCheckedHourDiff = dateTimeNow
    #         try:
    #             self.settings()
    #         except Exception as e:
    #             self.handleError(
    #                 "Error in settings",
    #                 "This error occured while the optimizer was running, the original message is: "
    #                 + repr(e),
    #                 "High",
    #             )
    # raise

    # def checkUpdateDaily(self, dateTimeNow):
    #     """
    #     If a day has passed, update conversion rate USD:EUR and spend data for all countries
    #     """
    #     timeDiff = dateTimeNow - self.lastCheckedConversionRate
    #     if timeDiff.days >= 1:
    #         self.lastCheckedConversionRate = dateTimeNow
    #         try:
    #             self.setConversion()
    #         except:
    #             reason = "SetConversion error"
    #             message = (
    #                 "There was a problem while calling setConversion in OptimizeAdsloop. \nThe original error was: "
    #                 + repr(e)
    #             )
    #             self.handleError(reason, message, "High")
    #         try:
    #             self.updateSpendData()
    #         except Exception as e:
    #             reason = "updateSpendData error"
    #             message = (
    #                 "There was a problem while calling updateSpendData in OptimizeAdsloop. \nThe original error was: "
    #                 + repr(e)
    #             )
    #             self.handleError(reason, message, "High")

    def settings_dict(self):
        return {
            "testAdBudget": self.testAdBudget,
            "adMinimalSpendDays": self.adMinimalSpendDays,
            "adMinimalSpendEuro": self.adMinimalSpendEuro,
            "minScalingCtr": self.minScalingCtr,
            "testEndedVisits": self.testEndedVisits,
            "testEndedDays": self.testEndedDays,
            "ctrSwingVisits": self.ctrSwingVisits,
            "ctrSwingPercentageOptimiser": self.ctrSwingPercentageOptimiser,
            "scheduleCtr": self.scheduleCtr,
            "daysMovingAverage": self.daysMovingAverage,
            "dollarToEuro": self.dollarToEuro,
            "scaleBudget": self.scaleBudget,
        }

    # def optimizeAds(self):
    #     """
    #     Infinitely check and update ads. Call this function to start the program.

    #     Returns: -
    #     """
    #     # Time values to determine when settings and conversion rate have te be updated
    #     # self.debugPrint("optimizeAds has been called")
    #     # self.lastCheckedHourDiff = dt.now()
    #     # self.lastCheckedConversionRate = dt.now()
    #     while True:
    #         try:
    #             self.optimizeAdsLoop()
    #         except Exception as e:
    #             try:
    #                 self.refreshDbConnection()
    #             except Exception as e:
    #                 print(
    #                     "DataBase cannot reconnect due to the following error: "
    #                     + repr(e)
    #                 )
    #             try:
    #                 reason = "Optimizer stopped - will try to restart"
    #                 message = (
    #                     "The optimizer for: "
    #                     + self.adPlatform
    #                     + " has crashed and will ty to restart. Please check whether the optimizer is still running correctly. The original error that occured is: "
    #                     + repr(e)
    #                 )
    #                 self.handleError(reason, message, "High")
    #             except Exception as e:
    #                 print(
    #                     f"Another issue arose while trying to send a notification log. Original error:\n{repr(e)}"
    #                 )


class AdSet(ABC):
    def __init__(
        self, campaign_id, adset_id, adPlatformConn, adPlatform, settings
    ):  # 2 db
        self.campaign_id = campaign_id
        self.adset_id = adset_id
        # self.db = db
        self.adPlatformConn = adPlatformConn
        self.adPlatform = adPlatform


class AdSetTraffic(AdSet):
    def __init__(self, campaign_id, adset_id, adPlatformConn, adPlatform, settings):
        super().__init__(campaign_id, adset_id, adPlatformConn, adPlatform, settings)
        # Adset metadata
        self.settings = settings
        self.maturity = None
        self.country = None
        self.genre = None
        self.linkfire_id = None
        self.budget = None
        self.currentBid = None
        self.landingPage = None
        self.ignoreDate = None
        self.manualChangeUpdated = None
        self.manualReason = None
        self.shouldCheck = None
        self.testEndedDays = None

        # Variables that are used during optimization
        self.dsp = "Spotify"
        self.newBid = None
        self.payPerMil = None
        self.totalListenersCountry = None
        self.totalStreamsCountry = None
        self.totalListeners = None
        self.totalStreams = None
        self.totalListenersPlaylist = None
        self.totalStreamsPlaylist = None
        self.profitMargin = None
        self.inflation = None
        self.dataDays = None
        self.genre_mapping = None
        self.roas = None
        self.ctr = None
        self.spend = None
        self.extraMessage = None
        self.moneySpend = None
        self.updated_volume = None

    def debugPrint(self, message):
        try:
            self.adPlatformConn.debugPrint(message)
        except Exception:
            if self.debug_mode:
                print(message)

    def handleError(self, reason, message, priority="Low"):
        """
        Send an error message to the database, which will be picked up to be emailed

        reason (str): The (short) reason for the error, will be set as part of the email subject [example: "Spend value not found"]
        message (str): The message body of the email. Detailed description of the error, include the location and exact values where an error occured

        Returns: -
        """
        try:
            self.adPlatformConn.handleError(reason, message, priority)
        except Exception:
            scheduler_id = None
            subject = f"[{reason}] "
            if priority == "Low":
                NotificationLogs.objects.create(
                    type_notification=subject,
                    notification_data=message,
                    email_sent="No",
                    scheduler_id=scheduler_id,
                )

            else:
                NotificationLogs.objects.create(
                    type_notification=subject,
                    notification_data=message,
                    email_sent="No",
                    priority=priority,
                    scheduler_id=scheduler_id,
                )

    ##################
    ## Optimization ##
    ##################

    def optimize(self):
        """
        Optimize the current adSet
        """
        # Set all variables that are in the Database
        self.setVariables()

        # Skip adsets that have not yet passed the time interval to be checked again
        if (
            not self.shouldCheck and not self.maturity == "New"
        ):  # TODO check if this works as intended (eg; only new and ads-to-check go through)
            return

        # Skip adSets with multiple countries, no error log necessary
        if not self.isSingleCountry():
            return

        # Skip adSets with a link that is not a Linkfire
        if not self.isLinkfire():
            return

        # Skip adSets where there is not enough data (and add it to the DB if it was not yet added)
        if not self.isorrectLinkfire():
            return

        # Skip adsets where a manual change was made in the webapp, after handling the change
        if self.manualChangeUpdated == "No":
            self.updateManualChange()
            return

        # Skip adsets that have an ignore date in the future
        if self.ignoreDate > dt.now():
            self.checkIgnoreDate()
            return

        try:
            self.optimizeAdSet()
        except Exception:
            # variables = (self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE adset_id=%s AND ad_platform=%s""",
            #     variables,
            #     True,
            # )
            AdAdsets.objects.filter(
                adset_id=self.adset_id, ad_platform=self.adPlatform
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise

    def setVariables(self):
        """
        Set the variables from the database the AdSet object will use
        """
        try:
            # adSetVars = (self.adset_id, self.campaign_id, self.adPlatform)
            # set = self.db.execSQL(
            #     """SELECT target_country, last_checked, linkfire_id, budget, bid, landingPage, ignore_until, manual_change_updated, manual_change_reason, maturity FROM ad_adsets WHERE adset_id=%s AND campaign_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     False,
            # )
            set = AdAdsets.objects.filter(
                adset_id=self.adset_id,
                campaign_id=self.campaign_id,
                ad_platform=self.adPlatform,
            ).values_list(
                "target_country",
                "last_checked",
                "linkfire_id",
                "budget",
                "bid",
                "landingPage",
                "ignore_until",
                "manual_change_updated",
                "manual_change_reason",
                "maturity",
                "updated_volume_adset",
                "max_budget",
                "strategy",
            )
            if len(set) > 0:
                # raise RuntimeError(
                #     f"Adset with id {self.adset_id} and campaign id {self.campaign_id} was not found in the Database."
                # )
                adSet = set[0]

                self.country = adSet[0]
                self.linkfire_id = adSet[2]
                self.budget = adSet[3]
                # If a bid is set, convert it to Decimal
                self.currentBid = adSet[4]
                if self.currentBid:
                    self.currentBid = Decimal(self.currentBid)
                self.landingPage = adSet[5]
                self.ignoreDate = adSet[6]
                self.manualChangeUpdated = adSet[7]
                self.manualReason = adSet[8]
                self.maturity = adSet[9]
                self.updated_volume = adSet[10]
                self.maxBudget = adSet[11]
                self.strategy = adSet[12]
                # Check whether the current ad should be checked (ie: more time has passed than the required wait interval)
                lastChecked = adSet[1]
                # Convert to datetime always
                if not isinstance(lastChecked, dt):
                    lastChecked = dt.combine(lastChecked, dt.min.time())
                dateTimeNow = dt.now()
                timeDiff = dateTimeNow - lastChecked
                # results = self.db.execSQL(
                #     """SELECT value FROM settings WHERE variable='optimize_interval_hours'""",
                #     (),
                #     False,
                # )
                results = Settings.objects.filter(
                    variable="optimize_interval_hours"
                ).values_list("value")
                secondDiff = int(results[0][0]) * 3600
                self.shouldCheck = timeDiff.days >= 1 or timeDiff.seconds > secondDiff

                # adCampVars = (self.campaign_id, self.adPlatform)
                # camp = self.db.execSQL(
                #     """SELECT genre FROM ad_campaigns WHERE campaign_id=%s AND ad_platform=%s""",
                #     adCampVars,
                #     False,
                # )
                camp = AdCampaigns.objects.filter(
                    campaign_id=self.campaign_id, ad_platform=self.adPlatform
                ).values_list("genre")
                # if len(set) == 0:
                #     raise RuntimeError(
                #         f"Campaign with id {self.campaign_id} was not found in the Database."
                #     )
                campaign = camp[0]
                self.genre = campaign[0]
        except Exception as e:
            reason = "setVariables error"
            message = (
                "There was a problem while calling setVariables. \nThe original error was: "
                + repr(e)
            )
            self.handleError(reason, message, "High")

    def isSingleCountry(self):
        """
        Chech whether the adset serves only a single country
        """
        if len(self.country) > 2:
            # variables = (self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE adset_id=%s AND ad_platform=%s""",
            #     variables,
            #     True,
            # )
            AdAdsets.objects.filter(
                adset_id=self.adset_id, ad_platform=self.adPlatform
            ).update(last_checked=dt.now(), updated_at=dt.now())
            return False
        return True

    def isLinkfire(self):
        """
        Chech whether the landingpage is a linkfire url
        """
        if self.landingPage is None:
            return False
        elif self.landingPage.find("lnk.to") == -1:
            return False
        return True

    def isorrectLinkfire(self):
        """
        Chech whether the linkfire is added to the database, add it if it is not.
        Return
        - False: If there is not enough linkfire data
        - True: When the linkfire is already added and there is enough data
        """
        # TODO hier verder
        if self.linkfire_id is None:
            try:
                enoughData = self.addLinkfire()
            except Exception as e:
                # variables = (self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE adset_id=%s AND ad_platform=%s""",
                #     variables,
                #     True,
                # )
                AdAdsets.objects.filter(
                    adset_id=self.adset_id, ad_platform=self.adPlatform
                ).update(last_checked=dt.now(), updated_at=dt.now())
                reason = "Landingpage error"
                message = repr(e)
                self.handleError(reason, message)
                return False
            # if the ad is NOT new or if there is NOT enough data in the DB, skip it
            if self.maturity != "New" and not enoughData:
                # variables = (self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE adset_id=%s AND ad_platform=%s""",
                #     variables,
                #     True,
                # )
                AdAdsets.objects.filter(
                    adset_id=self.adset_id, ad_platform=self.adPlatform
                ).update(last_checked=dt.now(), updated_at=dt.now())
                return False
        return True

    def addLinkfire(self):
        """
        Add the linkfire connected to the adset_id in scrape_linkfire and add the ID to the ad_adsets table, if it does not yet have a linkfire_id

        adset_id (int): id of an adset that does not yet have a linkfire_id
        genre (str): genre of the adset
        landingPage (str): full linkfire link

        If the landingPage is incorrect (ie, there is no "/" found, or if it is NULL), the adset's last_checked will be updated and an error will be put
        into the database.
        If there is an existing shorttag related to the landingPage in scrape_linkfires, the correspinding ID will be added to linkfire_id in ad_adsets.
        If there is no existing shorttag, it will be added to scrape_linkfires and the ID will be added to linkfire_id in ad_adsets.

        Returns: enoughData (bool): if there is more than ctrSwingVisits on this linkfire for the relevant country, return True, otherwise False
        """
        self.debugPrint("addLinkfire has been called")
        enoughData = False
        shortTag = ""
        if self.landingPage is None:
            shortTagLocation = -1
        else:
            shortTagLocation = self.landingPage.rfind("/")

        if shortTagLocation == -1:
            # variables = (self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked=DEFAULT WHERE adset_id=%s AND ad_platform=%s""",
            #     variables,
            #     True,
            # )
            AdAdsets.objects.filter(
                adset_id=self.adset_id, ad_platform=self.adPlatform
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise NullValueInDatabase(
            #     "No or incorrect landingPage for adset: "
            #     + str(self.adset_id)
            #     + " in genre: "
            #     + self.genre
            # )
        else:  # If the linkfire shorttag is not yet added to the scrape_linkfires table, add it, then add the ID to the adset in ad_adsets. Otherwise just ad the ID to the adset in ad_adsets
            shortTag = self.landingPage[shortTagLocation + 1 :]
            # variables = (shortTag,)
            # result = self.db.execSQL(
            #     """SELECT id, active FROM scrape_linkfires WHERE shorttag=%s""",
            #     variables,
            #     False,
            # )
            result = ScrapeLinkfires.objects.filter(shorttag=shortTag).values_list(
                "id", "is_active"
            )
            if len(result) == 0:  # add the linkfire to the DB
                # variables = (self.landingPage, shortTag, self.genre, "Yes")
                # self.db.insertSQL(
                #     """INSERT INTO scrape_linkfires (url, shorttag, label, active, addedOn) VALUES (%s, %s, %s, %s, DEFAULT)""",
                #     variables,
                # )
                ScrapeLinkfires.objects.create(
                    url=self.landingPage,
                    shorttag=shortTag,
                    scraper_group_id=self.genre,
                    addedOn=dt.now(),
                )

                # variables = (shortTag,)
                # result = self.db.execSQL(
                #     """SELECT id FROM scrape_linkfires WHERE shorttag=%s""",
                #     variables,
                #     False,
                # )

                result = ScrapeLinkfires.objects.filter(shorttag=shortTag).values_list(
                    "id"
                )
            else:  # check if there is enough data to work with
                if result[0][1] == "No":
                    # variables = ("Yes", result[0][0])
                    # self.db.execSQL(
                    #     """UPDATE `scrape_linkfires` SET `active` = %s WHERE id = %s;""",
                    #     variables,
                    #     True,
                    # )
                    result = ScrapeLinkfires.objects.filter(id=result[0][0]).update(
                        is_active=StatusType.YES, updated_at=dt.now()
                    )
                # variables = (
                #     self.country,
                #     result[0][0],
                #     self.country,
                #     result[0][0],
                #     self.settings["testEndedDays"],
                # )
                # res = """SELECT visits FROM linkfire_data WHERE country_code=%s AND linkfire_id=%s AND `date` IN (SELECT MAX(`date`) FROM linkfire_data WHERE country_code=%s AND linkfire_id=%s GROUP BY DATE(`date`)) ORDER BY date DESC LIMIT %s""".format(
                #     variables
                # )
                latest_date_list = (
                    LinkfireData.objects.filter(
                        country_code=self.country, linkfire_id=result[0][0]
                    )
                    .values(date1=TruncDate("date"), id1=Max("id"))
                    .annotate(max_date=Max("date"))
                    .order_by("-date1")
                    .values_list("max_date", flat=True)
                )
                res = LinkfireData.objects.filter(
                    country_code=self.country,
                    linkfire_id=result[0][0],
                    date__in=latest_date_list,
                ).values_list("visits")[: self.settings["testEndedDays"]]
                visits = sum(Decimal(data[0]) for data in res)
                if visits >= self.settings["ctrSwingVisits"]:
                    enoughData = True
            # variables = (result[0][0], self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET linkfire_id=%s WHERE adset_id=%s AND ad_platform=%s""",
            #     variables,
            #     True,
            # )
            AdAdsets.objects.filter(
                adset_id=self.adset_id, ad_platform=self.adPlatform
            ).update(linkfire_id=result[0][0], updated_at=dt.now())
        return enoughData

    def updateManualChange(self):
        """
        Update manually changed ads with an API call to relevant platform
        """
        try:
            self.adPlatformConn.updateAdGroup(
                self.currentBid, self.budget, self.adset_id, self.campaign_id
            )  # API CALL
            # adSetVars = ("Yes", self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT, manual_change_updated = %s WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(
                last_checked=dt.now(), manual_change_updated="Yes", updated_at=dt.now()
            )

            # adSetVars = (
            #     self.adPlatform,
            #     self.campaign_id,
            #     self.adset_id,
            #     None,
            #     self.currentBid,
            #     f"Manually changed adset to bid: {self.currentBid} and budget {self.budget} with the following reason: {self.manualReason}.",
            # )
            # adSets = self.db.insertSQL(
            #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
            #     adSetVars,
            # )

            AdLogs.objects.create(
                ad_platform=self.adPlatform,
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                old_bid=None,
                new_bid=self.currentBid,
                reason=f"Manually changed adset to bid: {self.currentBid} and budget {self.budget} with the following reason: {self.manualReason}.",
                loggedOn=dt.now(),
            )
            self.manualChangeUpdated = "Yes"
        except Exception as e:
            self.handleError(
                "Could not update manual change",
                f"We could not update adset {self.adset_id} in campaign {self.campaign_id} that was manually changed in the webaspp. Original error:\n{repr(e)}",
                "High",
            )
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())
        if self.ignoreDate < dt.now() and self.manualChangeUpdated == "No":
            self.handleError(
                "Could not update manual change",
                f"Adset {self.adset_id} in campaign {self.campaign_id} that was manually changed in the webaspp has not been updated, but the set dat has passed. Please manually change the bid again with a date further in the future.",
                "High",
            )
            # adSetVars = ("Yes", self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET manual_change_updated = %s WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(manual_change_updated=dt.now(), updated_at=dt.now())

    def checkIgnoreDate(self):
        """
        Send a message if the ignore-until date is 1 day off, or on friday if it ends in the weekend
        """
        if self.ignoreDate - timedelta(days=1) < dt.now() or (
            dt.now().weekday() == 4 and self.ignoreDate - timedelta(days=3) < dt.now()
        ):
            reason = "Manually changed adset is near end date"
            message = f"The adset with adsetID: {self.adset_id}, adcampaignID: {self.campaign_id}, genre: {self.genre} and country: {self.country} is set to resume normal optimisation at: {self.ignoreDate}. If you want to keep running this ad with its current bid, please extend the end date in the web app. \nThe reason for manual change was: {self.manualReason}"
            self.handleError(reason, message)
        # variables = (self.adset_id, self.adPlatform)
        # self.db.execSQL(
        #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE adset_id=%s AND ad_platform=%s""",
        #     variables,
        #     True,
        # )
        AdAdsets.objects.filter(
            adset_id=self.adset_id, ad_platform=self.adPlatform
        ).update(last_checked=dt.now(), updated_at=dt.now())

    def optimizeAdSet(self):
        """
        Handle new ads
        """
        if self.maturity in ["New", "NewRetry"]:
            self.optimizeNewAd()

        # Handle test ads that have to be checked
        elif self.maturity == "Test":
            self.optimizeTestAd()
            # justScaled = True

        # Handle normal ads that have to be checked
        elif self.maturity == "Mature":
            self.optimizeMatureAd()

    ## New Adset ##

    def optimizeNewAd(self):
        """
        Optimize a new adset and update db values for it.
        """
        time.sleep(3)  # Wait for update API
        self.debugPrint("optimizeNewAd has been called")
        try:
            self.newBid = self.getBid()
            print("###", self.newBid)
            self.adPlatformConn.updateAdGroup(
                self.newBid,
                self.settings["testAdBudget"],
                self.adset_id,
                self.campaign_id,
            )  # API CALL
            # adSetVars = (
            #     self.newBid,
            #     self.settings["testAdBudget"],
            #     "Test",
            #     self.campaign_id,
            #     self.adset_id,
            #     self.adPlatform,
            # )
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT, bid = %s, budget = %s, maturity=%s WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(
                last_checked=dt.now(),
                bid=self.newBid,
                budget=self.settings["testAdBudget"],
                maturity="Test",
                updated_at=dt.now(),
            )
            data = self.buildDataString()
            # adSetVars = (
            #     self.adPlatform,
            #     self.campaign_id,
            #     self.adset_id,
            #     None,
            #     self.newBid,
            #     f"Newly created test ad {data}",
            # )
            # adSets = self.db.execSQL(
            #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
            #     adSetVars,
            #     False,
            # )
            AdLogs.objects.create(
                ad_platform=self.adPlatform,
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                old_bid=None,
                new_bid=self.newBid,
                reason=f"Newly created test ad {data}",
                loggedOn=dt.now(),
            )
        except (NullValueInDatabase, ArithmeticError, ValueError):
            # adSetVars = ("NewRetry", self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET maturity=%s, last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(maturity="NewRetry", last_checked=dt.now(), updated_at=dt.now())
            # raise

    ## Test Adset ##

    def scaleTestAd(self):
        """
        Scale a test adset and update db values for it.
        Calculates new bid and scales budget to value from DB
        """
        try:
            self.maturity = "Mature"
            self.newBid = self.getBid()
            newBudget = self.scaleBudget()
            self.debugPrint(
                f"API call om bid te updaten naar {self.newBid} en budget naar {self.settings['scaleBudget']}"
            )
            # self.adPlatformConn.updateAdGroup(self.newBid, self.settings['scaleBudget'], self.adset_id, self.campaign_id) #API CALL

            # adSetVars = (
            #     self.newBid,
            #     self.settings["scaleBudget"],
            #     self.maturity,
            #     self.campaign_id,
            #     self.adset_id,
            #     self.adPlatform,
            # )
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET bid=%s, budget=%s, last_checked = DEFAULT, maturity=%s WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(
                bid=self.newBid,
                budget=newBudget,
                last_checked=dt.now(),
                maturity=self.maturity,
                updated_at=dt.now(),
            )
            data = self.buildDataString()
            # adSetVars = (
            #     self.adPlatform,
            #     self.campaign_id,
            #     self.adset_id,
            #     self.currentBid,
            #     self.newBid,
            #     f"Scale test ad {data}",
            # )
            # adSets = self.db.execSQL(
            #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
            #     adSetVars,
            #     False,
            # )
            AdLogs.objects.create(
                ad_platform=self.adPlatform,
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                old_bid=self.currentBid,
                new_bid=self.newBid,
                reason=f"Scale test ad {data}",
                loggedOn=dt.now(),
            )
        except (NullValueInDatabase, ArithmeticError, ValueError):
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise

    def turnOffTestAd(self, ctr, totalVisits, totalDays):
        """
        Turn off bad test adset
        """
        reason = "Turn off test ad because "
        if (
            totalVisits >= self.settings["testEndedVisits"]
            and ctr < self.settings["minScalingCtr"]
        ):
            reason += f" amount of vists ({self.settings['testEndedVisits']}) for a test has been passed and CTR is {ctr} which is lower than the required {self.settings['minScalingCtr']}"
        if (
            totalDays == self.settings["testEndedDays"]
            and totalVisits < self.settings["testEndedVisits"]
        ):
            reason += f" amount of days ({self.settings['testEndedDays']}) for a test has been passed and total visits is {totalVisits} which is lower than the required {self.settings['testEndedVisits']}"
        self.debugPrint("API call om test adset te stoppen")
        # self.adPlatformConn.updateAdGroup(None, None, self.adset_id, self.campaign_id) #API CALL
        # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
        # self.db.execSQL(
        #     """UPDATE ad_adsets SET last_checked = DEFAULT, active = "No"  WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
        #     adSetVars,
        #     True,
        # )
        AdAdsets.objects.filter(
            campaign_id=self.campaign_id,
            adset_id=self.adset_id,
            ad_platform=self.adPlatform,
        ).update(last_checked=dt.now(), active="No", updated_at=dt.now())

        # adSetVars = (
        #     self.adPlatform,
        #     self.campaign_id,
        #     self.adset_id,
        #     self.currentBid,
        #     None,
        #     reason,
        # )
        # adSets = self.db.execSQL(
        #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
        #     adSetVars,
        #     False,
        # )
        AdLogs.objects.create(
            ad_platform=self.adPlatform,
            campaign_id=self.campaign_id,
            adset_id=self.adset_id,
            old_bid=self.currentBid,
            new_bid=None,
            reason=reason,
            loggedOn=dt.now(),
        )

    def updateBidTestAd(self):
        """
        Update test adset with new bid
        """
        try:
            self.newBid = self.getBid()
            if self.newBid == self.currentBid:
                self.debugPrint(
                    f"Old and new bid are the same, so no API call is necessary"
                )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(last_checked=dt.now(), updated_at=dt.now())

            elif self.newBid < self.currentBid:
                self.debugPrint(
                    f"The newly calculated bid for this test ad is lower than the previous one. We do not lower test ad bids, so no change was made."
                )
                # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(last_checked=dt.now(), updated_at=dt.now())

                data = self.buildDataString()
                data += "\nThe newly calculated bid for this test ad is lower than the previous one. We do not lower test ad bids, so no change was made."
                # adSetVars = (
                #     self.adPlatform,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.currentBid,
                #     self.newBid,
                #     f"Update test ad bid {data}",
                # )
                # adSets = self.db.execSQL(
                #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
                #     adSetVars,
                #     False,
                # )
                AdLogs.objects.create(
                    ad_platform=self.adPlatform,
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    old_bid=self.currentBid,
                    new_bid=self.newBid,
                    reason=f"Update test ad bid {data}",
                    loggedOn=dt.now(),
                )
            else:
                self.debugPrint(f"API call om bid te updaten naar {self.newBid}")
                # self.adPlatformConn.updateAdGroup(self.newBid, None, self.adset_id, self.campaign_id) #API CALL
                # adSetVars = (
                #     self.newBid,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.adPlatform,
                # )
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET bid=%s, last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(bid=self.newBid, last_checked=dt.now(), updated_at=dt.now())

                data = self.buildDataString()
                # adSetVars = (
                #     self.adPlatform,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.currentBid,
                #     self.newBid,
                #     f"Update test ad bid {data}",
                # )
                # adSets = self.db.execSQL(
                #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
                #     adSetVars,
                #     False,
                # )
                AdLogs.objects.create(
                    ad_platform=self.adPlatform,
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    old_bid=self.currentBid,
                    new_bid=self.newBid,
                    reason=f"Update test ad bid {data}",
                    loggedOn=dt.now(),
                )

        except (NullValueInDatabase, ArithmeticError, ValueError):
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise

    def optimizeTestAd(self):
        """
        optimize a test ad and update db values for it.

        Will scale ad if it is good enough, turn it off if it is bad or update the bid if more testing is required.

        Returns: -
        """
        ctr, totalVisits, totalDays = self.getTestAdValues()
        # Scale ad with updated bid
        if (
            totalVisits >= self.settings["testEndedVisits"]
            and ctr >= self.settings["minScalingCtr"]
        ):
            self.scaleTestAd()

        # Turn Off adset
        elif (
            totalVisits >= self.settings["testEndedVisits"]
            and ctr < self.settings["minScalingCtr"]
            or totalDays == self.settings["testEndedDays"]
            and totalVisits < self.settings["testEndedVisits"]
        ):
            self.turnOffTestAd(ctr, totalVisits, totalDays)

        # Keep running test with updated bid
        else:
            self.updateBidTestAd()

    def getTestAdValues(self):
        """
        Get CTR and total visits for checking whether to scale, turn off or keep testing a test adset
        """
        # variables = (
        #     self.country,
        #     self.linkfire_id,
        #     self.country,
        #     self.linkfire_id,
        #     self.settings["testEndedDays"],
        # )
        # results = self.db.execSQL(
        #     """ SELECT visits, ctr FROM linkfire_data WHERE country_code=%s AND linkfire_id=%s AND `date` IN (SELECT MAX(`date`) FROM linkfire_data WHERE country_code=%s AND linkfire_id=%s GROUP BY DATE(`date`)) ORDER BY date DESC LIMIT %s""",
        #     variables,
        #     False,
        # )
        latest_date_list = (
            LinkfireData.objects.filter(
                country_code=self.country, linkfire_id=self.linkfire_id
            )
            .values(date1=TruncDate("date"), id1=Max("id"))
            .annotate(max_date=Max("date"))
            .order_by("-date1")
            .values_list("max_date", flat=True)
        )
        results = LinkfireData.objects.filter(
            country_code=self.country,
            linkfire_id=self.linkfire_id,
            date__in=latest_date_list,
        ).values_list("visits", "ctr")[: self.settings["testEndedDays"]]

        totalVisits = 0
        totalDays = 0
        ctrList = []
        for data in results:
            totalVisits += Decimal(data[0])
            ctrPair = (Decimal(data[0]), Decimal(data[1]))  # (visits, ctr)
            ctrList.append(ctrPair)
            totalDays += 1

        ctr = 0
        for pair in ctrList:
            ctr += (pair[0] / Decimal(totalVisits)) * pair[1]
        ctr = round(ctr, 2)

        return ctr, totalVisits, totalDays

    def scaleBudget(self):
        """
        Scale the current budget with X percent.
        """
        # results = self.db.execSQL(
        #     """SELECT value FROM settings WHERE variable='budget_scale_percentage'""",
        #     (),
        #     False,
        # )
        results = Settings.objects.filter(
            variable="budget_scale_percentage"
        ).values_list("value")
        if len(results) == 0:
            raise RuntimeError("Please add scale_percentage to the Settings table.")
        else:
            perc = results[0][0]
        multiplier = 1 + int(perc) / 100
        if self.budget >= self.maxBudget:
            return self.maxBudget
        newBudget = self.budget * multiplier
        return self.maxBudget if newBudget > self.maxBudget else int(newBudget)

    ## Mature Adset ##

    def turnOffMatureAd(self):
        """
        Turn off a bad mature adset
        """
        # self.adPlatformConn.updateAdGroup(None, None, adset_id, campaign_id) #API CALL
        # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
        # self.db.execSQL(
        #     """UPDATE ad_adsets SET last_checked = DEFAULT, active = "No"  WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
        #     adSetVars,
        #     True,
        # )
        AdAdsets.objects.filter(
            campaign_id=self.campaign_id,
            adset_id=self.adset_id,
            ad_platform=self.adPlatform,
        ).update(last_checked=dt.now(), active="No", updated_at=dt.now())
        reason = f"Turn off ad, because money spend on this ad is: {self.moneySpend}, which is less than the required amount of {self.settings['adMinimalSpendEuro']} euro."
        # adSetVars = (
        #     self.adPlatform,
        #     self.campaign_id,
        #     self.adset_id,
        #     self.currentBid,
        #     None,
        #     reason,
        # )
        # adSets = self.db.execSQL(
        #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
        #     adSetVars,
        #     False,
        # )
        AdLogs.objects.create(
            ad_platform=self.adPlatform,
            campaign_id=self.campaign_id,
            adset_id=self.adset_id,
            old_bid=self.currentBid,
            new_bid=None,
            reason=reason,
            loggedOn=dt.now(),
        )

    def updateMatureAd_cpc(self):
        """
        Update mature adset with new bid
        """
        try:
            self.newBid = self.getBid()
            newBudget = self.scaleBudget()
            if self.newBid != self.currentBid or self.budget != newBudget:
                self.debugPrint(
                    f"API call om bid te updaten naar {self.newBid} en budget naar {newBudget}"
                )
                # self.adPlatformConn.updateAdGroup(self.newBid, None, self.adset_id, self.campaign_id) #API CALL
                # adSetVars = (self.newBid, self.campaign_id, self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET bid=%s, last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(bid=self.newBid, last_checked=dt.now(), updated_at=dt.now())

                data = self.buildDataString()
                # adSetVars = (
                #     self.adPlatform,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.currentBid,
                #     self.newBid,
                #     f"Update bid {data}",
                # )
                # adSets = self.db.insertSQL(
                #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
                #     adSetVars,
                # )
                AdLogs.objects.create(
                    ad_platform=self.adPlatform,
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    old_bid=self.currentBid,
                    new_bid=self.newBid,
                    reason=f"Update bid {data}",
                    loggedOn=dt.now(),
                )
            else:
                self.debugPrint(
                    f"Old and new bid & budget are the same, so no API call is necessary"
                )
                # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(last_checked=dt.now(), updated_at=dt.now())

        except (NullValueInDatabase, ArithmeticError, ValueError):
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise

    def getVolumeAdsetData(self):
        cpc = None
        spend = None
        # vars = (self.adPlatform, self.campaign_id, self.adset_id)
        # insights = self.db.execSQL(
        #     """SELECT cpc, spend, date FROM adset_insights WHERE platform=%s AND campaign_id=%s AND adset_id = %s ORDER BY date DESC LIMIT 1""",
        #     vars,
        #     False,
        # )
        insights = (
            AdsetInsights.objects.filter(
                ad_platform=self.adPlatform,
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
            )
            .values_list("cpc", "spend", "date")
            .order_by("-date")[:1]
        )

        yesterday = dt.now().date() - timedelta(days=1)

        if len(insights) != 0 and insights[0][2] == yesterday:
            cpc = insights[0][0]
            spend = insights[0][1]
            ins_available = True
        else:
            ins_available = False

        return cpc, spend, ins_available

    def getMaxSpend(self):
        # vars = ("volume_spend_percentage",)
        # spend_perc = self.db.execSQL(
        #     """SELECT value FROM settings WHERE variable=%s""", vars, False
        # )
        try:
            spend_perc = Settings.objects.filter(
                variable="volume_spend_percentage"
            ).values_list("value")
            spend_perc = spend_perc[0][0]
            max_spend = (int(spend_perc) / 100) * self.budget
            return max_spend, spend_perc
        except Exception as e:
            self.handleError(
                "Error in Settings table",
                "volume_spend_percentage has not been set in the Settings table. Original error: "
                + repr(e),
            )

    def updateMatureAd_volume(self):
        """
        Update mature adset with new bid
        """
        try:
            self.newBid = self.getBid()
            newBudget = self.scaleBudget()
        except (NullValueInDatabase, ArithmeticError, ValueError):
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )

            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())

        # Get max spend
        max_spend, spend_perc = self.getMaxSpend()

        # Get spend and cpc
        cpc, spend, ins_available = self.getVolumeAdsetData()

        # Get max_bid
        # vars = (self.adPlatform, self.campaign_id, self.adset_id)
        # res = self.db.execSQL(
        #     """SELECT max_cpc FROM ad_adsets WHERE ad_platform=%s AND campaign_id=%s AND adset_id=%s""",
        #     vars,
        #     False,
        # )

        if res := AdAdsets.objects.filter(
            campaign_id=self.campaign_id,
            adset_id=self.adset_id,
            ad_platform=self.adPlatform,
        ).values_list("max_cpc"):
            max_cpc = Decimal(res[0][0])

            yesterday = dt.now().date() - timedelta(days=1)
            # If the new bid is higher than the old one, just increase it (even if it was already updated today)
            if self.newBid > self.currentBid:
                self.debugPrint(
                    f"API call om bid te updaten naar {self.newBid} en budget naar {newBudget}"
                )
                # self.adPlatformConn.updateAdGroup(self.newBid, newBudget, self.adset_id, self.campaign_id) #API CALL
                # adSetVars = (
                #     self.newBid,
                #     newBudget,
                #     self.newBid,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.adPlatform,
                # )
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET bid=%s,budget=%s ,max_cpc=%s, last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(
                    bid=self.newBid,
                    budget=newBudget,
                    max_cpc=self.newBid,
                    last_checked=dt.now(),
                    updated_at=dt.now(),
                )
                data = self.buildDataString()
                # adSetVars = (
                #     self.adPlatform,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.currentBid,
                #     self.newBid,
                #     f"Update bid {data}",
                # )
                # self.db.insertSQL(
                #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
                #     adSetVars,
                # )
                AdLogs.objects.create(
                    ad_platform=self.adPlatform,
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    old_bid=self.currentBid,
                    new_bid=self.newBid,
                    reason=f"Update bid {data}",
                    loggedOn=dt.now(),
                )
            elif (
                self.updated_volume <= yesterday and ins_available
            ):  # If last CPC check was yesterday or earlier, check now
                # Increase with 0.01 if there is still room and spend was low, decrease with 0,01 if we overshot CPC
                message = ""
                if self.newBid == max_cpc:
                    if spend < max_spend and cpc < max_cpc:
                        self.newBid = self.currentBid + Decimal("0.01")
                        message = f"\nWe spend less ({spend}) than {spend_perc}% of the budget ({max_spend}) and CPC ({cpc}) was lower than our calculated maximum bid ({self.newBid}), so we increased the bid by 0.01."
                    elif cpc > max_cpc:
                        self.newBid = self.currentBid - Decimal("0.01")
                        message = f"\nCPC ({cpc}) was higher than our calculated maximum bid ({self.newBid}), so we decreased the bid by 0.01."
                elif self.newBid < cpc:
                    message = f"\nThe new bid ({self.newBid}) was lower than CPC ({cpc}), so we set the bid to the newly calculated bid."
                self.debugPrint(
                    f"API call om bid te updaten naar {self.newBid} en budget naar {newBudget}"
                )
                # self.adPlatformConn.updateAdGroup(self.newBid, newBudget, self.adset_id, self.campaign_id) #API CALL
                # adSetVars = (
                #     self.newBid,
                #     newBudget,
                #     self.newBid,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.adPlatform,
                # )
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET bid=%s,budget=%s, max_cpc=%s, last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(
                    bid=self.newBid,
                    budget=newBudget,
                    max_cpc=self.newBid,
                    last_checked=dt.now(),
                    updated_at=dt.now(),
                )
                data = self.buildDataString() + message

                # adSetVars = (
                #     self.adPlatform,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.currentBid,
                #     self.newBid,
                #     f"Update bid {data}",
                # )
                # adSets = self.db.insertSQL(
                #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
                #     adSetVars,
                # )
                AdLogs.objects.create(
                    ad_platform=self.adPlatform,
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    old_bid=self.currentBid,
                    new_bid=self.newBid,
                    reason=f"Update bid {data}",
                    loggedOn=dt.now(),
                )
            else:
                # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(last_checked=dt.now(), updated_at=dt.now())

    def get_minimize_bounds(self):
        results = Settings.objects.filter(
            variable="minimize_bid_lowest_spend_percentage"
        ).values_list("value")

        if len(results) == 0:
            raise RuntimeError(
                'Please set a value for "minimize_bid_lowest_spend_percentage" in the database'
            )
        else:
            low = results[0][0]

        results = Settings.objects.filter(
            variable="minimize_bid_highest_spend_percentage"
        ).values_list("value")
        if len(results) == 0:
            raise RuntimeError(
                'Please set a value for "minimize_bid_highest_spend_percentage" in the database'
            )
        else:
            high = results[0][0]
        return low, high
        # Minimize bid lowest perc = 30%
        # Minimize bid highest perc = 50%
        # if spend >= upperbound (50%) --> new bid = cpc + 0.01
        # if spend <=  lower_bound (30%) --> new bid is average of cpc + calculated new bid => bid = (cpc + newbid) / 2
        # else --> No change needed

    def get_minimize_bid(self, newBudget):
        lower_perc, upper_perc = self.get_minimize_bounds()
        lower_bound = self.budget * Decimal(lower_perc / 100)
        upper_bound = self.budget * Decimal(upper_perc / 100)
        cpc, spend, ins_available = self.getVolumeAdsetData()
        if ins_available:
            if spend >= upper_bound:
                bid = cpc + Decimal("0.01")
                bid = self.getBid_within_margin(bid)
                self.extraMessage = f"This adset strategy is set to lowest cost. Because it spent more than {upper_perc}% of its budget, we used cpc ({cpc}) + 1 cent (= {bid}) as new bid."
            elif spend <= lower_bound:
                bid = (cpc + self.newBid) / 2
                bid = self.getBid_within_margin(bid)
                self.extraMessage = f"This adset strategy is set to lowest cost. Because it spent less than {lower_perc}% of its budget, we used the average of cpc ({cpc}) calculated bid ({self.newBid}) as new bid."
            else:
                bid = self.currentBid
                self.extraMessage = f"This adset strategy is set to lowest cost. Because we spend between {lower_perc}% and {upper_perc}% of our budget, we made no change to the bid."
        else:
            bid = self.newBid
        return bid

    def updateMatureAd_minimize_cost(self):
        """
        Update mature adset with new bid
        """
        change_needed = False
        try:
            self.newBid = self.getBid()
            newBudget = self.scaleBudget()
            bid = self.get_minimize_bid(newBudget)
            change_needed = (bid != self.currentBid) or (
                self.budget != newBudget
            )  # If equal  -> no change needed, if not equal -> change needed
            self.newBid = bid
            if change_needed:
                self.debugPrint(
                    f"API call om bid te updaten naar {self.newBid} en budget naar {newBudget}"
                )
                # self.adPlatformConn.updateAdGroup(self.newBid, newBudget, self.adset_id, self.campaign_id) #API CALL
                # adSetVars = (
                #     self.newBid,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.adPlatform,
                # )
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET bid=%s, last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(bid=self.newBid, last_checked=dt.now(), updated_at=dt.now())
                data = self.buildDataString()
                # adSetVars = (
                #     self.adPlatform,
                #     self.campaign_id,
                #     self.adset_id,
                #     self.currentBid,
                #     self.newBid,
                #     f"Update bid {data}",
                # )
                # adSets = self.db.insertSQL(
                #     """INSERT INTO `ad_logs`(`ad_platform`, `campaign_id`, `adset_id`, `old_bid`, `new_bid`, `reason`, `loggedOn`) VALUES (%s, %s, %s, %s, %s, %s, DEFAULT)""",
                #     adSetVars,
                # )
                AdLogs.objects.create(
                    ad_platform=self.adPlatform,
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    old_bid=self.currentBid,
                    new_bid=self.newBid,
                    reason=f"Update bid {data}",
                    loggedOn=dt.now(),
                )
            else:
                self.debugPrint(
                    f"Old and new bid & budget are the same, so no API call is necessary"
                )
                # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(last_checked=dt.now(), updated_at=dt.now())
        except (NullValueInDatabase, ArithmeticError, ValueError):
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise
        # change_needed = (self.budget != newBudget) #If equal  -> no change needed, if not equal -> change needed

    def optimizeMatureAd(self):
        """
        optimize an existing ad and update db values for it.

        Will turn off an underperforming ad or update it with a new bid.

        Returns: -
        """
        # adSetVars = (self.adPlatform, self.genre, self.country)
        # results = self.db.execSQL(
        #     """SELECT spend FROM spend_data WHERE ad_platform=%s AND genre=%s AND country = %s ORDER BY date_updated DESC LIMIT 1""",
        #     adSetVars,
        #     False,
        # )
        results = (
            SpendData.objects.filter(
                ad_platform="Tiktok", genre="Piano Fruits", country="DE"
            )
            .order_by("-date_updated")
            .values_list("spend")
            .first()
        )
        try:
            self.moneySpend = Decimal(results[0])
            # Turn off underperforming ad
            if self.moneySpend < self.settings["adMinimalSpendEuro"]:
                self.turnOffMatureAd()

            # Update ad with new bid
            else:
                if self.strategy == "min_cpc":
                    self.updateMatureAd_cpc()  # Standard. Calculate bid based on data and set this bid.
                elif self.strategy == "max_volume":
                    self.updateMatureAd_volume()  # Increase bid if CPC is lower than calculated bid > Causing the average CPC to be around the calculated bid for maximum volume
                elif self.strategy == "minimize_cost":
                    self.updateMatureAd_minimize_cost()
        except Exception:
            # adSetVars = (self.campaign_id, self.adset_id, self.adPlatform)
            # self.db.execSQL(
            #     """UPDATE ad_adsets SET last_checked = DEFAULT WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
            #     adSetVars,
            #     True,
            # )
            AdAdsets.objects.filter(
                campaign_id=self.campaign_id,
                adset_id=self.adset_id,
                ad_platform=self.adPlatform,
            ).update(last_checked=dt.now(), updated_at=dt.now())
            # raise NullValueInDatabase(
            #     f"Money spend from table spend_data for platform: {self.adPlatform}, genre: {self.genre} and country: {self.country} is empty"
            # )

    ##############
    ## Bid calc ##
    ##############

    def buildDataString(self):
        """
        Build a string with the data we used for calculations so we can add it to the ad_logs table
        """
        data = "\nData used:"
        data += "\nPayout per Million (dol): " + str(self.payPerMil)
        data += (
            "\nTotal Streams Genre: "
            + str(self.totalStreams)
            + " \nTotal Listeners Genre: "
            + str(self.totalListeners)
        )
        data += (
            "\nTotal Streams Country: "
            + str(self.totalStreamsCountry)
            + " \nTotal Listeners Country: "
            + str(self.totalListenersCountry)
        )
        data += (
            "\nTotal Streams Playlist: "
            + str(self.totalStreamsPlaylist)
            + " \nTotal Listeners Playlist: "
            + str(self.totalListenersPlaylist)
        )
        data += "\nProfit Margin: " + str(self.profitMargin)
        data += "\nROAS: " + str(self.roas)
        data += "\nCTR: " + str(self.ctr)
        data += "\nInflation: " + str(self.inflation)
        data += "\nSpend: " + str(self.spend)
        data += "\nDOL:EUR conversion rate: " + str(self.settings["dollarToEuro"])
        data += "\nFinal Calculated Bid: " + str(self.newBid)
        if self.extraMessage is not None:
            data += "\n" + str(self.extraMessage)
        data += "\nFinal Bid: " + str(self.newBid)
        return data

    def getBid_within_margin(self, bid):
        """
        Collects all necessary data from the database, then calls and returns bid_calc from optimizer

        genre (str): the genre of the adset we want to get a bid for
        country (str): the country of the adset we want to get a bid for
        linkfire_id (int): the relevant linkfire_id for the adset
        newAd (bool): flag for whether or not the adset is new (calc without ROAS and CTR) or existing (calc with ROAS and CTR)

        Returns: bid (Decimal)
        """
        try:
            # results = self.db.execSQL(
            #     """SELECT value FROM settings WHERE variable='max_bid_change'""",
            #     (),
            #     False,
            # )
            results = Settings.objects.filter(variable="max_bid_change").values_list(
                "value"
            )
            max_change = int(results[0][0])
        except Exception:
            self.handleError(
                "Bid calculation",
                "max_bid_change has not been set in the Settings table. We have used 20 as default value.",
            )
            max_change = 20
        max_inc = Decimal("1") + Decimal(max_change) / Decimal("100")
        max_dec = Decimal("1") - Decimal(max_change) / Decimal("100")
        self.extraMessage = None
        if self.currentBid is not None and bid > self.currentBid:
            if (
                bid >= self.currentBid * max_inc
            ):  # If the new bid is higher than oldBid + {max_change}%
                newBid = self.currentBid * max_inc
                self.handleError(
                    "Calculated bid exceeded margin",
                    f"The bid (calculated at {round(bid, 2)}) for adset with id {self.adset_id} in campaign {self.campaign_id} on platform {self.adPlatform} was more than {max_change}% higher than the previous bid ({self.currentBid}), so we only raised it by {max_change}% (at least 1 cent) to {round(newBid, 2)}. Please check whether the original calculation was correct and manually change it if so.",
                )
                if round(newBid, 2) == bid:
                    newBid += 1
                self.extraMessage = f"The calculated bid ({round(bid, 2)}) was more than {max_change}% lower than the previous bid ({round(self.currentBid, 2)}), so we only raised it by {max_change}% (at least 1 cent) to {round(newBid, 2)}."
                bid = newBid
        elif self.currentBid is not None and bid <= self.currentBid:
            if (
                bid <= self.currentBid * max_dec
            ):  # If the new bid is lower than oldBid - {max_change}%
                newBid = self.currentBid * max_dec
                if round(newBid, 2) == bid:
                    newBid -= 1
                self.handleError(
                    "Calculated bid exceeded margin",
                    f"The bid (calculated at {round(bid, 2)}) for adset with id {self.adset_id} in campaign {self.campaign_id} on platform {self.adPlatform} was more than {max_change}% lower than the previous bid ({round(self.currentBid, 2)}), so we only lowered it by {max_change}% (at least 1 cent) to {newBid}. Please check whether the original calculation was correct and manually change it if so.",
                )
                self.extraMessage = f"The calculated bid ({round(bid, 2)}) was more than {max_change}% lower than the previous bid ({round(self.currentBid, 2)}), so we only lowered it by {max_change}% (at least 1 cent) to {round(newBid, 2)}."
                bid = newBid
        elif self.currentBid is None and bid > 1.00:
            reason = "New bid exceeded max of 1 EUR"
            message = f"After calculating the bid for adset with ID: {self.adset_id} on platform {self.adPlatform} the calculated total was: {bid}. Since this is higher than the allowed 1 EUR for new adsets, the bid has been set to 1 EUR."
            self.handleError(reason, message)
            self.extraMessage = (
                "New bid exceeded max of 1 EUR, so it has been set to 1 EUR"
            )
            bid = 1.00
        return bid

    def getBid(self):
        """
        Collects all necessary data from the database, then calls and returns bid_calc from optimizer
        genre (str): the genre of the adset we want to get a bid for
        country (str): the country of the adset we want to get a bid for
        linkfire_id (int): the relevant linkfire_id for the adset
        newAd (bool): flag for whether or not the adset is new (calc without ROAS and CTR) or existing (calc with ROAS and CTR)
        Returns: bid (Decimal)
        """
        self.debugPrint("getBid has been called")
        self.setBidValues()
        bid = op.bid_calc(
            self.payPerMil,
            self.totalStreams,
            self.totalListeners,
            self.totalStreamsCountry,
            self.totalListenersCountry,
            self.totalStreamsPlaylist,
            self.totalListenersPlaylist,
            self.profitMargin,
            roas=self.roas,
            ctr=self.ctr,
            inflation=self.inflation,
            dollar_to_euro=Decimal(self.settings["dollarToEuro"]),
        )
        bid = self.getBid_within_margin(bid)
        return round(bid, 2)

    def setBidValues(self):
        """
        Set the necessary values to calculate the bid
        """
        self.set_data_days()
        self.setGenreMapping()
        self.setPayPerMil()
        (
            self.totalListenersCountry,
            self.totalStreamsCountry,
        ) = self.getListenersAndStreamsCountry(self.country)
        self.totalListeners, self.totalStreams = self.getListenersAndStreamsCountry(
            "Worldwide"
        )
        (
            self.totalListenersPlaylist,
            self.totalStreamsPlaylist,
        ) = self.getListenersAndStreamsPlaylist()
        self.setProfitMargin()
        self.setInflation()
        self.setRoasAndCtr()

    def setRoasAndCtr(self):
        """
        Set the ROAS and CTR we use for calculation
        """
        if self.maturity == "Mature":
            self.spend = self.getSpend()
            roas = op.calculate_roas(
                self.totalStreamsCountry,
                self.payPerMil,
                self.spend,
                Decimal(self.settings["dollarToEuro"]),
            )
            ctr = self.calculateCtr()
            if ctr == -1:
                # 3 dagen uitzetten als er een swing is
                turnOffEndDate = dt.now() + timedelta(days=3)
                reason = "Paused because of a big CTR swing"
                # adSetVars = (
                #     turnOffEndDate,
                #     "Yes",
                #     reason,
                #     campaign_id,
                #     adset_id,
                #     self.adPlatform,
                # )
                # self.db.execSQL(
                #     """UPDATE ad_adsets SET ignore_until = %s, manual_change_updated = %s, manual_change_reason = %s WHERE campaign_id=%s AND adset_id=%s AND ad_platform=%s""",
                #     adSetVars,
                #     True,
                # )
                AdAdsets.objects.filter(
                    campaign_id=self.campaign_id,
                    adset_id=self.adset_id,
                    ad_platform=self.adPlatform,
                ).update(
                    ignore_until=turnOffEndDate,
                    manual_change_updated="Yes",
                    manual_change_reason=reason,
                    updated_at=dt.now(),
                )
                # raise CTRSwingException()
        else:
            ctr = self.settings["scheduleCtr"]
            roas = 1
            self.spend = 0
        if ctr != -1:
            self.roas = roas
            self.ctr = ctr

    def calculateCtr(self):
        """
        Calculates CTR for combination of country and linkfire_id

        Calculation will calculate the weighed average CTR from (at least) the last ctrSwingVisits visits.
        If there is not enough vists in the past testEndedDays days, throw exception.
        Also calculate the weighed average CTR from (at least) the last ctrSwingVisits visits before the CTR calculated earlier.
        If the difference is more than ctrSwingPercentageOptimiser, throw exception

        country (str): the country of the adset we want to get a bid for
        linkfire_id (int): the relevant linkfire_id for the adset

        Returns: CTR (Decimal)
                 -1 if there is a large swing in the CTR
        """
        # variables = (
        #     self.country,
        #     self.linkfire_id,
        #     self.country,
        #     self.linkfire_id,
        #     self.settings["testEndedDays"],
        # )
        # results = self.db.execSQL(
        #     """ SELECT visits, ctr FROM linkfire_data WHERE country_code=%s AND linkfire_id=%s AND `date` IN (SELECT MAX(`date`) FROM linkfire_data WHERE country_code=%s AND linkfire_id=%s GROUP BY DATE(`date`)) ORDER BY date DESC LIMIT %s""",
        #     variables,
        #     False,
        # )
        latest_date_list = (
            LinkfireData.objects.filter(
                country_code=self.country, linkfire_id=self.linkfire_id
            )
            .values(date1=TruncDate("date"), id1=Max("id"))
            .annotate(max_date=Max("date"))
            .order_by("-date1")
            .values_list("max_date", flat=True)
        )
        results = LinkfireData.objects.filter(
            country_code=self.country,
            linkfire_id=self.linkfire_id,
            date__in=latest_date_list,
        ).values_list("visits", "ctr")[: self.settings["testEndedDays"]]

        visits = 0
        ctrList = []
        prevVisits = 0
        prevCtrList = []
        for data in results:
            if visits < self.settings["ctrSwingVisits"]:
                visits += Decimal(data[0])
                ctrPair = (Decimal(data[0]), Decimal(data[1]))  # (visits, ctr)
                ctrList.append(ctrPair)
            else:
                prevVisits += Decimal(data[0])
                ctrPair = (Decimal(data[0]), Decimal(data[1]))  # (visits, ctr)
                prevCtrList.append(ctrPair)
                if prevVisits >= self.settings["ctrSwingVisits"]:
                    break
        # ctr = 0
        if visits > self.settings["ctrSwingVisits"]:
            # raise NullValueInDatabase(
            #     f"There are less than {self.settings['ctrSwingVisits']} clicks on ad with linkfire ID: {self.linkfire_id} and country: {self.country}"
            # )
            # for pair in ctrList:
            #     ctr += (pair[0] / visits) * pair[1]
            ctr = sum((pair[0] / visits) * pair[1] for pair in ctrList)
            # If we only use 1 day of data and we have enough data to compare it to previous ctr, compare the values to check for a swing (due to corrupted data or weird outliers)
            if len(ctrList) == 1 and prevVisits >= self.settings["ctrSwingVisits"]:
                # prevCtr = 0
                # for pair in prevCtrList:
                #     prevCtr += (pair[0] / visits) * pair[1]
                prevCtr = sum(pair[0] / visits * pair[1] for pair in prevCtrList)
                if abs(prevCtr - ctr) > self.settings["ctrSwingPercentageOptimiser"]:
                    reason = "CTR swing"
                    message = (
                        "There is a swing of "
                        + str(abs(prevCtr - ctr))
                        + "%, which is more than the allowed "
                        + str(self.settings["ctrSwingPercentageOptimiser"])
                        + "% on adgroup with linkfire ID: "
                        + str(self.linkfire_id)
                        + " and country: "
                        + self.country
                    )
                    self.handleError(reason, message)
                    return -1
            return ctr

    def setPayPerMil(self):
        """
        Set the payout per million streams for calculation
        """
        try:
            # variables = (self.country, self.dsp)
            # results = self.db.execSQL(
            #     """SELECT dollar_per_mil FROM spotify_payout_data WHERE country=%s and dsp=%s ORDER BY date_statement DESC LIMIT 1""",
            #     variables,
            #     False,
            # )
            results = (
                SpotifyPayoutData.objects.filter(country=self.country, dsp=self.dsp)
                .values_list("dollar_per_mil")
                .order_by("-date_statement")[:1]
            )
            self.payPerMil = Decimal(results[0][0])
        except Exception:
            self.handleError(
                "setPayPerMil error",
                f"dollar_per_mil for country: {self.country} and dsp: {self.dsp} in method getBid in file Adopimizer.py is NULL",
            )

    def calcSevenDaySpotifyData(self, genreMapped, country):
        """
        Calculate the average maximum listeners and total streams from the past 7 days for all spotify profiles for the given country and genre
        """
        # vars = (genreMapped, country)
        # res = self.db.execSQL(
        #     """SELECT DISTINCT spotify_profile_id FROM spotify_1day_data WHERE genre=%s AND country=%s""",
        #     vars,
        #     False,
        # )
        res = (
            Spotify1DayData.objects.filter(
                scraper_group_id=genreMapped, country=country
            )
            .values_list("spotify_profile_id")
            .distinct()
        )
        max_listeners = 0
        total_streams = 0
        for profile in res:
            totalListenersCountry = 0
            totalStreamsCountry = 0
            # variables = (genreMapped, profile[0], country, self.dataDays)
            # results = self.db.execSQL(
            #     """SELECT listeners, streams FROM spotify_1day_data WHERE genre=%s AND spotify_profile_id=%s AND country=%s ORDER BY `date` DESC LIMIT %s""",
            #     variables,
            #     False,
            # )
            results = (
                Spotify1DayData.objects.filter(
                    scraper_group_id=genreMapped,
                    spotify_profile_id=profile[0],
                    country=country,
                )
                .values_list("listeners", "streams")
                .order_by("-date")[: self.dataDays]
            )
            if len(results) != 0:
                i = 0
                for res in results:
                    totalListenersCountry += int(res[0])
                    totalStreamsCountry += int(res[1])
                    i += 1
                avgListenersCountry = totalListenersCountry / i
                avgStreamsCountry = totalStreamsCountry / i
            else:
                self.handleError(
                    "No Spotify data found",
                    f"There was no Spotify listeners and streams data found for genre: {genreMapped}, country: {country} and Spotify profile id: {profile[0]}.",
                )
            max_listeners = max(avgListenersCountry, max_listeners)
            total_streams += avgStreamsCountry
        return max_listeners, total_streams

    def calcTwEightDaySpotifyData(self, genreMapped, country):
        """
        Take the maximum listeners and total streams from the past 28 days for all spotify profiles for the given country and genre
        """
        # vars = (genreMapped, country)
        # res = self.db.execSQL(
        #     """SELECT DISTINCT spotify_profile_id FROM spotify_28days_data WHERE genre=%s AND country=%s""",
        #     vars,
        #     False,
        # )
        res = (
            Spotify28DaysData.objects.filter(
                scraper_group_id=genreMapped, country=country
            )
            .values_list("spotify_profile_id")
            .distinct()
        )
        max_listeners = 0
        total_streams = 0
        for profile in res:
            totalListenersCountry = 0
            totalStreamsCountry = 0
            # variables = (genreMapped, profile[0], country)
            # results = self.db.execSQL(
            #     """SELECT listeners, streams FROM spotify_28days_data WHERE genre=%s AND spotify_profile_id=%s AND country=%s ORDER BY `date` DESC LIMIT 1""",
            #     variables,
            #     False,
            # )
            results = (
                Spotify28DaysData.objects.filter(
                    scraper_group_id=genreMapped,
                    spotify_profile_id=profile[0],
                    country=country,
                )
                .values_list("listeners", "streams")
                .order_by("-date")[:1]
            )
            if len(results) != 0:
                totalListenersCountry = results[0][0]
                totalStreamsCountry = results[0][1]
            else:
                self.handleError(
                    "No Spotify data found",
                    f"There was no Spotify listeners and streams data found for genre: {genreMapped}, country: {country} and Spotify profile id: {profile[0]}.",
                )
            max_listeners = max(totalListenersCountry, max_listeners)
            total_streams += totalStreamsCountry
        return max_listeners, total_streams

    def get_genre_mapping(self, dataDays):
        """
        Get genre mapping (and keep current genre if there is no mapping)
        """
        if dataDays == 7:
            map_days = "7day_data_map"
        elif dataDays == 28:
            map_days = "28day_data_map"
        elif dataDays == "playlist_data_map":
            map_days = "playlist_data_map"
        # else:
        #     raise RuntimeError(
        #         f"The number of days used to calculate the bid should be set to 7 or 28, but it is {dataDays}"
        #     )

        genre_map = self.genre_mapping[self.genre][map_days]
        if genre_map is not None:
            genreMapped = genre_map
        else:
            genreMapped = self.genre
        return genreMapped

    def set_data_days(self):
        """
        Get amount days to take data from
        """
        # vars = (self.genre,)
        # res = self.db.execSQL(
        #     """SELECT data_days FROM genres WHERE genre=%s""", vars, False
        # )
        res = ScraperGroup.objects.filter(group_name=self.genre).values_list(
            "data_days"
        )
        if len(res) != 0:
            self.dataDays = int(res[0][0])
        else:
            self.handleError(
                "set_data_days error",
                f"Genre {self.genre} was not found in the 'genres' database table. please add it in the webapp.",
            )

    def getListenersAndStreamsCountry(self, country):
        """
        Get the number of listeners and streams for the given country and genre
        """
        genreMapped = self.get_genre_mapping(self.dataDays)

        if self.dataDays == 7:
            max_listeners, total_streams = self.calcSevenDaySpotifyData(
                genreMapped, country
            )
        elif self.dataDays == 28:
            max_listeners, total_streams = self.calcTwEightDaySpotifyData(
                genreMapped, country
            )
        return max_listeners, total_streams

    def calcPlaylistSevenDays(self, genreMapped):
        """
        Calculate the average maximum listeners and total streams from the past 7 days for all spotify profiles for the given genre
        """
        # vars = (genreMapped, "1day")
        # res = self.db.execSQL(
        #     """SELECT DISTINCT spotify_profile_id FROM spotify_playlist_data WHERE genre=%s AND time_filter=%s""",
        #     vars,
        #     False,
        # )
        res = (
            SpotifyPlaylistData.objects.filter(
                scraper_group_id=genreMapped, time_filter="1day"
            )
            .values_list("spotify_profile_id")
            .distinct()
        )
        max_listeners = 0
        total_streams = 0
        for profile in res:
            totalListenersPlaylist = 0
            totalStreamsPlaylist = 0
            # variables = (genreMapped, profile[0], "1day", 7)
            # results = self.db.execSQL(
            #     """SELECT playlist_listeners, playlist_streams, date FROM spotify_playlist_data WHERE genre=%s AND spotify_profile_id=%s AND time_filter=%s ORDER BY `date` DESC LIMIT %s""",
            #     variables,
            #     False,
            # )
            results = (
                SpotifyPlaylistData.objects.filter(
                    scraper_group_id=genreMapped,
                    spotify_profile_id=profile[0],
                    time_filter="1day",
                )
                .values_list("playlist_listeners", "playlist_streams", "date")
                .order_by("-date")[:7]
            )
            if len(results) != 0:
                i = 0  # Final i should be the LIMIT value which is dataDays (unless we have fewer results)
                sumUp_totalListenersPlaylist = 0
                sumUp_totalStreamsPlaylist = 0
                for x in results:
                    i += 1
                    sumUp_totalListenersPlaylist += x[0]
                    sumUp_totalStreamsPlaylist += x[1]
                totalListenersPlaylist = sumUp_totalListenersPlaylist / i
                totalStreamsPlaylist = sumUp_totalStreamsPlaylist / i
            else:
                self.handleError(
                    "No Spotify data found",
                    f"There was no Spotify playlist listeners and streams data found for genre: {genreMapped} and Spotify profile id: {profile[0]}.",
                )
            max_listeners = max(totalListenersPlaylist, max_listeners)
            total_streams += totalStreamsPlaylist
        return max_listeners, total_streams

    def calcPlaylistTwEightDays(self, genreMapped):
        """
        Take the maximum listeners and total streams from the past 28 days for all spotify profiles for the given genre
        """
        # vars = (genreMapped, "28day")
        # res = self.db.execSQL(
        #     """SELECT DISTINCT spotify_profile_id FROM spotify_playlist_data WHERE genre=%s AND time_filter=%s""",
        #     vars,
        #     False,
        # )
        res = (
            SpotifyPlaylistData.objects.filter(
                scraper_group_id=genreMapped, time_filter="28day"
            )
            .values_list("spotify_profile_id")
            .distinct()
        )
        max_listeners = 0
        total_streams = 0
        for profile in res:
            totalListenersPlaylist = 0
            totalStreamsPlaylist = 0
            # variables = (genreMapped, profile[0], "28day")
            # results = self.db.execSQL(
            #     """SELECT playlist_listeners, playlist_streams, date FROM spotify_playlist_data WHERE genre=%s AND spotify_profile_id=%s AND time_filter=%s ORDER BY `date` DESC LIMIT 1""",
            #     variables,
            #     False,
            # )
            results = (
                SpotifyPlaylistData.objects.filter(
                    scraper_group_id=genreMapped,
                    spotify_profile_id=profile[0],
                    time_filter="28day",
                )
                .values_list("playlist_listeners", "playlist_streams", "date")
                .order_by("-date")[:1]
            )
            if len(results) != 0:
                totalListenersPlaylist = results[0][0]
                totalStreamsPlaylist = results[0][1]
            else:
                self.handleError(
                    "No Spotify data found",
                    f"There was no Spotify playlist listeners and streams data found for genre: {genreMapped} and Spotify profile id: {profile[0]}.",
                )
            max_listeners = max(totalListenersPlaylist, max_listeners)
            total_streams += totalStreamsPlaylist
        return max_listeners, total_streams

    def getListenersAndStreamsPlaylist(self):
        """
        Get the number of listeners and streams for the given genre
        """
        genreMapped = self.get_genre_mapping("playlist_data_map")

        if self.dataDays == 7:
            max_listeners, total_streams = self.calcPlaylistSevenDays(genreMapped)
        elif self.dataDays == 28:
            max_listeners, total_streams = self.calcPlaylistTwEightDays(genreMapped)
        else:
            self.handleError(
                "Incorrect nr of days",
                f"The number of days used to calculate the bid should be set to 7 or 28, but it is {self.dataDays}",
                "High",
            )
            return None, None
        return max_listeners, total_streams

    def setProfitMargin(self):
        """
        Set the profit margin used of calculation
        """
        try:
            # variables = (self.adPlatform,)
            # results = self.db.execSQL(
            #     """SELECT profit_margin FROM profit_margins WHERE ad_platform=%s""",
            #     variables,
            #     False,
            # )
            results = ProfitMargins.objects.filter(
                ad_platform=self.adPlatform
            ).values_list("profit_margin")
            self.profitMargin = int(results[0][0])
        except Exception:
            self.handleError(
                "setProfitMargin error",
                "profit_margin in method getBid for platform "
                + self.adPlatform
                + " in file Adopimizer.py is NULL",
            )

    def setInflation(self):
        """
        Set the inflation used of calculation
        """
        try:
            # variables = (self.genre,)
            # results = self.db.execSQL(
            #     """SELECT inflation_value FROM genres WHERE genre=%s""",
            #     variables,
            #     False,
            # )
            results = ScraperGroup.objects.filter(group_name=self.genre).values_list(
                "inflation_value"
            )
            self.inflation = int(results[0][0])
        except Exception:
            self.handleError(
                "setInflation()",
                "Inflation value for genre: "
                + self.genre
                + " in method getBid in file Adopimizer.py is NULL",
            )

    def getSpend(self):
        """
        Get avarage spend
        """
        try:
            # variables = (self.adPlatform, self.genre, self.country, self.dataDays)
            # results = self.db.execSQL(
            #     """SELECT spend FROM spend_data WHERE ad_platform=%s AND genre=%s AND country=%s AND data_days=%s ORDER BY date_updated DESC LIMIT 1""",
            #     variables,
            #     False,
            # )
            results = (
                SpendData.objects.filter(
                    ad_platform=self.adPlatform,
                    scraper_group_id=self.genre,
                    country=self.country,
                    data_days=self.dataDays,
                )
                .values_list("spend")
                .order_by("-date_updated")[:1]
            )
            return Decimal(results[0][0]) / self.dataDays
        except Exception:
            self.handleError(
                "getSpend error",
                f"Spend for adPlatform: {self.adPlatform} and genre: {self.genre} and country: {self.country} in method getBid in file Adopimizer.py is NULL",
            )

    def setGenreMapping(self):
        """
        Fetches data from `genre` table and fills dict with genre mappings for data
        :return: dict
        """
        genre_mapping = {}
        # results = self.db.execSQL(
        #     """SELECT genre, 1day_data_map, 7day_data_map, 28day_data_map, playlist_data_map FROM genres""",
        #     (),
        #     False,
        # )
        results = ScraperGroup.objects.all().values_list(
            "group_name",
            "1day_data_map",
            "7day_data_map",
            "28day_data_map",
            "playlist_data_map",
        )
        if results != 0:
            for x in results:
                genre = x[0]
                one_day_data_map = x[1]
                sev_day_data_map = x[2]
                twei_day_data_map = x[3]
                playlist_day_data_map = x[4]
                sub_dict = {
                    "1day_data_map": one_day_data_map,
                    "7day_data_map": sev_day_data_map,
                    "28day_data_map": twei_day_data_map,
                    "playlist_data_map": playlist_day_data_map,
                }
                genre_mapping.update({genre: sub_dict})
        self.genre_mapping = genre_mapping
