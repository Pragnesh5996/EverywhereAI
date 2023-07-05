from django.urls import re_path
from apps.payment.webhook import stripe_webhook_views

app_name = "payment"

urlpatterns = [
    re_path(r"stripe-webhook/", stripe_webhook_views.StripeWebhookAPIView.as_view()),
]
