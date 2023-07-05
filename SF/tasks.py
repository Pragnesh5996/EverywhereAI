from __future__ import absolute_import
from apps.common.models import (
    AdScheduler,
    Profile,
    AdAccount,
    AdCampaigns,
)
from apps.snapchat.helper.Snapchat_api_handler import SnapchatAPI
from celery import shared_task
from apps.tiktok.helper.Tiktok_api_handler import TikTokAPI
from apps.facebook.helper.Facebook_api_handler import FacebookAPI
from apps.linkfire.helper.Linkfire_api_handler import LinkfireApi
from apps.common.Optimizer.AdOptimizer import AdOptimizer
from apps.scraper.models import Settings, ScraperConnection
from apps.common.constants import (
    PlatFormType,
    AdAccountActiveType,
    ScraperConnectionType,
    ProgressType,
    StatusType,
    JobStatus,
    MPlatFormType,
    MilestoneProgess,
    PayoutStatus,
    ApprovalStatus,
    Adspend_Email_Status,
)
from apps.common.Optimizer.AdOptimizer import (
    NullValueInDatabase,
)
from SF import settings
from django_tenants.utils import get_tenant_model, tenant_context
from apps.main.models import Company, User
from apps.linkfire.scraper import linkfire
from apps.common.custom_exception import handle_error
from SF.celery import app
from apps.facebook.models import FacebookUsers, FacebookPages
from apps.marketplace.models import (
    SubmissionViewCount,
    SocialAuthkey,
    SocialProfile,
    Earning,
    Payout,
    MilestoneStatus,
    SpentBalance,
    SocialBusiness,
)
from apps.common.api_v1.serializers import ProfileSerializer
from django.core.cache import cache
from apps.common.models import ScraperGroup
from apps.common.default_data_set import set_default_data
from apps.common.urls_helper import URLHelper
import base64
import requests
from django.db.models import Sum
from django.db.models.functions import Coalesce
from apps.payment.helper.stripe_helper import StripeHelper
from datetime import datetime, timedelta
from apps.payment.models import Subscription
from apps.common.sendgrid import SendGrid
import json

url_hp = URLHelper()


@app.task(name="setconversion_update_spend_data")
def setconversion_update_spend_data():
    """
    This function Executes every day morning at 7:00 A.M
    This is a function that asynchronously calls the setconversion_update_spend_data_tenant task for each tenant (company) in the database.
    The function iterates over all tenants in the database (excluding the public schema)
    and calls the setconversion_update_spend_data_tenant task asynchronously (using delay) for each tenant,
    passing in the tenant's uid as an argument.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        setconversion_update_spend_data_tenant.delay(tenant.uid)


@shared_task
def setconversion_update_spend_data_tenant(uid):
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profiles = Profile.objects.all().exclude(ad_platform=PlatFormType.LINKFIRE)
        for profile in profiles:
            ad_platform = profile.ad_platform
            try:
                optimizer = AdOptimizer(
                    ad_platform, debug_mode=settings.DEBUG, profile=profile
                )
                optimizer.updateSpendData()
            except Exception as e:
                handle_error(
                    reason=f"{ad_platform} updateSpendData error", message=str(e)
                )
        optimizer.setConversion()


@app.task(name="update_daily_spend_data")
def update_daily_spend_data():
    """
    This function Executes every day morning at 9:00 A.M
    This is a function that asynchronously calls the update_daily_spend_data_tenant task for each tenant (company) in the database.
    The function iterates over all tenants in the database (excluding the public schema)
    and calls the update_daily_spend_data_tenant task asynchronously (using delay) for each tenant,
    passing in the tenant's uid as an argument.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        update_daily_spend_data_tenant.delay(tenant.uid)


@shared_task(queue="daily_spend_data")
def update_daily_spend_data_tenant(uid):
    """
    Daily Adspend Updater: Program that keeps track of adspend per ad platform and pushes to database.
    """
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profiles = Profile.objects.values("id").exclude(
            ad_platform=PlatFormType.LINKFIRE
        )
        for profile in profiles:
            update_daily_spend_data_tenant_profile.delay(uid, profile)


@shared_task(queue="daily_spend_data")
def update_daily_spend_data_tenant_profile(uid, profile):
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profile_id = profile.get("id")
        profile = Profile.objects.get(id=profile_id)
        ad_platform = profile.ad_platform
        try:
            api_classes = {
                PlatFormType.FACEBOOK: FacebookAPI,
                PlatFormType.TIKTOK: TikTokAPI,
                PlatFormType.SNAPCHAT: SnapchatAPI,
            }
            api = api_classes[ad_platform](debug_mode=settings.DEBUG, profile=profile)
            api.updateDailySpendData(uid=uid)

        except Exception as e:
            handle_error(
                f"{ad_platform} update_daily_spend_data_tenant_profile returned with an exception with profile id {profile_id}.",
                str(e),
            )


# Executes every 10 minutes and check database optimize_interval_hours
# This will optimize active adsets (bid & budget optimization) according to calculations
@app.task(name="optimizer")
def optimizer():
    """
    This is a function that optimizes ad campaigns for multiple tenants (companies).
    The optimization is done at intervals specified in the Settings model,
    and the function is called every hour to check if it is time to run the optimization.
    If the optimizeCampaigns method is successfully called for all profiles,
    the optimize_updated_interval_hours setting is updated to the next time the optimization should occur.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        with tenant_context(tenant):
            update_rate = int(
                Settings.objects.get(variable="optimize_interval_hours").value
            )
            now = datetime.now()
            current_time = int(now.strftime("%H"))
            next_update = int(
                Settings.objects.get(variable="optimize_updated_interval_hours").value
            )
            if current_time == next_update:
                if current_time < 24 - update_rate:
                    next_update = current_time + update_rate
                else:
                    next_update = current_time + update_rate - 24
                is_update_hours = True
                profiles = Profile.objects.all()
                for profile in profiles:
                    optimizer = AdOptimizer(
                        profile.ad_platform, debug_mode=settings.DEBUG
                    )
                    try:
                        optimizer.settings()
                        optimizer.optimizeCampaigns()

                    except NullValueInDatabase as e:
                        is_update_hours = False
                        optimizer.handleError(
                            "Error in settings",
                            "This error occured while the optimizer was running, the original message is: "
                            + str(e),
                            "High",
                        )

                if is_update_hours:
                    Settings.objects.filter(
                        variable="optimize_updated_interval_hours"
                    ).update(value=str(next_update), updated_at=datetime.now())


@app.task(name="initializer")
def initializer():
    """
    This is a function Executes every 4 hour.
    This is a function that initializes tasks for each tenant (company) in the database.
    The function iterates over all tenants in the database (excluding the public schema) and
    calls the initializer_tenant function asynchronously (using delay) for each tenant,
    passing in the tenant's uid as an argument.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        initializer_tenant.delay(tenant.uid)


@shared_task(queue="initializer")
def initializer_tenant(uid):
    """
    Will read all active campaigns, adsets, and more per adplatform and pushes to database.
    """
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profiles = Profile.objects.values().exclude(ad_platform=PlatFormType.LINKFIRE)
        for profile in profiles:
            initializer_tenant_profile.delay(uid, profile)


@shared_task(queue="profile")
def initializer_tenant_profile(uid, profile):
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        api_classes = {
            PlatFormType.FACEBOOK: FacebookAPI,
            PlatFormType.TIKTOK: TikTokAPI,
            PlatFormType.SNAPCHAT: SnapchatAPI,
        }
        profile_id = profile.get("id")
        profile = Profile.objects.get(id=profile_id)
        ad_platform = profile.ad_platform
        try:
            api = api_classes[ad_platform](debug_mode=settings.DEBUG, profile=profile)
            api.initializer()
        except Exception as e:
            handle_error(
                f"{ad_platform} initializer returned with an exception with profile id {profile_id}.",
                str(e),
            )


@app.task(name="scheduler")
def scheduler():
    """
    This is a function Executes every 4 hour.
    This is a function that asynchronously calls the scheduler task for each tenant (company) in the database.
    The function iterates over all tenants in the database (excluding the public schema)
    and calls the scheduler task asynchronously (using delay) for each tenant,
    passing in the tenant's uid as an argument.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        scheduler_tenant.delay(tenant.uid)


@shared_task
def scheduler_tenant(
    uid, _profile_id=None, multiple=True, ad_scheduler_instance_id=None
):
    """
    Will read database one or multiple entrie and schedule new ads accordingly
    """

    def get_filter_scheduler_ids(
        ad_platform, profile=None, ad_scheduler_instance_id=None, multiple=True
    ):
        if multiple:
            ad_scheduler_ids = AdScheduler.objects.filter(
                platform=ad_platform,
                completed="No",
                landingpage_url="Yes",
                profile=profile,
            ).values_list("id", flat=True)
        else:
            ad_scheduler_ids = AdScheduler.objects.filter(
                id=ad_scheduler_instance_id, landingpage_url="Yes", profile=profile
            ).values_list("id", flat=True)
        return ad_scheduler_ids

    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profiles = Profile.objects.all().exclude(ad_platform=PlatFormType.LINKFIRE)
        for profile in profiles.filter(
            **({"id": _profile_id} if _profile_id is not None else {})
        ):
            api_classes = {
                PlatFormType.FACEBOOK: FacebookAPI,
                PlatFormType.TIKTOK: TikTokAPI,
                PlatFormType.SNAPCHAT: SnapchatAPI,
            }
            ad_platform = profile.ad_platform
            try:
                api = api_classes[ad_platform](
                    debug_mode=settings.DEBUG, profile=profile
                )
                if profile.ad_platform == PlatFormType.TIKTOK:
                    ad_scheduler_data_all = AdScheduler.objects.filter(
                        id__in=get_filter_scheduler_ids(
                            PlatFormType.TIKTOK,
                            profile,
                            ad_scheduler_instance_id,
                            multiple=multiple,
                        )
                    ).values_list(
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
                        "music_sharing",
                        "stitch_duet",
                        "scraper_group__group_name",
                        "placement_type",
                    )
                    if ad_scheduler_data_all:
                        api.scheduler(ad_scheduler_data_all)
                if profile.ad_platform == PlatFormType.FACEBOOK:
                    AdScheduler.objects.filter(
                        completed="Ratelimit", platform=PlatFormType.FACEBOOK
                    ).update(
                        completed="No", updated_at=datetime.now()
                    )  # Reset schedule items that hit a rate limit and were not finished
                    ad_scheduler_data_all = AdScheduler.objects.filter(
                        id__in=get_filter_scheduler_ids(
                            PlatFormType.FACEBOOK,
                            profile,
                            ad_scheduler_instance_id,
                            multiple=multiple,
                        )
                    ).values_list(
                        "id",
                        "uploadsesid",
                        "landingpage_url",
                        "campaign_id",
                        "campaign_name",
                        "adaccount_id",
                        "scheduled_for",
                        "objective",
                        "scraper_group_id",
                        "facebook_pages_ids",
                    )
                    if ad_scheduler_data_all:
                        api.scheduler(ad_scheduler_data_all)
                if profile.ad_platform == PlatFormType.SNAPCHAT:
                    ad_scheduler_data_all = (
                        AdScheduler.objects.filter(
                            id__in=get_filter_scheduler_ids(
                                PlatFormType.SNAPCHAT,
                                profile,
                                ad_scheduler_instance_id,
                                multiple=multiple,
                            )
                        )
                        .exclude(landingpage_url=None)
                        .values_list(
                            "id",
                            "uploadsesid",
                            "landingpage_url",
                            "campaign_id",
                            "campaign_name",
                            "adaccount_id",
                            "scheduled_for",
                            "objective",
                            "scraper_group_id",
                        )
                    )
                    if ad_scheduler_data_all:
                        api.scheduler(ad_scheduler_data_all)
            except Exception as e:
                handle_error(
                    f"[Mainloop] Scheduler returned with an exception with profile_id",
                    str(e),
                )
                handle_error(
                    f"[Mainloop] {ad_platform} Scheduler returned with an exception with profile_id {profile.id}",
                    str(e),
                )


@app.task(name="linkfire_scraper")
def linkfire_scraper():
    """
    This is a function that asynchronously calls the linkfire_scraper task for each tenant (company) in the database.
    The function iterates over all tenants in the database (excluding the public schema)
    and calls the linkfire_scraper task asynchronously (using delay) for each tenant,
    passing in the tenant's uid as an argument.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        linkfire_scraper_tenant.delay(tenant.uid)


@shared_task
def linkfire_scraper_tenant(uid):
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        try:
            profile = ScraperConnection.objects.filter(
                ad_platform=ScraperConnectionType.LINKFIRESCRAPER,
                is_active=StatusType.YES,
            ).first()
            linkfire_username = (profile.username,)
            linkfire_password = base64.b64decode(profile.password)
            linkfire.linkfirescraper(linkfire_username, linkfire_password)
        except Exception as e:
            handle_error(
                f"{'[LinkfireMainScraperCeleryTask] Could not Complete'}", str(e)
            )


@app.task(name="linkfire_api")
def linkfire_api():
    """
    This is a function that asynchronously calls the linkfire_api_tenant task for each tenant (company) in the database.
    The function iterates over all tenants in the database (excluding the public schema)
    and calls the linkfire_api_tenant task asynchronously (using delay) for each tenant,
    passing in the tenant's uid as an argument.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        linkfire_api_tenant.delay(tenant.uid)


@shared_task
def linkfire_api_tenant(uid):
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        if Profile.objects.filter(ad_platform=PlatFormType.LINKFIRE).exists():
            try:
                linkfire_api = LinkfireApi(debug_mode=settings.DEBUG)
                linkfire_api.generate_missing_urls()
                linkfire_api.resolve_pending_status()
            except Exception as e:
                handle_error(
                    "[Mainloop] linkfire link generator returned with an exception.",
                    str(e),
                )


@app.task(name="linkfire_mediaservice_api")
def linkfire_mediaservice_api():
    """
    This is a function that appears to be designed to retrieve information from
    the Linkfire media service API and insert to LinkfireMediaservices table.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        with tenant_context(tenant):
            if Profile.objects.filter(ad_platform=PlatFormType.LINKFIRE).exists():
                try:
                    linkfire_api = LinkfireApi(debug_mode=settings.DEBUG)
                    linkfire_api.mediaservices()
                except Exception as e:
                    handle_error(
                        "[Mainloop] linkfire link generator returned with an exception.",
                        str(e),
                    )


@shared_task
def ad_account_active_action(ad_account_id, uid):
    """
    This fuction is execute if user adaccount active status enabled.
    """
    # Get the tenant based on the uid
    tenant = Company.objects.get(uid=uid)
    # Switch to the tenant's context
    with tenant_context(tenant):
        ad_account = AdAccount.objects.filter(id=ad_account_id)
        ad_platform = ad_account[0].profile.ad_platform
        profile = ad_account[0].profile
        ad_account_id = ad_account[0].account_id

        if ad_platform == PlatFormType.FACEBOOK:
            # Initialize the FacebookAPI object
            try:
                fb = FacebookAPI(debug_mode=settings.DEBUG, profile=profile)
                fb.initializer_campaigns(ad_account.values("account_id")[0])
                fb.updateDailySpendData(
                    ad_account_id, toggle_action="pending", pastdays="last_28d", uid=uid
                )
            except Exception as e:
                ad_account.update(
                    active=AdAccountActiveType.NO,
                    last_28days_spend_status=ProgressType.FAILED,
                )
                fb.handleError(
                    "[ad_account_active_action]",
                    f"{ad_platform} Something went wrong while adding an ad account data to the database profile_id:{profile.id} and ad_account_id {ad_account_id}. Original error: {str(e)}",
                )

        elif ad_platform == PlatFormType.SNAPCHAT:
            # Initialize the SnapchatAPI object
            sc = SnapchatAPI(debug_mode=settings.DEBUG, profile=profile)
            sc.campaigns_to_database(ad_account_id)

            # Get the campaigns for the ad account
            campaigns = AdCampaigns.objects.filter(
                ad_platform=PlatFormType.SNAPCHAT, advertiserid=ad_account_id
            ).values("campaign_id")

            # Iterate through the list of campaigns and add the ad sets and update the daily spend data for each campaign.
            for campaign in campaigns:
                campaign_id = campaign.get("campaign_id")
                try:
                    sc.adsets_to_database(campaign_id)
                except Exception as e:
                    sc.handleError(
                        "[Ad_account_active_action - adsets_to_database]",
                        f"Something went wrong while adding an adset to the database. Original error: {str(e)}",
                    )
            try:
                sc.updateDailySpendData(ad_account_id, pastdays="last_28d", uid=uid)
            except Exception as e:
                sc.handleError(
                    "[Ad_account_active_action - updateDailySpendData]",
                    f"Something went wrong while adding an updateDailySpendData to the database. Original error: {str(e)}",
                )

        elif ad_platform == PlatFormType.TIKTOK:
            # Initialize the TikTokAPI object with the given settings and profile
            try:
                tk = TikTokAPI(debug_mode=settings.DEBUG, profile=profile)
                tk.initializer_campaigns(
                    ad_account_id=ad_account_id, toggle_action="pending"
                )
                tk.initializer_groups(
                    ad_account_id=ad_account_id, toggle_action="pending"
                )
                tk.updateDailySpendData(
                    ad_account_id, toggle_action="pending", pastdays="last_28d", uid=uid
                )
            except Exception as e:
                ad_account.update(
                    active=AdAccountActiveType.NO,
                    last_28days_spend_status=ProgressType.FAILED,
                )
                tk.handleError(
                    "[ad_account_active_action]",
                    f"{ad_platform} Something went wrong while adding an ad account data to the database profile_id:{profile.id} and ad_account_id {ad_account_id}. Original error: {str(e)}",
                )
        ad_account.update(
            active=AdAccountActiveType.Yes,
            last_28days_spend_status=ProgressType.SUCCESS,
        )

        updated_queryset = Profile.objects.filter(ad_platform=ad_platform)
        serializer = ProfileSerializer(updated_queryset, many=True)
        profiles = serializer.data
        cache.set(f"{uid}_platform_{ad_platform}", profiles, 300)


@app.task(name="facebook_pages_room")
def facebook_pages_room():
    """
    This task is responsible for processing Facebook pages for each tenant
    It loops through all tenants except the default public schema and calls the
    `facebook_page_room_tenant` task for each tenant's UID.
    """
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        facebook_page_room_tenant.delay(tenant.uid)


@shared_task(queue="facebook_page_room_tenant")
def facebook_page_room_tenant(uid):
    """
    This shared task is used to update Facebook Page Room data for a specific tenant.
    It runs asynchronously using the "facebook_page_room_tenant" queue.
    """
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profiles_ids = Profile.objects.filter(
            ad_platform=PlatFormType.FACEBOOK
        ).values_list("id", flat=True)
        if profiles_ids:
            update_facebook_page_room_tenant.delay(uid, list(profiles_ids))


@shared_task(queue="update_facebook_page_room_tenant")
def update_facebook_page_room_tenant(uid, profiles_ids):
    """
    Task that updates the Facebook pages for a given tenant and set of profiles
    with information about available ad space.
    """
    tenant = Company.objects.get(uid=uid)
    with tenant_context(tenant):
        profiles = Profile.objects.filter(
            ad_platform=PlatFormType.FACEBOOK, id__in=profiles_ids
        )
        for profile in profiles:
            if facebook_user := FacebookUsers.objects.filter(profile=profile).first():
                if ad_account := AdAccount.objects.filter(profile=profile).first():
                    if facebook_pages := FacebookPages.objects.filter(
                        facebook_user=facebook_user
                    ).values("id", "page_id", "page_token"):
                        bulk_update_facebook_pages_objects = []
                        for facebook_page in facebook_pages:
                            page_id = facebook_page.get("page_id")
                            page_token = facebook_page.get("page_token")
                            if page_token:
                                try:
                                    fb = FacebookAPI(
                                        debug_mode=settings.DEBUG, profile=profile
                                    )
                                    room_left = fb.get_ad_space_available(
                                        page_id=page_id,
                                        account=ad_account.account_id,
                                    )
                                    page = FacebookPages.objects.get(
                                        id=facebook_page.get("id")
                                    )
                                    page.room_left = room_left
                                    page.updated_at = datetime.now()
                                    bulk_update_facebook_pages_objects.append(page)
                                except Exception as e:
                                    handle_error(
                                        f"{PlatFormType.FACEBOOK} update_facebook_page_room returned with an exception with profile id {profile.id}.",
                                        str(e),
                                    )
                        FacebookPages.objects.bulk_update(
                            bulk_update_facebook_pages_objects,
                            fields=["room_left", "updated_at"],
                        )


def create_company_schema(user_id, schema_name, email, company_name, uuid):
    """
    This task creates a new tenant schema for a company and sets it as the user's company.
    It also sets default data to the newly created database and creates a default ScraperGroup
    if one does not already exist.
    """
    company = Company(schema_name=schema_name, email=email, name=company_name, uid=uuid)
    company.save()

    User.objects.filter(id=user_id).update(company=company)

    # set default data to database
    set_default_data(company, email)

    with tenant_context(company):
        if not ScraperGroup.objects.filter(group_name="Default").exists():
            ScraperGroup.objects.create(
                group_name="Default",
                profile_url=url_hp.DEFAULT_SCAPER_GROUP_PROFILE_PICTURE,
            )


@shared_task
def create_stripe_customer(user_id, uuid):
    user = User.objects.get(id=user_id)
    stripe = StripeHelper()
    stripe.create_customer(user=user, uid=uuid)


@app.task(name="get_view_count")
def get_view_count():
    # For facebook platform only,
    # get the view count using third party api and save in SubmissionViewCount model
    insta_media_ids = SubmissionViewCount.objects.filter(
        job__status=JobStatus.ACTIVE,
        job__platforms=MPlatFormType.INSTAGRAM,
        submission__approval_status__approval_status=ApprovalStatus.ACCEPTED,
    ).values()
    if insta_media_ids:
        for record in insta_media_ids:
            profile = SocialProfile.objects.filter(
                user_id=record.get("user_id")
            ).values()
            data = SocialAuthkey.objects.filter(
                profile_id=profile[0].get("id"),
                profile__platforms=MPlatFormType.INSTAGRAM,
            ).values("access_token")
            media_id = record.get("media_id")
            r = requests.get(
                url=f"{url_hp.FACEBOOK_v16_URL}{media_id}/insights",
                params={
                    "metric": "impressions",
                    "access_token": data[0].get("access_token"),
                },
            )
            response = r.json()
            impression = response.get("data")[0].get("values")[0].get("value")
            SubmissionViewCount.objects.filter(id=record.get("id")).update(
                view_count=impression
            )
    else:
        tiktok_media_ids = SubmissionViewCount.objects.filter(
            job__status=JobStatus.ACTIVE,
            job__platforms=MPlatFormType.TIKTOK,
            submission__approval_status__approval_status=ApprovalStatus.ACCEPTED,
        ).values()
        for record in tiktok_media_ids:
            profile = SocialProfile.objects.filter(
                user_id=record.get("user_id")
            ).values()
            business_center_id = SocialBusiness.objects.filter(
                profile_id=profile[0].get("id")
            ).values("business_center_id")
            data = SocialAuthkey.objects.filter(
                profile_id=profile[0].get("id"),
                profile__platforms=MPlatFormType.TIKTOK,
            ).values("access_token")
            fields = [
                "item_id",
                "thumbnail_url",
                "caption",
                "likes",
                "comments",
                "shares",
                "video_views",
                "create_time",
                "total_time_watched",
                "average_time_watched",
                "reach",
                "full_video_watched_rate",
                "impression_sources",
                "audience_countries",
            ]
            media_id = record.get("media_id")
            params = {
                "business_id": business_center_id[0].get("business_center_id"),
                "filters.video_ids": media_id,
                "fields": json.dumps(fields),
            }
            headers = {
                "Access-Token": data[0].get("access_token"),
            }
            r = requests.get(
                url_hp.MP_TIKTOK_VIEW_COUNT_INFO,
                params=params,
                headers=headers,
            )
            response = r.json()
            view_count = response["data"]["videos"][0]["video_views"]
            SubmissionViewCount.objects.filter(id=record.get("id")).update(
                view_count=view_count
            )


@app.task(name="set_complete_milestone")
def set_complete_milestone():
    # get the view count and check that milestone met it's requirement or not
    insta_media_ids = SubmissionViewCount.objects.filter(
        job__status=JobStatus.ACTIVE,
        submission__approval_status__approval_status=ApprovalStatus.ACCEPTED,
    ).values()

    for record in insta_media_ids:
        milestones = MilestoneStatus.objects.filter(
            milestone__job_id=record.get("job_id"),
            milestone__view_count__lte=record.get("view_count"),
        ).select_related("milestone", "user")
        payout, _ = Payout.objects.update_or_create(
            user_id=record.get("user_id"),
            payout_status=PayoutStatus.READY_FOR_PAYOUT,
            defaults={
                "amount": 0,
            },
        )
        for item in milestones:
            MilestoneStatus.objects.filter(id=item.id).update(
                status=MilestoneProgess.COMPLETED
            )
            Earning.objects.update_or_create(
                user_id=record.get("user_id"),
                milestone_id=item.milestone.id,
                job_id=record.get("job_id"),
                payout_id=payout.id,
                defaults={
                    "amount": item.milestone.price,
                    "earning_date": datetime.now(),
                },
            )
        total_amount = Earning.objects.filter(payout_id=payout.id).aggregate(
            Sum("amount")
        )
        Payout.objects.filter(
            id=payout.id,
            user_id=record.get("user_id"),
            payout_status=PayoutStatus.READY_FOR_PAYOUT,
        ).update(amount=total_amount.get("amount__sum"))
        milestone = (
            MilestoneStatus.objects.filter(status=MilestoneProgess.COMPLETED)
            .values(
                "user__email",
                "submission__job__title",
            )
            .first()
        )
        if milestone:
            job_title = milestone.get("submission__job__title")
            email = milestone.get("user__email")
            sendgrid = SendGrid()
            sendgrid.send_email_for_milestone_reached(email, job_title)
        else:
            raise Exception("Mail is not sent.")


@app.task(name="facebook_refresh_token")
def facebook_refresh_token():

    profiles = SocialProfile.objects.filter(platforms=MPlatFormType.INSTAGRAM).values(
        "id"
    )

    for profile in profiles:
        today_date = datetime.now().date()
        facebook_auth_data = SocialAuthkey.objects.filter(
            profile_id=profile.get("id"),
        ).values("access_token", "created_at")
        params = {
            "client_id": settings.MP_FACEBOOK_APP_ID,
            "client_secret": settings.MP_FACEBOOK_SECRET_ID,
            "grant_type": "fb_exchange_token",
            "fb_exchange_token": facebook_auth_data[0].get("access_token"),
        }
        expire_date = (
            facebook_auth_data[0].get("created_at") + timedelta(days=59)
        ).date()
        if expire_date == today_date:
            r = requests.get(url_hp.MP_FACEBOOK_ACCESS_TOKEN, params=params)
            response = r.json()
            SocialAuthkey.objects.filter(profile_id=profile.get("id"),).update(
                access_token=response.get("access_token"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )


@app.task(name="tiktok_refresh_token")
def tiktok_refresh_token():

    profiles = SocialProfile.objects.filter(platforms=MPlatFormType.TIKTOK).values("id")
    for profile in profiles:
        today_date = datetime.now().date()
        tiktok_auth_data = SocialAuthkey.objects.filter(
            profile_id=profile.get("id"),
        ).values("refresh_token", "created_at")
        params = {
            "client_key": settings.MP_TIKTOK_APP_ID,
            "grant_type": "refresh_token",
            "refresh_token": tiktok_auth_data[0].get("refresh_token"),
        }
        expire_date = (tiktok_auth_data[0].get("created_at") + timedelta(days=1)).date()
        if expire_date == today_date:
            r = requests.post(url_hp.MP_TIKTOK_REFRESH_TOKEN, params=params)
            response = r.json()
            SocialAuthkey.objects.filter(profile_id=profile.get("id"),).update(
                access_token=response["data"]["access_token"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )


@app.task(name="update_spent_balance")
def update_spent_balance():
    # update the spent balance if milestone is completed
    all_record = SpentBalance.objects.filter(job__status=JobStatus.ACTIVE).values()
    for record in all_record:
        total_spent_amount = MilestoneStatus.objects.filter(
            milestone__job_id=record.get("job_id"),
            status=MilestoneProgess.COMPLETED,
        ).aggregate(spent_amount=Coalesce(Sum("milestone__price"), 0))

        SpentBalance.objects.filter(id=record.get("id")).update(
            amount=total_spent_amount.get("spent_amount")
        )


@app.task(name="check_free_trial_date")
def check_free_trial_date():
    Company.objects.filter(expire_free_trial__date=datetime.now().date()).update(
        is_free_trial=False, updated_at=datetime.now()
    )


@app.task(name="free_trial_expiry_reminder_email")
def free_trial_expiry_reminder_email():
    two_days_from_now = (datetime.now() + timedelta(days=2)).date()
    records_within_two_days = Company.objects.filter(
        expire_free_trial__date=two_days_from_now
    ).values("name", "email")
    sendgrid = SendGrid()
    for company in records_within_two_days:
        sendgrid.send_email_for_free_trial_expire_reminder(company=company)


@shared_task(queue="fetch_latest_profile_data")
def fetch_latest_profile_data(uid, profile_id, ad_platform):
    tenant = Company.objects.get(uid=uid)

    with tenant_context(tenant):
        profile_obj = Profile.objects.get(id=profile_id)
        api_classes = {
            PlatFormType.FACEBOOK: FacebookAPI,
            PlatFormType.TIKTOK: TikTokAPI,
            PlatFormType.SNAPCHAT: SnapchatAPI,
        }
        try:
            api = api_classes[ad_platform](
                debug_mode=settings.DEBUG, profile=profile_obj
            )
            if ad_platform == PlatFormType.FACEBOOK:
                api.get_instagram_accounts()
                update_facebook_page_room_tenant.s(uid=uid, profiles_ids=[profile_id])
            api.initializing_bussiness_adaccounts()
            return {"profile_id": profile_id, "error": False, "error_message": None}
        except Exception as e:
            return {"profile_id": profile_id, "error": True, "error_message": str(e)}


@app.task(name="adspend_limit_exceeded_reminder_email")
def adspend_limit_exceeded_reminder_email():
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        adspend_limit_exceeded_reminder_email_tenant.delay(tenant.uid)


@shared_task
def adspend_limit_exceeded_reminder_email_tenant(uid):
    tenant = Company.objects.get(uid=uid)

    with tenant_context(tenant):
        try:
            customer = Company.objects.get(uid=uid)
            # Ad-spend amount calculation
            stripe = StripeHelper()
            adspend_amount, overcharge_percentage = stripe.adspend_limit_count(
                uid, customer.stripe_customer_id
            )
            status = Subscription.objects.filter(
                company=uid,
                status=Adspend_Email_Status.Active_Status,
                email_status=False,
            ).exists()
            if adspend_amount and status:
                sendgrid = SendGrid()
                sendgrid.adspend_limit_exceeded_email(
                    email=customer.email,
                    overcharge_percentage=overcharge_percentage,
                    username=customer.name,
                )
                status_update = Subscription.objects.get(
                    company=uid, status=Adspend_Email_Status.Active_Status
                )
                status_update.email_status = True
                status_update.save()

        except Exception as e:
            return {"error": True, "error_message": str(e)}


@app.task(queue="email")
def send_sendgrid_mail(payload):
    r = requests.request(
        "POST",
        url=url_hp.SENDGRID_URL,
        data=json.dumps(payload),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        },
    )
    if r.status_code not in [200, 201, 202]:
        pass


# celery -A SF  worker --loglevel=info
# celery -A SF worker -B
