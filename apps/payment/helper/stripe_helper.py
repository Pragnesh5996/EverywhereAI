import stripe
from SF import settings
from datetime import datetime, timezone, timedelta
from apps.payment.models import Payment, Subscription
from apps.main.models import Company
from apps.common.urls_helper import URLHelper
import requests
from apps.common.models import DailyAdspendGenre
from django.db.models import Sum

url_hp = URLHelper()

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeHelper:
    def create_token(self, card_number, exp_month, exp_year, cvc):
        """
        Create a new payment source token for a card.
        """
        token = stripe.Token.create(
            card={
                "number": card_number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc,
            },
        )
        return token

    def asign_token_to_customer(self, company, token):
        """
        Assigns a new payment source token to a Stripe customer.
        """
        customer = stripe.Customer.retrieve(company.stripe_customer_id)
        customer.source = token.id
        customer.save()

    def create_customer(self, user, uid):
        """
        Create a new customer with the given email address.
        """
        try:
            expire_free_trial = datetime.now() + timedelta(days=30)
            customer = stripe.Customer.create(
                email=user.email,
                name=user.first_name,
                metadata={
                    "company_id": uid,
                },
            )
            Company.objects.filter(uid=uid).update(
                stripe_customer_id=customer.get("id"),
                expire_free_trial=expire_free_trial,
            )
            return customer
        except stripe.error.StripeError:
            pass

    def retrieve_customer(self, customer_id):
        """
        Retrieve an existing customer by their ID.
        """
        customer = stripe.Customer.retrieve(customer_id)
        return customer

    def create_subscription(self, stripe_customer_id, plan_id):
        """
        Create a new subscription for the given customer and plan.
        """
        stripe_subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[
                {"price": plan_id},
            ],
            billing_cycle_anchor=1635580800,
            metadata={
                "user_id": self.user.id,
                "plan_id": plan_id,
            },
        )

        subscription = Subscription.objects.create(
            customer=self,
            plan_id=plan_id,
            stripe_subscription_id=stripe_subscription.get("id"),
            current_period_start=datetime.fromtimestamp(
                stripe_subscription.get("current_period_start"), timezone.utc
            ),
            current_period_end=datetime.fromtimestamp(
                stripe_subscription.get("current_period_end"), timezone.utc
            ),
            status=stripe_subscription.get("status"),
        )
        return subscription

    def update_subscription(self, subscription_id, **update_fields):
        """
        Update an existing subscription with the given metadata fields.
        """
        subscription = stripe.Subscription.modify(
            subscription_id,
            metadata=update_fields,
        )
        return subscription

    def retrieve_subscription(self, subscription_id):
        """
        Retrieve an existing subscription by its ID.
        """
        subscription = stripe.Subscription.retrieve(subscription_id)
        return subscription

    def cancel_subscription(self, subscription_id):
        """
        Cancel an existing subscription by its ID.
        """
        subscription = stripe.Subscription.delete(subscription_id)
        return subscription

    def retrieve_plan_list(self):
        """
        This function retrieves a list of all plans from the Stripe API using the Stripe SDK.
        """
        return stripe.Price.list()

    def retrieve_plan_price(self, plan_id):
        """
        This function retrieves the price of a Stripe plan with the given plan ID.
        """
        plan_price = stripe.Price.retrieve(plan_id)
        return plan_price

    def create_charge(self, customer, amount):
        """
        Create a new charge for the given customer with the given amount and currency.
        """
        stripe_charge = stripe.Charge.create(
            customer=customer.stripe_customer_id,
            amount=int(amount / 100),
            currency="usd",
            metadata={
                "user_id": customer.user.id,
            },
        )
        Payment.objects.create(
            customer=customer,
            amount=amount,
            stripe_charge_id=stripe_charge.get("id"),
            status=stripe_charge.get("status"),
        )

    def checkout_payment(self, plan_id, stripe_customer_id, adspend_amount):
        if adspend_amount:
            extra_charges = {
                "price_data": {
                    "currency": "usd",
                    # additional amount in cents to Convert in doller
                    "unit_amount": int(adspend_amount * 100),
                    "product_data": {
                        "name": "Additional charges Based on Ad-spend",
                    },
                },
                "quantity": 1,
            }
        else:
            extra_charges = {}

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": plan_id,
                    "quantity": 1,
                },
                extra_charges,
            ],
            mode="subscription",
            customer=stripe_customer_id,
            success_url=url_hp.CHECKOUT_PAYMENT_SUCCESS_URL,
            cancel_url=url_hp.CHECKOUT_PAYMENT_CANCEL_URL,
        )
        return checkout_session

    def upgradesubsciption(self, subscription_id, price_id):
        subscription = stripe.Subscription.retrieve(subscription_id)
        upgrade_plan = stripe.Subscription.modify(
            subscription_id,
            items=[
                {
                    "id": subscription["items"]["data"][0].id,
                    "price": price_id,
                }
            ],
        )
        return upgrade_plan

    def check_customer_subscriptions(self, customer_id):
        subscriptions = stripe.Subscription.list(customer=customer_id)
        return subscriptions.data if subscriptions.data else []

    def currency_exchnage_rate(self, adspend_currency):
        url = f"{url_hp.CURRANCY_EXCHANEG_RATE}/{settings.EXCHANGE_RATE_API_KEY}/pair/{adspend_currency}/USD"
        response = requests.get(url)
        data = response.json()
        return data

    def webhook_subscription(self, subscription):
        company_id = Company.objects.get(
            stripe_customer_id=subscription.get("customer")
        )
        Subscription.objects.create(
            company=company_id,
            stripe_subscription_id=subscription.get("id"),
            status=subscription.get("status"),
            plan_id=subscription.get("plan").get("id"),
            current_period_start=datetime.fromtimestamp(
                subscription.get("current_period_start")
            ),
            current_period_end=datetime.fromtimestamp(
                subscription.get("current_period_end")
            ),
            stripe_invoice_id=subscription.get("latest_invoice"),
            ad_spend_limit=subscription.get("plan")
            .get("metadata")
            .get("ad_spend_limit"),
            ad_spend_percentage=subscription.get("plan")
            .get("metadata")
            .get("percentage"),
        )

    def cancel_at_period_end(self, session_id):
        session = stripe.checkout.Session.retrieve(session_id)
        if session.subscription:
            subscription = stripe.Subscription.retrieve(session.subscription)
            subscription.cancel_at_period_end = True
            subscription.save()
            return True
        return False

    def create_paln(self, amount, interval, plan_name, ad_spend_limit, customer):
        try:
            product = stripe.Product.create(
                name=f"Enterprise Plan of {customer.stripe_customer_id}"
            )
            new_plan = stripe.Plan.create(
                amount=amount * 100,
                currency="usd",
                interval=interval,
                product=product.get("id"),
                nickname=plan_name,
                metadata={
                    "ad_spend_limit": ad_spend_limit,
                },
            )
            return new_plan
        except Exception as e:
            return str(e)

    def adspend_limit_count(self, uid, stripe_customer_id):
        adspend_date = (
            Subscription.objects.filter(company=uid, status="active")
            .values_list(
                "current_period_start",
                "current_period_end",
                "ad_spend_limit",
                "ad_spend_percentage",
            )
            .last()
        )
        if adspend_date:
            start_date = adspend_date[0].date()
            end_date = adspend_date[1].date()
            daily_adspend_data = (
                DailyAdspendGenre.objects.filter(date__range=(start_date, end_date))
                .values("account_id", "ad_account_currency")
                .annotate(total_spend=Sum("spend"))
                .values("ad_account_currency", "total_spend")
            )
            sum_of_adspend = 0.0
            for data in daily_adspend_data:
                if data.get("ad_account_currency") and data.get("total_spend"):
                    rate = self.currency_exchnage_rate(
                        adspend_currency=data.get("ad_account_currency")
                    )
                    result = rate.get("conversion_rate") * float(
                        data.get("total_spend")
                    )
                sum_of_adspend += result
            if adspend_date[2] is not None and sum_of_adspend > adspend_date[2]:
                check_subsciption = self.check_customer_subscriptions(
                    customer_id=stripe_customer_id
                )
                percentage = (
                    check_subsciption[0].get("plan").get("metadata").get("percentage")
                )
                addtional_amount = sum_of_adspend - adspend_date[2]
                adspend_amount = float(percentage) * addtional_amount / 100
                overcharge_percentage = adspend_date[3]
            else:
                adspend_amount, overcharge_percentage = None, None
        else:
            adspend_amount, overcharge_percentage = None, None

        return adspend_amount, overcharge_percentage

