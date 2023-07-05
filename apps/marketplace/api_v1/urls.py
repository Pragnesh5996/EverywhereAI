from django.urls import re_path
from rest_framework import routers
from apps.marketplace.api_v1 import views

router = routers.SimpleRouter()
router.register("job", views.JobAPIViewSet)
router.register("job-category", views.JobCategoryAPIViewSet)
router.register("submission", views.SubmissionAPIViewSet)
router.register("my-submission", views.MySubmissionAPIViewSet)
router.register("submission-approval-status", views.SubmissionApprovalStatusAPIViewSet)
router.register("submission-view-count", views.SubmissionViewCountAPIViewSet)
router.register("creator-profile", views.CreatorProfileAPIViewSet)
router.register("brand-profile", views.BrandProfileAPIViewSet)
router.register("my-job", views.MyJobAPIViewSet)
router.register("update-job-status", views.MyJobAPIViewSet)
router.register("job-slider-value", views.JobSliderValueAPIViewSet)
router.register("cpm", views.CPMAPIViewSet)
router.register("jobmilestones", views.JobMilestonesAPIViewSet)
router.register("my-past-submission", views.MyPastSubmissionAPIViewSet)
router.register("draft", views.DraftAPIViewSet)
router.register("payout", views.PayoutAPIViewSet)
router.register("payout-balance", views.PayoutBalanceAPIViewSet)


app_name = "marketplace"
urlpatterns = [
    re_path(r"job-titles/$", views.JobListAPI.as_view({'get': 'list'})),
    re_path(
        r"connect-snapchat/",
        views.ConnectSocialSnapChatApiView.as_view(),
    ),
    re_path(
        r"connect-facebook/",
        views.ConnectSocialFacebookApiView.as_view(),
    ),
    re_path(
        r"connect-tiktok/",
        views.ConnectSocialTiktokApiView.as_view(),
    ),
    re_path(
        r"vdo-webhook/",
        views.VdoCipherAPIViewSet.as_view(),
    ),
    re_path(
        r"video-otp/",
        views.VdoCipherOTPAPIViewSet.as_view(),
    ),
    re_path(
        r"presigned-url/",
        views.PresignedURLApiView.as_view(),
    ),
    re_path(
        r"disconnect-platforms/",
        views.DisconnectPlatformsApiView.as_view(),
    ),
    re_path(
        r"generate-invoice/(?P<id>\d+)/",
        views.GenerateInvoiceAPIViewSet.as_view(),
    ),
    re_path(
        r"download-submission-video/(?:(?P<video_id>\w+)/)?$",
        views.DownloadSubmissionVideoApiView.as_view(),
    ),
] + router.urls
