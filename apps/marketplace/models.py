from django.db import models
from apps.common.constants import (
    PublishedContentType,
    ApprovalStatus,
    MPlatFormType,
    DimensionType,
    JobStatus,
    MilestoneProgess,
    PayoutStatus,
    JobPaymentStatus,
    JobPaymentType,
)
from apps.common.models import TimeStampModel
from django.db.models import JSONField

# Create your models here.
class CreatorProfile(TimeStampModel):
    user = models.OneToOneField(
        "main.User", on_delete=models.CASCADE, blank=True, null=True
    )
    display_name = models.CharField(max_length=60, blank=True, null=True)
    profile_picture = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "creator_profile"


class BrandProfile(TimeStampModel):
    user = models.OneToOneField(
        "main.User", on_delete=models.CASCADE, blank=True, null=True
    )
    brand_logo = models.TextField(blank=True, null=True)
    brand_name = models.CharField(max_length=60, blank=True, null=True)
    brand_description = models.CharField(max_length=250, blank=True, null=True)
    website_url = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "brand_profile"


class JobCategory(TimeStampModel):
    category_name = models.CharField(max_length=60, blank=True, null=True, unique=True)

    class Meta:
        managed = True
        db_table = "job_category"


class Job(TimeStampModel):
    user = models.ForeignKey(
        "main.User",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="user_details",
    )
    brand = models.ForeignKey(
        BrandProfile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="brand_details",
    )
    category = models.ForeignKey(
        JobCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="category_details",
    )
    publish_content_type = models.CharField(
        max_length=45, choices=PublishedContentType.CHOICES, blank=True, null=True
    )
    dimension = models.CharField(
        max_length=100, choices=DimensionType.CHOICES, blank=True, null=True
    )
    platforms = models.CharField(
        max_length=100, choices=MPlatFormType.CHOICES, blank=True, null=True
    )
    title = models.CharField(max_length=45, blank=True, null=True)
    job_description = models.CharField(max_length=400, blank=True, null=True)
    thumbnails = models.TextField(blank=True, null=True)
    thumbnails_name = models.TextField(blank=True, null=True)
    thumbnails_type = models.TextField(blank=True, null=True)
    budget = models.IntegerField(blank=True, null=True, default=0)
    selected_budget = models.IntegerField(blank=True, null=True, default=0)
    job_requirements = JSONField(null=False, default=dict)
    status = models.CharField(
        max_length=45,
        choices=JobStatus.CHOICES,
        blank=True,
        null=True,
        default=JobStatus.ACTIVE,
    )

    class Meta:
        managed = True
        db_table = "job"


class Submission(TimeStampModel):
    user = models.ForeignKey(
        "main.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="submission_detail",
    )
    video_id = models.TextField(blank=True, null=True)
    vdo_payload = JSONField(null=False, default=dict)
    video_status = models.TextField(blank=True, null=True)
    social_post_link = models.TextField(blank=True, null=True)
    submission_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "submission"


class SubmissionApprovalStatus(TimeStampModel):
    submission = models.ForeignKey(
        Submission,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approval_status",
    )
    approval_status = models.CharField(
        max_length=45,
        choices=ApprovalStatus.CHOICES,
        blank=True,
        null=True,
        default=ApprovalStatus.APPROVAL_NEEDED,
    )
    feedback = models.TextField(blank=True, null=True, default="")

    class Meta:
        managed = True
        db_table = "submission_approval_status"


class SubmissionViewCount(TimeStampModel):
    user = models.ForeignKey(
        "main.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="job",
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    media_id = models.CharField(max_length=45, blank=True, null=True)
    view_count = models.IntegerField(blank=True, null=True)
    platforms = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        unique_together = [["job", "platforms"]]
        db_table = "submission_view_count"


class SocialProfile(TimeStampModel):
    first_name = models.CharField(max_length=45, blank=True, null=True)
    last_name = models.CharField(max_length=45, blank=True, null=True)
    username = models.CharField(max_length=45, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    platforms = models.CharField(max_length=45, choices=MPlatFormType.CHOICES)
    user = models.ForeignKey(
        "main.User",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        managed = True
        db_table = "social_profile"


class SocialAuthkey(TimeStampModel):
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    profile = models.ForeignKey(
        SocialProfile, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        managed = True
        db_table = "social_auth_key"


class SocialCPM(TimeStampModel):
    platform_type = models.TextField(blank=True, null=True)
    minimum = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    balanced = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    maximum = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    class Meta:
        managed = True
        db_table = "social_cpm"


class JobMilestones(TimeStampModel):
    job = models.ForeignKey(
        Job, on_delete=models.SET_NULL, blank=True, null=True, related_name="milestone"
    )
    price = models.IntegerField(blank=True, null=True)
    view_count = models.IntegerField(blank=True, null=True)
    milestone_number = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "job_milestones"


class MilestoneStatus(TimeStampModel):
    milestone = models.ForeignKey(
        JobMilestones,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="milestonestatus_milestone",
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="milestonestatus_submission",
    )
    user = models.ForeignKey(
        "main.User",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="jobmilestone_user",
    )
    status = models.CharField(
        max_length=45,
        choices=MilestoneProgess.CHOICES,
        blank=True,
        null=True,
        default=MilestoneProgess.IN_PROGRESS,
    )

    class Meta:
        managed = True
        db_table = "milestone_status"


class SocialBusiness(TimeStampModel):
    fb_page_id = models.CharField(max_length=45, blank=True, null=True)
    business_id = models.CharField(max_length=45, blank=True, null=True)
    organization_id = models.CharField(max_length=45, blank=True, null=True)
    business_center_id = models.CharField(max_length=45, blank=True, null=True)
    name = models.CharField(max_length=45, blank=True, null=True)
    profile = models.ForeignKey(
        SocialProfile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="social_profile",
    )

    class Meta:
        managed = True
        db_table = "social_business"


class Draft(TimeStampModel):
    user = models.OneToOneField(
        "main.User", on_delete=models.CASCADE, blank=True, null=True
    )
    draft_data = JSONField(null=False, default=dict)
    current_page = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "draft"


class Earning(TimeStampModel):
    user = models.ForeignKey(
        "main.User", on_delete=models.CASCADE, blank=True, null=True
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="job_details",
    )
    milestone = models.ForeignKey(
        JobMilestones,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="milestone_details",
    )
    amount = models.IntegerField(blank=True, null=True)
    payout = models.ForeignKey(
        "marketplace.Payout",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="earning_payout",
    )
    earning_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "earning"


class Payout(TimeStampModel):
    user = models.ForeignKey(
        "main.User",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="payout_user",
    )
    amount = models.IntegerField(blank=True, null=True)
    payout_method = models.CharField(
        max_length=45, blank=True, null=True
    )  # such as bank transfer, paypal etc
    payout_status = models.CharField(
        max_length=45,
        blank=True,
        null=True,
        choices=PayoutStatus.CHOICES,
        default=PayoutStatus.READY_FOR_PAYOUT,
    )  # pending, completed, failed
    pdf_url = models.TextField(blank=True, null=True)
    payout_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "payout"


class SpentBalance(TimeStampModel):
    user = models.ForeignKey(
        "main.User",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spentbalance_user",
    )
    brand = models.ForeignKey(
        BrandProfile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="spentbalance_brand",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="spentbalance_job",
    )
    amount = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "spent_balance"

class JobPayment(TimeStampModel):
    brand = models.ForeignKey(
        BrandProfile,
        on_delete=models.CASCADE,
        related_name="jobpayment_brand",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payment_job",
    )
    amount = models.IntegerField()
    payment_type = models.CharField(
        max_length=45,
        choices=JobPaymentType.CHOICES,
    )
    paymentid = models.CharField(max_length=100)
    status = models.CharField(
        max_length=45,
        choices=JobPaymentStatus.CHOICES,
        default=JobPaymentStatus.COMPLETED,
    )