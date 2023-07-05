from django.urls import re_path
from rest_framework import routers
from apps.accounts.api_v1 import views

router = routers.SimpleRouter()
router.register("user", views.UserViewset)
router.register("roles", views.RoleViewset)
router.register("permissions", views.PermissionsViewset)

app_name = "accounts"

urlpatterns = [
    re_path(r"create-business-account/$", views.CreateBusinessAccountAPIView.as_view()),
    re_path(r"social-signup/(?P<slug>[-\w]+)/$", views.SocialSignupAPIView.as_view()),
    re_path(r"update-profile-picture/$", views.UpdateProfilePictureAPIView.as_view()),
    re_path(r"verify-login-user/$", views.VerifyLoginUser.as_view()),
    re_path(r"set-role-permissions/$", views.SetRoleAndPermissionsApiView.as_view()),
    re_path(
        r"set-user-role-permissions/$", views.SetUserRoleAndPermissionsApiView.as_view()
    ),
    re_path(r"send-user-invitation/$", views.SendUserInvitationAPIView.as_view()),
    re_path(r"resend-user-invitation/$", views.ReSendUserInvitationAPIView.as_view()),
    re_path(r"reset-password/$", views.ResetPasswordAPIView.as_view()),
    re_path(r"forgot-password/$", views.ForgotPasswordAPIView.as_view()),
    re_path(
        r"forgot-password-token-verify/$",
        views.ForgotPasswordTokenVerifyAPIView.as_view(),
    ),
    re_path(
        r"forgot-password-confirm/$",
        views.ForgotPasswordConfirmView.as_view(),
    ),
    re_path(
        r"type-business-update/$",
        views.TypeBusinessUpdateView.as_view(),
    ),
    re_path(r"resend-otp-via-email/$", views.ReSendOtpViaEmailAPIView.as_view()),
    re_path(
        r"verify-registration-email-otp/$",
        views.VerifyRegistrationEmailOtpAPIView.as_view(),
    ),
    re_path(
        r"export-users/$",
        views.ExportUsersAPIView.as_view(),
    ),
    re_path(
        r"user-email-existence/$",
        views.UserEmailExistenceOrInvalidAPIView.as_view(),
    ),
] + router.urls
