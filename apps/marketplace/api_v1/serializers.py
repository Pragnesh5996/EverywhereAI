import json
from apps.marketplace.models import (
    Job,
    JobCategory,
    Submission,
    SubmissionApprovalStatus,
    SubmissionViewCount,
    CreatorProfile,
    BrandProfile,
    SocialCPM,
    JobMilestones,
    Draft,
    SocialAuthkey,
    SocialProfile,
    Payout,
    Earning,
    MilestoneStatus,
    SpentBalance,
    JobPayment,
)
from apps.common.constants import (
    ApprovalStatus,
)
from rest_framework import serializers
from django.db.models import Sum, F, Min, Q
from apps.common.constants import Marketplace, MilestoneProgess
from random import randint
from apps.common.s3_helper import S3BucketHelper
from django.conf import settings
import requests
from apps.common.urls_helper import URLHelper
url_hp = URLHelper()

class CreatorProfileSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for CreatorProfile.
    It allows for the serialization of all fields of the CreatorProfile model.
    """

    percentage = serializers.SerializerMethodField()
    integrated_platforms = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    platform_username = serializers.SerializerMethodField()

    def get_integrated_platforms(self, creator):

        integrated_platforms = {platform: False for platform in Marketplace.platforms}
        profile = SocialProfile.objects.filter(user_id=creator.user.id).values()
        if profile:
            for profiles in profile:
                data = SocialAuthkey.objects.filter(
                    profile_id=profiles.get("id"),
                    profile__platforms__in=Marketplace.platforms,
                ).values("profile__platforms", "access_token")
                for row in data:
                    if "profile__platforms" in row and "access_token" in row:
                        platform = row["profile__platforms"]
                        access_token = row["access_token"]
                        if access_token:
                            integrated_platforms[platform] = True
        return integrated_platforms

    def get_percentage(self, creator_profile):
        """
        This function is calculate percentage of creatorprofile
        """
        total = 0
        if creator_profile:
            profile = SocialProfile.objects.filter(
                user_id=creator_profile.user.id
            ).values()
            if profile:
                data = SocialAuthkey.objects.filter(
                    profile_id=profile[0].get("id"),
                    profile__platforms__in=Marketplace.platforms,
                ).values("profile__platforms", "access_token")
                for row in data:
                    if "profile__platforms" in row and "access_token" in row:
                        access_token = row["access_token"]
                        if access_token:
                            total += Marketplace.creator_percentage.get("platform", 0)
            if CreatorProfile.objects.filter(id=creator_profile.id).exclude(
                display_name__isnull=True
            ):
                total += Marketplace.creator_percentage.get("display_name", 0)
            if CreatorProfile.objects.filter(id=creator_profile.id).exclude(
                profile_picture__isnull=True
            ):
                total += Marketplace.creator_percentage.get("profile_picture", 0)
        return total

    def get_profile_picture_url(self, creator_profile):
        """get thumbnail presign read signed URL"""
        try:
            thumbnail = (
                creator_profile.profile_picture
                if creator_profile.profile_picture
                else None
            )
            if thumbnail:
                # Use the thumbnail object key to generate a presigned URL.
                s3 = S3BucketHelper()
                response = s3.read_presigned_url(thumbnail)
                return response
            else:
                return None
        except Exception:
            # Handle any exceptions that occur.
            return None

    def get_platform_username(self, creator):

        username = Marketplace.social_platform
        profiles = SocialProfile.objects.filter(user_id=creator.user.id).values()
        for profile in profiles:
            platform = profile["platforms"]
            if platform in  username:
                username[platform] = profile.get("username")

        return username

    class Meta:
        model = CreatorProfile
        fields = "__all__"
        depth = 1


class BrandProfileSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for BrandProfile.
    It allows for the serialization of all fields of the BrandProfile model.
    """

    percentage = serializers.SerializerMethodField()
    brand_logo_url = serializers.SerializerMethodField()

    def get_percentage(self, brand_profile):
        """
        This function is calculate percentage of brandprofile
        """
        total = 0
        if BrandProfile.objects.filter(id=brand_profile.id).exclude(
            brand_name__isnull=True
        ):
            total += Marketplace.brand_percentage.get("brand_name", 0)
        if BrandProfile.objects.filter(id=brand_profile.id).exclude(
            brand_description__isnull=True
        ):
            total += Marketplace.brand_percentage.get("brand_description", 0)
        if BrandProfile.objects.filter(id=brand_profile.id).exclude(
            brand_logo__isnull=True
        ):
            total += Marketplace.brand_percentage.get("brand_logo", 0)
        return total

    def get_brand_logo_url(self, brand_profile):
        """get thumbnail presign read signed URL"""
        try:
            thumbnail = brand_profile.brand_logo if brand_profile.brand_logo else None
            if thumbnail:
                # Use the thumbnail object key to generate a presigned URL.
                s3 = S3BucketHelper()
                response = s3.read_presigned_url(thumbnail)
                return response
            else:
                return None
        except Exception:
            # Handle any exceptions that occur.
            return None

    class Meta:
        model = BrandProfile
        fields = "__all__"
        depth = 1


class JobCategorySerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for JobCategory.
    It allows for the serialization of all fields of the JobCategory model.
    """

    class Meta:
        model = JobCategory
        fields = "__all__"


class JobMilestonesSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for JobMilestones.
    It allows for the serialization of all fields of the JobMilestones model.
    """

    class Meta:
        model = JobMilestones
        fields = ["milestone"]


class SubmissionApprovalStatusSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for ContentApprovalStatus.
    It allows for the serialization of all fields of the ContentApprovalStatus model.
    """

    class Meta:
        model = SubmissionApprovalStatus
        fields = "__all__"
        depth = 1


class JobThumbnailSerializer(serializers.ModelSerializer):

    thumbnails_url = serializers.SerializerMethodField()

    def get_thumbnails_url(self, job, *args, **kwargs):
        """get thumbnail presign read signed URL"""
        try:
            thumbnail = job.thumbnails if job.thumbnails else None
            if thumbnail:
                # Use the thumbnail object key to generate a presigned URL.
                s3 = S3BucketHelper()
                response = s3.read_presigned_url(thumbnail)
                return response
            else:
                return None
        except Exception:
            # Handle any exceptions that occur.
            return None

    class Meta:
        model = Job
        fields = "__all__"


class SubmissionSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for ContentDetails.
    It allows for the serialization of all fields of the ContentDetails model.
    """

    approval_status = SubmissionApprovalStatusSerializer(many=True, read_only=True)
    job_details = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    budget_value = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    milestone = serializers.SerializerMethodField()
    next_milestone_view = serializers.SerializerMethodField()
    total_submission = serializers.SerializerMethodField()
    submission_video_url = serializers.SerializerMethodField()

    def get_budget_value(self, submission, *args, **kwargs):
        """
        This function is count spent budget in particular job
        """
        percentage = randint(1, 100)
        job = Job.objects.get(id=submission.job.id)
        spent = (job.budget * percentage) / 100
        budget = {"total": job.budget, "spent": spent, "percentage": percentage}
        return budget

    def get_view_count(self, submission, *args, **kwargs):
        """
        This function is calculate sum of total view in particular job
        """
        return (
            SubmissionViewCount.objects.filter(job_id=submission.job.id).aggregate(
                total_view_count=Sum("view_count")
            )["total_view_count"]
            or 0
        )

    def get_milestone(self, submission, *args, **kwargs):
        """
        This function is filter milestone data
        """
        total = MilestoneStatus.objects.filter(
            milestone__job__id=submission.job.id, user__id=submission.user.id
        ).count()
        completed = MilestoneStatus.objects.filter(
            milestone__job__id=submission.job.id,
            user__id=submission.user.id,
            status=MilestoneProgess.COMPLETED,
        ).count()
        return {"total": total, "completed": completed}

    def get_brand(self, submission, *args, **kwargs):
        """
        This function for brand data
        """
        try:
            data = BrandProfile.objects.get(user_id=submission.job.user.id)
            return BrandProfileSerializer(data).data
        except Exception:
            return {}

    def get_creator(self, submission, *args, **kwargs):
        """
        This function for creator data
        """
        try:
            data = CreatorProfile.objects.get(user_id=submission.user.id)
            return CreatorProfileSerializer(data).data
        except Exception:
            return {}

    def get_job_details(self, submission, *args, **kwargs):
        """
        This function for job details
        """
        try:
            data = Job.objects.get(id=submission.job.id)
            return JobThumbnailSerializer(data).data
        except Exception:
            return {}

    def get_next_milestone_view(self, submission, *args, **kwargs):
        """
        This function is to get view count of upcoming milestone
        """
        milestone_status = (
            MilestoneStatus.objects.filter(
                submission_id=submission.id,
                user_id=submission.user.id,
                status=MilestoneProgess.IN_PROGRESS,
            )
            .annotate(min_milestone_number=Min("milestone__milestone_number"))
            .filter(Q(milestone__milestone_number=F("min_milestone_number")))
            .select_related("milestone")
            .first()
        )

        return milestone_status.milestone.view_count if milestone_status else 0

    def get_total_submission(self, submission, *args, **kwargs):
        """
        This function is calculate total submission
        """
        all = Submission.objects.filter(
            user_id=submission.user.id
        ).count()
        earning = Submission.objects.filter(
            user_id=submission.user.id,
            approval_status__approval_status=ApprovalStatus.ACCEPTED
        ).count()
        action_required = Submission.objects.filter(
            user_id=submission.user.id,
            approval_status__approval_status=ApprovalStatus.CREATOR_POST_PENDING
        ).count()
        pending = Submission.objects.filter(
            user_id=submission.user.id,
            approval_status__approval_status__in=[ApprovalStatus.APPROVAL_NEEDED,ApprovalStatus.POST_CONFIRMATION_PENDING]
        ).count()
        declined = Submission.objects.filter(
            user_id=submission.user.id,
            approval_status__approval_status=ApprovalStatus.DECLINED
        ).count()

        return {
            "total": all,
            "earning": earning,
            "action_required": action_required,
            "pending" : pending,
            "declined" : declined
        }

    def get_submission_video_url(self, submission, *args, **kwargs):
        try:
            submission = Submission.objects.filter(
                id=submission.id,
                user_id=submission.user.id,
                approval_status__approval_status=ApprovalStatus.ACCEPTED
            ).values("video_id").first()
            video_id = submission.get("video_id")

            url = f"{url_hp.VDOCIPHER_URL}/videos/{video_id}/files"
            headers = {"Authorization": f"Apisecret {settings.VDOCIPHER_API_SECRET_KEY}"}
            response = requests.get(url=url, headers=headers)
            response_data = response.json()

            for data in response_data:
                encryption_type=data.get('encryption_type')
                if encryption_type == Marketplace.encryption_type:
                    file_id = data.get('id')
                    file_url = f"{url_hp.VDOCIPHER_URL}/videos/{video_id}/files/{file_id}"
                    file_response = requests.get(url=file_url, headers=headers)
                    redirect_url = file_response.json()
                    return redirect_url
        except Exception:
            return {}
    class Meta:
        model = Submission
        exclude = ("job",)
        depth = 1


class JobSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Job.
    It allows for the serialization of all fields of the Job model.
    """

    budget_value = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    submission = serializers.SerializerMethodField()
    milestone = serializers.SerializerMethodField()
    thumbnails_url = serializers.SerializerMethodField()
    brand_details = serializers.SerializerMethodField()

    def get_budget_value(self, job, *args, **kwargs):
        """
        This function is count spent budget in particular job
        """
        spent = (
            SpentBalance.objects.filter(job_id=job.id, user_id=job.user.id)
            .values("amount")
            .first()
        )
        spent_amount = spent.get("amount") if spent is not None else 0
        percentage = (spent_amount * 100) / job.budget if job.budget > 0 else 0
        budget = {
            "total": job.budget,
            "spent": spent_amount,
            "percentage": percentage,
        }
        return budget

    def get_submission_count(self, job, *args, **kwargs):
        """
        This function is count total submission in particular job
        """
        return Submission.objects.filter(
            user_id=self.context.get("request").user.id, job_id=job.id
        ).count()

    def get_view_count(self, job, *args, **kwargs):
        """
        This function is calculate sum of total view in particular job
        """
        return (
            SubmissionViewCount.objects.filter(job_id=job.id).aggregate(
                total_view_count=Sum("view_count")
            )["total_view_count"]
            or 0
        )

    def get_submission(self, job, *args, **kwargs):
        """
        This function is to get the submission of perticular user
        """
        try:
            data = Submission.objects.get(
                user_id=self.context.get("request").user.id, job_id=job.id
            )
            return SubmissionSerializer(data).data
        except Exception:
            return {}

    def get_milestone(self, job, *args, **kwargs):
        """
        This function is filter milestone data
        """
        return JobMilestones.objects.filter(job_id=job.id).values("price", "view_count")

    def get_thumbnails_url(self, job, *args, **kwargs):
        """get thumbnail presign read signed URL"""
        try:
            thumbnail = job.thumbnails if job.thumbnails else None
            if thumbnail:
                # Use the thumbnail object key to generate a presigned URL.
                s3 = S3BucketHelper()
                response = s3.read_presigned_url(thumbnail)
                return response
            else:
                return None
        except Exception:
            # Handle any exceptions that occur.
            return None

    def get_brand_details(self, job, *args, **kwargs):
        """
        This function for brand data
        """
        try:
            data = BrandProfile.objects.get(id=job.brand.id)
            return BrandProfileSerializer(data).data
        except Exception:
            return {}

    class Meta:
        model = Job
        exclude = ("brand",)
        depth = 1


class SubmissionViewCountSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for ContentViewCount.
    It allows for the serialization of all fields of the ContentViewCount model.
    """

    class Meta:
        model = SubmissionViewCount
        fields = "__all__"
        depth = 1


class CPMSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for CPM.
    It allows for the serialization of all fields of the CPM model.
    """

    class Meta:
        model = SocialCPM
        fields = "__all__"


class DraftSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Draft.
    It allows for the serialization of all fields of the Draft model.
    """

    thumbnail_url = serializers.SerializerMethodField()

    def get_thumbnail_url(self, draft, *args, **kwargs):
        """get thumbnail presign read signed URL"""
        try:
            # Parse the JSON string into a dictionary
            data = draft.draft_data
            if "jobDetails" in data and "thumbnail" in data["jobDetails"]:

                thumbnail = data["jobDetails"]["thumbnail"]
                # Use the thumbnail object key to generate a presigned URL.
                s3 = S3BucketHelper()
                response = s3.read_presigned_url(thumbnail)
                return response
            else:
                # Handle the case where the thumbnail key is not present.
                return {}
        except Exception:
            # Handle any exceptions that occur.
            return {}

    class Meta:
        model = Draft
        fields = "__all__"


class EarningSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for earned amount after reached to the milestone.
    It allows for the serialization of all fields of the Earning model.
    """

    class Meta:
        model = Earning
        fields = "__all__"
        depth = 2


class PayoutSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Payout.
    It allows for the serialization of all fields of the Payout model.
    """

    earning_payout = EarningSerializer(many=True, read_only=True)

    class Meta:
        model = Payout
        fields = "__all__"

class JobPaymentSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for JobPayment.
    It allows for the serialization of all fields of the JobPayment model.
    """

    class Meta:
        model = JobPayment
        fields = "__all__"