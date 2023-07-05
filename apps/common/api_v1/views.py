from apps.common.api_v1.serializers import (
    CampaignSerializer,
    AdAccountSerializer,
    ProfileSerializer,
    AdAdsetsGetallDataSerializer,
    GetAdAccountUsingProfileSerializer,
    SchedulePresetSerializer,
    SchedulerHistorySerializer,
    AutoSchedulerDraftSerializer,
    ScheduleHistorysProgressSerializer,
    SchedulerHistoryDetailsSerializer,
)
from apps.common.paginations import PageNumberPagination7
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from apps.common.models import (
    AdAccount,
    AdScheduler,
    AdAdsets,
    Profile,
    AdCampaigns,
    Authkey,
    Pixels,
    CustomConversionEvents,
    CustomAudiences,
    AdCreativeIds,
    SchedulePresets,
    AutoSchedulerDraft,
)
from datetime import datetime, timedelta
from apps.common.Optimizer.AdOptimizer import AdOptimizer
from apps.common.Optimizer.AdOptimizer import NullValueInDatabase
from apps.facebook.models import FacebookUsers
from apps.common.models import DailyAdspendGenre
from SF.tasks import (
    update_daily_spend_data_tenant,
    setconversion_update_spend_data_tenant,
    initializer_tenant,
    scheduler_tenant,
    ad_account_active_action,
)
from apps.common.constants import (
    PlatFormType,
    AdAccountActiveType,
    CreativeType,
    PlacementType,
    ProgressType,
    ScraperConnectionType,
    ConversationEvent,
    StatusType,
)
from SF import settings
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from apps.facebook.helper.Facebook_api_handler import FacebookAPI
from apps.snapchat.helper.Snapchat_api_handler import SnapchatAPI
from apps.tiktok.helper.Tiktok_api_handler import TikTokAPI
from django.db.models import Sum, Count
from django.db.models import Q, Prefetch
from rest_framework import filters
from django.core.cache import cache
import requests
import random
import string
import os
from apps.common.s3_helper import S3BucketHelper
from apps.common.upload_creative_helper import UploadCreativeHelper
from django.db import transaction
from apps.common.custom_exception import AmazonS3UploadingException
from apps.scraper.models import ScraperConnection
import json
from apps.common.urls_helper import URLHelper
import collections
from apps.common.custom_decorators import track_error
from rest_framework.permissions import AllowAny
from apps.main.models import Webhook
from apps.common.auto_scheduler_helper import Scheduler
import math
from rest_framework.permissions import SAFE_METHODS
from apps.payment.models import Payment
from celery import group
from rest_framework import status
from rest_framework.response import Response
import time
from SF.tasks import fetch_latest_profile_data
from django.core.files.storage import FileSystemStorage
from botocore.exceptions import ClientError

url_hp = URLHelper()


class CreativeUploadAPIView(generics.CreateAPIView):
    """
    CreativeUploadAPIView is an API endpoint for uploading creatives (images or videos) to Amazon S3 and the AdCreativeIds database table.
    The endpoint accepts a list of creatives and a list of ad platforms as input and performs various checks and operations on the creatives,
    such as checking the file type and resolution, uploading the creatives to S3, and creating AdCreativeIds objects in the database.
    The endpoint also handles exceptions and returns appropriate error messages if any issues occur during the upload process.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=["schedule_platforms", "creatives", "uploadSesid"]
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        An endpoint for uploading creative in s3 and database AdCreativeIds table.
        """

        ad_platforms = list(request.data.get("schedule_platforms").split(","))
        creative = request.FILES.get("creatives")
        warning_message = None

        if not creative:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Creative is missing.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        uploadsesid = request.data.get("uploadSesid")
        facebook_profile_id = request.data.get("facebook_profile_id")

        parent_dir = f"{settings.BASE_DIR}/media/upload_creative"
        try:
            facebook_selected = PlatFormType.FACEBOOK in ad_platforms
            creative_name = creative.name.replace(" ", "_")
            creative_size = UploadCreativeHelper.check_size(creative.size)
            creative_type = UploadCreativeHelper.check_video_or_image(creative.name)
            valid_size = round(creative.size / 1048576, 2)
            if (creative_type == CreativeType.IMAGE and valid_size > 16) or (
                creative_type == CreativeType.VIDEO and valid_size > 512
            ):
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": "Please upload valid creative for video 512 mb and image 16 mb.",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )

            fs = FileSystemStorage(location=parent_dir)
            creative_name = fs.save(creative_name, creative)
            path = f"{settings.BASE_DIR}/media/upload_creative/{creative_name}"
            (
                resolution_xy,
                resolution_x,
                resolution_y,
                is_valid,
                error_message,
            ) = UploadCreativeHelper.find_creative_resolution(
                creative_name, creative_type, uploadsesid
            )

            if not is_valid:
                if fs.exists(path):
                    fs.delete(creative_name)
                return Response(
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                    data={
                        "error": True,
                        "data": [],
                        "message": error_message,
                    },
                )
            valid_post_placements = [PlatFormType.FACEBOOK]
            valid_story_placements = [
                PlatFormType.FACEBOOK,
                PlatFormType.TIKTOK,
                PlatFormType.SNAPCHAT,
            ]
            facebook_user_id = None
            if facebook_selected:
                try:
                    facebook_user = FacebookUsers.objects.get(
                        profile_id=facebook_profile_id
                    )
                    facebook_user_id = facebook_user.user_id
                except FacebookUsers.DoesNotExist:
                    pass

            if any(
                placement in ad_platforms for placement in valid_post_placements
            ) and (
                resolution_x == resolution_y
                or (5 * resolution_x) / 4 == resolution_y
                or (4 * resolution_x) / 3 == resolution_y
            ):
                if facebook_selected:
                    placement_type = PlacementType.POST

            elif (
                any(placement in ad_platforms for placement in valid_story_placements)
                and (16 * resolution_x) / 9 == resolution_y
            ):
                placement_type = PlacementType.STORY
            else:
                placement_type = PlacementType.OTHER
                resolution_ratio = UploadCreativeHelper.calculate_ratio(
                    resolution_x, resolution_y
                )
                warning_message = f"Invalid dimensions. Guide: Facebook/Insta: 1:1, 3:4 or 4:5. Any other platform: 16:9 or other options. Current resolution is: {resolution_ratio}"
            ad_creative = AdCreativeIds.objects.create(
                uploadsesid=uploadsesid,
                ad_platform=None,
                filename=creative_name,
                creative_type=creative_type,
                placement_type=placement_type,
                uploaded_on=datetime.now(),
                resolution=resolution_xy,
                user_id=facebook_user_id,
                creative_size=creative_size,
            )

            # create an instance of the S3BucketHelper class
            s3 = S3BucketHelper(foldername=f"upload_creative/{uploadsesid}", path=path)

            # upload a file to the S3 bucket
            is_success, error_message = s3.upload_to_s3(creative_name)
            if is_success:
                if fs.exists(path):
                    fs.delete(creative_name)
                AdCreativeIds.objects.filter(id=ad_creative.id).update(
                    url=f"{url_hp.AWS_CREATIVE_BASE_URL}/upload_creative/{uploadsesid}/{creative_name}",
                    updated_at=datetime.now(),
                )
            else:
                if fs.exists(path):
                    fs.delete(creative_name)
                raise AmazonS3UploadingException(error_message)

            creative_placement_type_counting = (
                AdCreativeIds.objects.filter(
                    uploadsesid=uploadsesid,
                    placement_type__in=[
                        PlacementType.POST,
                        PlacementType.STORY,
                        PlacementType.REELS,
                        PlacementType.OTHER,
                    ],
                )
                .values_list("placement_type")
                .annotate(count=Count("placement_type"))
                .order_by()
                .values("placement_type", "count")
            )
            uploaded_creative = AdCreativeIds.objects.filter(
                uploadsesid=uploadsesid
            ).values(
                "id",
                "filename",
                "url",
                "creative_type",
                "placement_type",
                "creative_size",
                "landingpage_url",
            )

        except (Exception, AmazonS3UploadingException) as e:
            path = f"{settings.BASE_DIR}/media/upload_creative/{creative_name}"
            if fs.exists(path):
                fs.delete(creative_name)
            return Response(
                status=status.HTTP_406_NOT_ACCEPTABLE,
                data={
                    "error": True,
                    "data": [],
                    "message": str(e),
                },
            )
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                "error": False,
                "data": [
                    {
                        "uploadSesid": uploadsesid,
                        "warning_message": warning_message,
                        "creative_placement_type_counting": creative_placement_type_counting,
                        "uploaded_creative": uploaded_creative,
                    }
                ],
                "message": "Your creatives were successfully uploaded.",
            },
        )


class CreativeDeleteAPIView(generics.CreateAPIView):
    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["creative_name", "uploadSesid"])
    def post(self, request, *args, **kwargs):
        """
        This class provides an endpoint for deleting creatives from s3 and the AdCreativeIds table.
        """
        creative_name = request.data.get("creative_name")
        uploadsesid = request.data.get("uploadSesid")
        try:
            s3 = S3BucketHelper(foldername=f"upload_creative/{uploadsesid}")
            is_success, error_message = s3.delete_to_s3(creative_name=creative_name)
            if is_success:
                AdCreativeIds.objects.filter(
                    uploadsesid=uploadsesid,
                    filename=creative_name,
                ).delete()
            else:
                raise AmazonS3UploadingException(error_message)

        except (Exception, AmazonS3UploadingException) as e:
            return Response(
                status=status.HTTP_406_NOT_ACCEPTABLE,
                data={
                    "error": False,
                    "data": [],
                    "message": str(e),
                },
            )
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                "error": False,
                "data": [],
                "message": "Your creatives were successfully removed.",
            },
        )


class GetDimensionsAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        creative_list = request.FILES.getlist("creatives")
        if not creative_list:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"{'creative is missing'}",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        data = []
        for creative in creative_list:
            creative_type = UploadCreativeHelper.check_video_or_image(creative.name)
            if creative_type == CreativeType.VIDEO:
                creative_type = CreativeType.VIDEO
                check_dimensiton_creative_path = f"{settings.BASE_DIR}/media/upload_creative/check_dimensiton/{creative.name}"
                destination = open(check_dimensiton_creative_path, "wb+")
                for chunk in creative.chunks():
                    destination.write(chunk)
                destination.close()
            else:
                creative_type = CreativeType.IMAGE
            (
                resolution_xy,
                resolution_x,
                resolution_y,
                is_valid,
                error_message,
            ) = UploadCreativeHelper.find_creative_resolution(
                creative, creative_type, uploadsesid="check_dimensiton"
            )

            if not is_valid:
                data.append(
                    {
                        "is_valid_dimensions": False,
                        "error_message": error_message,
                        "creative_name": creative.name,
                        "widthxheight": resolution_xy,
                        "width": resolution_x,
                        "height": resolution_y,
                    }
                )
            else:
                if (
                    resolution_x == resolution_y
                    or (5 * resolution_x) / 4 == resolution_y
                    or (4 * resolution_x) / 3 == resolution_y
                    or (16 * resolution_x) / 9 == resolution_y
                ):
                    data.append(
                        {
                            "is_valid_dimensions": True,
                            "error_message": error_message,
                            "creative_name": creative.name,
                            "widthxheight": resolution_xy,
                            "width": resolution_x,
                            "height": resolution_y,
                        }
                    )
                else:
                    data.append(
                        {
                            "is_valid_dimensions": False,
                            "error_message": "Invalid Dimentions",
                            "creative_name": creative.name,
                            "widthxheight": resolution_xy,
                            "width": resolution_x,
                            "height": resolution_y,
                        }
                    )
            if os.path.exists(check_dimensiton_creative_path):
                os.remove(check_dimensiton_creative_path)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": data,
                "message": "",
            },
        )


class BulkCreativeLandingPageUrlUpdateAPIView(generics.CreateAPIView):
    """
    An endpoint for updating landingpage_url in AdCreativeIds table.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["creative_data"])
    def put(self, request, *args, **kwargs):
        """
        An endpoint for updating landingpage_url in AdCreativeIds table.
        """
        creative_data = request.data.get("creative_data")
        ids = [creative["id"] for creative in creative_data]
        creatives = AdCreativeIds.objects.select_for_update().filter(id__in=ids)
        for creative in creative_data:
            creatives.filter(id=creative.get("id")).update(
                landingpage_url=creative.get("landingpage_url"),
                updated_at=datetime.now(),
            )
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                "error": False,
                "data": [],
                "message": "creative has been successfully updated.",
            },
        )


class CreateSchedulerAPIView(generics.CreateAPIView):
    """
    An endpoint for insert record in ad_scheduler table.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["uploadsesid","countries","campaign_objective","bid_strategy"])
    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        user = self.request.user.id
        uploadsesid = request.data.get("uploadsesid")
        if uploadsesid is None or uploadsesid == "":
            return Response(
                status=status.HTTP_406_NOT_ACCEPTABLE,
                data={
                    "error": True,
                    "data": [],
                    "message": "Uploadsesid should not be null or blank.",
                },
            )
        Scheduler(scheduling_info=request.data, user_uid=uid, auth_user=user)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                "error": False,
                "data": [],
                "message": "creative has been successfully uploaded.",
            },
        )


class OptimizerAPIView(generics.CreateAPIView):
    """
    This endpoint for optimizer.
    This will optimize active adsets (bid & budget optimization) according to calculations.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        day_before_date = datetime.now() - timedelta(days=1)
        AdAdsets.objects.filter(active="Yes").update(
            last_checked=day_before_date, updated_at=datetime.now()
        )
        for platform in [
            PlatFormType.SNAPCHAT,
            PlatFormType.FACEBOOK,
            PlatFormType.TIKTOK,
        ]:
            optimizer = AdOptimizer(platform, debug_mode=settings.DEBUG)
            try:
                optimizer.settings()
                optimizer.optimizeCampaigns()

            except NullValueInDatabase as e:
                optimizer.handleError(
                    "Error in settings",
                    "This error occured while the optimizer was running, the original message is: "
                    + str(e),
                    "High",
                )
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    data={"error": True, "data": [], "message": str(e)},
                )
        return Response(
            status=status.HTTP_200_OK, data={"error": False, "data": [], "message": ""}
        )


class InitializerAPIView(generics.CreateAPIView):
    """
    This endpoint for initializer.
    Will read all active campaigns, adsets, and more per adplatform and pushes to database.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        initializer_tenant.delay(uid)
        return Response(
            status=status.HTTP_200_OK, data={"error": False, "data": [], "message": ""}
        )


class SchedulerAPIView(generics.CreateAPIView):
    """
    This endpoint for Scheduler.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        scheduler_tenant.delay(uid)
        return Response(
            status=status.HTTP_200_OK, data={"error": False, "data": [], "message": ""}
        )


class UpdateDailySpendDataAPIView(generics.CreateAPIView):
    """
    This APIView is used to update daily spend data for the provided user.
    Daily Adspend Updater: Program that keeps track of adspend per ad platform and pushes to database
    It invokes the update_daily_spend_data_tenant Celery task to update the data asynchronously.
    The task is called using the 'delay' method which runs the task in the background.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        update_daily_spend_data_tenant.delay(uid)
        return Response(
            status=status.HTTP_200_OK, data={"error": False, "data": [], "message": ""}
        )


class SetConversionUpdateSpendDataAPIView(generics.CreateAPIView):
    """
    This is the SetConversionUpdateSpendDataAPIView class which is responsible for
    updating the spend data in the database.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        setconversion_update_spend_data_tenant.delay(uid)
        return Response(
            status=status.HTTP_200_OK, data={"error": False, "data": [], "message": ""}
        )


class AdAccountActiveStatusChangeAPIView(ModelViewSet):
    """
    This APIView is used to change the active status of an ad account.
    It allows users to enable or disable their ad accounts.
    It also triggers a task to perform some actions on the ad account based on the updated active status.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = AdAccount.objects.all()
    serializer_class = AdAccountSerializer
    http_method_names = ["put"]

    @track_error()
    def update(self, request, pk=None):
        uid = request.headers.get("uid")
        instance = self.get_object()
        ad_platform = instance.profile.ad_platform
        for attr, value in request.data.items():
            setattr(instance, attr, value)
        instance.save()
        ad_account_id = instance.id
        is_stop = False
        cache_dict = cache.get(f"{uid}_platform_{ad_platform}")
        if cache_dict:
            cache_json = json.dumps(cache.get(f"{uid}_platform_{ad_platform}"))
            cache_dict = json.loads(cache_json)
            for profile in cache_dict:
                for adaccount in profile.get("ad_accounts"):
                    if adaccount.get("id") == ad_account_id:
                        adaccount.update({"active": request.data.get("active")})
                        if request.data.get("active") != AdAccountActiveType.NO:
                            adaccount.update(
                                {"last_28days_spend_status": ProgressType.INPROGRESS}
                            )
                            setattr(
                                instance,
                                "last_28days_spend_status",
                                ProgressType.INPROGRESS,
                            )
                            instance.save()
                            ad_account_active_action.delay(
                                ad_account_id=instance.id,
                                uid=uid,
                            )
                        is_stop = True
                        break
                if is_stop:
                    break
            cache_dict = [collections.OrderedDict(profile) for profile in cache_dict]
            if not instance.active == AdAccountActiveType.Yes:
                cache.set(f"{uid}_platform_{ad_platform}", cache_dict, 300)

        else:
            if request.data.get("active") != AdAccountActiveType.NO:
                setattr(instance, "last_28days_spend_status", ProgressType.INPROGRESS)
                instance.save()
                ad_account_active_action.delay(
                    ad_account_id=instance.id,
                    uid=uid,
                )
            updated_queryset = Profile.objects.filter(ad_platform=ad_platform)
            serializer = ProfileSerializer(updated_queryset, many=True)
            profiles = serializer.data
            cache.set(f"{uid}_platform_{ad_platform}", profiles, 300)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": AdAccountSerializer(self.get_object()).data,
                "message": "Adaccount has been updated successfully.",
            },
        )


class PlatformCountAPIView(APIView):
    """
    This is a class that defines the API endpoint for getting the count of profiles
    on different ad platforms.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        profile_counts = (
            Profile.objects.filter(is_active=StatusType.YES)
            .prefetch_related("ad_accounts")
            .aggregate(
                google_count=Count("pk", filter=Q(ad_platform=PlatFormType.GOOGLE)),
                facebook_count=Count("pk", filter=Q(ad_platform=PlatFormType.FACEBOOK)),
                snapchat_count=Count("pk", filter=Q(ad_platform=PlatFormType.SNAPCHAT)),
                tiktok_count=Count("pk", filter=Q(ad_platform=PlatFormType.TIKTOK)),
                linkfire_count=Count("pk", filter=Q(ad_platform=PlatFormType.LINKFIRE)),
            )
        )

        ad_account_counts = (
            AdAccount.objects.filter(active=AdAccountActiveType.Yes)
            .prefetch_related("profile")
            .aggregate(
                facebook_adaccount_count=Count(
                    "pk", filter=Q(profile__ad_platform=PlatFormType.FACEBOOK)
                ),
                snapchat_adaccount_count=Count(
                    "pk", filter=Q(profile__ad_platform=PlatFormType.SNAPCHAT)
                ),
                tiktok_adaccount_count=Count(
                    "pk", filter=Q(profile__ad_platform=PlatFormType.TIKTOK)
                ),
            )
        )

        scraper_counts = ScraperConnection.objects.filter(
            is_active=StatusType.YES
        ).aggregate(
            linkfire_scraper_count=Count(
                "pk", filter=Q(ad_platform=ScraperConnectionType.LINKFIRESCRAPER)
            ),
            spotify_scraper_count=Count(
                "pk", filter=Q(ad_platform=ScraperConnectionType.SPOTIFYSCRAPER)
            ),
        )
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": [
                    {
                        "google": profile_counts.get("google_count", 0),
                        "facebook": profile_counts.get("facebook_count", 0),
                        "snapchat": profile_counts.get("snapchat_count", 0),
                        "tiktok": profile_counts.get("tiktok_count", 0),
                        "linkfire": profile_counts.get("linkfire_count", 0),
                        "linkfire-scraper": scraper_counts.get(
                            "linkfire_scraper_count", 0
                        ),
                        "spotify-scraper": scraper_counts.get(
                            "spotify_scraper_count", 0
                        ),
                        "facebook_ad_account_count": ad_account_counts.get(
                            "facebook_adaccount_count", 0
                        ),
                        "snapchat_ad_account_count": ad_account_counts.get(
                            "snapchat_adaccount_count", 0
                        ),
                        "tiktok_ad_account_count": ad_account_counts.get(
                            "tiktok_adaccount_count", 0
                        ),
                    }
                ],
                "message": "",
            },
        )


class DailyAdspendGenrefilterAPIView(APIView):
    """
    This class represents the view for filtering the daily ad spend data by genre.
    It allows users to specify a start and end date, and optionally, a list of campaign IDs and/or a list of ad account IDs.
    The view will then filter the daily ad spend data by these parameters and return the total spend for the specified time period.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=["start_date", "end_date", "campaign_id", "account_id"]
    )
    def get(self, request, *args, **kwargs):
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        campaign_id = request.data.get("campaign_id")
        campaign_list = [int(x) for x in campaign_id.split(",")] if campaign_id else []
        account_id = request.data.get("account_id")
        ad_account_list = [int(x) for x in account_id.split(",")] if account_id else []
        if start_date == "" or end_date == "":
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "The start and end date is requried.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        filters = {
            "date__range": [start_date, end_date],
            "ad_account_id__in": ad_account_list,
            "campaign_id__in": campaign_list,
        }
        filters = {k: v for k, v in filters.items() if v}
        spend = DailyAdspendGenre.objects.filter(**filters).aggregate(
            total_spend=Sum("spend")
        )

        return Response(
            status=status.HTTP_200_OK,
            data={"error": False, "data": [spend], "message": ""},
        )


class AdsetAPIView(ModelViewSet):
    """
    A viewset for managing adsets.
    Provides the following features:
    - Listing adsets
    - Filtering adsets by start and end date
    - Filtering adsets by ad platform
    - Searching adsets by adsets ID or name
    - Ordering adsets by any field
    - Pagination of results
    """

    authentication_classes = (TokenAuthentication,)
    queryset = AdAdsets.objects.all()
    serializer_class = AdAdsetsGetallDataSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["adset_id", "adset_name"]
    http_method_names = ["get", "put"]
    pagination_class = PageNumberPagination7

    def get_queryset(self):
        queryset = super(AdsetAPIView, self).get_queryset()
        ad_platform = self.request.query_params.get("ad_platform")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        new_end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        return (
            queryset.filter(ad_platform=ad_platform).filter(
                **{
                    "last_checked__range": [
                        start_date,
                        new_end_date + timedelta(days=1),
                    ]
                }
                if start_date and len(start_date) != 0
                else {},
            )
            if self.request.method in SAFE_METHODS
            else queryset
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Adset has been updated.",
            },
            status=status.HTTP_200_OK,
        )


class CampaignAPIViewSet(ModelViewSet):
    """
    A viewset for managing campaigns.
    Provides the following features:
    - Listing campaigns
    - Filtering campaigns by start and end date
    - Filtering campaigns by ad platform
    - Searching campaigns by campaign ID or name
    - Ordering campaigns by any field
    - Pagination of results
    """

    authentication_classes = (TokenAuthentication,)
    queryset = AdCampaigns.objects.all()
    serializer_class = CampaignSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = [
        "campaign_id",
        "campaign_name",
        "scraper_group__group_name",
        "automatic",
    ]
    pagination_class = PageNumberPagination7
    http_method_names = ["get", "put"]

    def get_queryset(self):
        queryset = super(CampaignAPIViewSet, self).get_queryset()
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        ad_platform = self.request.query_params.get("ad_platform")
        new_end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        return (
            queryset.filter(ad_platform=ad_platform).filter(
                **{"created_at__range": [start_date, new_end_date + timedelta(days=1)]}
                if start_date and len(start_date) != 0
                else {},
            )
            if self.request.method in SAFE_METHODS
            else queryset
        )

    @track_error(validate_api_parameters=["automatic"])
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Campaign auto optimize has been updated.",
            },
            status=status.HTTP_200_OK,
        )


class InterestAPIView(APIView):
    """
    A view for getting a list of recommended interests based on a search keyword.
    The ad platform, profile id, advertiser id, and search keyword are passed in the request data.
    The view returns a list of dictionaries containing the id and name of the recommended interests.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=[
            "ad_platform",
            "profile_id",
            "search_keyword",
            "advertiser_id",
        ]
    )
    def post(self, request, *args, **kwargs):
        ad_platform = request.data.get("ad_platform")
        profile_id = request.data.get("profile_id")
        search_keyword = request.data.get("search_keyword")
        advertiser_id = request.data.get("advertiser_id")
        interest_data_list = []
        if ad_platform == PlatFormType.FACEBOOK:
            access_token = (
                Authkey.objects.filter(profile_id=profile_id)
                .values("access_token")
                .first()
            )
            params = {
                "interest_list": f"['{search_keyword}']",
                "type": "adinterestsuggestion",
                "access_token": access_token.get("access_token"),
            }
            response = requests.get(url_hp.FACEBOOK_SEARCH_INTREST_URL, params)
            if response.ok:
                if response_data := response.json().get("data"):
                    interest_data_list = list(
                        map(
                            lambda data: {
                                "id": data.get("id"),
                                "name": data.get("name"),
                            },
                            response_data,
                        )
                    )
            else:
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": response.json().get("error").get("message"),
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        elif ad_platform == PlatFormType.TIKTOK:
            """advertiser_id is account_id"""
            ad_account = (
                AdAccount.objects.select_related("profile")
                .values("profile_id")
                .get(account_id=advertiser_id)
            )
            authkey = (
                Authkey.objects.filter(profile_id=ad_account.get("profile_id"))
                .select_related("access_token")
                .values("access_token")
                .first()
            )
            response = requests.get(
                url_hp.TIKTOK_RECOMMENED_URL,
                params={
                    "advertiser_id": advertiser_id,
                    "keyword": search_keyword,
                },
                headers={
                    "Accept": "application/json",
                    "Access-Token": authkey.get("access_token"),
                },
            )
            r = response.json()
            if r.get("code") == 0:
                if response_data := r.get("data").get("recommended_keywords"):
                    interest_data_list = [
                        {"id": data.get("keyword_id"), "name": data.get("keyword")}
                        for data in response_data
                    ]
            else:
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": r.get("message"),
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        elif ad_platform == PlatFormType.SNAPCHAT:
            """access_token is Bearer token in Snap"""
            profile_obj = Profile.objects.get(id=profile_id)
            sc = SnapchatAPI(debug_mode=False, profile=profile_obj)
            response = requests.get(
                url_hp.SNAPCHAT_INTREST_URL,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {sc.access_token}",
                },
            )
            if response.status_code == 200:
                if response_data := response.json().get("targeting_dimensions"):
                    interest_data_list = list(
                        map(
                            lambda data: {
                                "id": data.get("scls").get("id"),
                                "name": data.get("scls").get("name"),
                            },
                            response_data,
                        )
                    )
            else:
                message = (
                    "Unauthorized"
                    if response.status_code == 401
                    else response.json().get("debug_message", "")
                )

                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": message,
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": interest_data_list,
                "message": "",
            },
        )


class ProfileAPIView(APIView):
    """
    This APIView provides functionality for fetching a list of profiles that are
    associated with a specific ad platform.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_platform"])
    def post(self, request, *args, **kwargs):
        ad_platform = request.data.get("ad_platform")
        profiles = Profile.objects.filter(ad_platform=ad_platform).values(
            "id", "first_name", "last_name", "ad_platform", "email", "avatar_url"
        )
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": profiles,
                "message": "",
            },
        )


class GetAdAccountUsingProfileAPIView(APIView):
    """
    This view handles the retrieval of ad accounts for a given profile. It first checks if the data is present in
    cache, and if it is, it returns the cached data. If the data is not in cache, it retrieves the data from the relevant ad
    platform (Facebook, TikTok, or Snapchat) and stores it in the database. It then serializes the data and stores it in cache
    before returning it to the client.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["profile_id"])
    def post(self, request, *args, **kwargs):
        profile_id = request.data.get("profile_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_{profile_id}"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(f"{uid}_{profile_id}"),
                    "message": "",
                },
            )
        ad_accounts = AdAccount.objects.filter(
            profile_id=profile_id, active=AdAccountActiveType.Yes
        )
        serializer = GetAdAccountUsingProfileSerializer(ad_accounts, many=True)
        cache.set(f"{uid}_{profile_id}", serializer.data, 300)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": serializer.data,
                "message": "",
            },
        )


class GetCampaignUsingAdAccountAPIView(APIView):
    """
    This view handles the retrieval of campaigns for a given ad account. It first checks if the data is present in
    cache, and if it is, it returns the cached data. If the data is not in cache, it retrieves the data from the relevant ad
    platform (Facebook, TikTok, or Snapchat) and stores it in the database. It then serializes the data and stores it in cache
    before returning it to the client.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=[
            "advertiser_id",
            "ad_platform",
            "search_keyword",
            "objective",
        ]
    )
    def post(self, request, *args, **kwargs):
        advertiser_id = request.data.get("advertiser_id")
        ad_platform = request.data.get("ad_platform")
        uid = request.headers.get("uid")
        search_keyword = request.data.get("search_keyword")
        objective = request.data.get("objective")
        if cache.get(f"{uid}_{advertiser_id}_{ad_platform}_{objective}"):
            if bool(search_keyword):
                adcampaigns_yes = AdCampaigns.objects.filter(
                    campaign_name__icontains=search_keyword,
                    advertiserid=advertiser_id,
                    objective__icontains=objective,
                    active="Yes",
                ).order_by("-active")
                adcampaigns_no = AdCampaigns.objects.filter(
                    campaign_name__icontains=search_keyword,
                    advertiserid=advertiser_id,
                    objective__icontains=objective,
                    active="No",
                ).order_by("-active")[:20]
                combined_status = adcampaigns_yes | adcampaigns_no
                serializer = CampaignSerializer(combined_status, many=True)
                return Response(
                    status=status.HTTP_200_OK,
                    data={
                        "error": False,
                        "data": serializer.data,
                        "message": "",
                    },
                )
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(
                        f"{uid}_{advertiser_id}_{ad_platform}_{objective}"
                    ),
                    "message": "",
                },
            )

        adcampaigns_yes = AdCampaigns.objects.filter(
            campaign_name__icontains=search_keyword,
            advertiserid=advertiser_id,
            objective__icontains=objective,
            active="Yes",
        ).order_by("-active")
        adcampaigns_no = AdCampaigns.objects.filter(
            campaign_name__icontains=search_keyword,
            advertiserid=advertiser_id,
            objective__icontains=objective,
            active="No",
        ).order_by("-active")[:20]
        combined_status = adcampaigns_yes | adcampaigns_no
        serializer = CampaignSerializer(combined_status, many=True)
        cache.set(
            f"{uid}_{advertiser_id}_{ad_platform}_{objective}", serializer.data, 300
        )
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": serializer.data,
                "message": "",
            },
        )


class IdentityAPIView(APIView):
    """
    This class is used to get the identity information of a TikTok advertiser account.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["advertiser_id"])
    def post(self, request, *args, **kwargs):
        advertiser_id = request.data.get("advertiser_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_{advertiser_id}_identity_{PlatFormType.TIKTOK}"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(
                        f"{uid}_{advertiser_id}_identity_{PlatFormType.TIKTOK}"
                    ),
                    "message": "",
                },
            )
        ad_account = AdAccount.objects.get(account_id=advertiser_id)
        access_token = (
            Authkey.objects.filter(profile_id=ad_account.profile_id)
            .values_list("access_token", flat=True)
            .first()
        )
        response = requests.get(
            url_hp.TIKTOK_IDENTITY_URL,
            params={
                "advertiser_id": advertiser_id,
            },
            headers={
                "Accept": "application/json",
                "Access-Token": access_token,
            },
        )
        r = response.json()
        if r.get("code") == 0:
            identity_list = r.get("data").get("identity_list")
            cache.set(
                f"{uid}_{advertiser_id}_identity_{PlatFormType.TIKTOK}",
                identity_list,
                300,
            )
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": identity_list,
                    "message": "",
                },
            )
        else:
            return Response(
                data={"error": True, "data": [], "message": f"{r.get('message')}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class ApplistAPIView(APIView):
    """
    This class is used to get a list of apps associated with a given advertiser ID.
    The list is returned as a response to a POST request made to this view.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["advertiser_id"])
    def post(self, request, *args, **kwargs):
        advertiser_id = request.data.get("advertiser_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_{advertiser_id}_apps_{PlatFormType.TIKTOK}"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(
                        f"{uid}_{advertiser_id}_apps_{PlatFormType.TIKTOK}"
                    ),
                    "message": "",
                },
            )
        ad_account = (
            AdAccount.objects.select_related("profile")
            .values("profile_id")
            .get(account_id=advertiser_id)
        )
        authkey = (
            Authkey.objects.filter(profile_id=ad_account.get("profile_id"))
            .select_related("access_token")
            .values("access_token")
            .first()
        )
        response = requests.get(
            url_hp.TIKTOK_APPLIST_URL,
            params={
                "advertiser_id": advertiser_id,
            },
            headers={
                "Accept": "application/json",
                "Access-Token": authkey.get("access_token"),
            },
        )
        r = response.json()
        if r.get("code") == 0:
            app_list = r.get("data").get("apps")
            cache.set(
                f"{uid}_{advertiser_id}_apps_{PlatFormType.TIKTOK}",
                app_list,
                300,
            )
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": app_list,
                    "message": "",
                },
            )
        else:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"{r.get('message')}",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )


class GetPixelUsingAdAccountAPIView(APIView):
    """
    This view handles the retrieval of pixels for a given ad account. It first checks if the data is present in
    cache, and if it is, it returns the cached data. If the data is not in cache, it retrieves the data from the relevant ad
    platform (Facebook, TikTok, or Snapchat) and stores it in the database. It then serializes the data and stores it in cache
    before returning it to the client.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_platform", "advertiser_id"])
    def post(self, request, *args, **kwargs):
        ad_platform = request.data.get("ad_platform")
        advertiser_id = request.data.get("advertiser_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_{advertiser_id}_pixels_{ad_platform}"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(f"{uid}_{advertiser_id}_pixels_{ad_platform}"),
                    "message": "",
                },
            )
        pixels = Pixels.objects.filter(advertiser_id=advertiser_id).values(
            "pixel_id", "name"
        )
        cache.set(f"{uid}_{advertiser_id}_pixels_{ad_platform}", pixels, 300)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": pixels,
                "message": "",
            },
        )


class GetOptimizeEventUsingAdAccountAPIView(APIView):
    """
    This view handles the retrieval of optimization events for a given ad account. It first checks if the data is present in
    cache, and if it is, it returns the cached data. If the data is not in cache, it retrieves the data from the relevant ad
    platform (Facebook, TikTok, or Snapchat) and stores it in the database. It then serializes the data and stores it in cache
    before returning it to the client.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_platform", "account_id", "pixel_id"])
    def post(self, request, *args, **kwargs):
        ad_platform = request.data.get("ad_platform")
        account_id = request.data.get("account_id")
        pixel_id = request.data.get("pixel_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_optimize_event_{account_id}_{ad_platform}"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(
                        f"{uid}_optimize_event_{account_id}_{ad_platform}"
                    ),
                    "message": "",
                },
            )

        custom_conversion_events = list(
            CustomConversionEvents.objects.filter(
                account_id=account_id, pixel_id=pixel_id
            ).values_list("name","event_id")
        )
        custom_conversion_events_dict = {key.split()[0]: value for key, value in custom_conversion_events}
        conversation_event = {
            PlatFormType.FACEBOOK: ConversationEvent.FACEBOOK,
            PlatFormType.TIKTOK: ConversationEvent.TIKTOK,
            PlatFormType.SNAPCHAT: ConversationEvent.SNAPCHAT,
        }
        # custom_conversion_events = custom_conversion_events + conversation_event.get(
        #     ad_platform
        # )
        static_custom_conversion_events = conversation_event.get(
            ad_platform
        )
        events_dict = dict(static_custom_conversion_events[0], **custom_conversion_events_dict)
        cache.set(
            f"{uid}_optimize_event_{account_id}_{ad_platform}",
            # list(set(custom_conversion_events)),
            events_dict,
            300,
        )
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": events_dict,
                "message": "",
            },
        )


class CustomAudienceUsingAdaccountAPIView(APIView):
    """
    This view handles the retrieval of custom audiences for a given ad account. It first checks if the data is present in cache,
    and if it is, it returns the cached data. If the data is not in cache, it retrieves the data from the relevant ad platform
    (Facebook, TikTok, or Snapchat) and stores it in the database. It then serializes the data and stores it in cache before
    returning it to the client.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_platform", "account_id"])
    def post(self, request, *args, **kwargs):
        ad_platform = request.data.get("ad_platform")
        account_id = request.data.get("account_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_custom_audiences_{account_id}_{ad_platform}"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(
                        f"{uid}_custom_audiences_{account_id}_{ad_platform}"
                    ),
                    "message": "",
                },
            )

        custom_audiences = CustomAudiences.objects.filter(account_id=account_id).values(
            "audience_id", "name"
        )
        cache.set(
            f"{uid}_custom_audiences_{account_id}_{ad_platform}", custom_audiences, 300
        )
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": custom_audiences,
                "message": "",
            },
        )


class SchedulePresetAPIViewSet(ModelViewSet):
    """
    The SchedulePresetAPIViewSet is a viewset class that provides API endpoints for
    creating, updating, retrieving, and deleting SchedulePresets.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = SchedulePresets.objects.all()
    serializer_class = SchedulePresetSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["preset_name"]
    pagination_class = None
    http_method_names = ["get", "put", "post", "delete"]

    def get_queryset(self):
        with_schedule_preset_settings_data = (
            self.request.query_params.get("with_schedule_preset_settings_data")
            == "True"
        )
        SchedulePresetSerializer.with_schedule_preset_settings_data = (
            with_schedule_preset_settings_data
        )
        queryset = super(SchedulePresetAPIViewSet, self).get_queryset()
        return queryset

    @track_error(validate_api_parameters=["preset_name"])
    def create(self, request, *args, **kwargs):
        request.data["created_on"] = datetime.now()
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save(created_by=self.request.user)
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "The preset has been successfully created.",
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": serializer.errors.get("preset_name")[0],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @track_error()
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        for attr, value in request.data.items():
            setattr(instance, attr, value)
        instance.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Preset has been successfully updated.",
            },
            status=status.HTTP_200_OK,
        )

    @track_error()
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "The preset has been removed.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, instance):
        instance.delete()


class ScheduleHistorysAPIViewSet(ModelViewSet):
    """
    This class handles the scheduler history information along with the percentage. also shows the entire batch in one click.
    The data in the AdScheduler, Linkfire-generated links,AdAdsets, and AdCreativeIds is used to get the relevant platform (Facebook, TikTok, or Snapchat).
    """

    authentication_classes = (TokenAuthentication,)
    queryset = AdScheduler.objects.all()
    serializer_class = SchedulerHistorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["extra_name", "landingpage_url", "scraper_group__group_name"]
    pagination_class = PageNumberPagination7
    http_method_names = ["get"]

    def get_queryset(self):
        scraper_group = self.request.query_params.get("scraper_group")
        group_by_id = (
            AdScheduler.objects.all()
            .distinct("uploadsesid")
            .values_list("id", flat=True)
        )
        queryset_result = (
            (
                AdScheduler.objects.all()
                .filter(id__in=group_by_id)
                .order_by("-created_on")
            )
            .filter(**{"scraper_group": scraper_group} if scraper_group else {})
            .exclude(platform="CUSTOM_LINKFIRE")
        )
        return queryset_result


class RetryScheduleBatchAPIView(APIView):
    """
    This class handles the retry of the schedule batch using the upload session id.
    It first validates the required parameters, then updates the completion status of the AdScheduler model to "No".
    It returns a success message with a 200 OK status code if the batch has been successfully retried.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["uploadsesid"])
    def post(self, request, *args, **kwargs):
        uploadsesid = request.data.get("uploadsesid")
        AdScheduler.objects.filter(uploadsesid=uploadsesid).update(completed="No")
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Batch has been successfully retryed.",
            },
            status=status.HTTP_200_OK,
        )


class StopSchedulingAPIViewSet(APIView):
    """
    This class handles the stop of the schedule batch using the upload session id.
    It first validates the required parameters and then updates the completion status of the AdScheduler model to "Stop".
    It returns a success message with a 200 OK status code if the batch has been successfully stopped.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_scheduler_id", "completed"])
    def post(self, request, *args, **kwargs):
        ad_scheduler_id = request.data.get("ad_scheduler_id")
        completed = request.data.get("completed")
        AdScheduler.objects.filter(id=ad_scheduler_id).update(completed=completed)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Scheduling changes in this batch are done.",
            },
            status=status.HTTP_200_OK,
        )


class FetchLatestProfileDataAPIViewSet(APIView):
    """
    This api represents that allows users to retrieve the latest
    profile data from different ad platforms (such as Facebook, TikTok, and Snapchat).
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_platform"])
    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        ad_platform = request.data.get("ad_platform")
        profile_response = []
        profiles = Profile.objects.filter(ad_platform=ad_platform).exclude(
            ad_platform=PlatFormType.LINKFIRE
        )
        tasks = [
            fetch_latest_profile_data.s(uid, profile_obj.id, ad_platform)
            for profile_obj in profiles
        ]

        if tasks:
            # Run all tasks in parallel using Celery's group function
            result = group(tasks).apply_async()
            # Wait for all tasks to complete
            while not result.ready():
                time.sleep(1)
            task_results = result.get()
            profile_response += task_results

            # Check if all tasks were successful
            if all(task.successful() for task in result):
                if cache.get(f"{uid}_platform_{ad_platform}"):
                    cache.delete(f"{uid}_platform_{ad_platform}")
            else:
                # If any tasks failed, return an error response
                return Response(
                    data={
                        "error": "One or more tasks failed",
                        "data": profile_response,
                        "message": f"{ad_platform} data update failed.",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # If no tasks were created, return a success response
        return Response(
            data={
                "error": None,
                "data": profile_response,
                "message": f"{ad_platform} latest data updated successfully.",
            },
            status=status.HTTP_200_OK,
        )


class FetchLatestAdaccountDataAPIViewSet(APIView):
    """
    This class handles the most recent information from the profile ID, platform ID, and account ID.
    The data in the ad account, campaign pixels, custom audiences, audiences is updated for the relevant ad platform (Facebook, TikTok, or Snapchat) and stored in the database.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["ad_platform", "profile_id", "advertiser_id"])
    def post(self, request, *args, **kwargs):
        ad_platform = request.data.get("ad_platform")
        profile_id = request.data.get("profile_id")
        advertiser_id = request.data.get("advertiser_id")
        profile_obj = Profile.objects.get(id=profile_id)

        # Use a dictionary to map the ad_platform to the corresponding API class
        api_classes = {
            PlatFormType.FACEBOOK: FacebookAPI,
            PlatFormType.TIKTOK: TikTokAPI,
            PlatFormType.SNAPCHAT: SnapchatAPI,
        }
        # Look up the class using the ad_platform and call the method
        try:
            api = api_classes[ad_platform](
                debug_mode=settings.DEBUG, profile=profile_obj
            )
            if ad_platform == PlatFormType.FACEBOOK:
                api.initializing_bussiness_adaccounts()
                api.initializer_campaigns(
                    {"account_id": advertiser_id},
                    api="get-campaign-using-adaccount",
                )
                business_id = AdAccount.objects.filter(account_id=advertiser_id).values(
                    "business_id__business_id"
                )[0]
                api.initializer_pixels(
                    business_id=business_id["business_id__business_id"]
                )
                api.customConversionEvents_to_database(account_id=advertiser_id)
                api.customAudiences_to_database(account=advertiser_id)
            elif ad_platform == PlatFormType.TIKTOK:
                api.initializing_bussiness_adaccounts()
                api.initializer_campaigns(ad_account_id=advertiser_id)
                api.initializer_pixels(advertiser_id=advertiser_id)
                api.initialize_audience_data(account_id=advertiser_id)
            elif ad_platform == PlatFormType.SNAPCHAT:
                api.initializing_bussiness_adaccounts()
                api.campaigns_to_database(advertiser_id)
                api.pixels_to_database(account_id=advertiser_id)
                api.audiences_to_database(account_id=advertiser_id)
            message = None
            error = False
        except Exception as e:
            message = str(e)
            error = True
        return Response(
            data={
                "error": None,
                "data": [
                    {
                        "profile_id": profile_id,
                        "advertiser_id": advertiser_id,
                        "error": error,
                        "error_message": message,
                    }
                ],
                "message": f"{ad_platform} latest data updated successfully.",
            },
            status=status.HTTP_200_OK,
        )


class ReuseHistoryBatchAPIView(APIView):
    """
    This class handles the most recent information from the profile ID, platform ID, and account ID.
    The data in the ad account, campaign pixels, custom audiences, audiences is updated for the relevant ad platform (Facebook, TikTok, or Snapchat) and stored in the database.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["reuse_batch"])
    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        reuse_batch = request.data.get("reuse_batch")
        create_uploadsesid = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=13)
        )
        for reuse_batch_data in reuse_batch:
            profile_id = reuse_batch_data.get("profile_id")
            ad_scheduler_id = reuse_batch_data.get("ad_scheduler_id")
            ad_creative_id = reuse_batch_data.get("ad_creative_id")
            batch = AdScheduler.objects.filter(id=ad_scheduler_id).values().first()
            create_batch = AdScheduler(
                uploadsesid=create_uploadsesid,
                platform=batch.get("platform"),
                scraper_group_id=batch.get("scraper_group_id"),
                type_post=batch.get("type_post"),
                placement_type=batch.get("placement_type"),
                campaign_name=batch.get("campaign_name"),
                campaign_id=batch.get("campaign_id"),
                adaccount_id=batch.get("adaccount_id"),
                extra_name=batch.get("extra_name"),
                bundle_countries=batch.get("bundle_countries"),
                countries=batch.get("countries"),
                age_range=batch.get("age_range"),
                budget=batch.get("budget"),
                max_budget=batch.get("max_budget"),
                dayparting=batch.get("dayparting"),
                language=batch.get("language"),
                landingpage_url=batch.get("landingpage_url"),
                heading=batch.get("heading"),
                caption=batch.get("caption"),
                bid_strategy=batch.get("bid_strategy"),
                bid=batch.get("bid"),
                objective=batch.get("objective"),
                pixel_id=batch.get("pixel_id"),
                event_type=batch.get("event_type"),
                app_platform=batch.get("app_platform"),
                application_id=batch.get("application_id"),
                custom_audiences=batch.get("custom_audiences"),
                ignore_until=batch.get("ignore_until"),
                scheduled_for=batch.get("scheduled_for"),
                strategy=batch.get("strategy"),
                interests=batch.get("interests"),
                accelerated_spend=batch.get("accelerated_spend"),
                completed="No",
                user_id=batch.get("user_id"),
                authkey_email_user=batch.get("authkey_email_user"),
                tiktok_identity_type=batch.get("tiktok_identity_type"),
                tiktok_identity_id=batch.get("tiktok_identity_id"),
                company_name=batch.get("company_name"),
                instagram_id=batch.get("instagram_id"),
                facebook_pages_ids=batch.get("facebook_pages_ids"),
                profile_id=profile_id,
            )
            create_batch._uuid = uid
            create_batch._profile_id = profile_id
            create_batch.save()
            creative_list = AdCreativeIds.objects.filter(id__in=ad_creative_id).values()
            for creative in creative_list:
                create_creative = AdCreativeIds(
                    uploadsesid=create_batch.uploadsesid,
                    ad_platform=creative.get("ad_platform"),
                    filename=creative.get("filename"),
                    url=creative.get("url"),
                    thumbnail_url=creative.get("thumbnail_url"),
                    creative_type=creative.get("creative_type"),
                    placement_type=creative.get("placement_type"),
                    notes=creative.get("notes"),
                    user_id=creative.get("user_id"),
                    landingpage_url=creative.get("landingpage_url"),
                    heading=creative.get("heading"),
                    resolution=creative.get("resolution"),
                    caption=creative.get("caption"),
                    ad_adset_id=creative.get("ad_adset_id"),
                    scheduler_id=create_batch.id,
                    creative_size=creative.get("creative_size"),
                    linkfire_id=creative.get("linkfire_id"),
                )
                create_creative.save()
        return Response(
            data={
                "error": True,
                "data": [],
                "message": "Reuse the batch that was successfully created.",
            },
            status=status.HTTP_201_CREATED,
        )


class AutoSchedulerDraftAPIViewSet(ModelViewSet):
    """
    Draft is a viewset class that provides CRUD operations for Draft model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = AutoSchedulerDraft.objects.all()
    serializer_class = AutoSchedulerDraftSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    pagination_class = None
    http_method_names = ["get", "post", "delete"]

    @track_error()
    def list(self, request, *args, **kwargs):
        queryset = super(AutoSchedulerDraftAPIViewSet, self).get_queryset()
        return Response(
            data={
                "error": False,
                "data": queryset.filter(user_id=self.request.user.id).values(),
                "message": None,
            },
            status=status.HTTP_200_OK,
        )

    @track_error()
    def create(self, request, *args, **kwargs):
        draft_data = request.data.get("draft_data", {})
        current_page = request.data.get("current_page")
        user = self.request.user
        draft, _ = AutoSchedulerDraft.objects.update_or_create(
            user=user,
            defaults={
                "draft_data": draft_data,
                "current_page": current_page,
            },
        )
        serializer = self.get_serializer(draft, context={"request": request})
        return Response(
            data={
                "error": False,
                "data": [serializer.data],
                "message": "Draft has been successfully created.",
            },
            status=status.HTTP_201_CREATED,
        )

    @track_error()
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "The draft has been deleted.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, instance):
        try:
            draft_data = AutoSchedulerDraft.objects.get(id=instance.id)
        except AutoSchedulerDraft.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={
                    "error": True,
                    "data": [],
                    "message": "AutoScheduler draft detail not found.",
                },
            )
        draft_data = self.serializer_class(draft_data, many=False).data
        
        creatives = draft_data.get("draft_data").get("creatives")
        uploadsesid = draft_data.get("draft_data").get("uploadsesId")
        
        s3 = S3BucketHelper(foldername=f"upload_creative/{uploadsesid}")
        deleted_creatives = []
        error_message = None

        for creative in creatives.get("files"):
            creative_name = creative.get("path").replace(" ", "_")
            try:
                is_success, error_message = s3.delete_to_s3(creative_name=creative_name)
                if is_success:
                    deleted_creatives.append(creative_name)
                else:
                    raise AmazonS3UploadingException(error_message)
            except (Exception, AmazonS3UploadingException) as e:
                error_message = str(e)
                break

        if error_message:
            return Response(
                status=status.HTTP_406_NOT_ACCEPTABLE,
                data={
                    "error": False,
                    "data": [],
                    "message": error_message,
                },
            )
        # delete folder after delete files
        try:
            s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=f"upload_creative/{uploadsesid}")
        except ClientError as e:
            return Response(
                status=status.HTTP_406_NOT_ACCEPTABLE,
                data={
                    "error": False,
                    "data": [],
                    "message": str(e),
                },
            )
        
        AdCreativeIds.objects.filter(
            uploadsesid=uploadsesid,
            filename__in=deleted_creatives,
        ).delete()
        instance.delete()


class GenerateUploadsesIdAPIView(APIView):
    """
    The GenerateUploadsesIdAPIView is a view class that provides an API endpoint
    for generating a unique identifier for AdCreativeIds objects.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        uploadsesid = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=13)
        )

        while AdCreativeIds.objects.filter(uploadsesid=uploadsesid).exists():
            uploadsesid = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=13)
            )

        return Response(
            data={
                "error": False,
                "data": {"uploadsesid": uploadsesid},
                "message": "Uploadses id has been successfully generated.",
            },
            status=status.HTTP_201_CREATED,
        )


class TestWebhookAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        Webhook.objects.create(json_data=request.data)
        return Response(
            status=status.HTTP_200_OK,
        )


class ReviewPageAdsetCalculationAPIView(APIView):
    """
    ReviewPageAdsetCalculation is a viewset class that provides scheduler review page adsets based on placement,bundle countries, and platform.
    """

    authentication_classes = (TokenAuthentication,)

    results = {}

    def build_adsets(self, uploadsesid, max_nr_creatives):
        ad_creatives = AdCreativeIds.objects.filter(uploadsesid=uploadsesid).values(
            "id", "filename", "url", "creative_type", "placement_type", "creative_size"
        )
        adset = math.ceil(len(ad_creatives) / max_nr_creatives)
        sublists = [
            ad_creatives[data_index : data_index + max_nr_creatives]
            for data_index in range(0, len(ad_creatives), max_nr_creatives)
        ]
        return sublists, adset

    def handel_facebook_adset(self):
        facebook = []
        if facebook_adset := self.request.data.get("Facebook"):
            placements = facebook_adset.get("placements")
            max_nr_creatives = facebook_adset.get("max_nr_creatives")
            placement_type = facebook_adset.get("placement_type")
            creative, adset = self.build_adsets(
                self.request.data.get("uploadsesid"), max_nr_creatives
            )
            if self.request.data.get("bundle_countries"):
                if placements:
                    placement_type = None
                else:
                    manual_placement = placement_type.split(",")
                for value in [placement_type] if placements else manual_placement:
                    facebook = [
                        {
                            "countries": self.request.data.get("countries"),
                            "ad_creative": creative[index]
                            if index < len(creative)
                            else [],
                            "daily_budget": self.request.data.get("daily_budget"),
                            "placement_type": value,
                        }
                        for index in range(adset)
                    ]
            else:
                countries_list = self.request.data.get("countries").split(",")
                if placements:
                    facebook = [
                        {
                            "countries": each_countries,
                            "ad_creative": creative[index]
                            if index < len(creative)
                            else [],
                            "daily_budget": self.request.data.get("daily_budget"),
                            "placement_type": None,
                        }
                        for each_countries in countries_list
                        for index in range(adset)
                    ]
                else:
                    manual_palcement = placement_type.split(",")
                    facebook = [
                        dict(
                            countries=each_countries,
                            ad_creative=creative[index]
                            if index < len(creative)
                            else [],
                            daily_budget=self.request.data.get("daily_budget"),
                            placement_type=value,
                        )
                        for value in manual_palcement
                        for each_countries in countries_list
                        for index in range(adset)
                    ]
        self.results["Facebook"] = facebook

    def handel_tiktok_adset(self):
        tiktok = []
        if tiktok_adset := self.request.data.get("Tiktok"):
            max_nr_creatives = tiktok_adset.get("max_nr_creatives")
            creative, adset = self.build_adsets(
                self.request.data.get("uploadsesid"), max_nr_creatives
            )
            countries_list = self.request.data.get("countries").split(",")
            if self.request.data.get("bundle_countries"):
                tiktok = [
                    {
                        "countries": self.request.data.get("countries"),
                        "ad_creative": creative[value] if value < len(creative) else [],
                        "daily_budget": self.request.data.get("daily_budget"),
                        "placement_type": None,
                    }
                    for value in range(adset)
                ]
            else:
                tiktok = [
                    dict(
                        countries=each_countries,
                        ad_creative=creative[value] if value < len(creative) else [],
                        daily_budget=self.request.data.get("daily_budget"),
                        placement_type=None,
                    )
                    for each_countries in countries_list
                    for value in range(adset)
                ]
        self.results["Tiktok"] = tiktok

    def handel_snapchat_adset(self):
        snap = []
        if snap_adset := self.request.data.get("Snap"):
            max_nr_creatives = snap_adset.get("max_nr_creatives")
            creative, adset = self.build_adsets(
                self.request.data.get("uploadsesid"), max_nr_creatives
            )
            countries_list = self.request.data.get("countries").split(",")
            if self.request.data.get("bundle_countries"):
                snap = [
                    dict(
                        countries=self.request.data.get("countries"),
                        ad_creative=creative[value] if value < len(creative) else [],
                        daily_budget=self.request.data.get("daily_budget"),
                        placement_type=None,
                    )
                    for value in range(adset)
                ]
            else:
                snap = [
                    dict(
                        countries=each_countries,
                        ad_creative=creative[value] if value < len(creative) else [],
                        daily_budget=self.request.data.get("daily_budget"),
                        placement_type=None,
                    )
                    for each_countries in countries_list
                    for value in range(adset)
                ]
        self.results["Snap"] = snap

    def run_parallel(self, *functions):
        from multiprocessing import Process

        processes = []
        for function in functions:
            proc = Process(target=function)
            proc.start()
            processes.append(proc)
        for proc in processes:
            proc.join()

    @track_error()
    def post(self, request, *args, **kwargs):
        self.run_parallel
        (
            self.handel_tiktok_adset(),
            self.handel_snapchat_adset(),
            self.handel_facebook_adset(),
        )

        return Response(
            data={
                "error": False,
                "data": {
                    "Facebook": self.results.get("Facebook"),
                    "Tiktok": self.results.get("Tiktok"),
                    "Snap": self.results.get("Snap"),
                },
                "message": "",
            },
            status=status.HTTP_200_OK,
        )


class InsertReuseCreativeAPIView(APIView):
    """
    This class is responsible for handling the creation of
    AdCreatives by reusing existing ones.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=["uploadsesid", "reuse_creatives", "old_uploadsesid"]
    )
    def post(self, request, *args, **kwargs):
        uploadsesid = request.data.get("uploadsesid")
        old_uploadsesid = request.data.get("old_uploadsesid")
        reuse_creatives = request.data.get("reuse_creatives")
        bulk_ad_creative_create_objects = []
        for creative in reuse_creatives:
            bulk_ad_creative_create_objects.append(
                AdCreativeIds(**{**creative, **{"uploadsesid": uploadsesid}})
            )

        AdCreativeIds.objects.bulk_create(bulk_ad_creative_create_objects)

        creative_placement_type_counting = (
            AdCreativeIds.objects.filter(
                uploadsesid=uploadsesid,
                placement_type__in=[
                    PlacementType.POST,
                    PlacementType.STORY,
                    PlacementType.REELS,
                ],
            )
            .values_list("placement_type")
            .annotate(count=Count("placement_type"))
            .order_by()
            .values("placement_type", "count")
        )
        uploaded_creative = AdCreativeIds.objects.filter(
            uploadsesid=uploadsesid
        ).values(
            "id",
            "filename",
            "url",
            "creative_type",
            "placement_type",
            "creative_size",
            "landingpage_url",
        )
        adscheduler_data = (
            AdScheduler.objects.filter(uploadsesid=old_uploadsesid)
            .values("auto_scheduler_json")
            .first()
        )
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                "error": False,
                "data": [
                    {
                        "uploadSesid": uploadsesid,
                        "creative_placement_type_counting": creative_placement_type_counting,
                        "uploaded_creative": uploaded_creative,
                        "adscheduler_data": adscheduler_data.get("auto_scheduler_json"),
                    }
                ],
                "message": "Creative has been successfully inserted.",
            },
        )


class ScheduleHistorysProgressAPIViewSet(ModelViewSet):
    """
    This class handles the scheduler history information along with the percentage. also shows the entire batch in one click.
    The data in the AdScheduler, Linkfire-generated links,AdAdsets, and AdCreativeIds is used to get the relevant platform (Facebook, TikTok, or Snapchat).
    """

    authentication_classes = (TokenAuthentication,)
    queryset = AdScheduler.objects.all()
    serializer_class = ScheduleHistorysProgressSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["extra_name", "landingpage_url", "scraper_group__group_name"]
    pagination_class = PageNumberPagination7
    http_method_names = ["get"]

    def get_queryset(self):
        scraper_group = self.request.query_params.get("scraper_group")
        group_by_id = (
            AdScheduler.objects.filter(uploadsesid__isnull=False)
            .distinct("uploadsesid")
            .values_list("id", flat=True)
        )
        queryset_result = (
            (AdScheduler.objects.filter(id__in=group_by_id).order_by("-created_on"))
            .filter(**{"scraper_group": scraper_group} if scraper_group else {})
            .exclude(platform="CUSTOM_LINKFIRE")
        )
        return queryset_result


class SchedulerHistoryDetailsAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["uploadsesid"])
    def post(self, request, *args, **kwargs):
        uploadsesid_data = request.data.get("uploadsesid")
        scheduler_data = AdScheduler.objects.filter(uploadsesid=uploadsesid_data)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": SchedulerHistoryDetailsSerializer(
                    scheduler_data, many=True
                ).data,
                "message": "",
            },
        )
