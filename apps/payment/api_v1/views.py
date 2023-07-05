from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.payment.models import Subscription, Payment
from rest_framework.permissions import AllowAny
from apps.payment.helper.stripe_helper import StripeHelper
from apps.common.constants import StripeSubscriptionStatus
from apps.main.models import Company
import datetime
from apps.common.sendgrid import SendGrid
from SF import settings
from django.core.cache import cache

class SubscribeAPIView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        stripe = StripeHelper()

        try:
            plan_id = request.data.get("plan_id")
            uid = request.headers.get("uid")
            customer = Company.objects.filter(uid=uid).first()
            stripe.create_subscription(
                customer_id=customer.stripe_customer_id, plan_id=plan_id
            )
            plan_price = stripe.retrieve_plan_price(plan_id=plan_id)
            stripe.create_charge(customer=customer, amount=plan_price)
        except Exception as e:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": e.user_message,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Payment has been successfully paid.",
            },
            status=status.HTTP_200_OK,
        )


class CheckSubscriptionAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.user.company.uid
        customer = Company.objects.get(uid=uid)
        if customer.is_free_trial:
            subscription = False
        else:
            subscription = Subscription.objects.filter(
                customer__company_uid=uid
            ).latest("-created_at")
        return Response(
            data={
                "error": False,
                "data": {
                    "subscription": subscription.status
                    == StripeSubscriptionStatus.ACTIVE
                    if subscription
                    else StripeSubscriptionStatus.FREE_TRIAL
                },
                "message": None,
            },
            status=status.HTTP_200_OK,
        )


class PlanListAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        stripe = StripeHelper()
        plans = stripe.retrieve_plan_list()
        return Response(
            data={
                "error": False,
                "data": plans,
                "message": None,
            },
            status=status.HTTP_200_OK,
        )


class CheckCardAPIView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        try:
            uid = request.headers.get("uid")
            card_number = request.data.get("number")
            exp_month = request.data.get("exp_month")
            exp_year = request.data.get("exp_year")
            cvc = request.data.get("cvc")

            stripe = StripeHelper()
            token = stripe.create_token(
                card_number=card_number, exp_month=exp_month, exp_year=exp_year, cvc=cvc
            )
            company = Company.objects.filter(company_uid=uid).first()
            stripe.asign_token_to_customer(company=company, token=token)

            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": None,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": e.user_message,
                },
                status=status.HTTP_200_OK,
            )


class CheckoutPaymentAPIview(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        try:
            plan_id = request.data.get("plan_id")
            uid = request.headers.get("uid")
            customer = Company.objects.get(uid=uid)
            # Check Already Subsctiption Plan
            stripe = StripeHelper()
            check_subsciption = stripe.check_customer_subscriptions(
                customer_id=customer.stripe_customer_id
            )
            if check_subsciption:
                subscription_id = request.data.get("subscription_id")
                upgrade_plan = stripe.upgradesubsciption(
                    subscription_id=subscription_id,
                    price_id=plan_id,
                )
                return Response(
                    data={
                        "error": False,
                        "data": [upgrade_plan],
                        "message": "Congratulations on successfully upgrading your plan!",
                    },
                    status=status.HTTP_200_OK,
                )

            # Ad-spend amount calculation
            adspend_amount, overcharge_percentage = stripe.adspend_limit_count(
                uid, customer.stripe_customer_id
            )

            checkout_session = stripe.checkout_payment(
                plan_id=plan_id,
                stripe_customer_id=customer.stripe_customer_id,
                adspend_amount=adspend_amount,
            )

            Payment.objects.create(
                company=customer,
                stripe_customer_id=checkout_session.customer,
                payment_status=checkout_session.payment_status,
                amount=checkout_session.amount_total,
                session_id=checkout_session.id,
            )
            return Response(
                data={
                    "error": False,
                    "data": checkout_session.url,
                    "message": None,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": str(e),
                },
                status=status.HTTP_200_OK,
            )


class CustomerSubsciptionAPIview(APIView):
    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        uid = request.user.company.uid
        subscription = cache.get(f"{uid}_subscription_{request.user.id}")
        if not subscription:
            customer = Company.objects.get(uid=uid)
            if customer.is_free_trial:
                is_free_trial = True
                today = datetime.date.today()
                free_trial_days_left = (customer.expire_free_trial.date() - today).days
                if free_trial_days_left < 0:
                    free_trial_days_left, is_free_trial = "Trial ended", False
            else:
                is_free_trial, free_trial_days_left = False, "Trial ended"
            stripe = StripeHelper()
            check_subsciption = stripe.check_customer_subscriptions(
                customer_id=customer.stripe_customer_id
            )
            subscription = {
                "is_free_trial": is_free_trial,
                "free_trial_days_left": free_trial_days_left,
                "customer_subscription": check_subsciption,
            }
            cache.set(f"{uid}_subscription_{request.user.id}", subscription, 300)
        return Response(
            data={
                "error": False,
                "data": subscription,
                "message": "",
            },
            status=status.HTTP_200_OK,
        )


class UpgradeSubsciptionAPIview(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        subscription_id = request.data.get("subscription_id")
        price_id = request.data.get("price_id")
        stripe = StripeHelper()
        upgrade_plan = stripe.upgradesubsciption(
            subscription_id=subscription_id,
            price_id=price_id,
        )
        return Response(
            data={
                "error": False,
                "data": [upgrade_plan],
                "message": "",
            },
            status=status.HTTP_200_OK,
        )


class RequestEnterpricePlanApiView(APIView):
    """
    RequestEnterpricePlanApiView is a viewset class that send notification email when user select enterprise plan.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        note = request.data.get("aditional_notes")
        monthly_adspend = request.data.get("estimated_monthly_adspend")
        SendGrid.send_email_to_enterprise_plan(
            email=settings.ENTERPRISE_ADMIN_EMAIL,
            useremail=request.user.email,
            firstname=request.user.first_name,
            lastname=request.user.last_name,
            monthly_adspend=monthly_adspend,
            note=note,
        )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Your notification for the Enterprise Plan has been successfully sent.",
            },
            status=status.HTTP_200_OK,
        )


class CreateEnterpricePlanAPIview(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.user.company.uid
        customer = Company.objects.get(uid=uid)
        amount = request.data.get("amount")
        interval = request.data.get("interval")
        plan_name = request.data.get("plan_name")
        ad_spend_limit = request.data.get("ad_spend_limit")
        stripe = StripeHelper()
        create_plan = stripe.create_paln(
            amount, interval, plan_name, ad_spend_limit, customer
        )
        return Response(
            data={
                "error": False,
                "data": [create_plan],
                "message": "",
            },
            status=status.HTTP_200_OK,
        )


class CancelSubscriptionAPIview(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        subscription_id = request.data.get("subscription_id")
        try:
            stripe = StripeHelper()
            stripe.cancel_subscription(subscription_id)
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Subscription is deleted successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": str(e),
                },
                status=status.HTTP_200_OK,
            )
