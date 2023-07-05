from apps.common.constants import CreativeType, PublishedContentType, Marketplace
from apps.marketplace.models import (
    Job,
    JobCategory,
    Submission,
    SubmissionApprovalStatus,
    SubmissionViewCount,
    CreatorProfile,
    BrandProfile,
    SocialProfile,
    SocialAuthkey,
    SocialBusiness,
    SocialCPM,
    JobMilestones,
    MilestoneStatus,
    Draft,
    Payout,
    SpentBalance,
    JobPayment,
)
from apps.marketplace.api_v1.serializers import (
    JobSerializer,
    JobCategorySerializer,
    SubmissionSerializer,
    SubmissionApprovalStatusSerializer,
    SubmissionViewCountSerializer,
    CreatorProfileSerializer,
    BrandProfileSerializer,
    JobMilestonesSerializer,
    CPMSerializer,
    DraftSerializer,
    PayoutSerializer,
    JobPaymentSerializer,
)
from rest_framework.viewsets import ModelViewSet
from rest_framework import filters, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from SF import settings
from apps.common.s3_helper import S3BucketHelper
from apps.common.upload_creative_helper import UploadCreativeHelper
from apps.marketplace.helper.budget_handler import BudgetCalculation
from apps.marketplace.helper.generate_invoice import generate_pdf
from apps.common.constants import (
    MPlatFormType,
    JobStatus,
    ApprovalStatus,
    MilestoneProgess,
    PayoutStatus,
    JobPaymentStatus,
    JobPaymentType
)
from apps.accounts.social_accounts import SocialAccountOAuth
from rest_framework import generics

from django.db.models import Q
from apps.common.sendgrid import SendGrid
from apps.common.custom_decorators import track_error
from apps.common.urls_helper import URLHelper
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
import json
from django.views.decorators.csrf import csrf_exempt
import requests
from apps.marketplace.helper.mfacebook_api_handler import MFacebookAPI, MFacebookMediaId
import random
import string
from pathlib import PurePath
from django.db.models import Sum
from apps.common.paginations import PageNumberPagination
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import zipfile
from io import BytesIO
import cgi
from django.http import HttpResponse

url_hp = URLHelper()


class CreatorProfileAPIViewSet(ModelViewSet):
    """
    CreatorProfileAPIViewSet is a viewset class that provides CRUD operations for CreatorProfile model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = CreatorProfile.objects.all()
    serializer_class = CreatorProfileSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["display_name"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super(CreatorProfileAPIViewSet, self).get_queryset()
        if self.request.user and self.request.query_params.get("flag") == "my_creator":
            data = queryset.filter(user_id=self.request.user.id)
            return data
        return queryset

    @track_error(validate_api_parameters=["display_name"])
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=self.request.user.id)
        return Response(
            data={
                "error": False,
                "data": [serializer.data],
                "message": "Your Creator Info has been successfully updated.",
            },
            status=status.HTTP_201_CREATED,
        )

    @track_error()
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=self.request.user.id)
        return Response(
            data={
                "error": False,
                "data": [serializer.data],
                "message": "Creator Marketplace has been successfully updated",
            },
        )


class BrandProfileAPIViewSet(ModelViewSet):
    """
    BrandProfileAPIViewSet is a viewset class that provides CRUD operations for BrandProfile model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = BrandProfile.objects.all()
    serializer_class = BrandProfileSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["brand_name"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super(BrandProfileAPIViewSet, self).get_queryset()
        if self.request.user and self.request.query_params.get("flag") == "my_brand":
            data = queryset.filter(user_id=self.request.user.id)
            return data
        queryset = queryset.filter(user_id=self.request.user.id)
        return queryset

    @track_error(validate_api_parameters=["brand_name"])
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=self.request.user.id)
        return Response(
            data={
                "error": False,
                "data": [serializer.data],
                "message": "Your Brand Info has been successfully updated.",
            },
            status=status.HTTP_201_CREATED,
        )

    @track_error()
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=self.request.user.id)
        return Response(
            data={
                "error": False,
                "data": [serializer.data],
                "message": "Brand profile has been successfully updated.",
            },
            status=status.HTTP_200_OK,
        )


class JobAPIViewSet(ModelViewSet):
    """
    JobAPIViewSet is a viewset class that provides CRUD operations for Job model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["title"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    @track_error()
    def list(self, request, *args, **kwargs):
        queryset = Job.objects.filter(
            status=JobStatus.ACTIVE,
        ) #.exclude(user_id=self.request.user.id)
        if request.query_params.get("publish_content_type"):
            queryset = queryset.filter(
                publish_content_type=request.query_params.get("publish_content_type"),
                status=JobStatus.ACTIVE,
            ) #.exclude(user_id=self.request.user.id)
        if request.query_params.get("category"):
            queryset = queryset.filter(category=request.query_params.get("category"))
        serializer = JobSerializer(queryset, many=True, context={"request": request})
        return Response(
            data={
                "error": False,
                "data": serializer.data,
                "message": "Job details fetch successfully.",
            },
            status=status.HTTP_200_OK,
        )

    @track_error(
        validate_api_parameters=[
            "brand",
            "category",
            "thumbnails",
            "job_requirements",
            "selected_budget",
        ]
    )
    def create(self, request, *args, **kwargs):
        brand = request.data.get("brand")
        category = request.data.get("category")
        payment_status = request.data.get("payment_status", "")
        payment_type = request.data.get("payment_type", "")
        payment_id = request.data.get("payment_id", "")

        brand_profile = BrandProfile.objects.filter(
            user_id=self.request.user.id, id=brand
        ).values()
        if not brand_profile:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Brand profile doesn't exist for this user.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        
        if payment_status == JobPaymentStatus.COMPLETED and payment_type and payment_id: 
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(
                user_id=self.request.user.id,
                brand_id=brand,
                category_id=category,
            )
            if (
                serializer.data
                and request.data.get("publish_content_type")
                == PublishedContentType.COLLECT_VIDEO_AND_POST
            ):
                bc_handler = BudgetCalculation(request.data)
                bc_handler.get_milestone(serializer.data.get("id"))
            Draft.objects.filter(user=self.request.user.id).delete()
            SpentBalance.objects.get_or_create(
                user_id=self.request.user.id,
                brand_id=brand,
                job_id=serializer.data.get("id"),
                amount=0,
            )
            
            payment_data = {
                "brand":brand,
                "job":serializer.data.get("id"),
                "amount":serializer.data.get("budget"),
                "payment_type":payment_type,
                "paymentid":payment_id,
            }
            payment = JobPaymentSerializer(data=payment_data)
            payment.is_valid(raise_exception=True)
            payment.save()

            return Response(
                data={
                    "error": False,
                    "data": [serializer.data],
                    "message": "Job Details has been successfully created.",
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Job Details has not been created.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @track_error(validate_api_parameters=["brand", "category"])
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        brand = request.data.get("brand")
        category = request.data.get("category")
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            user_id=self.request.user.id, brand_id=brand, category_id=category
        )
        return Response(
            data={
                "error": False,
                "data": [serializer.data],
                "message": "Job has been successfully updated",
            },
        )

class JobListAPI(ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = Job.objects.all()
    pagination_class = None
    http_method_names = ["get"]

    @track_error()
    def list(self, request, *args, **kwargs):
        queryset = Job.objects.filter(
            user_id=request.user.id
        ).values("title", "id")
        return Response(
            data={
                "error": False,
                "data": queryset,
                "message": "Job titles fetch successfully.",
            },
            status=status.HTTP_200_OK,
        )

class JobCategoryAPIViewSet(ModelViewSet):
    """
    JobCategoryAPIViewSet is a viewset class that provides CRUD operations for JobCategory model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["category_name"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]


class SubmissionAPIViewSet(ModelViewSet):
    """
    SubmissionAPIViewSet is a viewset class that provides CRUD operations for Submission model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    pagination_class = None
    http_method_names = ["get", "post", "put", "delete"]

    @track_error()
    def create_video_policy(self, title):
        url = f"{url_hp.VDOCIPHER_URL}/videos"
        headers = {"Authorization": f"Apisecret {settings.VDOCIPHER_API_SECRET_KEY}"}
        params = {"title": title}
        # Make the request to generate policy for upload video
        response = requests.put(url, headers=headers, params=params)
        return response.json() if response.status_code == 200 else {}

    @track_error()
    def upload_to_s3(self, policy_response, creator_content):

        # Define the data
        data = {
            "policy": policy_response.get("policy"),
            "key": policy_response.get("key"),
            "x-amz-signature": policy_response.get("x-amz-signature"),
            "x-amz-algorithm": policy_response.get("x-amz-algorithm"),
            "x-amz-date": policy_response.get("x-amz-date"),
            "x-amz-credential": policy_response.get("x-amz-credential"),
            "success_action_status": 201,
            "success_action_redirect": "",
        }
        url = policy_response.get("uploadLink")
        files = {"file": creator_content}
        # Make the request to upload video to vdocipher
        response = requests.post(url, data=data, files=files)
        return response

    def get_queryset(self):
        queryset = super(SubmissionAPIViewSet, self).get_queryset()
        status = self.request.query_params.get("status")
        job_id = self.request.query_params.get("search")
        if job_id and status:
            if status not in ["accepted", "declined"]:
                queryset = queryset.filter(job__id=job_id, approval_status__approval_status=status)
            else:
                queryset = []
            return queryset
        if job_id:
            queryset = queryset.filter(job__id=job_id).exclude(
                approval_status__approval_status__in=[ApprovalStatus.ACCEPTED,ApprovalStatus.DECLINED]
            )
            return queryset

        return queryset.filter(
            **(
                {"approval_status__approval_status": status}
                if status
                else {
                    "approval_status__approval_status__in": [
                        ApprovalStatus.APPROVAL_NEEDED,
                        ApprovalStatus.CREATOR_POST_PENDING,
                        ApprovalStatus.POST_CONFIRMATION_PENDING,
                    ]
                }
            )
        ).exclude(user_id=self.request.user.id)

    @track_error(validate_api_parameters=["job_id", "video"])
    def create(self, request, *args, **kwargs): 
        ## Update resubmission Flag ##
        resubmit = request.query_params.get('resubmit')
        creator_content = request.FILES.pop("video")[0]
        job_id = request.data.get("job_id")
        user_id = self.request.user.id
        try:
            job = Job.objects.get(id=job_id).user_id
        except Job.DoesNotExist:
            return Response({"error":True, "message":"Job detail not found"})
        if job == user_id:
            return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": "User cannot upload submission in their own jobs",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )
        if Submission.objects.filter(job__id=job_id, user=user_id).exists() and not resubmit:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Submission already exist.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        creator_content_type = UploadCreativeHelper.check_video_or_image(
            creator_content.name
        )

        if creator_content_type != CreativeType.VIDEO:
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    "error": True,
                    "data": [],
                    "message": f"{creator_content_type} is not supported.",
                },
            )
        policy_response = self.create_video_policy(creator_content.name)
        if len(policy_response.get("clientPayload")) > 0:
            video_data = self.upload_to_s3(
                policy_response.get("clientPayload"), creator_content
            )
            if video_data.status_code == 201:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(
                    user_id=self.request.user.id,
                    job_id=request.data.get("job_id"),
                    video_id=policy_response.get("videoId"),
                )
                submission = Submission.objects.latest("id")
                SubmissionApprovalStatus.objects.create(
                    submission=submission,
                    approval_status=ApprovalStatus.APPROVAL_NEEDED,
                )
                milestone_ids = (
                    JobMilestones.objects.only("id")
                    .prefetch_related("job")
                    .filter(job_id=job_id)
                )
                milestone_obj = [
                    MilestoneStatus(
                        status=MilestoneProgess.IN_PROGRESS,
                        milestone_id=recoard.id,
                        user=self.request.user,
                        submission=submission,
                    )
                    for recoard in milestone_ids
                ]
                MilestoneStatus.objects.bulk_create(milestone_obj, batch_size=100)
                submission = Submission.objects.filter(job_id=job_id).values(
                    "job__title",
                    "job__brand__user__email",
                ).first()
                if submission:
                    job_title = submission.get("job__title")
                    email = submission.get("job__brand__user__email")
                    sendgrid = SendGrid()
                    sendgrid.send_email_for_upload_content(email,job_title)
                else:
                    raise Exception("Mail is not sent.")
                return Response(
                    data={
                        "error": False,
                        "data": [serializer.data],
                        "message": "Video has been Uploaded Successfully.",
                    },
                    status=status.HTTP_201_CREATED,
                )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Video has been already exist.",
            },
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )

    @track_error(validate_api_parameters=["social_post_link"])
    def update(self, request, pk=None):
        social_post_link = request.data.get("social_post_link")
        user_id = self.request.user.id
        submission_id = int(pk)
        instance = Submission.objects.get(id=submission_id)
        media_id = None
        if instance.job.platforms == MPlatFormType.INSTAGRAM:
            fb_media_id = MFacebookMediaId(social_post_link, user_id)
            media_id = fb_media_id.get_media_id()
        elif instance.job.platforms == MPlatFormType.TIKTOK:
            path = PurePath(social_post_link)
            media_id = path.parts[-1] if path.parts[-1] else None
        elif instance.job.platforms == MPlatFormType.SNAPCHAT:
            print("snapchat post link to save media in db")

        if media_id is not None:
            instance.social_post_link = request.data.get("social_post_link")
            instance.save()

            SubmissionApprovalStatus.objects.filter(submission__id=instance.id).update(
                approval_status=ApprovalStatus.POST_CONFIRMATION_PENDING
            )
            SubmissionViewCount.objects.filter(submission__id=instance.id).get_or_create(
                media_id=media_id,
                platforms=instance.job.platforms,
                user_id=self.request.user.id,
                submission_id=instance.id,
                view_count=0,
            )
            submission = Submission.objects.filter(id=instance.id).values(
                    "user__first_name",
                    "job__brand__brand_name",
                    "job__brand__user__email",
                ).first()
            if submission:
                creator_name = submission.get("user__first_name")
                email = submission.get("job__brand__user__email")
                sendgrid = SendGrid()
                sendgrid.send_email_for_social_post_link(email,creator_name)
            else:
                raise Exception("Mail is not sent.")

            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Social post link updated successfully",
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"Invalid social post link for {instance.job.platforms}",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )


class MySubmissionAPIViewSet(ModelViewSet):
    """
    SubmissionAPIViewSet is a viewset class that provides CRUD operations for Submission model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields =  None
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super(MySubmissionAPIViewSet, self).get_queryset()
        queryset = queryset.filter(user_id=self.request.user.id)
        approval_status = self.request.query_params.get("approval_status")
        publish_content_type = self.request.query_params.get("publish_content_type")
        search = self.request.query_params.get("search")
        page = self.request.query_params.get("page", 1)
        page_size = 6

        if publish_content_type and page:
            queryset = queryset.filter(job__publish_content_type=publish_content_type)

        if approval_status == "pending" and page:
            queryset = queryset.filter(
                Q(approval_status__approval_status=ApprovalStatus.APPROVAL_NEEDED)
                | Q(
                    approval_status__approval_status=ApprovalStatus.POST_CONFIRMATION_PENDING
                )
            )
        elif approval_status in ["earning", "approved", "action_required", "declined"] and page:
            if search:
                approval_statuses = {
                    "approved": ApprovalStatus.ACCEPTED,
                    "declined": ApprovalStatus.DECLINED,
                }
                queryset = queryset.filter(
                    job__title__icontains=search,
                    approval_status__approval_status=approval_statuses.get(approval_status)
                )
            else:
                approval_statuses = {
                    "earning": ApprovalStatus.ACCEPTED,
                    "approved": ApprovalStatus.ACCEPTED,
                    "action_required": ApprovalStatus.CREATOR_POST_PENDING,
                    "declined": ApprovalStatus.DECLINED,
                }
                queryset = queryset.filter(
                    approval_status__approval_status=approval_statuses.get(approval_status)
                )
        paginator = Paginator(queryset, page_size)
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(page)
        except EmptyPage:
            queryset = []
        
        return queryset


class MyPastSubmissionAPIViewSet(ModelViewSet):
    """
    SubmissionAPIViewSet is a viewset class that provides CRUD operations for Submission model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["job__brand__brand_name"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        queryset = super(MyPastSubmissionAPIViewSet, self).get_queryset()
        approval_status = self.request.query_params.get("approval_status")
        job_id = self.request.query_params.get("job_id")

        return queryset.filter(
            job__id=job_id,
            job__user_id=self.request.user.id,
            approval_status__approval_status=approval_status,
        )


class SubmissionApprovalStatusAPIViewSet(ModelViewSet):
    """
    SubmissionApprovalStatusAPIViewSet is a viewset class that provides CRUD operations for Submission model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = SubmissionApprovalStatus.objects.all()
    serializer_class = SubmissionApprovalStatusSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["feedback"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    @track_error()
    def create(self, request, *args, **kwargs):

        submission = request.data.get("submission")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(submission_id=submission)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @track_error()
    def update(self, request, *args, **kwargs):

        instance = self.get_object()
        submission_id = request.data.get("submission")
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user_id=self.request.user.id, submission_id=submission_id)
        aproval_status = serializer.data["approval_status"]

        if serializer.data:
            creator_email = SubmissionApprovalStatus.objects.filter(id=submission_id).values(
                "submission__job__title",
                "submission__user__email",
                "submission__job__user__first_name",
                #"submission__user__creatorprofile__display_name",
            ).first()
            if creator_email:
                job_title = creator_email.get("submission__job__title")
                email = creator_email.get("submission__user__email")
                brand_name = creator_email.get("submission__job__user__first_name")
                sendgrid = SendGrid()
                if aproval_status:
                    if aproval_status == ApprovalStatus.CREATOR_POST_PENDING:
                        sendgrid.send_email_for_approval_status_approved(email, brand_name, job_title)
                    elif aproval_status == ApprovalStatus.ACCEPTED:
                        sendgrid.send_email_for_approval_status_accepted(email,brand_name, job_title)
                    elif aproval_status == ApprovalStatus.DECLINED:
                        sendgrid.send_email_for_approval_status_declined(email,brand_name,job_title)
                else:
                    raise Exception("Mail is not sent.")
            else:
                raise Exception("Creator profile does not exist or does not have a display name.")
        return Response(
                data={
                    "error": True,
                    "data": [serializer.data],
                    "message": "Submission status update successfully",
                },
                status=status.HTTP_200_OK,
            )


class SubmissionViewCountAPIViewSet(ModelViewSet):
    """
    SubmissionViewCountAPIViewSet is a viewset class that provides CRUD operations for SubmissionViewCount model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = SubmissionViewCount.objects.all()
    serializer_class = SubmissionViewCountSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["platforms"]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    @track_error()
    def create(self, request, *args, **kwargs):

        job = request.data.get("job")
        user = request.data.get("user")
        submission = request.data.get("submission")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(job_id=job, submission_id=submission, user_id=user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class MyJobAPIViewSet(ModelViewSet):

    authentication_classes = (TokenAuthentication,)
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    #search_fields = ["title", "brand__brand_name"]
    pagination_class = None
    http_method_names = ["get", "patch", "put"]

    def get_queryset(self):

        queryset = super(MyJobAPIViewSet, self).get_queryset()
        queryset = self.queryset.filter(
            user_id=self.request.user.id, status=JobStatus.ACTIVE
        )
        page = self.request.query_params.get("page", 1)
        page_size = 6
        if self.request.query_params.get("flag") == JobStatus.CLOSED and page:
            queryset = self.queryset.filter(
                user_id=self.request.user.id, status=JobStatus.CLOSED
            )
            
            paginator = Paginator(queryset, page_size)
            try:
                queryset = paginator.page(page)
            except PageNotAnInteger:
                queryset = paginator.page(page)
            except EmptyPage:
                queryset = []
            return queryset
        elif self.request.query_params.get("search") and page:
            queryset = self.queryset.filter(
                title__icontains=self.request.query_params.get("search"), status=JobStatus.CLOSED, user_id=self.request.user.id
            )
            
            paginator = Paginator(queryset, page_size)
            try:
                queryset = paginator.page(page)
            except PageNotAnInteger:
                queryset = paginator.page(page)
            except EmptyPage:
                queryset = []
            
            return queryset
        return queryset

    @track_error()
    def update(self, request, pk=None):
        job_id = int(pk)
        data = Job.objects.filter(id=job_id, status=JobStatus.ACTIVE).update(
            status=JobStatus.CLOSED
        )
        return Response(
            data={
                "error": False,
                "data": [data],
                "message": "This job has been closed by the brand.",
            },
            status=status.HTTP_200_OK,
        )


class ConnectSocialSnapChatApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the Snapchat. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database. It also calls the SnapchatAPI class to retrieve
    data from the Snapchat API.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        if code is None or len(code) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "code is required.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        auth = SocialAccountOAuth(code)

        response, access_token, refresh_token = auth.snapchat_login_verification()

        if response.status_code != 200:

            return Response(
                data={
                    "error": True,
                    "data": [response.json()],
                    "message": f"{response.json().get('error_description')}",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        r = response.json()
        first_name, last_name = r.get("me").get("display_name").split(" ", 1)
        profile, created = SocialProfile.objects.get_or_create(
            email=r.get("me").get("email")
        )
        profile.first_name = first_name
        profile.last_name = last_name
        profile.platforms = MPlatFormType.SNAPCHAT
        profile.save()

        authkey, created = SocialAuthkey.objects.get_or_create(profile=profile)
        authkey.access_token = access_token
        authkey.refresh_token = refresh_token
        authkey.save()

        return Response(
            data={
                "error": False,
                "data": [],
                "message": "snapchat connection is successfully integrated.",
            },
            status=status.HTTP_200_OK,
        )


class JobSliderValueAPIViewSet(ModelViewSet):
    """
    JobSliderValueAPIViewSet is a viewset class that provides CRUD operations for Job model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["category_name"]
    pagination_class = None
    http_method_names = ["get"]

    @track_error()
    def list(self, request, *args, **kwargs):
        bc_handler = BudgetCalculation(request.data)
        stage = bc_handler.getJobStage()
        slider_value_map = {
            "easy": (100, 200, 300),
            "medium": (200, 500, 700),
            "hard": (300, 800, 2000),
        }
        minimum, balanced, maximum = slider_value_map.get(stage, (0, 0, 0))

        return Response(
            data={
                "error": True,
                "data": {
                    "stage": stage,
                    "slider_value": {
                        "minimum": minimum,
                        "balanced": balanced,
                        "maximum": maximum,
                    },
                },
                "message": "Slider value fetch successfully",
            },
            status=status.HTTP_200_OK,
        )


class CPMAPIViewSet(ModelViewSet):
    """
    JobSliderValueAPIViewSet is a viewset class that provides CRUD operations for Job model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = SocialCPM.objects.all()
    serializer_class = CPMSerializer


class JobMilestonesAPIViewSet(ModelViewSet):
    """
    JobMilestonesAPIViewSet is a viewset class that provides CRUD operations for Job model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = JobMilestones.objects.all()
    serializer_class = JobMilestonesSerializer


class VdoCipherAPIViewSet(APIView):

    permission_classes = (AllowAny,)

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        # Parse the JSON data from the request
        data = json.loads(request.body)
        # Check that this is a Video Cipher webhook
        if data.get("event") == "video:ready":
            # Take any necessary action with the processed video data
            payload = data.get("payload")
            Submission.objects.filter(video_id=payload.get("id")).update(
                video_status=payload.get("status"), vdo_payload=payload
            )

        # Return a response to Video Cipher to confirm receipt of the webhook
        return Response(status=status.HTTP_200_OK)


class VdoCipherOTPAPIViewSet(APIView):

    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):

        # url = "https://dev.vdocipher.com/api/videos/2dc7a9192b934499885cbba368db2ff6/otp"
        url = f"{url_hp.VDOCIPHER_URL}/videos/{request.POST.get('video_id')}/otp"
        headers = {"Authorization": f"Apisecret {settings.VDOCIPHER_API_SECRET_KEY}"}
        data = {
            "annotate": "[{'type':'rtext', 'text':' Everywhere AI', 'alpha':'0.60', 'color':'0xFFFFFF','size':'30', 'interval':'5000'}]"
        }
        r = requests.post(url=url, headers=headers, data=data)

        if r.status_code == 200:
            data = r.json()
            return Response(
                data={
                    "error": False,
                    "data": data,
                    "message": "OTP fetch successfully.",
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            data={
                "error": True,
                "data": [],
                "message": "Some thing went wrong",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class ConnectSocialFacebookApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the Facebook. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database.It also calls the FacebookAPI class to retrieve
    data from the Facebook API.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        # # creator_profile = CreatorProfile.objects.filter(user=self.request.user.id).first()
        # # creator_profile_id = creator_profile.id if creator_profile else None
        code = request.GET.get("code")
        if code is None or len(code) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "code is required.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        auth = SocialAccountOAuth(code)
        (
            response,
            access_token,
            refresh_token,
        ) = auth.marketplace_facebook_login_verification()
        if response.status_code != 200:
            return Response(data=response.json(), status=status.HTTP_406_NOT_ACCEPTABLE)
        profile_response = response.json()

        fb = MFacebookAPI(
            user=self.request.user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            profile=profile_response,
        )
        error, message = fb.get_business_id()

        if error is False:
            CreatorProfile.objects.get_or_create(user_id=self.request.user.id)

        return Response(
            data={
                "error": error,
                "data": [],
                "message": message,
            },
            status=status.HTTP_200_OK,
        )


class DraftAPIViewSet(ModelViewSet):
    """
    Draft is a viewset class that provides CRUD operations for Draft model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Draft.objects.all()
    serializer_class = DraftSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["platforms"]
    pagination_class = None
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        queryset = super(DraftAPIViewSet, self).get_queryset()
        queryset = self.queryset.filter(user_id=self.request.user.id)
        return queryset

    @track_error()
    def create(self, request, *args, **kwargs):

        draft_data = request.data.get("draft_data", {})
        current_page = request.data.get("current_page")
        user = self.request.user
        draft, _ = Draft.objects.update_or_create(
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
                "message": "Draft created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Draft delete successfully.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
        except Exception:
            return Response({"detail": "Cannot delete this object because it is referenced by other objects."}, status=status.HTTP_400_BAD_REQUEST)



class ConnectSocialTiktokApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the TikTok. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database. It also calls the TikTokAPI class to retrieve
    data from the TikTok API.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        if code is None or len(code) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "code is required.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        auth = SocialAccountOAuth(code)
        response, user_response = auth.marketplace_tiktok_login_verification()
        if response.status_code != 200 and user_response.status_code != 200:
            return Response(data=response.json(), status=status.HTTP_406_NOT_ACCEPTABLE)
        r = response.json()
        access_token, refresh_token, creator_id = (
            r.get("data").get("access_token"),
            r.get("data").get("refresh_token"),
            r.get("data").get("creator_id"),
        )

        if creator_id is None:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Creator id is missing.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        ur = user_response.json()

        display_name = ur.get("data").get("display_name")
        first_name, _, last_name = display_name.partition(" ")
        socialdata = SocialProfile.objects.filter(user_id=request.user.id, platforms=MPlatFormType.TIKTOK)
        if not socialdata:
            profile, _ = SocialProfile.objects.update_or_create(
                platforms=MPlatFormType.TIKTOK,
                user_id=request.user.id,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
            SocialAuthkey.objects.update_or_create(
                profile=profile,
                defaults={"access_token": access_token, "refresh_token": refresh_token},
            )

            SocialBusiness.objects.update_or_create(
                profile=profile,
                defaults={"business_center_id": creator_id},
            )

            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Tiktok connection is successfully integrated.",
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Tiktok connection is already integrated.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class PresignedURLApiView(APIView):

    permission_classes = (AllowAny,)

    @track_error(validate_api_parameters=["type", "file_name"])
    def post(self, request, *arg, **kwargs):
        type = request.data.get("type")
        file_name = request.data.get("file_name")
        uploadsesid = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=10)
        )
        object_key = f"{type}/{uploadsesid}_{file_name}"
        s3 = S3BucketHelper()
        response = s3.write_presigned_url(object_key)

        return Response(
            data={
                "error": False,
                "data": {
                    "writeURL": response,
                    "objectKey": object_key,
                },
                "message": "Presigned Url fetch successfully",
            },
            status=status.HTTP_200_OK,
        )


class PayoutAPIViewSet(ModelViewSet):
    """
    Payout is a viewset class that provides CRUD operations for Payout model.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["payout_status"]
    pagination_class = None
    http_method_names = ["get", "post"]

    def get_queryset(self):
        queryset = super(PayoutAPIViewSet, self).get_queryset()
        queryset = self.queryset.filter(user_id=self.request.user.id)
        return queryset

    @track_error()
    def create(self, request, *args, **kwargs):

        user_id = self.request.user.id
        data = Payout.objects.filter(
            user_id=user_id,
            payout_status=PayoutStatus.READY_FOR_PAYOUT,
        ).update(payout_status=PayoutStatus.PAID_OUT)

        if data:
            return generate_pdf(user_id)

        return Response(
            data={
                "error": True,
                "data": [],
                "message": "Balance already withdraw.",
            },
            status=status.HTTP_200_OK,
        )


class PayoutBalanceAPIViewSet(ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = None
    pagination_class = None
    http_method_names = ["get"]

    @track_error()
    def list(self, request, *arg, **kwargs):
        total_earnings = (
            Payout.objects.filter(
                user_id=self.request.user.id,
                payout_status=PayoutStatus.PAID_OUT,
            ).aggregate(amount=Sum("amount"))["amount"]
            or 0
        )

        current_balance = (
            Payout.objects.filter(
                user_id=self.request.user.id,
                payout_status=PayoutStatus.READY_FOR_PAYOUT,
            ).aggregate(amount=Sum("amount"))["amount"]
            or 0
        )

        return Response(
            data={
                "error": False,
                "data": {
                    "total_earnings": total_earnings,
                    "current_balance": current_balance,
                },
                "message": "Balance details fetch successfully.",
            },
            status=status.HTTP_200_OK,
        )

class DisconnectPlatformsApiView(generics.CreateAPIView):

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *arg, **kwargs):

        submission_instagram = Submission.objects.filter(user_id=self.request.user.id, job__platforms=MPlatFormType.INSTAGRAM).count()
        submission_tiktok = Submission.objects.filter(user_id=self.request.user.id, job__platforms=MPlatFormType.TIKTOK).count()
        if not submission_instagram:
            SocialProfile.objects.filter(user_id=self.request.user.id, platforms=MPlatFormType.INSTAGRAM).delete()
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "facebook disconnect successfully",
                },
                status=status.HTTP_200_OK,
            )
        elif not submission_tiktok:
            SocialProfile.objects.filter(user_id=self.request.user.id, platforms=MPlatFormType.TIKTOK).delete()
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "tiktok disconnect successfully",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                "error": True,
                "data": [],
                "message": "Submission have already attached",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

class GenerateInvoiceAPIViewSet(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, id):

        user_id = request.GET.get("user_id")
        return generate_pdf(user_id, payout_id=id)

class DownloadSubmissionVideoApiView(APIView):

    authentication_classes = (TokenAuthentication,)

    def get(self, request, video_id=None, *args, **kwargs):
        # Check All Video Download #
        redirect_urls = []
        if video_id:
            url = f"{url_hp.VDOCIPHER_URL}/videos/{video_id}/files"
            headers = {"Authorization": f"Apisecret {settings.VDOCIPHER_API_SECRET_KEY}"}
            response = requests.get(url=url, headers=headers)
            response_data = response.json()

            for data in response_data:
                encryption_type=data.get('encryption_type')
                if encryption_type ==  Marketplace.encryption_type:
                    file_id = data.get('id')
                    file_url = f"{url_hp.VDOCIPHER_URL}/videos/{video_id}/files/{file_id}"
                    file_response = requests.get(url=file_url, headers=headers)
                    redirect_url = file_response.json()
                    redirect_urls.append(redirect_url["redirect"])
            response = requests.get(redirect_urls[0])

            # Check if the request was successful
            if response.status_code != 200:
                # Raise an exception if the request was not successful
                raise Exception("Failed to download video: HTTP status code {}".format(response.status_code))

            # Get file name from response headers
            filename = None
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                _, params = cgi.parse_header(content_disposition)
                filename = params.get('filename')

            # Open a new file in binary mode and write the contents of the response to it
            # Create a response object with the video content
            response = HttpResponse(response.content, content_type=response.headers['Content-Type'])
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        else:
            submissions = Submission.objects.filter(
                job__user_id=self.request.user.id,
                approval_status__approval_status=ApprovalStatus.ACCEPTED
            ).values("video_id")
            for submission in submissions:
                video_id = submission.get("video_id")
                url = f"{url_hp.VDOCIPHER_URL}/videos/{video_id}/files"
                headers = {"Authorization": f"Apisecret {settings.VDOCIPHER_API_SECRET_KEY}"}
                response = requests.get(url=url, headers=headers)
                if response.status_code == 200:
                    response_data = response.json()
                    for data in response_data:
                        encryption_type=data.get('encryption_type')
                        if encryption_type ==  Marketplace.encryption_type:
                            file_id = data.get('id')
                            file_url = f"{url_hp.VDOCIPHER_URL}/videos/{video_id}/files/{file_id}"
                            file_response = requests.get(url=file_url, headers=headers)
                            redirect_url = file_response.json()
                            redirect_urls.append(redirect_url.get("redirect"))
            if redirect_urls:
                zip_file = BytesIO()
                with zipfile.ZipFile(zip_file, 'w') as zip:
                    for video_url in redirect_urls:

                        response = requests.get(video_url)
                        video_content = response.content

                        # Get file name from response headers
                        filename = None
                        content_disposition = response.headers.get('content-disposition')
                        if content_disposition:
                            _, params = cgi.parse_header(content_disposition)
                            filename = params.get('filename')
                        # Create zip file containing video
                        zip.writestr(filename, video_content)

                # Return zip file as HTTP response
                response = HttpResponse(zip_file.getvalue(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="Videos.zip"'
            else:
                response = Response(
                    {"error":True, "message":"You haven't any submission yet."}, status=status.HTTP_404_NOT_FOUND)
        return response