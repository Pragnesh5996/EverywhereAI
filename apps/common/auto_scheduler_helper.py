from apps.common.constants import PlatFormType, PlacementType, AdvantageplacementType

from apps.common.models import (
    AdCreativeIds,
    AdScheduler,
    Language,
    Day_Parting,
    SchedulePresetsSettings,
    SchedulePresets,
    AutoSchedulerDraft,
)
from apps.error_notifications.models import NotificationLogs
from django.db.models import Count
from django.contrib.postgres.aggregates.general import ArrayAgg
from datetime import datetime
from collections import deque
from apps.facebook.models import FacebookUsers
import os
import shutil
from SF import settings


class Scheduler:
    def __init__(self, scheduling_info, user_uid, auth_user) -> None:
        # common value
        self.uuid = user_uid
        self.user = auth_user
        self.uploadsesid = scheduling_info.get("uploadsesid")
        self.group_id = scheduling_info.get("group_id")
        self.objective = scheduling_info.get("campaign_objective")
        self.budget = scheduling_info.get("budget") or None
        self.bid_strategy = scheduling_info.get("bid_strategy")
        self.bid = scheduling_info.get("bid_cost") or None
        self.countries_obj = scheduling_info.get("countries")
        self.countries = (
            ",".join(country["Code"] for country in self.countries_obj)
            if self.countries_obj
            else None
        )
        self.is_bundle_countries = scheduling_info.get("is_bundle_countries")
        self.is_language = scheduling_info.get("is_language")
        self.languages = scheduling_info.get("languages")
        self.schedule_date = scheduling_info.get("schedule_date")

        self.facebook = scheduling_info.get("Facebook")
        self.tiktok = scheduling_info.get("Tiktok")
        self.snapchat = scheduling_info.get("Snapchat")
        self.key = None
        self.prfile_id = None
        self.creative_id_list = []
        self.facebook_creative_id_list = []
        self.tiktok_snap_creative_id_list = []
        self.scheduling_info = scheduling_info
        # Autoplacement
        self.auto_placement = None
        self.placement_list = None
        # platfrom wise value
        self.adcreative_obj = self.adcrartive_detail()
        if self.facebook:
            self.key = "key"
            self.prfile_id = self.facebook.get("profile_id")
            self.user_id = FacebookUsers.objects.filter(
                profile_id=self.prfile_id
            ).values_list("user_id", flat=True)[0]
            self.auto_placement = self.facebook.get("auto_placement")
            self.placement_list = self.facebook.get("placement_list").split(",")
            self.creative_calculation(platfrom=PlatFormType.FACEBOOK)
            self.facebook_scheduler()

        if self.tiktok:
            self.key = "code"
            self.prfile_id = self.tiktok.get("profile_id")
            self.user_id = None
            self.creative_calculation(platfrom=PlatFormType.TIKTOK)
            self.tiktok_scheduler()

        if self.snapchat:
            self.key = "id"
            self.prfile_id = self.snapchat.get("profile_id")
            self.user_id = None
            self.creative_calculation(platfrom=PlatFormType.SNAPCHAT)
            self.snapchat_scheduler()

        # delete Null placement creative
        AdCreativeIds.objects.filter(id__in=self.creative_id_list).delete()

        # AutoschedulerDraft record delete
        AutoSchedulerDraft.objects.filter(user_id=self.user).delete()

        # Preset
        self.preset = scheduling_info.get("preset")
        self.preset_setup(json_data=scheduling_info, preset=self.preset)
        
        # Get the list of scheduler IDs where creative is null
        ids = AdScheduler.objects.filter(
            uploadsesid=self.uploadsesid
        ).exclude(
            id__in=AdCreativeIds.objects.filter(uploadsesid=self.uploadsesid).values("scheduler_id")
        ).values_list("id", flat=True)
        # Delete the scheduler records in bulk
        AdScheduler.objects.filter(id__in=ids).delete()

    def handleerror(self, reason, message):
        """
        Puts an error message in database
        Parameters reason, message (String, String)
        Returns: None
        """
        subject = f"[{reason}] Autoscheduler Save."
        notification = '{"reason":' + subject + ', "text_body":' + message + "}"
        NotificationLogs.objects.create(
            type_notification=reason,
            notification_data=notification,
            notification_sent="No",
        )

    def adcrartive_detail(self):
        try:
            adcreative_obj = (
                AdCreativeIds.objects.filter(
                    uploadsesid=self.uploadsesid,
                    placement_type__in=[
                        PlacementType.POST,
                        PlacementType.STORY,
                        PlacementType.REELS,
                        PlacementType.OTHER,
                    ],
                )
                .values_list("creative_type", "placement_type")
                .annotate(
                    count=Count("placement_type"),
                    creative_ids=ArrayAgg("id", distinct=True),
                )
                .order_by()
                .values(
                    "creative_type",
                    "placement_type",
                    "count",
                    "creative_ids",
                )
            )
            for item in adcreative_obj:
                self.creative_id_list += item["creative_ids"]
            return adcreative_obj
        except Exception as e:
            self.handleerror(
                "[adcrartive_detail] Could not get completed data in database",
                repr(e),
            )
            raise e

    def adcreative_detail_platfrom(self, platfrom):
        try:
            placement_type_list = None
            if platfrom == PlatFormType.FACEBOOK:
                placement_type_list = (
                    [
                        "Facebook_Feed",
                        "Facebook_Reels",
                        "Facebook_Story",
                        "Instagram_Stream",
                        "Instagram_Reels",
                        "Instagram_Story",
                    ]
                    if not self.auto_placement
                    else ["Default"]
                )
            if platfrom == PlatFormType.SNAPCHAT:
                placement_type_list = ["Automatic"]
            if platfrom == PlatFormType.TIKTOK:
                placement_type_list = ["Placement_tiktok"]
            adcreative_obj = (
                AdCreativeIds.objects.filter(
                    ad_platform=platfrom,
                    uploadsesid=self.uploadsesid,
                    advantage_placement__in=placement_type_list,
                )
                .values_list("creative_type", "advantage_placement")
                .annotate(
                    count=Count("advantage_placement"),
                    creative_ids=ArrayAgg("id", distinct=True),
                )
                .order_by()
                .values(
                    "creative_type",
                    "advantage_placement",
                    "count",
                    "creative_ids",
                    "ad_platform"
                    # "placement_type",
                )
            )
            return adcreative_obj
        except Exception as e:
            self.handleerror(
                "[adcrartive_detail_platfrom] Could not get completed data in database",
                repr(e),
            )
            raise e

    def facebook_scheduler(self):
        try:
            facebook_adcreative_obj = self.adcreative_detail_platfrom(
                PlatFormType.FACEBOOK
            )
            self.creative_ids_by_placement = {}
            self.type_post = {}
            for craetive in facebook_adcreative_obj:
                if craetive["ad_platform"] == PlatFormType.FACEBOOK:
                    self.creative_ids_by_placement[
                        craetive["advantage_placement"]
                    ] = craetive["creative_ids"]
                    self.type_post[craetive["advantage_placement"]] = craetive[
                        "creative_type"
                    ]
            self.Facebook_Feed = self.creative_ids_by_placement.get(
                AdvantageplacementType.FACEBOOK_FEED
            )
            self.Facebook_Reels = self.creative_ids_by_placement.get(
                AdvantageplacementType.FACEBOOK_REELS
            )
            self.Facebook_Story = self.creative_ids_by_placement.get(
                AdvantageplacementType.FACEBOOK_STORY
            )
            self.Instagram_Stream = self.creative_ids_by_placement.get(
                AdvantageplacementType.INSTAGRAM_STREAM
            )
            self.Instagram_Reels = self.creative_ids_by_placement.get(
                AdvantageplacementType.INSTAGRAM_REELS
            )
            self.Instagram_Story = self.creative_ids_by_placement.get(
                AdvantageplacementType.INSTAGRAM_STORY
            )
            self.Default = self.creative_ids_by_placement.get(
                AdvantageplacementType.DEFAULT
            )
            if self.Facebook_Feed:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.FACEBOOK_FEED,
                    creative_list=self.Facebook_Feed,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
            if self.Facebook_Reels:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.FACEBOOK_REELS,
                    creative_list=self.Facebook_Reels,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
            if self.Facebook_Story:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.FACEBOOK_STORY,
                    creative_list=self.Facebook_Story,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
            if self.Instagram_Stream:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.INSTAGRAM_STREAM,
                    creative_list=self.Instagram_Stream,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
            if self.Instagram_Reels:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.INSTAGRAM_REELS,
                    creative_list=self.Instagram_Reels,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
            if self.Instagram_Story:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.INSTAGRAM_STORY,
                    creative_list=self.Instagram_Story,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
            if self.Default:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.DEFAULT,
                    creative_list=self.Default,
                    platform=PlatFormType.FACEBOOK,
                    post=self.type_post,
                )
        except Exception as e:
            self.handleerror(
                "[facebook_autoscheduler_record] Could not  completed insert data in database",
                repr(e),
            )
            raise e

    def tiktok_scheduler(self):
        try:
            tiktok_adcreative_obj = self.adcreative_detail_platfrom(PlatFormType.TIKTOK)
            self.creative_ids_by_placement = {}
            self.type_post = {}
            for craetive in tiktok_adcreative_obj:
                if craetive["ad_platform"] == PlatFormType.TIKTOK:
                    self.creative_ids_by_placement[
                        craetive["advantage_placement"]
                    ] = craetive["creative_ids"]
                    self.type_post[craetive["advantage_placement"]] = craetive[
                        "creative_type"
                    ]
            self.placement_tiktok_creative_ids_list = (
                self.creative_ids_by_placement.get(
                    AdvantageplacementType.PLACEMENT_TIKTOK
                )
            )

            if self.placement_tiktok_creative_ids_list:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.PLACEMENT_TIKTOK,
                    creative_list=self.placement_tiktok_creative_ids_list,
                    platform=PlatFormType.TIKTOK,
                    post=self.type_post,
                )
        except Exception as e:
            self.handleerror(
                "[facebook_autoscheduler_record] Could not  completed insert data in database",
                repr(e),
            )
            raise e

    def snapchat_scheduler(self):
        try:
            snapchat_adcreative_obj = self.adcreative_detail_platfrom(
                PlatFormType.SNAPCHAT
            )
            self.creative_ids_by_placement = {}
            self.type_post = {}
            for craetive in snapchat_adcreative_obj:
                if craetive["ad_platform"] == PlatFormType.SNAPCHAT:
                    self.creative_ids_by_placement[
                        craetive["advantage_placement"]
                    ] = craetive["creative_ids"]
                    self.type_post[craetive["advantage_placement"]] = craetive[
                        "creative_type"
                    ]
            self.automatic_creative_ids_list = self.creative_ids_by_placement.get(
                AdvantageplacementType.AUTOMATIC
            )

            if self.automatic_creative_ids_list:
                self.create_scheduler(
                    placement_type=AdvantageplacementType.AUTOMATIC,
                    creative_list=self.automatic_creative_ids_list,
                    platform=PlatFormType.SNAPCHAT,
                    post=self.type_post,
                )
        except Exception as e:
            self.handleerror(
                "[facebook_autoscheduler_record] Could not  completed insert data in database",
                repr(e),
            )
            raise e

    def create_scheduler(self, placement_type, creative_list, platform, post):
        if platform == PlatFormType.FACEBOOK:
            data = self.facebook
            interests_obj = data.get("interests")
            custom_audience_obj = data.get("custom_audience")
            interest_str = (
                ",".join(interest["id"] for interest in interests_obj)
                if interests_obj
                else None
            )
            custom_audience_str = (
                ",".join(audience["audience_id"] for audience in custom_audience_obj)
                if custom_audience_obj
                else None
            )
            dayparting = False
            automatic_placement = True if self.auto_placement else False

        if platform == PlatFormType.TIKTOK:
            data = self.tiktok
            dayparting = data.get("dayparting")
            automatic_placement = False
            interests_obj = data.get("interests")
            custom_audience_obj = data.get("custom_audience")
            interest_str = (
                ",".join(interest["id"] for interest in interests_obj)
                if interests_obj
                else None
            )
            custom_audience_str = (
                ",".join(audience["audience_id"] for audience in custom_audience_obj)
                if custom_audience_obj
                else None
            )

            if dayparting:
                offset = data.get("dayparting_ofset")
                dayparting_list = data.get("dayparting_list")

        if platform == PlatFormType.SNAPCHAT:
            automatic_placement = True
            data = self.snapchat
            dayparting = False
            interests_obj = data.get("interests")
            custom_audience_obj = data.get("custom_audience")
            interest_str = (
                ",".join(interest["id"] for interest in interests_obj)
                if interests_obj
                else None
            )
            custom_audience_str = (
                ",".join(audience["audience_id"] for audience in custom_audience_obj)
                if custom_audience_obj
                else None
            )

        results = AdCreativeIds.objects.filter(id__in=creative_list).values(
            "landingpage_url"
        )

        if not results:
            landingpage_url = "No"
        elif results[0]["landingpage_url"] is None:
            landingpage_url = "No"
        elif len(set(result["landingpage_url"] for result in results)) >= 1:
            landingpage_url = "Yes"
        else:
            landingpage_url = "No"

        chunks_obj = self.chunks(creative_list, data.get("maxcreatives"))
        for batch in chunks_obj:
            bulk_language_objects = []
            current_obj = AdScheduler(
                auto_scheduler_json=self.scheduling_info,
                uploadsesid=self.uploadsesid,
                platform=platform,
                scraper_group_id=self.group_id,
                type_post=post.get(placement_type),
                # placement_type=placement_type,
                campaign_name=data.get("campaign_name") or None,
                campaign_id=data.get("campaign_id") or None,
                adaccount_id=data.get("advertiser_id"),
                extra_name=data.get("extra_name") or None,
                bundle_countries=self.is_bundle_countries,
                countries=self.countries,
                age_range=data.get("age_group"),
                budget=self.budget,
                max_budget=None,
                dayparting=dayparting,
                language=self.is_language,
                landingpage_url=landingpage_url,
                heading=data.get("heading") or None,
                caption=data.get("caption") or None,
                bid_strategy="Bid" if self.bid_strategy == "Bid Cap" else "Lowestcost",
                bid=self.bid,
                objective=self.objective,
                pixel_id=data.get("pixel_id") or None,
                event_type=data.get("event_type") or None,
                custom_audiences=custom_audience_str,
                ignore_until=data.get("ignore_until"),
                scheduled_for=self.schedule_date,
                strategy=data.get("strategy") or None,
                interests=interest_str,
                accelerated_spend=data.get("accelerated_spend"),
                user_id=self.user_id,
                authkey_email_user=data.get("authkey_email_user"),
                tiktok_identity_type=data.get("tiktok_identity_type") or None,
                tiktok_identity_id=data.get("tiktok_identity_id") or None,
                facebook_pages_ids=data.get("facebook_pages"),
                instagram_id=data.get("instagram_id") or None,
                company_name=data.get("company_name") or None,
                profile_id=self.prfile_id,
                automatic_placement=automatic_placement,
                selected_placement=placement_type,
            )
            current_obj._uuid = self.uuid
            current_obj._profile_id = self.prfile_id
            current_obj.save()
            AdCreativeIds.objects.filter(id__in=batch).update(
                scheduler_id=current_obj.id, updated_at=datetime.now()
            )
            if platform == PlatFormType.TIKTOK and dayparting:
                self.dayparting_calculation(
                    scheduler_id=current_obj.id,
                    offset=offset,
                    dayparting_list=dayparting_list,
                )
            if self.is_language:
                if not self.is_bundle_countries:
                    for code in self.languages:
                        # name = list(item.keys())[0]
                        # keys = [d.get(self.key) for d in item[name]]
                        # keys_str = ",".join(map(str, keys))
                        # language_list = [
                        #     id for id in keys_str.split(",") if id != "None"
                        # ]

                        keys = [d.get(self.key) for d in self.languages[code]]
                        keys_str = ",".join(map(str, keys))
                        language_list = [
                            id for id in keys_str.split(",") if id != "None"
                        ]
                        if keys_str and language_list:
                            bulk_language_objects.append(
                                Language(
                                    ad_scheduler_id=current_obj.id,
                                    country_code=code,
                                    language_string=",".join(language_list).strip(),
                                )
                            )
                else:
                    language_list = [
                        str(id.get(self.key))
                        for id in self.languages
                        if id.get(self.key) is not None
                    ]

                    if language_list:
                        bulk_language_objects.append(
                            Language(
                                ad_scheduler_id=current_obj.id,
                                country_code=self.countries,
                                language_string=",".join(language_list).strip(),
                            )
                        )
                Language.objects.bulk_create(bulk_language_objects)

    def chunks(self, ln, n):
        # For item i in a range that is a length of l,
        for i in range(0, len(ln), n):
            # Create an index range for l of n items:
            yield ln[i : i + n]

    def dayparting_calculation(self, scheduler_id, offset, dayparting_list):
        if not self.is_bundle_countries:
            bulk_dayparting_objects = []
            for country in self.countries.split(","):
                dayparting_string = ""
                if offset:
                    rotate = offset.get(country)
                    for dayparting in dayparting_list:
                        d = deque(dayparting)
                        d.rotate(int(rotate))
                        dayparting_string += "".join(d)
                    bulk_dayparting_objects.append(
                        Day_Parting(
                            ad_scheduler_id=scheduler_id,
                            country_code=country,
                            dayparting_string=dayparting_string,
                        )
                    )
                else:
                    dayparting_string += "".join(dayparting_list)
                    bulk_dayparting_objects.append(
                        Day_Parting(
                            ad_scheduler_id=scheduler_id,
                            country_code=country,
                            dayparting_string=dayparting_string,
                        )
                    )
            Day_Parting.objects.bulk_create(bulk_dayparting_objects)
        else:
            dayparting_string = ""
            if offset:
                for dayparting in dayparting_list:
                    d = deque(dayparting)
                    d.rotate(int(offset))
                    dayparting_string += "".join(d)
            else:
                dayparting_string += "".join(dayparting_list)
            Day_Parting.objects.create(
                ad_scheduler_id=scheduler_id,
                country_code=self.countries,
                dayparting_string=dayparting_string,
            )

    def offset_calculation(self):
        pass

    def carousel_calculation(self):
        pass

    def creative_calculation(self, platfrom):
        if platfrom == PlatFormType.FACEBOOK:
            self.facebook_creative_id_list = []
            creatives_to_copy = None
            for item in self.adcreative_obj:
                self.facebook_creative_id_list += item["creative_ids"]
            creatives_to_copy = AdCreativeIds.objects.filter(
                id__in=self.facebook_creative_id_list
            )
            if self.auto_placement:
                bulk_creative_objects = [
                    AdCreativeIds(
                        uploadsesid=creative.uploadsesid,
                        ad_platform=PlatFormType.FACEBOOK,
                        filename=creative.filename,
                        url=creative.url,
                        creative_type=creative.creative_type,
                        placement_type=creative.placement_type,
                        user_id=creative.user_id,
                        landingpage_url=creative.landingpage_url,
                        advantage_placement="Default",
                        resolution=creative.resolution,
                        creative_size=creative.creative_size,
                    )
                    for creative in creatives_to_copy
                ]
            else:
                bulk_creative_objects = [
                    AdCreativeIds(
                        uploadsesid=creative.uploadsesid,
                        ad_platform=PlatFormType.FACEBOOK,
                        filename=creative.filename,
                        url=creative.url,
                        creative_type=creative.creative_type,
                        placement_type=creative.placement_type,
                        user_id=creative.user_id,
                        landingpage_url=creative.landingpage_url,
                        advantage_placement=placement,
                        resolution=creative.resolution,
                        creative_size=creative.creative_size,
                    )
                    for placement in self.placement_list
                    for creative in creatives_to_copy
                ]

            AdCreativeIds.objects.bulk_create(bulk_creative_objects)
        if platfrom in {PlatFormType.TIKTOK, PlatFormType.SNAPCHAT}:
            self.tiktok_snap_creative_id_list = []
            creatives_to_copy = None
            advantage_placement = (
                "Placement_tiktok" if platfrom == PlatFormType.TIKTOK else "Automatic"
            )
            for item in self.adcreative_obj:
                if item.get("placement_type") == PlacementType.STORY:
                    self.tiktok_snap_creative_id_list += item["creative_ids"]
            creatives_to_copy = AdCreativeIds.objects.filter(
                id__in=self.tiktok_snap_creative_id_list
            )
            bulk_creative_objects = [
                AdCreativeIds(
                    uploadsesid=creative.uploadsesid,
                    ad_platform=platfrom,
                    filename=creative.filename,
                    url=creative.url,
                    creative_type=creative.creative_type,
                    placement_type=creative.placement_type,
                    user_id=creative.user_id,
                    landingpage_url=creative.landingpage_url,
                    advantage_placement=advantage_placement,
                    resolution=creative.resolution,
                    creative_size=creative.creative_size,
                )
                for creative in creatives_to_copy
            ]
            AdCreativeIds.objects.bulk_create(bulk_creative_objects)

    def preset_setup(self, json_data, preset):
        if preset.get("action") == "New":
            preset_name = preset.get("preset_name")
            preset_obj = SchedulePresets.objects.create(
                preset_name=preset_name, created_by_id=self.user
            )
            SchedulePresetsSettings(
                preset_json_data=json_data, schedule_preset_id=preset_obj.id
            ).save()
        if preset.get("action") == "Overwrite":
            preset_id = preset.get("id")
            SchedulePresetsSettings.objects.update_or_create(
                schedule_preset_id=preset_id, defaults={"preset_json_data": json_data}
            )
