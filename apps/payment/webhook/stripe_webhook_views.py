from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from SF import settings
import stripe
from apps.payment.models import Subscription, Plan, Payment
from apps.payment.helper.stripe_helper import StripeHelper
from apps.common.constants import Webhook_Event_Type
from apps.main.models import Company


class StripeWebhookAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
        event = None
        payload = request.body
        sig_header = request.headers.get("stripe-signature")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError as e:
            # Invalid payload
            raise e
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise e

        # Handle the event
        if event["type"] == Webhook_Event_Type.Subscription_Created:
            subscription = event.get("data").get("object")
            webhook_stripe = StripeHelper()
            webhook_stripe.webhook_subscription(subscription=subscription)
        elif event["type"] == Webhook_Event_Type.Subscription_Deleted:
            subscription = event.get("data").get("object")
            Subscription.objects.filter(
                stripe_subscription_id=subscription.get("id")
            ).update(status=subscription.get("status"))
        elif event["type"] == Webhook_Event_Type.Subscription_Paused:
            subscription = event.get("data").get("object")
        elif event["type"] == Webhook_Event_Type.Subscription_Updated:
            subscription = event.get("data").get("object")
            webhook_stripe = StripeHelper()
            webhook_stripe.webhook_subscription(subscription=subscription)
        elif event["type"] == Webhook_Event_Type.Plan_Created:
            plan = event.get("data").get("object")
            Plan.objects.create(
                stripe_plan_id=plan.get("id"),
                plan_name=plan.get("nickname"),
                status=plan.get("active"),
                interval=plan.get("interval"),
                amount=plan.get("amount") / 100,
            )
        elif event["type"] == Webhook_Event_Type.Plan_Deleted:
            plan = event.get("data").get("object")
            Plan.objects.get(stripe_plan_id=plan.get("id")).delete()
        elif event["type"] == Webhook_Event_Type.Successfully_paid:
            payment_data = event.get("data").get("object")
            customer = Company.objects.get(stripe_customer_id=payment_data.customer)
            Payment.objects.create(
                company=customer,
                stripe_customer_id=payment_data.customer,
                payment_status=payment_data.status,
                amount=payment_data.total,
            )
        else:
            print("Unhandled event type {}".format(event["type"]))

        return Response(
            data={
                "error": False,
                "data": [],
                "message": "",
            },
            status=status.HTTP_200_OK,
        )
