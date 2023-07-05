from rest_framework import serializers
from django.db.models import Sum
from datetime import date, timedelta
from apps.common.models import (
    AdAccount,
    Profile,
    DailyAdspendGenre,
    AdAdsets,
    AdCampaigns,
    AdCreativeIds,
    SchedulePresets,
    SchedulePresetsSettings,
    AdScheduler,
    AutoSchedulerDraft,
    Language,
    AdAccount,
)
from apps.facebook.api_v1.serializers import (
    InstagramAccountsSerializer,
    FacebookPagesSerializer,
)
from apps.facebook.models import InstagramAccounts, FacebookPages
from apps.linkfire.models import LinkfireGeneratedLinks
from apps.error_notifications.api_v1.views import ErorrMessage
from django.db.models import Count, Q
from rest_framework.validators import UniqueValidator


class AdAccountSerializer(serializers.ModelSerializer):
    """
    The AdAccountSerializer class is responsible for serializing instances of the AdAccount
    model for use in the API. It defines a custom field called 'spend', which calculates the
    total spend for an ad account over the last 28 days.
    """

    spend = serializers.SerializerMethodField()

    def get_spend(self, ad_account):
        last_28_day_date = date.today() - timedelta(days=28)
        spend = DailyAdspendGenre.objects.filter(
            ad_account__account_id=ad_account.account_id, date__gte=last_28_day_date
        ).aggregate(Sum("spend"))
        return str(spend.get("spend__sum")) if spend.get("spend__sum") else None

    class Meta:
        model = AdAccount
        fields = "__all__"


class ProfileSerializer(serializers.ModelSerializer):
    """
    The ProfileSerializer class is responsible for serializing instances of the Profile
    model for use in the API. It defines a custom field called 'ad_accounts', which
    retrieves all ad accounts associated with a particular profile and serializes them
    using the AdAccountSerializer class.
    """

    ad_accounts = serializers.SerializerMethodField()
    facebook_pages = serializers.SerializerMethodField()
    instagram_accounts = serializers.SerializerMethodField()

    def get_ad_accounts(self, profile):
        if not isinstance(profile, dict):
            profile = profile.__dict__
        ad_accounts = AdAccount.objects.filter(profile=profile.get("id")).order_by("id")
        return AdAccountSerializer(ad_accounts, many=True).data

    def get_facebook_pages(self, profile):
        if not isinstance(profile, dict):
            profile = profile.__dict__
        facebook_pages = FacebookPages.objects.filter(
            facebook_user__profile=profile.get("id")
        ).order_by("id")
        return FacebookPagesSerializer(facebook_pages, many=True).data

    def get_instagram_accounts(self, profile):
        if not isinstance(profile, dict):
            profile = profile.__dict__
        instagram_accounts = InstagramAccounts.objects.filter(
            facebook_business__profile_id=profile.get("id")
        ).order_by("-id")
        return InstagramAccountsSerializer(instagram_accounts, many=True).data

    class Meta:
        model = Profile
        fields = "__all__"


class AdAccountActiveStatusChangeSerializer(serializers.ModelSerializer):
    """
    The AdAccountActiveStatusChangeSerializer class is responsible for serializing instances of the AdAccount
    model for the purpose of changing the active status of an ad account. It only includes the 'active' field
    in the serialized data, as this is the only field that needs to be updated.
    """

    class Meta:
        model = AdAccount
        fields = ("active",)


class AdAdsetsGetallDataSerializer(serializers.ModelSerializer):
    """
    The AdAdsetsGetallDataSerializer class is responsible for serializing instances of the AdAdsets
    model for the purpose of retrieving all data for ad sets in the API. It includes all fields in the
    serialized data, as indicated by the 'fields' attribute in the Meta class.
    """

    class Meta:
        model = AdAdsets
        fields = "__all__"


class CampaignSerializer(serializers.ModelSerializer):
    """
    The CampaignSerializer class is responsible for serializing instances of the AdCampaigns
    model for use in the API. It includes all fields in the serialized data, as indicated by
    the 'fields' attribute in the Meta class.
    """

    class Meta:
        model = AdCampaigns
        fields = "__all__"


class GetAdAccountUsingProfileSerializer(serializers.ModelSerializer):
    """
    The GetAdAccountUsingProfileSerializer class is responsible for serializing instances of the AdAccount
    model for the purpose of retrieving all ad accounts associated with a particular profile. It includes
    all fields in the serialized data, as indicated by the 'fields' attribute in the Meta class.
    """

    class Meta:
        model = AdAccount
        fields = "__all__"


class SchedulePresetsSettingsSerializer(serializers.ModelSerializer):
    """
    The SchedulePresetsSettingsSerializer class is responsible for serializing instances of the SchedulePresetsSettings
    model for use in the API. It includes all fields in the serialized data, as indicated by
    the 'fields' attribute in the Meta class.
    """

    class Meta:
        model = SchedulePresetsSettings
        fields = "__all__"

    """
    The SchedulePresetSerializer class is responsible for serializing instances of the SchedulePresets
    model for use in the API. It includes all fields in the serialized data, as indicated by
    the 'fields' attribute in the Meta class.
    """


class SchedulePresetSerializer(serializers.ModelSerializer):
    """
    This is a serializer class for the SchedulePresets model in Django.
    It defines how the model's data should be serialized and deserialized in order to be sent over the API.
    The schedule_presets_settings field is defined as a SerializerMethodField,
    which means that the value for this field will be determined by the get_schedule_presets_settings method.
    The with_schedule_preset_settings_data class attribute is used to determine whether or not the data for the schedule_presets_settings field should be included in the serialized output.
    The __init__ method is used to set the value of this attribute when an instance of the serializer is created.
    """

    preset_name = serializers.CharField(
        max_length=255,
        validators=[
            UniqueValidator(
                queryset=SchedulePresets.objects.all(),
                message="This preset name is already in use.",
            )
        ],
    )

    with_schedule_preset_settings_data = False

    def __init__(self, *args, **kwargs):
        super(SchedulePresetSerializer, self).__init__(*args, **kwargs)
        SchedulePresetSerializer.with_schedule_preset_settings_data = (
            self.with_schedule_preset_settings_data
        )

    schedule_presets_settings = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    def get_created_by(self, preset):
        return preset.created_by.get_full_name()

    def get_schedule_presets_settings(self, preset):
        if self.with_schedule_preset_settings_data:
            schedule_presets_settings_object = SchedulePresetsSettings.objects.filter(
                schedule_preset_id=preset.id
            )
            return SchedulePresetsSettingsSerializer(
                schedule_presets_settings_object, many=True
            ).data
        else:
            return None

    class Meta:
        model = SchedulePresets
        fields = "__all__"


class AdSchedulerSerializer(serializers.ModelSerializer):
    """
    The AdSchedulerSerializer class is responsible for serializing instances of the AdScheduler
    model for use in the API. It includes all fields in the serialized data, as indicated by
    the 'fields' attribute in the Meta class.
    """

    class Meta:
        model = AdScheduler
        fields = "__all__"


class SchedulerHistorySerializer(serializers.ModelSerializer):
    """
    The SchedulerHistorySerializer class is responsible for serializing instances of the AdScheduler
    model for use in the API. It includes all fields in the serialized data, as indicated by
    the 'fields' attribute in the Meta class.
    """

    platforms = serializers.SerializerMethodField()
    adaccount_name = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()
    common_objective = serializers.SerializerMethodField()

    def calculate_percentage(self, amount_done, amount_total):
        if amount_total == 0 or amount_done == 0:
            percentage = 0
        else:
            percentage = (amount_done * 100) / amount_total
            if percentage < 25:
                percentage = 0
            elif percentage < 50:
                percentage = 25
            elif percentage < 75:
                percentage = 50
            elif percentage < 100:
                percentage = 75
            else:
                percentage = 100
        return percentage

    def ad_sets_data(self, ad_scheduler, each_ad_scheduler):
        countries_array = []
        if ad_scheduler.bundle_countries:
            adset_data = AdAdsets.objects.filter(
                scheduler=each_ad_scheduler.get("id")
            ).values("adset_name", "target_country")
            country_uniq = []
            for countries in adset_data:
                country_uniq.append(countries["target_country"])
                countries_array.append(
                    {
                        "adset_name": "done",
                        "target_country": countries["target_country"],
                    }
                )
            unmatched = (
                set(country_uniq) - set((ad_scheduler.countries).split(","))
                if country_uniq and ad_scheduler.countries
                else set()
            )
            for keys in unmatched:
                countries_array.append(
                    {"adset_name": "notdone", "target_country": keys}
                )
        else:
            adset_data = AdAdsets.objects.filter(
                scheduler=each_ad_scheduler.get("id")
            ).values("adset_name", "target_country")
            if adset_data:
                countries_array = adset_data
            else:
                if each_ad_scheduler.get("countries"):
                    countries_list = each_ad_scheduler.get("countries").split(",")
                    for countries in countries_list:
                        countries_array.append(
                            {"adset_name": "Creating...", "target_country": countries}
                        )
        return countries_array

    # error message
    def error_message(self, ad_scheduler):
        results_map = {
            "Error": {
                "is_error": True,
                "error_message": ErorrMessage().get_message(ad_scheduler.get("id")),
                "status": "Error",
            },
            "Pending": {
                "is_error": False,
                "error_message": None,
                "status": "Linkfires...",
            },
            "No": {"is_error": False, "error_message": None, "status": "Scheduling"},
            "Yes": {"is_error": False, "error_message": None, "status": "Done"},
            "Stop": {"is_error": False, "error_message": None, "status": "Stop"},
        }
        default_result = {"is_error": False, "error_message": None, "status": None}
        completed = ad_scheduler.get("completed")
        final_result = results_map.get(completed, default_result)
        return final_result

    def platform_calculation(self, ad_platform_dict):
        (
            parent_amount_linkfires_done,
            parent_amount_adsets_done,
            parent_amount_creatives_done,
            parent_amount_campaigns_done,
            parent_total_linkfires,
            parent_total_adsets,
            parent_total_creatives,
            parent_total_campaigns,
        ) = [0] * 8

        for each_platform in ["Facebook", "Snap", "Tiktok"]:
            counting = {
                "linkfire": {"done": 0, "total": 0},
                "adset": {"done": 0, "total": 0},
                "creatives": {"done": 0, "total": 0},
                "campaigns": {"done": 0, "total": 0},
                "percentage": 0,
            }
            total_linkfires, amount_linkfires_done = [0] * 2
            total_creatives, amount_creatives_done = [0] * 2
            total_adsets, amount_adsets_done = [0] * 2
            total_campaigns, amount_campaigns_done = [0] * 2
            for convert_list in ad_platform_dict.get(each_platform).get("data"):
                # Linkfire Calculation
                if linkfire_date := convert_list.get("linkfire"):
                    for each_linkfire in linkfire_date:
                        total_linkfires += len(linkfire_date)
                        counting["linkfire"]["total"] = total_linkfires
                        if each_linkfire.get("status") == "Published":
                            amount_linkfires_done += 1
                            counting["linkfire"]["done"] = amount_linkfires_done

                # creatives Calculation
                if creatives_date := convert_list.get("creatives"):
                    total_creatives += len(creatives_date)
                    counting["creatives"]["total"] = total_creatives
                    for each_creatives in creatives_date:
                        if (
                            each_creatives.get("creative_id") != None
                            and each_creatives.get("uploaded_on") != None
                        ):
                            amount_creatives_done += 1
                            counting["creatives"]["done"] = amount_creatives_done

                # adsets Calculation
                if adset_date := convert_list.get("adset"):
                    for each_adset in adset_date.get("countries"):
                        total_adsets += 1
                        check_adset_str = next(iter(each_adset.values()))
                        if check_adset_str == "Creating...":
                            amount_adsets_done += 0
                        elif check_adset_str == "done":
                            amount_adsets_done += 1
                        elif check_adset_str == "notdone":
                            amount_adsets_done += 0
                        else:
                            amount_adsets_done += 1
                        counting["adset"]["done"] = amount_adsets_done
                        counting["adset"]["total"] = total_adsets

                # campaigns Calculation
                if campaigns_data := convert_list.get("campaigns"):
                    total_campaigns = len(campaigns_data)
                    counting["campaigns"]["total"] = total_campaigns
                    name_check, id_check = campaigns_data.get(
                        "campaign_name"
                    ), campaigns_data.get("campaign_id")
                    if name_check and id_check:
                        amount_campaigns_done = 2
                    elif name_check or id_check is None:
                        amount_campaigns_done = 1
                    else:
                        amount_campaigns_done = 0
                    counting["campaigns"]["done"] = amount_campaigns_done

            # calculation of each platform
            parent_amount_linkfires_done += amount_linkfires_done
            parent_amount_adsets_done += amount_adsets_done
            parent_amount_creatives_done += amount_creatives_done
            parent_amount_campaigns_done += amount_campaigns_done
            parent_total_linkfires += total_linkfires
            parent_total_adsets += total_adsets
            parent_total_creatives += total_creatives
            parent_total_campaigns += total_campaigns

            # Each platform calculation of percentage
            amount_done = (
                amount_linkfires_done
                + amount_adsets_done
                + amount_creatives_done
                + amount_campaigns_done
            )
            amount_total = (
                total_linkfires + total_adsets + total_creatives + total_campaigns
            )
            percentage = self.calculate_percentage(amount_done, amount_total)
            counting["percentage"] = percentage
            ad_platform_dict.get(each_platform).get("counting").append(counting)

        return (
            parent_amount_linkfires_done,
            parent_total_linkfires,
            parent_amount_adsets_done,
            parent_total_adsets,
            parent_amount_creatives_done,
            parent_total_creatives,
            parent_amount_campaigns_done,
            parent_total_campaigns,
        )

    def get_platforms(self, ad_scheduler):
        # common for all  platform
        main_ad_platform_dict = {
            "Facebook": {"data": [], "counting": []},
            "Snap": {"data": [], "counting": []},
            "Tiktok": {"data": [], "counting": []},
            "percentage": [],
        }
        platform_list = ["Facebook", "Snap", "Tiktok"]

        # Ad scheduler data with multiple rows based on uploadsesid
        ad_scheduler_id = AdScheduler.objects.filter(
            uploadsesid=ad_scheduler.uploadsesid
        ).values()

        for ad_scheduler_data in ad_scheduler_id:
            ad_platform_dict = {
                "adScheduler": {},
                "linkfire": [],
                "adset": [],
                "creatives": [],
                "campaigns": {},
                "error": {},
            }
            # Linkfire data
            link_fire_data = (
                LinkfireGeneratedLinks.objects.filter(
                    ad_scheduler_id=ad_scheduler_data.get("id")
                )
                .values(
                    "id",
                    "domain",
                    "shorttag",
                    "status",
                    "is_scraped",
                    "ad_scheduler_id",
                )
                .order_by("added_on")
            )
            ad_platform = ad_scheduler_data.get("platform")
            if ad_platform in platform_list:
                ad_platform_dict.get("linkfire").extend(link_fire_data)
                ad_platform_dict["campaigns"] = {
                    "campaign_name": ad_scheduler_data.get("campaign_name"),
                    "campaign_id": ad_scheduler_data.get("campaign_id"),
                }
                # ad_platform_dict.get("adScheduler").append(ad_scheduler_data)
                ad_platform_dict["adScheduler"] = ad_scheduler_data

            # AD sets
            countries_array_data = self.ad_sets_data(ad_scheduler, ad_scheduler_data)
            if ad_platform in platform_list:
                ad_platform_dict["adset"] = {"countries": countries_array_data}

            # Ad creative data
            ad_creative_ids = AdCreativeIds.objects.filter(
                scheduler_id=ad_scheduler_data.get("id")
            ).values(
                "id",
                "filename",
                "url",
                "thumbnail_url",
                "creative_type",
                "placement_type",
                "uploaded_on",
                "notes",
                "user_id",
                "ad_platform",
                "ad_scheduler_id",
                "landingpage_url",
                "creative_id",
                "resolution",
                "creative_size",
            )
            for ad_creative_data in ad_creative_ids:
                ad_platform = ad_creative_data.get("ad_platform")
                if ad_platform in platform_list:
                    ad_platform_dict.get("creatives").append(ad_creative_data)

            if ad_platform in platform_list:
                error_message = self.error_message(ad_scheduler_data)
                ad_platform_dict["error"] = error_message
                main_ad_platform_dict.get(ad_platform).get("data").append(
                    ad_platform_dict
                )

        # Calculation Logic
        (
            parent_amount_linkfires_done,
            parent_total_linkfires,
            parent_amount_adsets_done,
            parent_total_adsets,
            parent_amount_creatives_done,
            parent_total_creatives,
            parent_amount_campaigns_done,
            parent_total_campaigns,
        ) = self.platform_calculation(main_ad_platform_dict)

        # Total percentage
        amount_done = (
            parent_amount_linkfires_done
            + parent_amount_adsets_done
            + parent_amount_creatives_done
            + parent_amount_campaigns_done
        )
        amount_total = (
            parent_total_linkfires
            + parent_total_adsets
            + parent_total_creatives
            + parent_total_campaigns
        )
        percentage = self.calculate_percentage(amount_done, amount_total)
        main_ad_platform_dict["percentage"] = percentage
        return main_ad_platform_dict

    # adaccount_name
    def get_adaccount_name(self, ad_scheduler):
        account_name = (
            AdAccount.objects.filter(account_id=ad_scheduler.adaccount_id)
            .only("account_name")
            .first()
        )
        return account_name.account_name if account_name else None

    def get_error(self, ad_scheduler):
        data = AdScheduler.objects.get(id=ad_scheduler.id)
        error_message = self.error_message(AdSchedulerSerializer(data).data)
        return error_message

    def get_common_objective(self, ad_scheduler):
        return (
            AdScheduler.objects.filter(id=ad_scheduler.id)
            .values(
                "id",
                "scraper_group_id",
                "budget",
                "max_budget",
                "objective",
                "uploadsesid",
                "bundle_countries",
                "countries",
                "language",
                "scheduled_for",
                "language_ad_scheduler__country_code",
                "language_ad_scheduler__language_string",
            )
            .first()
        )

    class Meta:
        model = AdScheduler
        fields = [
            "id",
            "uploadsesid",
            "platforms",
            "created_on",
            "scraper_group",
            "landingpage_url",
            "extra_name",
            "adaccount_name",
            "completed",
            "error",
            "common_objective",
        ]


class AutoSchedulerDraftSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Draft(auto scheduler page).
    It allows for the serialization of all fields of the Draft model.
    """

    class Meta:
        model = AutoSchedulerDraft
        fields = "__all__"


class ScheduleHistorysProgressSerializer(serializers.ModelSerializer):
    """
    The SchedulerHistorySerializer class is responsible for serializing instances of the AdScheduler
    model for use in the API. It includes all fields in the serialized data, as indicated by
    the 'fields' attribute in the Meta class.
    """

    percentage = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    def calculate_percentage(self, amount_done, amount_total):
        if amount_total == 0 or amount_done == 0:
            return 0
        percentage = min(int(amount_done / amount_total * 100), 100)
        percentage = (percentage // 25) * 25
        return percentage

    def get_percentage(self, ad_scheduler):
        ad_scheduler_id = AdScheduler.objects.filter(
            uploadsesid=ad_scheduler.uploadsesid
        ).values("id", "bundle_countries", "countries", "campaign_name", "campaign_id")

        ad_scheduler_ids = [ad_scheduler.get("id") for ad_scheduler in ad_scheduler_id]
        total_adsets, amount_adsets_done = 0, 0

        # Linkfire Calculation
        linkfire_counts = LinkfireGeneratedLinks.objects.filter(
            ad_scheduler_id__in=ad_scheduler_ids
        ).aggregate(
            total_linkfires=Count("id"),
            amount_linkfires_done=Count("id", filter=Q(status="Published")),
        )

        # creatives Calculation
        creative_counts = AdCreativeIds.objects.filter(
            scheduler_id__in=ad_scheduler_ids
        ).aggregate(
            total_creatives=Count("id"),
            amount_creatives_done=Count(
                "id", filter=Q(uploaded_on__isnull=False, creative_id__isnull=False)
            ),
        )

        # campaigns Calculation
        total_campaigns = ad_scheduler_id.count() * 2
        amount_campaigns_done = sum(
            [
                2
                if ad_scheduler.get("campaign_id") is not None
                and ad_scheduler.get("campaign_name") is not None
                else 1
                if ad_scheduler.get("campaign_id") is not None
                or ad_scheduler.get("campaign_name") is not None
                else 0
                for ad_scheduler in ad_scheduler_id
            ]
        )

        for ad_scheduler_data in ad_scheduler_id:
            # adsets Calculation
            adset_data = AdAdsets.objects.filter(
                scheduler_id=ad_scheduler_data.get("id")
            ).values_list("target_country", flat=True)
            countries_array = []
            if ad_scheduler_data.get("bundle_countries"):
                country_uniq = set(adset_data[0].split(',')) if adset_data else set(adset_data)
                countries_array = [
                    ("done", target_country) for target_country in adset_data
                ]
                unmatched = (
                    country_uniq -  set((ad_scheduler_data.get("countries")).split(","))
                    if country_uniq and ad_scheduler_data.get("countries")
                    else set()
                )
                countries_array += [("notdone", keys) for keys in unmatched]
            elif adset_data:
                countries_array = AdAdsets.objects.filter(
                    scheduler_id=ad_scheduler_data.get("id")
                ).values_list("adset_name", "target_country")
            else:
                countries_str = ad_scheduler_data.get("countries")
                if countries_str:
                    countries_array += [
                        ("Creating...", countries)
                        for countries in countries_str.split(",")
                    ]

            total_adsets += len(countries_array)
            amount_adsets_done += sum(
                1
                for adset_name, target_country in countries_array
                if adset_name not in ("Creating...", "notdone")
            )


        percentage = self.calculate_percentage(
            amount_done=linkfire_counts.get("amount_linkfires_done")
            + amount_adsets_done
            + creative_counts.get("amount_creatives_done")
            + amount_campaigns_done,
            amount_total=linkfire_counts.get("total_linkfires")
            + total_adsets
            + creative_counts.get("total_creatives")
            + total_campaigns,
        )
        return percentage

    def get_error(self, ad_scheduler):
        completed = ad_scheduler.completed
        if completed == "Error":
            message = ErorrMessage().get_message(ad_scheduler.id)
            return {"status": completed, "error_message": message}
        else:
            return {"status": completed, "error_message": None}

    def get_platform(self, ad_scheduler):
        return (
            AdScheduler.objects.filter(uploadsesid=ad_scheduler.uploadsesid)
            .values_list("platform", flat=True)
            .distinct()
        )

    class Meta:
        model = AdScheduler
        fields = [
            "id",
            "uploadsesid",
            "created_on",
            "scraper_group",
            "landingpage_url",
            "extra_name",
            "scheduled_for",
            "percentage",
            "error",
            "platform",
        ]


class SchedulerHistoryDetailsSerializer(serializers.ModelSerializer):
    ad_creative = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()
    ad_adsets = serializers.SerializerMethodField()
    adaccount = serializers.SerializerMethodField()

    def get_ad_creative(self, ad_scheduler):
        return AdCreativeIds.objects.filter(scheduler_id=ad_scheduler.id).values(
            "id",
            "filename",
            "url",
            "creative_type",
            "landingpage_url",
            "placement_type",
            "resolution",
            "user_id",
            "creative_size",
        )

    def get_error(self, ad_scheduler):
        completed = ad_scheduler.completed
        if completed == "Error":
            message = ErorrMessage().get_message(ad_scheduler.id)
            return {"status": completed, "error_message": message}
        else:
            return {"status": completed, "error_message": None}

    def get_adaccount(self, ad_scheduler):
        return AdAccount.objects.filter(account_id=ad_scheduler.adaccount_id).values(
            "account_id",
            "account_name",
        )

    def get_ad_adsets(self, ad_scheduler):
        adset_data = AdAdsets.objects.filter(scheduler_id=ad_scheduler.id).values(
            "adset_name", "target_country"
        )
        countries_array = []
        if ad_scheduler.bundle_countries:
            country_uniq = []
            for countries in adset_data:
                country_uniq.append(countries.get("target_country"))
                countries_array.append(
                    {
                        "adset_name": "done",
                        "target_country": countries["target_country"],
                    }
                )
            unmatched = (
                set(country_uniq) - set((ad_scheduler.countries).split(","))
                if country_uniq and ad_scheduler.countries
                else set()
            )
            for keys in unmatched:
                countries_array.append(
                    {"adset_name": "notdone", "target_country": keys}
                )
        else:
            if adset_data:
                countries_array = adset_data
            else:
                countries_str = ad_scheduler.countries
                if countries_str:
                    countries_list = countries_str.split(",")
                    for countries in countries_list:
                        countries_array.append(
                            {
                                "adset_name": "Creating...",
                                "target_country": countries,
                            }
                        )

        return countries_array

    class Meta:
        model = AdScheduler
        fields = [
            "id",
            "platform",
            "placement_type",
            "countries",
            "landingpage_url",
            "campaign_name",
            "extra_name",
            "selected_placement",
            "scheduled_for",
            "ad_creative",
            "error",
            "ad_adsets",
            "adaccount",
        ]
