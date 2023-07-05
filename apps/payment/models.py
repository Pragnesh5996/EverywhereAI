from django.db import models
from apps.common.models import TimeStampModel


# Create your models here.
class Plan(TimeStampModel):
    stripe_plan_id = models.CharField(max_length=100, primary_key=True)
    plan_name = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    interval = models.CharField(max_length=20, null=True, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)


class Subscription(TimeStampModel):
    company = models.ForeignKey(
        "main.Company", on_delete=models.CASCADE, null=True, blank=True
    )
    plan_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    status = models.CharField(
        max_length=20
    )  # incomplete, incomplete_expired, trialing, active, past_due, canceled, or unpaid
    ad_spend_limit = models.IntegerField(null=True, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, null=True, blank=True)
    ad_spend_percentage = models.CharField(max_length=100, null=True, blank=True)
    email_status = models.BooleanField(default=False)


class Payment(TimeStampModel):
    company = models.ForeignKey(
        "main.Company", on_delete=models.CASCADE, null=True, blank=True
    )
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_status = models.CharField(max_length=20, null=True, blank=True)
    session_id = models.CharField(max_length=180, null=True, blank=True)
