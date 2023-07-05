from django.urls import re_path
from rest_framework import routers
from apps.common.api_v1 import views

router = routers.SimpleRouter()
router.register(
    "adaccount-active-status-channge", views.AdAccountActiveStatusChangeAPIView
)
router.register("adset", views.AdsetAPIView)
router.register("campaign", views.CampaignAPIViewSet)
router.register("schedule-presets", views.SchedulePresetAPIViewSet)
router.register("schedule-historys", views.ScheduleHistorysAPIViewSet)
router.register("auto-scheduler-draft", views.AutoSchedulerDraftAPIViewSet)
router.register("schedule-historys-progress", views.ScheduleHistorysProgressAPIViewSet)


app_name = "common"
urlpatterns = [
    re_path(r"ad-creative-upload/$", views.CreativeUploadAPIView.as_view()),
    re_path(r"ad-creative-delete/$", views.CreativeDeleteAPIView.as_view()),
    re_path(
        r"bulk-ad-creative-landingpage-url-update/$",
        views.BulkCreativeLandingPageUrlUpdateAPIView.as_view(),
    ),
    re_path(r"get-dimensions/$", views.GetDimensionsAPIView.as_view()),
    re_path(r"create-scheduler/$", views.CreateSchedulerAPIView.as_view()),
    re_path(r"optimizer/$", views.OptimizerAPIView.as_view()),
    re_path(r"initializer/$", views.InitializerAPIView.as_view()),
    re_path(r"scheduler/$", views.SchedulerAPIView.as_view()),
    re_path(r"update-daily-spend-data/$", views.UpdateDailySpendDataAPIView.as_view()),
    re_path(
        r"set-conversion-and-update-spend-data/$",
        views.SetConversionUpdateSpendDataAPIView.as_view(),
    ),
    re_path(r"platform-count/$", views.PlatformCountAPIView.as_view()),
    re_path(r"dailyaddspend-filter/$", views.DailyAdspendGenrefilterAPIView.as_view()),
    re_path(r"interest/$", views.InterestAPIView.as_view()),
    re_path(r"profile/$", views.ProfileAPIView.as_view()),
    re_path(
        r"get-adaccount-using-profile-id/$",
        views.GetAdAccountUsingProfileAPIView.as_view(),
    ),
    re_path(
        r"get-campaign-using-adaccount/$",
        views.GetCampaignUsingAdAccountAPIView.as_view(),
    ),
    re_path(r"identity/$", views.IdentityAPIView.as_view()),
    re_path(r"applist/$", views.ApplistAPIView.as_view()),
    re_path(
        r"get-pixel-using-adaccount/$", views.GetPixelUsingAdAccountAPIView.as_view()
    ),
    re_path(
        r"get-optimize-event-using-adaccount/$",
        views.GetOptimizeEventUsingAdAccountAPIView.as_view(),
    ),
    re_path(
        r"get-custom-audience-using-adaccount/$",
        views.CustomAudienceUsingAdaccountAPIView.as_view(),
    ),
    re_path(
        r"retry-schedule-batch/$",
        views.RetryScheduleBatchAPIView.as_view(),
    ),
    re_path(
        r"stop-scheduling/$",
        views.StopSchedulingAPIViewSet.as_view(),
    ),
    re_path(
        r"fetch-latest-profile-data/$",
        views.FetchLatestProfileDataAPIViewSet.as_view(),
    ),
    re_path(
        r"fetch-latest-adaccount-data/$",
        views.FetchLatestAdaccountDataAPIViewSet.as_view(),
    ),
    re_path(
        r"reuse-history-batch/$",
        views.ReuseHistoryBatchAPIView.as_view(),
    ),
    re_path(
        r"generate-uploadses-id/$",
        views.GenerateUploadsesIdAPIView.as_view(),
    ),
    re_path(
        r"review-page-adset-calculation/$",
        views.ReviewPageAdsetCalculationAPIView.as_view(),
    ),
    re_path(
        r"insert-reuse-creatives/$",
        views.InsertReuseCreativeAPIView.as_view(),
    ),
    re_path(
        r"schedule-historys-details/$",
        views.SchedulerHistoryDetailsAPIView.as_view(),
    ),
] + router.urls
