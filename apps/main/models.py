from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.contrib.auth.models import AbstractUser
from apps.common.constants import SocialAccountType, GenderType
from apps.common.models import TimeStampModel
import datetime

# here is a Tenant model
class Company(TenantMixin, TimeStampModel):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    uid = models.UUIDField(primary_key=True, editable=True)
    timezone = models.CharField(max_length=500, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    is_free_trial = models.BooleanField(default=True)
    expire_free_trial = models.DateTimeField(null=True, blank=True)


class Domain(DomainMixin):
    pass


class User(AbstractUser):
    username = None
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=17, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="user_company",
    )
    social_account = models.PositiveSmallIntegerField(
        choices=SocialAccountType.CHOICES, default=SocialAccountType.NORMAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    profile_pic = models.CharField(max_length=500, blank=True, null=True)
    country = models.CharField(max_length=150, blank=True, null=True)
    gender = models.PositiveSmallIntegerField(
        choices=GenderType.CHOICES, blank=True, null=True
    )
    is_verified_user = models.BooleanField(default=False)
    reason_to_use_everywhereai = models.TextField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @classmethod
    def get_roles(self, user):
        return list(user.groups.values_list("name", flat=True))

    @classmethod
    def get_permissions(self, user):
        return [
            permission.codename
            for role in user.groups.all()
            for permission in role.permissions.all()
        ]

    @classmethod
    def assign_permissions_to_role(self, role, permissions):
        role.permissions.set(list(permissions))

    @classmethod
    def assign_role_to_user(self, user, role):
        user.groups.set([role])


class SocialAccountToken(TimeStampModel):
    user = models.ForeignKey(
        "main.User", on_delete=models.CASCADE, related_name="socialaccounttoken_user"
    )
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)


class ForgotPasswordToken(TimeStampModel):
    user = models.ForeignKey(
        "User", related_name="reset_tokens", on_delete=models.CASCADE
    )
    token = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        get_latest_by = ("created_at",)

    def __str__(self):
        return f"{self.user} - {self.token}"

    @classmethod
    def has_latest_token(cls, user):
        last_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
        return cls.objects.filter(
            is_active=True, user=user, created_at__lte=last_time
        ).exists()


class RegistrationOtp(TimeStampModel):
    email = models.CharField(max_length=150, blank=True, null=True)
    otp = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        get_latest_by = ("created_at",)


class Webhook(models.Model):
    json_data = models.JSONField(blank=True, null=True)
    text_data = models.TextField(blank=True, null=True)
