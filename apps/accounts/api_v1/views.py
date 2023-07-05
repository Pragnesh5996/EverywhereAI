from datetime import datetime
from apps.marketplace.models import BrandProfile
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.main.models import (
    User,
    Company,
    SocialAccountToken,
    ForgotPasswordToken,
    RegistrationOtp,
)
from apps.common.constants import RoleType
from django.contrib.auth.hashers import check_password
from rest_framework.views import APIView
from apps.accounts.api_v1.serializers import (
    SocialSignupSerializer,
    BusinessAccountSerializer,
    UserReadSerializer,
    UserUpdateSerializer,
    SendUserInvitationSerializer,
    ForgotPasswordSerializer,
    PasswordVerifySerializer,
    PermissionSerializer,
    RoleSerializer,
    TypeBusinessUpdateSerializer,
)
from apps.common.generate_schema_name import Schema
from rest_framework.authtoken.models import Token
from django.db import transaction
from apps.accounts.social_accounts import SocialAccountOAuth
from django.contrib.auth.hashers import make_password
from apps.common.sendgrid import SendGrid
from apps.accounts.custom_token_generator import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from apps.common.constants import SocialAccountType, CreativeType
from SF import settings
from rest_framework.viewsets import ModelViewSet
from django.contrib.auth.models import Permission, Group
from rest_framework.permissions import SAFE_METHODS
from apps.common.permissions import (
    CustomModelPermissions,
    AdminPermission,
)
from apps.common.s3_helper import S3BucketHelper
from apps.common.upload_creative_helper import UploadCreativeHelper
from apps.common.custom_exception import AmazonS3UploadingException, SendGridException
import os
from apps.common.urls_helper import URLHelper
from apps.common.custom_decorators import (
    track_error,
)
import random
import secrets
import csv
from django.http import HttpResponse
from rest_framework import filters
from SF.tasks import create_company_schema, create_stripe_customer
from validate_email import validate_email
from django.core.cache import cache

url_hp = URLHelper()


class CreateBusinessAccountAPIView(generics.CreateAPIView):
    """
    This is a view for creating a business account. It handles the process of creating
    a company and a user associated with the company, and setting default data in the
    database. It also generates a unique schema name for the company and auth token for the user.
    """

    serializer_class = BusinessAccountSerializer
    permission_classes = (AllowAny,)

    @track_error(
        validate_api_parameters=[
            "first_name",
            "last_name",
            "company_name",
            "email",
            "password",
            "reason_to_use_everywhereai",
        ]
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schema_name = Schema().generate_schema_name()
        uuid = Schema().generate_uuid()

        # check schema name unique or not if not then again new schema name generate
        while Company.objects.filter(schema_name=schema_name).exists():
            schema_name = Schema().generate_schema_name()

        # check uidschema name unique or not if not then again new uid generate
        while Company.objects.filter(uid=uuid).exists():
            uuid = Schema().generate_uuid()

        email = request.data.get("email")
        company_name = request.data.get("company_name")
        user = serializer.save(is_superuser=True, is_staff=True)
        user_id = user.id
        create_company_schema(
            user_id=user_id,
            schema_name=schema_name,
            email=email,
            company_name=company_name,
            uuid=uuid,
        )

        token, _ = Token.objects.get_or_create(user=user)
        otp = random.SystemRandom().randint(100000, 999999)
        useridb64 = urlsafe_base64_encode(force_bytes(user.id))
        otpb64 = urlsafe_base64_encode(force_bytes(otp))
        RegistrationOtp.objects.create(email=email, otp=otp)
        email_verification_link = (
            f"{url_hp.FRONTEND_REGISTER_URL}?useridb64={useridb64}&otpb64={otpb64}"
        )
        SendGrid().send_email_for_email_verification(
            recipient_email=email,
            username=user.get_full_name(),
            email_verification_link=email_verification_link,
        )
        transaction.on_commit(
            lambda: create_stripe_customer.delay(user_id=user.id, uuid=uuid)
        )
        permissions = Permission.objects.values_list("id", flat=True)
        group, _ = Group.objects.get_or_create(name=RoleType.ADMIN)

        user.assign_permissions_to_role(role=group, permissions=list(permissions))
        user.assign_role_to_user(user=user, role=group.id)
        return Response(
            status=status.HTTP_201_CREATED,
            data={
                "error": False,
                "data": [
                    {
                        "user_id": user_id,
                        "user": user.email,
                        "profile_pic": user.profile_pic,
                        "token": token.key,
                        "uid": uuid,
                        "company_name": company_name,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "reason_to_use_everywhereai": user.reason_to_use_everywhereai,
                        "is_superuser": user.is_superuser,
                        "is_verified_user": user.is_verified_user,
                        "roles": user.get_roles(user),
                        "permissions": user.get_permissions(user),
                        "social_account": user.social_account,
                    }
                ],
                "message": "A verification link has been sent to your email address. Please click the link to continue your registration process.",
            },
        )


class VerifyLoginUser(APIView):
    """
    This is a view for verifying the login of a user. It checks the email and password
    provided by the user against the database, and returns the user's information and a
    token if the login is successful. It also updates the user's last login time.
    """

    permission_classes = (AllowAny,)

    @track_error(validate_api_parameters=["email", "password"])
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")
        try:
            user = User.objects.get(email=email)
            try:
                request_reset_password = ForgotPasswordToken.objects.get(user_id=user.id, is_active=True)
                if request_reset_password:
                    return Response(
                        data={
                            "error": True,
                            "data": [],
                            "message": "It's look like you are requested for the forgot password,Please complete that process before trying to login.",
                        },
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            except ForgotPasswordToken.DoesNotExist:
                pass
            if len(user.password) == 0 or user.password is None:
                if user.social_account == SocialAccountType.GOOGLE:
                    social_account = "Google"
                elif user.social_account == SocialAccountType.FACEBOOK:
                    social_account = "Facebook"
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": f"It looks like you have registered this account through {social_account},Please try logging in with your {social_account} account or contact us for further assistance.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            elif not check_password(password, user.password):
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": "Your email or password is incorrect. Please check your details and try again.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Your email or password is incorrect. Please check your details and try again.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        user.last_login = datetime.now()
        user.save()
        if not user.is_verified_user:
            otp = random.SystemRandom().randint(100000, 999999)
            useridb64 = urlsafe_base64_encode(force_bytes(user.id))
            otpb64 = urlsafe_base64_encode(force_bytes(otp))
            RegistrationOtp.objects.create(email=email, otp=otp)
            email_verification_link = (
                f"{url_hp.FRONTEND_REGISTER_URL}?useridb64={useridb64}&otpb64={otpb64}"
            )
            SendGrid().send_email_for_email_verification(
                recipient_email=email,
                username=user.get_full_name(),
                email_verification_link=email_verification_link,
            )
        brand = BrandProfile.objects.filter(user=user).values()
        return Response(
            data={
                "error": False,
                "data": [
                    {
                        "user_id": user.id,
                        "user": user.email,
                        "profile_pic": user.profile_pic,
                        "token": token.key,
                        "uid": user.company.uid,
                        "company_name": user.company.name,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "reason_to_use_everywhereai": user.reason_to_use_everywhereai,
                        "is_superuser": user.is_superuser,
                        "brand": list(brand),
                        "is_verified_user": user.is_verified_user,
                        "roles": user.get_roles(user),
                        "permissions": user.get_permissions(user),
                        "social_account": user.social_account,
                    }
                ],
                "message": "Hello there! You've successfully logged in.",
            },
            status=status.HTTP_200_OK,
        )


class SocialSignupAPIView(generics.CreateAPIView):
    """
    This class handles the creation of a business user via social login (e.g. Google, Facebook).
    It also handles logging in an existing user who has signed up through a social account.
    """

    serializer_class = SocialSignupSerializer
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        """
        Handles sign up requests through Google or Facebook.
        Returns:
            - HTTP 200 with a token and user information if sign up was successful
            - HTTP 400 if the user is already registered through normal sign up or through a different social media platform
            - HTTP 406 if there was an error during the sign up process
        """
        code = request.GET.get("code")
        if code is None:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "code is required.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        auth = SocialAccountOAuth(code)
        if kwargs.get("slug") == "google":
            response, access_token, refresh_token = auth.google_login_verification(
                api="social-signup"
            )
            if response.status_code != 200:
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": f"{response.json().get('error')}",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )
            r = response.json()
            user_info = {"email": r.get("email")}
            user_info["first_name"] = r.get("given_name")
            user_info["last_name"] = r.get("family_name")
            user_info["social_account"] = SocialAccountType.GOOGLE

        if kwargs.get("slug") == "facebook":
            response, access_token, refresh_token = auth.facebook_login_verification(
                api="social-signup"
            )
            r = response.json()
            if response.status_code != 200:
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": f"{r.pop('error').get('message')}",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )
            else:
                if r.get("email") is None:
                    return Response(
                        data={
                            "error": True,
                            "data": [],
                            "message": "It looks like your Facebook account is registered with a phone number only. To sign up for EverywhereAI using your Facebook account, please add a valid email address to your Facebook settings and try connecting again.",
                        },
                        status=status.HTTP_406_NOT_ACCEPTABLE,
                    )
            user_info = {"email": r.get("email")}
            user_info["first_name"] = r.get("first_name")
            user_info["last_name"] = r.get("last_name")
            user_info["social_account"] = SocialAccountType.FACEBOOK

        email = user_info.get("email")
        user = User.objects.filter(email=email).first()

        if user:
            if user_info["social_account"] != user.social_account:
                if user.social_account == SocialAccountType.NORMAL:
                    social_account_platform = "normal"
                elif user.social_account == SocialAccountType.GOOGLE:
                    social_account_platform = "google"
                else:
                    social_account_platform = "facebook"
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": f"It looks like you have already registered this account through {social_account_platform}. Please try logging in with your {social_account_platform} account or contact us for further assistance.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if user.password:
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": f"The user is already registered through {kwargs.get('slug')}.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token, _ = Token.objects.get_or_create(user=user)
            social_user, created = SocialAccountToken.objects.get_or_create(user=user)
            social_user.access_token = access_token
            social_user.refresh_token = refresh_token
            social_user.save()
            user.last_login = datetime.now()
            user.save()
            if user.reason_to_use_everywhereai is None or len(token.key) == 0:
                return Response(
                    data={
                        "error": False,
                        "data": [
                            {
                                "user_id": user.id,
                                "user": user.email,
                                "profile_pic": user.profile_pic,
                                "token": token.key,
                                "uid": user.company.uid,
                                "company_name": user.company.name,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "reason_to_use_everywhereai": user.reason_to_use_everywhereai,
                                "is_superuser": user.is_superuser,
                                "is_verified_user": True,
                                "roles": user.get_roles(user),
                                "permissions": user.get_permissions(user),
                                "social_account": user.social_account,
                            }
                        ],
                        "message": None,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    data={
                        "error": False,
                        "data": [
                            {
                                "user_id": user.id,
                                "user": user.email,
                                "profile_pic": user.profile_pic,
                                "token": token.key,
                                "uid": user.company.uid,
                                "company_name": user.company.name,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "reason_to_use_everywhereai": user.reason_to_use_everywhereai,
                                "is_superuser": user.is_superuser,
                                "is_verified_user": True,
                                "roles": user.get_roles(user),
                                "permissions": user.get_permissions(user),
                                "social_account": user.social_account,
                            }
                        ],
                        "message": None,
                    },
                    status=status.HTTP_200_OK,
                )

        serializer = self.get_serializer(data=user_info)
        serializer.is_valid(raise_exception=True)
        schema_name = Schema().generate_schema_name()
        uuid = Schema().generate_uuid()

        # check schema name unique or not if not then again new schema name generate
        while Company.objects.filter(schema_name=schema_name).exists():
            schema_name = Schema().generate_schema_name()

        # check uidschema name unique or not if not then again new uid generate
        while Company.objects.filter(uid=uuid).exists():
            uuid = Schema().generate_uuid()

        user = self.create_user(serializer, schema_name, email, uuid)
        token, _ = Token.objects.get_or_create(user=user)
        social_user, created = SocialAccountToken.objects.get_or_create(user=user)
        social_user.access_token = access_token
        social_user.refresh_token = refresh_token
        social_user.save()
        permissions = Permission.objects.values_list("id", flat=True)
        group, _ = Group.objects.get_or_create(name=RoleType.ADMIN)
        group.permissions.set(list(permissions))
        user.groups.set([group.id])
        return Response(
            data={
                "error": False,
                "data": [
                    {
                        "user_id": user.id,
                        "user": user.email,
                        "profile_pic": user.profile_pic,
                        "token": token.key,
                        "uid": uuid,
                        "company_name": None,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "reason_to_use_everywhereai": user.reason_to_use_everywhereai,
                        "is_superuser": user.is_superuser,
                        "is_verified_user": True,
                        "roles": user.get_roles(user),
                        "permissions": user.get_permissions(user),
                        "social_account": user.social_account,
                    }
                ],
                "message": "Your account was successfully created!",
            },
            status=status.HTTP_201_CREATED,
        )

    def create_user(self, serializer, schema_name, email, uuid):
        user = serializer.save(is_superuser=True, is_staff=True)
        create_company_schema(
            user_id=user.id,
            schema_name=schema_name,
            email=email,
            company_name="",
            uuid=uuid,
        )
        transaction.on_commit(
            lambda: create_stripe_customer.delay(user_id=user.id, uuid=uuid)
        )
        return user


class UserViewset(ModelViewSet):
    """
    This class represents a viewset for managing users. It allows for
    reading and updating user information.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = User.objects.all()
    # permission_classes = [AdminPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["first_name", "last_name", "email"]
    pagination_class = None
    http_method_names = ["get", "put"]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return UserReadSerializer
        return UserUpdateSerializer

    def get_queryset(self):
        queryset = cache.get(f"{self.request.headers.get('uid')}_user_{self.request.user.id}")
        if queryset:
            return queryset
        else:
            queryset = super(UserViewset, self).get_queryset()
            if bool(self.kwargs):
                cache.set(f"{self.request.headers.get('uid')}_user_{self.request.user.id}", queryset, 300)
                return queryset
        return queryset.filter(company__uid=self.request.headers.get("uid")).exclude(
            id=self.request.user.id
        )

    @track_error()
    def update(self, request, *args, **kwargs):
        user_instance = self.get_object()
        company_instance = user_instance.company
        company_name = request.data.get("company_name")
        profile_pic = request.FILES.get("profile_pic")
        if profile_pic:
            creative_type = UploadCreativeHelper.check_video_or_image(profile_pic.name)
            if creative_type == CreativeType.VIDEO:
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": "Something went wrong with saving your changes. Please try again.",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )

            profile_picture_store_path = (
                f"{settings.BASE_DIR}/media/upload_profile_pic/{profile_pic.name}"
            )
            destination = open(profile_picture_store_path, "wb+")
            for chunk in profile_pic.chunks():
                destination.write(chunk)
            destination.close()

            # create an instance of the S3BucketHelper class
            s3 = S3BucketHelper(
                foldername=f"{'upload_profile_pic'}", path=profile_picture_store_path
            )

            # upload a file to the S3 bucket
            is_success, error_message = s3.upload_to_s3(profile_pic.name)
            if is_success:
                os.remove(profile_picture_store_path)
                profile_url = f"{url_hp.AWS_CREATIVE_BASE_URL}/upload_profile_pic/{profile_pic.name}"
                setattr(user_instance, "profile_pic", profile_url)
            else:
                os.remove(profile_picture_store_path)
                raise AmazonS3UploadingException(error_message)

        if company_name and company_instance.name != company_name:
            company_instance.name = company_name
            company_instance.save()

        for attr, value in request.data.items():
            if attr == "gender" and value == "" and len(value) == 0:
                value = None
            if (
                attr != "company_name"
                and getattr(user_instance, attr) != value
                and attr != "profile_pic"
            ):
                setattr(user_instance, attr, value)
        user_instance.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Your changes have been saved successfully.",
            },
            status=status.HTTP_200_OK,
        )


class UpdateProfilePictureAPIView(generics.CreateAPIView):
    """
    An endpoint for uploading profile picture to s3 and updating it in the database.
    """

    authentication_classes = (TokenAuthentication,)
    # permission_classes = (CustomModelPermissions,)
    queryset = User.objects.all()

    @track_error(validate_api_parameters=["profile_pic"])
    def post(self, request, *args, **kwargs):
        profile_pic = self.request.FILES.get("profile_pic")
        if not profile_pic:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"{'Profile picture is missing'}",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        creative_type = UploadCreativeHelper.check_video_or_image(profile_pic.name)
        if creative_type == CreativeType.VIDEO:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Please upload an image, not a video.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        profile_picture_store_path = (
            f"{settings.BASE_DIR}/media/upload_profile_pic/{profile_pic.name}"
        )
        destination = open(profile_picture_store_path, "wb+")
        for chunk in profile_pic.chunks():
            destination.write(chunk)
        destination.close()

        # create an instance of the S3BucketHelper class
        s3 = S3BucketHelper(
            foldername=f"{'upload_profile_pic'}", path=profile_picture_store_path
        )

        # upload a file to the S3 bucket
        is_success, error_message = s3.upload_to_s3(profile_pic.name)
        if is_success:
            os.remove(profile_picture_store_path)
            profile_pic = (
                f"{url_hp.AWS_CREATIVE_BASE_URL}/upload_profile_pic/{profile_pic.name}"
            )
            User.objects.filter(id=self.request.user.id).update(profile_pic=profile_pic)
        else:
            os.remove(profile_picture_store_path)
            raise AmazonS3UploadingException(error_message)

        return Response(
            data={
                "error": False,
                "data": [],
                "message": "User profile picture has been successfully uploaded.",
            },
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )


class RoleViewset(ModelViewSet):
    """
    Viewset for managing roles in the application.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Group.objects.all()
    serializer_class = RoleSerializer
    pagination_class = None
    permission_classes = []

    def get_queryset(self):
        return super(RoleViewset, self).get_queryset()

    @track_error(validate_api_parameters=["name"])
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "The role has been successfully created.",
            },
            status=status.HTTP_201_CREATED,
        )


class PermissionsViewset(ModelViewSet):
    """
    This class represents the PermissionsViewset which allows users to view permissions.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    pagination_class = None

    def get_queryset(self):
        return super(PermissionsViewset, self).get_queryset()


class SetRoleAndPermissionsApiView(generics.CreateAPIView):
    """
    This view is used to set permissions for a given role.
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = []

    @track_error(validate_api_parameters=["role", "permissions"])
    def post(self, request, *args, **kwargs):
        role = self.request.data.get("role")
        permissions = self.request.data.get("permissions")
        if not (isinstance(role, int) and isinstance(permissions, list)):
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "missing role or permission (please provide an integer(role) or list of integer format(permission)).",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        group = Group.objects.get(id=role)
        group.permissions.set(permissions)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Successfully set up roles and permissions.",
            },
            status=status.HTTP_200_OK,
        )


class SetUserRoleAndPermissionsApiView(generics.CreateAPIView):
    """
    This view is used to set role for a given user.
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = []

    @track_error(validate_api_parameters=["user_id", "role_id"])
    def post(self, request, *args, **kwargs):
        user_id = self.request.data.get("user_id")
        role_id = self.request.data.get("role_id")
        if not (isinstance(user_id, int) and isinstance(role_id, int)):
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "missing role_id or user_id(please provide integer format).",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        user = User.objects.get(id=user_id)
        user.groups.set([role_id])
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Successfully assign roles and permissions to the user.",
            },
            status=status.HTTP_200_OK,
        )


class SendUserInvitationAPIView(generics.CreateAPIView):
    """
    In this api create user invitation for specific role and send mail -- to -> invited user email.
    """

    serializer_class = SendUserInvitationSerializer
    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=["first_name", "last_name", "email", "role_id"]
    )
    def create(self, request, *args, **kwargs):
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        email = request.data.get("email")
        role_id = request.data.get("role_id")

        user = User.objects.filter(email=email)
        if user:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "The user is already registered.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = Company.objects.get(uid=request.headers.get("Uid"))
        password = secrets.token_urlsafe(settings.INVITE_USER_PASSWORD_LENGTH)
        user = serializer.save(
            company=company,
            password=make_password(password),
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
        user.groups.set([role_id])
        Token.objects.get_or_create(user=user)
        try:
            sendgrid = SendGrid()
            sendgrid.send_email_to_invite_user(
                full_name=f"{first_name} {last_name}", email=email, password=password
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "The invitation was successfully sent.",
                },
                status=status.HTTP_201_CREATED,
            )
        except SendGridException as e:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"User invitation not successfully sent in email because something went wrong in sendgrid :{str(e)}",
                },
                status=status.HTTP_201_CREATED,
            )


class ReSendUserInvitationAPIView(APIView):
    """
    In this api resend the user invitation if user did not recive invitation.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["email"])
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
            password = secrets.token_urlsafe(settings.INVITE_USER_PASSWORD_LENGTH)
            user.password = password = make_password(password)
            user.save()
            sendgrid = SendGrid()
            sendgrid.send_email_to_invite_user(
                full_name=f"{user.first_name} {user.last_name}",
                email=email,
                password=password,
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "The invitation was successfully resent to the user.",
                },
                status=status.HTTP_200_OK,
            )
        except (SendGridException, Exception) as e:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"The invitation could not be resent due to an error. Please wait a little and try again :{str(e)}",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )


class ResetPasswordAPIView(APIView):
    """
    An endpoint for reset password.(not for social users)
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["new_password", "old_password"])
    def post(self, request, *args, **kwargs):
        new_password = request.data.get("new_password")
        old_password = request.data.get("old_password")
        if check_password(old_password, request.user.password):
            User.objects.filter(email=request.user.email).update(
                password=make_password(new_password)
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Your password has been successfully updated.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                "error": True,
                "data": [],
                "message": "The new passwords you entered do not match. Please try again.",
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordAPIView(APIView):
    """
    A view for handling forgot password requests.
    It sends an email with a link to reset the password.(not for social users)
    """

    serializer_class = ForgotPasswordSerializer
    permission_classes = (AllowAny,)

    @track_error()
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        useridb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        self.set_token(user, token)
        forgot_password_link = (
            f"{url_hp.FRONTEND_FORGOT_PASSWORD_URL}?useridb64={useridb64}&token={token}"
        )

        try:
            # Send the forgot password email
            sendgrid = SendGrid()
            sendgrid.send_email_to_forgot_password_link(
                email=user.email,
                username=user.get_full_name(),
                forgot_password_link=forgot_password_link,
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "If your email address is familiar to us, you will receive a password reset link. If you do not see it in your mailbox, please check your spam folder or contact us for further assistance.",
                },
                status=status.HTTP_201_CREATED,
            )
        except SendGridException:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "The password reset link could not be sent due to an error. Please wait a little and try again.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

    def set_token(self, user, token):
        # Deactivate any previous tokens for the user
        ForgotPasswordToken.objects.filter(user=user).update(
            is_active=False, updated_at=datetime.now()
        )

        # Create a new token for the user
        ForgotPasswordToken.objects.create(user=user, token=token)


class ForgotPasswordTokenVerifyAPIView(APIView):
    """
    A view for verifying forgot password tokens.
    It checks the validity of the token and useridb64 provided in the request.
    """

    permission_classes = (AllowAny,)

    @track_error()
    def get(self, request, *arg, **kwargs):
        useridb64 = request.GET.get("useridb64")
        token = request.GET.get("token")
        if (token is None or len(token) == 0) and (
            useridb64 is None or len(useridb64) == 0
        ):
            return Response(
                data={
                    "error": True,
                    "data": [{"is_token_valid": False}],
                    "message": "The token and useridb64 are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if useridb64 is None or len(useridb64) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [{"is_token_valid": False}],
                    "message": "The useridb64 is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if token is None or len(token) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [{"is_token_valid": False}],
                    "message": "The token is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uid = urlsafe_base64_decode(useridb64).decode("utf-8")
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if (
            user is not None
            and default_token_generator.check_token(user, token)
            and ForgotPasswordToken.objects.filter(
                user=user, token=token, is_active=True
            ).exists()
        ):
            return Response(
                data={
                    "error": False,
                    "data": [{"is_token_valid": True}],
                    "message": "The token is validated.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                "error": True,
                "data": [{"is_token_valid": False}],
                "message": "The token is not validated.",
            },
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )


class ForgotPasswordConfirmView(APIView):
    """
    A view for confirming forgot password requests.
    It verifies the token and useridb64 provided in the request, and sets a new password for the user.
    """

    serializer_class = PasswordVerifySerializer
    permission_classes = (AllowAny,)

    @track_error()
    def post(self, request, *arg, **kwargs):
        serializer = PasswordVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        useridb64 = request.GET.get("useridb64")
        token = request.GET.get("token")
        if (token is None or len(token) == 0) and (
            useridb64 is None or len(useridb64) == 0
        ):
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "The token and useridb64 are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if useridb64 is None or len(useridb64) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "The useridb64 is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if token is None or len(token) == 0:
            return Response(
                data={"error": True, "data": [], "message": "The token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uid = urlsafe_base64_decode(useridb64).decode("utf-8")
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if (
            user is not None
            and default_token_generator.check_token(user, token)
            and ForgotPasswordToken.objects.filter(
                user=user, is_active=True, token=token
            ).exists()
        ):

            user.set_password(
                serializer.validated_data["password1"]
            )  # set_password also hashes the password that the user will get
            user.save()
            ForgotPasswordToken.objects.filter(user=user).update(
                is_active=False, updated_at=datetime.now()
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Your password has been updated successfully.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                "error": True,
                "data": [],
                "message": "This password reset link has expired or already been used. Please request a new password reset link.",
            },
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )


class TypeBusinessUpdateView(APIView):
    """
    A view for updating the type of business and company name for a user.
    It verifies the user and updates the type of business and company name in the database.
    """

    authentication_classes = (TokenAuthentication,)
    serializer_class = TypeBusinessUpdateSerializer

    def get_object(self, id):
        try:
            return User.objects.get(id=id)
        except User.DoesNotExist:
            return None

    @track_error(
        validate_api_parameters=[
            "company_name",
            "reason_to_use_everywhereai",
        ]
    )
    def put(self, request, *args, **kwargs):
        company_name = request.data.get("company_name")
        reason_to_use_everywhereai = request.data.get("reason_to_use_everywhereai")
        typebusiness_instance = self.get_object(request.user.id)
        if not typebusiness_instance:
            return Response(
                data={"error": True, "data": [], "message": "User is not exsist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TypeBusinessUpdateSerializer(
            instance=typebusiness_instance,
            data={
                "reason_to_use_everywhereai": reason_to_use_everywhereai,
            },
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            Company.objects.filter(uid=request.user.company_id).update(
                name=company_name
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "Hello there! You've successfully logged in.",
                },
                status=status.HTTP_200_OK,
            )


class ReSendOtpViaEmailAPIView(APIView):
    """
    This class defines an API view for sending a One-Time Password (OTP) to a given email address,
    to be used for email verification. The OTP is randomly generated and stored in the database along
    with the recipient email. The email is sent using the SendGrid API.
    This view allows any user (i.e., does not require authentication) to access it, as specified by
    the AllowAny permission class.
    """

    permission_classes = (AllowAny,)

    @track_error(validate_api_parameters=["user_id", "email"])
    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        recipient_email = request.data.get("email")
        user = User.objects.get(id=user_id)
        otp = random.SystemRandom().randint(100000, 999999)
        useridb64 = urlsafe_base64_encode(force_bytes(user.id))
        otpb64 = urlsafe_base64_encode(force_bytes(otp))
        RegistrationOtp.objects.filter(email=recipient_email).update(
            is_active=False, updated_at=datetime.now()
        )
        RegistrationOtp.objects.create(email=recipient_email, otp=otp)
        email_verification_link = (
            f"{url_hp.FRONTEND_REGISTER_URL}?useridb64={useridb64}&otpb64={otpb64}"
        )
        SendGrid().send_email_for_email_verification(
            recipient_email=recipient_email,
            username=user.get_full_name(),
            email_verification_link=email_verification_link,
        )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "A link to verify your email address has been sent successfully.",
            },
            status=status.HTTP_200_OK,
        )


class VerifyRegistrationEmailOtpAPIView(APIView):
    """
    This view is used to verify the OTP sent to the user's email during registration process.
    """

    permission_classes = (AllowAny,)

    @track_error(validate_api_parameters=["useridb64", "otpb64"])
    def post(self, request, *args, **kwargs):
        useridb64, otpb64 = request.data.get("useridb64"), request.data.get("otpb64")
        user_id, otp = urlsafe_base64_decode(useridb64).decode(
            "utf-8"
        ), urlsafe_base64_decode(otpb64).decode("utf-8")
        user = User.objects.get(id=user_id)
        token, _ = Token.objects.get_or_create(user=user)
        registration_otp = RegistrationOtp.objects.filter(
            email=user.email, is_active=True, otp=otp
        ).first()
        if registration_otp and registration_otp.otp == otp:
            user.is_verified_user = True
            user.save()
            return Response(
                data={
                    "error": False,
                    "data": [
                        {
                            "user_id": user.id,
                            "user": user.email,
                            "token": token.key,
                            "uid": user.company.uid,
                            "company_name": user.company.name,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "reason_to_use_everywhereai": user.reason_to_use_everywhereai,
                            "is_verified_user": user.is_verified_user,
                            "roles": user.get_roles(user),
                            "permissions": user.get_permissions(user),
                        }
                    ],
                    "message": "Your email has been successfully verified.",
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                data={
                    "error": True,
                    "data": [{"is_valid_otp": False}],
                    "message": "This verification link is not validated or has expired. Click here to resend a verification link.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )


class ExportUsersAPIView(APIView):
    """
    This API view exports a CSV file containing user data for the given user IDs.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["user_ids"])
    def post(self, request, *args, **kwargs):
        user_ids = request.data.get("user_ids")
        filters = {"id__in": user_ids}
        users = User.objects.filter(**filters if user_ids else {})
        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = 'attachment; filename="everywhere-ai-user-data.csv"'
        writer = csv.writer(response)
        writer.writerow(["id", "first name", "last name", "email"])
        for user in users:
            writer.writerow([user.id, user.first_name, user.last_name, user.email])
        return response


class UserEmailExistenceOrInvalidAPIView(APIView):
    """
    API view for checking if a user with a given email invalid or already exists in the database.
    """

    permission_classes = []

    @track_error(validate_api_parameters=["email"])
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        exists = User.objects.filter(email=email).exists()
        if not validate_email(email):
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Enter a valid email address.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        return Response(
            data={
                "error": exists,
                "data": [],
                "message": "Account already exists." if exists else None,
            },
            status=status.HTTP_406_NOT_ACCEPTABLE if exists else status.HTTP_200_OK,
        )
