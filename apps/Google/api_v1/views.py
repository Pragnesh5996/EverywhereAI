from apps.accounts.social_accounts import SocialAccountOAuth
from apps.common.api_v1.serializers import ProfileSerializer
from apps.common.paginations import PageNumberPagination10
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
from apps.common.custom_decorators import track_error


class ConnectGoogleApiView(generics.CreateAPIView):
    """
    This is the view for connecting to the Google. It handles the process of
    authenticating the user, getting the access and refresh tokens, and storing the
    information in the database. It also calls the GoogleAPI class to retrieve
    data from the Google API.
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
        response, access_token, refresh_token = auth.google_login_verification(
            api="google-connect"
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

        profile, created = Profile.objects.get_or_create(email=r.get("email"))
        profile.first_name = r.get("given_name")
        profile.last_name = r.get("family_name")
        profile.ad_platform = PlatFormType.GOOGLE
        profile.save()

        authkey, created = Authkey.objects.get_or_create(profile=profile)
        authkey.access_token = access_token
        authkey.refresh_token = refresh_token
        authkey.save()

        uid = request.headers.get("uid")
        if cache.get(f"{uid}_platform_{PlatFormType.GOOGLE}"):
            cache.delete(f"{uid}_platform_{PlatFormType.GOOGLE}")

        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Google connection is successfully integrated.",
            },
            status=status.HTTP_200_OK,
        )


class GoogleProfileViewset(ModelViewSet):
    """
    This is the viewset for handling the GOOGLE profiles. It provides the
    functionality for listing and deleting profiles. It also
    handles pagination and caching of the data.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = Profile.objects.filter(ad_platform=PlatFormType.GOOGLE)
    serializer_class = ProfileSerializer
    pagination_class = PageNumberPagination10

    @track_error()
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        uid = request.headers.get("uid")
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            if cache.get(f"{uid}_platform_{PlatFormType.GOOGLE}"):
                return self.get_paginated_response(
                    cache.get(f"{uid}_platform_{PlatFormType.GOOGLE}")
                )
            cache.set(f"{uid}_platform_{PlatFormType.GOOGLE}", serializer.data, 300)
            return self.get_paginated_response(serializer.data)

    @track_error()
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        uid = request.headers.get("uid")
        if cache.get(f"{uid}_platform_{PlatFormType.GOOGLE}"):
            cache.delete(f"{uid}_platform_{PlatFormType.GOOGLE}")
        return Response(
            data={"error": False, "data": [], "message": "profile is deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, instance):
        instance.delete()
