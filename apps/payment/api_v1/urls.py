from django.urls import re_path
from apps.payment.api_v1 import views

app_name = "payment"

urlpatterns = [
    re_path(r"plans/$", views.PlanListAPIView.as_view()),
    re_path(r"check-card/$", views.CheckCardAPIView.as_view()),
    re_path(r"subcribe/$", views.SubscribeAPIView.as_view()),
    re_path(r"check-subscription/$", views.CheckSubscriptionAPIView.as_view()),
    re_path(r"subscribe-plan/$", views.CheckoutPaymentAPIview.as_view()),
    re_path(r"customer-subscription/$", views.CustomerSubsciptionAPIview.as_view()),
    re_path(r"update-subscription/$", views.UpgradeSubsciptionAPIview.as_view()),
    re_path(r"request-enterprise-plan/$", views.RequestEnterpricePlanApiView.as_view()),
    re_path(r"create-enterprise-plan/$", views.CreateEnterpricePlanAPIview.as_view()),
    re_path(r"cancel-subscription/$", views.CancelSubscriptionAPIview.as_view()),
]
