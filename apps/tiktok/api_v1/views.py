from apps.accounts.social_accounts import SocialAccountOAuth
from apps.common.api_v1.serializers import ProfileSerializer
from apps.tiktok.helper.Tiktok_api_handler import (
    TikTokAPI,
    is_valid_tiktok_access_token,
)
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
from SF import settings
from datetime import datetime as dt
from apps.common.custom_decorators import track_error
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor


class ConnectTiktokApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the TikTok. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database. It also calls the TikTokAPI class to retrieve
    data from the TikTok API.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error()
    def get(self, request, *args, **kwargs):
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
        response, access_token, refresh_token = auth.tiktok_login_verification()
        if response.status_code != 200:
            return Response(data=response.json(), status=status.HTTP_406_NOT_ACCEPTABLE)
        r = response.json()
        profile_id = r.get("data").get("core_user_id")
        display_name = r.get("data").get("display_name")
        avatar_url = r.get("avatar_url")
        first_name, _, last_name = display_name.partition(" ")
        with transaction.atomic():
            profile, _ = Profile.objects.update_or_create(
                email=r.get("data").get("email"),
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "ad_platform": PlatFormType.TIKTOK,
                    "avatar_url": avatar_url,
                    "social_profile_id": profile_id,
                },
            )

            Authkey.objects.update_or_create(
                profile=profile,
                defaults={"access_token": access_token, "refresh_token": refresh_token},
            )
            try:
                tk = TikTokAPI(debug_mode=settings.DEBUG, profile=profile)
                tk.initializing_bussiness_adaccounts()

                uid = request.headers.get("uid")
                if cache.get(f"{uid}_platform_{PlatFormType.TIKTOK}"):
                    cache.delete(f"{uid}_platform_{PlatFormType.TIKTOK}")
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


class TiktokProfileViewset(ModelViewSet):
    """
    This is the viewset for handling the Tiktok profiles. It provides the
    functionality for listing and deleting profiles. It also
    handles caching of the data.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Profile.objects.filter(ad_platform=PlatFormType.TIKTOK).values()
    serializer_class = ProfileSerializer
    http_method_names = ["get", "delete"]

    @track_error()
    def list(self, request, *args, **kwargs):
        self.queryset = self.get_queryset()
        uid = request.headers.get("uid")
        cache_dict = cache.get(f"{uid}_platform_{PlatFormType.TIKTOK}")
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
            profile__ad_platform=PlatFormType.TIKTOK
        ).values_list("access_token", flat=True)
        with ThreadPoolExecutor(5) as executor:
            connections = list(
                executor.map(is_valid_tiktok_access_token, access_tokens)
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
        tiktok_profiles = serializer.data
        cache.set(f"{uid}_platform_{PlatFormType.TIKTOK}", tiktok_profiles, 300)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": True,
                "data": tiktok_profiles,
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
        cache_dict = cache.get(f"{uid}_platform_{PlatFormType.TIKTOK}")
        if cache_dict:
            cache_dict.remove(
                next((item for item in cache_dict if item["id"] == profile_id), None)
            )
            cache.set(f"{uid}_platform_{PlatFormType.TIKTOK}", cache_dict, 300)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{first_name} {last_name} has been removed from TikTok Ads connections.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, profile_id):
        Profile.objects.filter(id=profile_id).delete()
