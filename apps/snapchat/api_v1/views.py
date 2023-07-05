from apps.accounts.social_accounts import SocialAccountOAuth
from apps.common.api_v1.serializers import ProfileSerializer
from apps.snapchat.helper.Snapchat_api_handler import SnapchatAPI
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
from apps.common.custom_decorators import track_error
from django.db import transaction


class ConnectSnapChatApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the Snapchat. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database. It also calls the SnapchatAPI class to retrieve
    data from the Snapchat API.
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
        response, access_token, refresh_token = auth.snapchat_login_verification()
        if response.status_code != 200:

            return Response(
                data={
                    "error": True,
                    "data": [response.json()],
                    "message": f"{response.json().get('error_description')}",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        r = response.json()
        if 'me' not in r:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Create ads manager and complete your profile.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        profile_id = r.get("me").get("id")
        display_name = r.get("me").get("display_name")
        first_name, _, last_name = display_name.partition(" ")
        with transaction.atomic():
            profile, _ = Profile.objects.update_or_create(
                email=r.get("me").get("email"),
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "ad_platform": PlatFormType.SNAPCHAT,
                    "social_profile_id": profile_id,
                },
            )

            Authkey.objects.update_or_create(
                profile=profile,
                defaults={"access_token": access_token, "refresh_token": refresh_token},
            )
            try:
                sc = SnapchatAPI(debug_mode=settings.DEBUG, profile=profile)
                sc.initializing_bussiness_adaccounts()

                uid = request.headers.get("uid")
                if cache.get(f"{uid}_platform_{PlatFormType.SNAPCHAT}"):
                    cache.delete(f"{uid}_platform_{PlatFormType.SNAPCHAT}")

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


class SnapProfileViewset(ModelViewSet):
    """
    This is the viewset for handling the Snapchat profiles. It provides the
    functionality for listing and deleting profiles. It also
    handles caching of the data.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Profile.objects.filter(ad_platform=PlatFormType.SNAPCHAT).values()
    serializer_class = ProfileSerializer
    http_method_names = ["get", "delete"]

    @track_error()
    def list(self, request, *args, **kwargs):
        self.queryset = self.get_queryset()
        uid = request.headers.get("uid")
        cache_dict = cache.get(f"{uid}_platform_{PlatFormType.SNAPCHAT}")
        if cache_dict:
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "error": False,
                    "data": cache_dict,
                    "message": "",
                },
            )
        snap_profiles = ProfileSerializer(self.queryset, many=True).data
        cache.set(f"{uid}_platform_{PlatFormType.SNAPCHAT}", snap_profiles, 300)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "error": False,
                "data": snap_profiles,
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
        cache_dict = cache.get(f"{uid}_platform_{PlatFormType.SNAPCHAT}")
        if cache_dict:
            cache_dict.remove(
                next((item for item in cache_dict if item["id"] == profile_id), None)
            )
            cache.set(f"{uid}_platform_{PlatFormType.SNAPCHAT}", cache_dict, 300)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{first_name} {last_name} has been removed from Snapchat Ads connections.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, profile_id):
        Profile.objects.filter(id=profile_id).delete()
