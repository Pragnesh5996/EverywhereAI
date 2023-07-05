from apps.accounts.social_accounts import SocialAccountOAuth
from apps.common.api_v1.serializers import ProfileSerializer
from apps.facebook.helper.Facebook_api_handler import (
    FacebookAPI,
    is_valid_facebook_access_token,
)
from apps.facebook.models import FacebookPages, FacebookUsers, InstagramAccounts
from rest_framework import generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from apps.common.models import (
    Authkey,
    Profile,
)
from apps.common.constants import PlatFormType
from rest_framework.viewsets import ModelViewSet
from django.core.cache import cache
from rest_framework.views import APIView
from SF import settings
from apps.common.custom_decorators import track_error
from SF.tasks import update_facebook_page_room_tenant
from datetime import datetime as dt
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor


class ConnectFacebookApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the Facebook. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database.It also calls the FacebookAPI class to retrieve
    data from the Facebook API.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        if code is None or len(code) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "code is required.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        auth = SocialAccountOAuth(code)
        response, access_token, refresh_token = auth.facebook_login_verification(
            api="facebook-connect"
        )
        if response.status_code != 200:
            return Response(data=response.json(), status=status.HTTP_406_NOT_ACCEPTABLE)
        r = response.json()

        profile_id, first_name, last_name, email, avatar_url = (
            r.get("id"),
            r.get("first_name"),
            r.get("last_name"),
            r.get("email"),
            r.get("picture").get("data").get("url"),
        )
        with transaction.atomic():
            profile, _ = Profile.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "ad_platform": PlatFormType.FACEBOOK,
                    "avatar_url": avatar_url,
                    "social_profile_id": profile_id,
                },
            )

            Authkey.objects.update_or_create(
                profile=profile,
                defaults={"access_token": access_token, "refresh_token": refresh_token},
            )

            FacebookUsers.objects.update_or_create(
                user_id=r.get("id"),
                defaults={"profile": profile, "user_access_token": access_token},
            )
            try:
                fb = FacebookAPI(debug_mode=settings.DEBUG, profile=profile)
                fb.initializing_bussiness_adaccounts()
                uid = request.headers.get("uid")
                update_facebook_page_room_tenant.delay(
                    uid=uid, profiles_ids=[profile.id]
                )

                if cache.get(f"{uid}_platform_{PlatFormType.FACEBOOK}"):
                    cache.delete(f"{uid}_platform_{PlatFormType.FACEBOOK}")

            except Exception as e:
                # If an error occurs, rollback all database changes made so far
                transaction.set_rollback(True)
                return Response(
                    data={
                        "error": True,
                        "data": [],
                        "message": str(e),
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )

        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{first_name} {last_name} has been successfully connected.",
            },
            status=status.HTTP_200_OK,
        )


class FacebookProfileViewset(ModelViewSet):
    """
    This is the viewset for handling the Facebook profiles. It provides the
    functionality for listing and deleting profiles.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Profile.objects.filter(ad_platform=PlatFormType.FACEBOOK).values()
    serializer_class = ProfileSerializer
    http_method_names = ["get", "delete"]

    @track_error()
    def list(self, request, *args, **kwargs):
        self.queryset = self.get_queryset()
        uid = request.headers.get("uid")
        cache_dict = cache.get(f"{uid}_platform_{PlatFormType.FACEBOOK}")
        if cache_dict:
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache_dict,
                    "message": "",
                },
            )
        profile_bulk_update_objects = []
        access_tokens = Authkey.objects.filter(
            profile__ad_platform=PlatFormType.FACEBOOK
        ).values_list("access_token", flat=True)
        with ThreadPoolExecutor(5) as executor:
            connections = list(
                executor.map(is_valid_facebook_access_token, access_tokens)
            )
        for connection_result in connections:
            profile_obj = Profile.objects.get(
                authkey_profile__access_token=connection_result.get("access_token")
            )
            profile_obj.is_connection_established = connection_result.get("is_valid")
            profile_obj.connection_error_message = connection_result.get(
                "error_message"
            )
            profile_obj.updated_at = dt.now()
            profile_bulk_update_objects.append(profile_obj)

        Profile.objects.bulk_update(
            profile_bulk_update_objects,
            ["is_connection_established", "connection_error_message", "updated_at"],
        )

        updated_queryset = self.queryset.filter()
        serializer = self.get_serializer(updated_queryset, many=True)
        facebook_profiles = serializer.data
        cache.set(f"{uid}_platform_{PlatFormType.FACEBOOK}", facebook_profiles, 300)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": facebook_profiles,
                "message": "",
            },
        )

    @track_error()
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        profile_id = instance.get("id")
        first_name = instance.get("first_name")
        last_name = instance.get("last_name")
        self.perform_destroy(profile_id)
        uid = request.headers.get("uid")
        cache_dict = cache.get(f"{uid}_platform_{PlatFormType.FACEBOOK}")
        if cache_dict:
            cache_dict.remove(
                next((item for item in cache_dict if item["id"] == profile_id), None)
            )
            cache.set(f"{uid}_platform_{PlatFormType.FACEBOOK}", cache_dict, 300)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{first_name} {last_name} has been removed from Meta Ads connections.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, profile_id):
        Profile.objects.filter(id=profile_id).delete()


class FacebookPagesList(APIView):
    """
    List of Facebook pages based on profile id
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["business_id"])
    def post(self, request, format=None):
        business_id = request.data.get("business_id")
        # facebook_user = (
        #     FacebookUsers.objects.filter(profile_id=profile_id).values().first()
        # )
        # facebook_pages = FacebookPages.objects.filter(
        #     facebook_user=facebook_user.get("id")
        # ).values("page_id", "page_name", "room_left")
        facebook_pages = FacebookPages.objects.filter(
            facebook_business_id=business_id
        ).values("page_id", "page_name", "room_left")
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": facebook_pages,
                "message": "",
            },
        )


class InstagramAccountsUsingPageIdAPIView(APIView):
    """
    Instagram account using the page id to return an Instagram ID and name.
    """

    authentication_classes = (TokenAuthentication,)

    def fetch_instagram_accounts(self, profile_id, facebook_business_id):
        profile_obj = Profile.objects.get(id=profile_id)
        fb = FacebookAPI(debug_mode=False, profile=profile_obj)
        fb.get_instagram_accounts(business_id=facebook_business_id)

    def run_parallel(self, *functions):
        from multiprocessing import Process

        processes = []
        for function in functions:
            proc = Process(target=function)
            proc.start()
            processes.append(proc)
        for proc in processes:
            proc.join()

    # @track_error(validate_api_parameters=["profile_id", "page_id"])
    @track_error(validate_api_parameters=["profile_id", "business_id"])
    def post(self, request, *args, **kwargs):
        profile_id = request.data.get("profile_id")
        # facebook_page_id = request.data.get("page_id")
        facebook_business_id = request.data.get("business_id")
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_{facebook_business_id}_instagram"):
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache.get(f"{uid}_{facebook_business_id}_instagram"),
                    "message": "",
                },
            )
        self.run_parallel
        (self.fetch_instagram_accounts(profile_id, facebook_business_id))
        instagram_accounts_list = InstagramAccounts.objects.filter(
            facebook_business_id=facebook_business_id
        ).values(
            "instagram_account_id", "instagram_account_name", "instagram_profile_pic"
        )
        cache.set(
            f"{uid}_{facebook_business_id}_instagram", instagram_accounts_list, 300
        )
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": instagram_accounts_list,
                "message": "",
            },
        )
