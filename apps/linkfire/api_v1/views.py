from SF.tasks import linkfire_api
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from apps.scraper.models import (
    SpotifyProfiles,
    Spotify1DayData,
    Spotify28DaysData,
    Spotify7DaysData,
    SpotifyPlaylistData,
    ScraperConnection,
)
from apps.common.models import ScraperGroup, Profile, Authkey, AdScheduler
from apps.linkfire.models import (
    LinkfireMediaservices,
    LinkfireLinkSettings,
    LinkfireUrl,
    ScrapeLinkfires,
    LinkfireGeneratedLinks,
    LinkfireData,
    LinkfireBoards,
)
from apps.linkfire.api_v1.serializers import (
    LinkfireMediaservicesSerializer,
    LinkFireLinkSetingsSerializer,
    ScraperGroupSerializer,
    ScrapeLinkfiresReadSerializer,
    ScrapeLinkfiresUpdateSerializer,
    SpotifyScraperInfoSerializer,
    LinkfireGeneratorSerializer,
)
from rest_framework.viewsets import ModelViewSet
from rest_framework import filters
from apps.common.upload_creative_helper import UploadCreativeHelper
from apps.common.constants import (
    CreativeType,
    ScraperConnectionType,
    StatusType,
)
import os
from SF import settings
from apps.common.s3_helper import S3BucketHelper
from rest_framework.views import APIView
from apps.common.constants import PlatFormType
import requests
from apps.common.paginations import PageNumberPagination10
from rest_framework.permissions import SAFE_METHODS
from datetime import datetime as dt
from apps.common.api_v1.serializers import ProfileSerializer
import base64
from apps.common.urls_helper import URLHelper
from apps.common.custom_decorators import track_error
from apps.linkfire.helper.Linkfire_api_handler import LinkfireApi

url_hp = URLHelper()


class ConnectLinkFireGeneratorApiView(generics.CreateAPIView):
    """
    This class provides an endpoint for connecting to the Linkfire API.
    It receives the client secret as a parameter and uses it to request an access token from the Linkfire API.
    If the request is successful, the access token and refresh token are saved to the database.
    """

    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        return Response(
            data={
                "error": False,
                "data": ProfileSerializer(
                    Profile.objects.filter(ad_platform=PlatFormType.LINKFIRE),
                    many=True,
                ).data,
                "message": "",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        client_secret = request.data.get("client_secret")
        if client_secret is None or len(client_secret) == 0:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "client_secret is required.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        first_name = request.user.first_name
        last_name = request.user.last_name
        email = request.user.email

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": "Strange_Fruits_API",
            "scope": "public.api",
            "client_secret": client_secret,
        }
        response = requests.request(
            "POST",
            url_hp.LINKFIRE_CONNECT_URL,
            headers=headers,
            data=data,
        )
        if response.status_code == 200:
            r = response.json()

            profile, _ = Profile.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "ad_platform": PlatFormType.LINKFIRE,
                },
            )

            Authkey.objects.update_or_create(
                profile=profile,
                defaults={
                    "access_token": client_secret,
                    "refresh_token": f"{r.get('token_type')} {r.get('access_token')}",
                },
            )

            headers = {
                "Api-Version": "v1.0",
                "Content-Type": "application/json",
                "Authorization": f"{r.get('token_type')} {r.get('access_token')}",
            }

            boards_response = requests.request(
                "GET", url_hp.LINKFIRE_BOARDS_URL, headers=headers
            )

            if boards_response.status_code == 200:
                r = boards_response.json()
                board_data = r.get("data")
                if board_data and len(board_data) == 1:
                    name = board_data[0].get("name")
                    board_id = board_data[0].get("id")

                    profile = Profile.objects.filter(
                        ad_platform=PlatFormType.LINKFIRE, is_active=StatusType.YES
                    ).first()

                    LinkfireBoards.objects.update_or_create(
                        board_id=board_id,
                        defaults={"name": name, "profile": profile},
                    )
                    return Response(
                        data={
                            "error": False,
                            "data": [{"is_multiple_board": False, "board_data": []}],
                            "message": f"{first_name} {last_name} has been successfully connected.",
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        data={
                            "error": False,
                            "data": [
                                {"is_multiple_board": True, "board_data": board_data}
                            ],
                            "message": f"{first_name} {last_name} has been successfully connected.",
                        },
                        status=status.HTTP_200_OK,
                    )
            else:
                return Response(
                    data={
                        "error": True,
                        "data": [{"is_multiple_board": False, "board_data": []}],
                        "message": f"{first_name} {last_name} has been successfully connected. and {boards_response.json().get('errors')[0].get('message')}",
                    },
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                )

        else:
            client_secret_response = response.json().get("error")
            if client_secret_response == "invalid_client":
                client_secret_response = "Invalid API key or IP address not whitelisted, please check and try again."
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": client_secret_response,
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

    @track_error(validate_api_parameters=["id"])
    def delete(self, request, *args, **kwargs):
        profile_id = self.request.data.get("id")
        linkfire_generator = Profile.objects.get(id=profile_id)
        linkfire_generator.is_active = StatusType.NO
        linkfire_generator.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{linkfire_generator.first_name} {linkfire_generator.last_name} has been removed from Linkfire Generator connections.",
            },
            status=status.HTTP_200_OK,
        )


class LinkfireDataScraperConnectionAPIView(generics.CreateAPIView):
    """
    This class is responsible for handling the connection to the Linkfire Scraper Setting.
    It gets the linkfire_username and linkfire_password through a GET request and returns it.
    It is responsible for handling the connection to the Linkfire Scraper.
    It accepts the linkfire_username and linkfire_password through a POST request and
    updates the corresponding values in the ScraperConnection table.
    It returns a response indicating whether the connection was successful or not.
    and also update the value "null" in the ScraperConnection table when deleting the connection.
    """

    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        scraper_connection = ScraperConnection.objects.filter(
            ad_platform=ScraperConnectionType.LINKFIRESCRAPER, is_active=StatusType.YES
        ).first()
        if not scraper_connection:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "No any linkfire scraper connection availble.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        return Response(
            data={
                "error": False,
                "data": [
                    {
                        "id": scraper_connection.id,
                        "linkfire_username": scraper_connection.username,
                        "linkfire_password": scraper_connection.password,
                    }
                ],
                "message": "",
            },
            status=status.HTTP_200_OK,
        )

    @track_error(validate_api_parameters=["linkfire_username", "linkfire_password"])
    def post(self, request, *args, **kwargs):
        linkfire_username = request.data.get("linkfire_username")
        linkfire_password = request.data.get("linkfire_password")

        encoded_linkfire_password = base64.b64encode(bytes(linkfire_password, "utf-8"))
        # decoded_linkfire_password = base64.b64decode(encoded_linkfire_password)

        ScraperConnection.objects.update_or_create(
            username=linkfire_username,
            defaults={
                "password": encoded_linkfire_password.decode(),
                "ad_platform": ScraperConnectionType.LINKFIRESCRAPER,
            },
        )

        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Linkfire data scraper has been successfully connected.",
            },
            status=status.HTTP_200_OK,
        )

    @track_error(validate_api_parameters=["id"])
    def delete(self, request, *args, **kwargs):
        scraper_connection_id = self.request.data.get("id")
        scraper_connection = ScraperConnection.objects.get(id=scraper_connection_id)
        scraper_connection.is_active = StatusType.NO
        scraper_connection.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{scraper_connection.username} has been removed from Linkfire Data Scraper connections.",
            },
            status=status.HTTP_200_OK,
        )


class SpotifyScraperConnectionAPIView(generics.CreateAPIView):
    """
    This class is responsible for handling the connection to the Spotify Scraper.
    It accepts the spotify_username and spotify_password through a POST request and
    updates the corresponding values in the ScraperConnection table.
    It returns a response indicating whether the connection was successful or not.
    and also update the value "null" in the ScraperConnection table when deleting the connection.
    """

    authentication_classes = (TokenAuthentication,)

    def get(self, request, *args, **kwargs):
        scraper_connection = ScraperConnection.objects.filter(
            ad_platform=ScraperConnectionType.SPOTIFYSCRAPER, is_active=StatusType.YES
        ).first()
        if not scraper_connection:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "No any spotify scraper connection availble.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        return Response(
            data={
                "error": False,
                "data": [
                    {
                        "id": scraper_connection.id,
                        "spotify_username": scraper_connection.username,
                        "spotify_password": scraper_connection.password,
                    }
                ],
                "message": "",
            },
            status=status.HTTP_200_OK,
        )

    @track_error(validate_api_parameters=["spotify_username", "spotify_password"])
    def post(self, request, *args, **kwargs):
        spotify_username = request.data.get("spotify_username")
        spotify_password = request.data.get("spotify_password")

        encoded_spotify_password = base64.b64encode(bytes(spotify_password, "utf-8"))
        # decoded_spotify_password = base64.b64decode(encoded_linkfire_password)

        ScraperConnection.objects.update_or_create(
            username=spotify_username,
            defaults={
                "password": encoded_spotify_password.decode(),
                "ad_platform": ScraperConnectionType.SPOTIFYSCRAPER,
            },
        )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{spotify_username} has been successfully connected.",
            },
            status=status.HTTP_200_OK,
        )

    @track_error(validate_api_parameters=["id"])
    def delete(self, request, *args, **kwargs):
        scraper_connection_id = self.request.data.get("id")
        scraper_connection = ScraperConnection.objects.get(id=scraper_connection_id)
        scraper_connection.is_active = StatusType.NO
        scraper_connection.save()

        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{scraper_connection.username} was removed from the Spotify connections.",
            },
            status=status.HTTP_200_OK,
        )


class LinkfireAPIView(generics.CreateAPIView):
    """
    A view class to trigger a celery task to fetch linkfire links.
    """

    authentication_classes = (TokenAuthentication,)

    def post(self, request, *args, **kwargs):
        uid = request.headers.get("uid")
        linkfire_api.delay(uid)
        return Response(status=status.HTTP_200_OK)


class ScraperGroupAPIViewSet(ModelViewSet):
    """
    ScraperGroupAPIViewSet is a viewset class that provides CRUD operations for ScraperGroup model. It allows you to
    create a new scraper group, list all genres, retrieve a specific scraper group, update a scraper group, and delete a scraper group.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = ScraperGroup.objects.all()
    serializer_class = ScraperGroupSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["group_name", "id"]
    pagination_class = None
    http_method_names = ["get", "post", "put", "delete"]

    def get_queryset(self):
        with_counting = self.request.query_params.get("with_counting") == "True"
        ScraperGroupSerializer.with_counting = with_counting
        queryset = super(ScraperGroupAPIViewSet, self).get_queryset()
        return queryset

    @track_error(validate_api_parameters=["group_name"])
    def create(self, request, *args, **kwargs):
        if ScraperGroup.objects.filter(
            group_name=request.data.get("group_name")
        ).exists():
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "This group name is already exists.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            profile_url="https://fruitsagency-bucket.s3.eu-west-3.amazonaws.com/upload_genre_profile/DefaultProfile.png"
        )
        # profile_pic = request.FILES.pop("profile_pic")[0]
        # profile_pic_size = UploadCreativeHelper.checkSize(profile_pic.size)
        # profile_pic_type = UploadCreativeHelper.check_video_or_image(profile_pic.name)
        # if profile_pic_type == CreativeType.VIDEO:
        #     return Response(
        #         status=status.HTTP_201_CREATED,
        #         data={
        #             "error": True,
        #             "data": [],
        #             "message": f"Video file is not supported.",
        #         },
        #     )
        # if profile_pic_size > 1:
        #     return Response(
        #         status=status.HTTP_201_CREATED,
        #         data={
        #             "error": True,
        #             "data": [],
        #             "message": f"File size {profile_pic_size} MB exceeds maximum file size of 5 MB.",
        #         },
        #     )
        # path = (
        #     f"{settings.BASE_DIR}/media/upload_genre_profile/{profile_pic.name}"
        # )
        # destination = open(path, "wb+")
        # for chunk in profile_pic.chunks():
        #     destination.write(chunk)
        # destination.close()

        # # create an instance of the S3BucketHelper class
        # s3 = S3BucketHelper(foldername="upload_genre_profile", path=path)

        # # upload a linkfire group profile picture to the S3 bucket
        # if s3.upload_to_s3(profile_pic.name):
        #     os.remove(path)
        #     serializer = self.get_serializer(data=request.data)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save(
        #         profile_url=f"{url_hp.AWS_CREATIVE_BASE_URL}/upload_genre_profile/{profile_pic.name}"
        #     )
        #     return Response(
        #         data={
        #             "error": False,
        #             "data": [],
        #             "message": "Linkfire Group has been successfully created.",
        #         },
        #         status=status.HTTP_201_CREATED,
        #     )
        # return Response(
        #     data={
        #         "error": False,
        #         "data": [],
        #         "message": "Linkfire Group has not been successfully created.",
        #     },
        #     status=status.HTTP_406_NOT_ACCEPTABLE,
        # )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Linkfire Group has been successfully created.",
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        scraper_group_id = instance.id
        self.perform_destroy(instance)
        LinkfireLinkSettings.objects.filter(scraper_group_id=scraper_group_id).delete()
        LinkfireUrl.objects.filter(scraper_group_id=scraper_group_id).delete()

        scraper_group = ScraperGroup.objects.filter(group_name="Default").first()

        LinkfireData.objects.filter(scraper_group_id=scraper_group_id).update(
            scraper_group_id=scraper_group.id
        )
        SpotifyPlaylistData.filter(scraper_group_id=scraper_group_id).update(
            scraper_group_id=scraper_group.id
        )
        SpotifyProfiles.filter(scraper_group_id=scraper_group_id).update(
            scraper_group_id=scraper_group.id
        )
        Spotify1DayData.filter(scraper_group_id=scraper_group_id).update(
            scraper_group_id=scraper_group.id
        )
        Spotify7DaysData.filter(scraper_group_id=scraper_group_id).update(
            scraper_group_id=scraper_group.id
        )
        Spotify28DaysData.filter(scraper_group_id=scraper_group_id).update(
            scraper_group_id=scraper_group.id
        )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "The Linkfire Group has been deleted.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, instance):
        instance.delete()

    @track_error(validate_api_parameters=["group_name"])
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        for attr, value in request.data.items():
            setattr(instance, attr, value)
        instance.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Scraper Group has been successfully updated.",
            },
            status=status.HTTP_200_OK,
        )


class UpdateScraperGroupProfilePictureAPIView(generics.CreateAPIView):
    """
    This is an endpoint for updating the profile picture for a scraper group.
    It receives a scraper group ID and a file object for the profile picture,
    and updates the profile picture for the scraper group in the database.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["scraper_group_id", "profile_pic"])
    def post(self, request, *args, **kwargs):
        scraper_group_id = request.data.get("scraper_group_id")
        profile_pic = request.FILES.pop("profile_pic")
        profile_pic_size = UploadCreativeHelper.check_size(profile_pic.size)
        profile_pic_type = UploadCreativeHelper.check_video_or_image(profile_pic.name)
        if profile_pic_type == CreativeType.VIDEO:
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    "error": True,
                    "data": [],
                    "message": f"{'Video file is not supported.'}",
                },
            )
        if profile_pic_size > 5:
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    "error": True,
                    "data": [],
                    "message": f"File size {profile_pic_size} MB exceeds maximum file size of 5 MB.",
                },
            )
        path = f"{settings.BASE_DIR}/media/upload_genre_profile/{profile_pic.name}"
        destination = open(path, "wb+")
        for chunk in profile_pic.chunks():
            destination.write(chunk)
        destination.close()

        # create an instance of the S3BucketHelper class
        s3 = S3BucketHelper(foldername="upload_genre_profile", path=path)

        # upload a linkfire group profile to the S3 bucket
        if s3.upload_to_s3(profile_pic.name):
            os.remove(path)
            ScraperGroup.objects.filter(id=scraper_group_id).update(
                profile_url=f"{url_hp.AWS_CREATIVE_BASE_URL}/upload_genre_profile/{profile_pic.name}",
                updated_at=dt.now(),
            )
            return Response(
                data={
                    "error": False,
                    "data": [],
                    "message": "ScraperGroup profile picture has been successfully updated.",
                },
                status=status.HTTP_200_OK,
            )


class AddLinkFireUrlAPIView(APIView):
    """
    This class represents an endpoint for adding a Linkfire url.
    It receives a POST request with the linkfire group id, media service id, default url and territory urls,
    and updates the LinkfireLinkSettings table's default_url and territory_url fields accordingly.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=[
            "scraper_group_id",
            "mediaservice_id",
            "default_url",
            "territory_urls",
        ]
    )
    def post(self, request, *args, **kwargs):
        scraper_group_id = request.data.get("scraper_group_id")
        mediaservice_id = request.data.get("mediaservice_id")
        default_url = request.data.get("default_url")
        territory_urls = request.data.get("territory_urls")

        if default_url:
            linkfire_url, _ = LinkfireUrl.objects.get_or_create(
                scraper_group_id=scraper_group_id,
                mediaServiceId=mediaservice_id,
                isoCode="Default",
            )
            linkfire_url.url = default_url
            linkfire_url.save()

        if territory_urls:
            for territory in territory_urls:
                for iso_code, url in territory.items():
                    linkfire_url, _ = LinkfireUrl.objects.get_or_create(
                        scraper_group_id=scraper_group_id,
                        mediaServiceId=mediaservice_id,
                        url=url,
                        isoCode=iso_code,
                    )
                    linkfire_url.url = url
                    linkfire_url.save()

        # Count the number of LinkfireUrl objects with the specified linkfire group id and mediaServiceId and isoCode equel to "Default" or isoCode not equel to "Default".
        count_isocode_with_default = (
            LinkfireUrl.objects.only("id")
            .filter(
                scraper_group_id=scraper_group_id,
                mediaServiceId=mediaservice_id,
                isoCode="Default",
                url__isnull=False,
            )
            .count()
        )
        count_isocode_without_default = (
            LinkfireUrl.objects.only("id")
            .filter(scraper_group_id=scraper_group_id, mediaServiceId=mediaservice_id)
            .exclude(isoCode="Default")
            .count()
        )

        if count_isocode_with_default > 0:
            LinkfireLinkSettings.objects.only("id").filter(
                scraper_group_id=scraper_group_id, mediaserviceid=mediaservice_id
            ).update(default_url="Yes", updated_at=dt.now())
        if count_isocode_without_default > 0:
            LinkfireLinkSettings.objects.only("id").filter(
                scraper_group_id=scraper_group_id, mediaserviceid=mediaservice_id
            ).update(territory_url="Yes", updated_at=dt.now())
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Linkfire url has been successfully added.",
            },
            status=status.HTTP_200_OK,
        )


class DeleteLinkfireUrl(generics.CreateAPIView):
    """
    :An endpoint for deleting a Linkfire url and updating
    the LinkfireLinkSettings table's is_default and is_territory_url fields.
    """

    authentication_classes = (TokenAuthentication,)

    def delete(self, request, linkfireurl_id, *args, **kwargs):
        # If the LinkfireUrl object exists, delete it and update the LinkfireLinkSettings table.
        if (
            link_fireurl := LinkfireUrl.objects.only("id")
            .filter(id=linkfireurl_id)
            .first()
        ):
            # Retrieve the linkfire group id and mediaServiceId fields of the LinkfireUrl object.
            linkfireurl_scraper_group_id = link_fireurl.scraper_group_id
            linkfireurl_mediaservice_id = link_fireurl.mediaServiceId

            # Delete the LinkfireUrl object.
            if link_fireurl.isoCode != "Default":
                link_fireurl.delete()
            else:
                link_fireurl.url = None
                link_fireurl.save()

            # Count the number of LinkfireUrl objects with the specified linkfire group id and mediaServiceId and isoCode equel to "Default" or isoCode not equel to "Default".
            count_isocode_with_default = (
                LinkfireUrl.objects.only("id")
                .filter(
                    scraper_group_id=linkfireurl_scraper_group_id,
                    mediaServiceId=linkfireurl_mediaservice_id,
                    isoCode="Default",
                    url__isnull=False,
                )
                .count()
            )
            count_isocode_without_default = (
                LinkfireUrl.objects.only("id")
                .filter(
                    scraper_group_id=linkfireurl_scraper_group_id,
                    mediaServiceId=linkfireurl_mediaservice_id,
                )
                .exclude(isoCode="Default")
                .count()
            )

            if count_isocode_with_default == 0:
                LinkfireLinkSettings.objects.only("id").filter(
                    scraper_group_id=linkfireurl_scraper_group_id,
                    mediaserviceid=linkfireurl_mediaservice_id,
                ).update(default_url="No", updated_at=dt.now())
            if count_isocode_without_default == 0:
                LinkfireLinkSettings.objects.only("id").filter(
                    scraper_group_id=linkfireurl_scraper_group_id,
                    mediaserviceid=linkfireurl_mediaservice_id,
                ).update(territory_url="No", updated_at=dt.now())

        else:
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "Linkfire url does not exists.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Linkfire url has been successfully deleted.",
            },
            status=status.HTTP_200_OK,
        )


class LinkfireMediaServicesAPIViewSet(ModelViewSet):
    """
    This class represents a view set for LinkFire media services.
    It includes an endpoint for retrieving media services and allows for filtering and ordering of the queryset.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = LinkfireMediaservices.objects.all()
    serializer_class = LinkfireMediaservicesSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["mediaservice_id", "name"]
    pagination_class = None
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = super(LinkfireMediaServicesAPIViewSet, self).get_queryset()
        return queryset


class LinkfireLinkSettingsAPIViewSet(ModelViewSet):
    """
    This class represents a view set for LinkFire link settings.
    It includes endpoints for retrieving, creating, and deleting link settings, as well as a method for filtering the queryset by linkfire group id.
    It also includes a method for creating associated LinkFire URLs when a new link setting is created.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = LinkfireLinkSettings.objects.all()
    serializer_class = LinkFireLinkSetingsSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = [
        "mediaservicename",
        "mediaserviceid",
        "customctatext",
        "scraper_group__group_name",
    ]
    pagination_class = None
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        queryset = super(LinkfireLinkSettingsAPIViewSet, self).get_queryset()
        scraper_group_id = self.request.query_params.get("scraper_group_id")
        return queryset.filter(
            **{"scraper_group_id": scraper_group_id} if scraper_group_id else {},
        )

    @track_error(
        validate_api_parameters=[
            "scraper_group_id",
            "mediaservice_id",
            "mediaservice_name",
            "heading",
            "caption",
        ]
    )
    def create(self, request, *args, **kwargs):
        scraper_group_id = request.data.get("scraper_group_id")
        mediaserviceid = request.data.get("mediaservice_id")
        mediaservicename = request.data.get("mediaservice_name")
        heading = request.data.get("heading")
        caption = request.data.get("caption")
        linkfire_group = ScraperGroup.objects.filter(id=scraper_group_id).first()
        if LinkfireLinkSettings.objects.filter(
            scraper_group_id=scraper_group_id,
            mediaserviceid=mediaserviceid,
            mediaservicename=mediaservicename,
        ).exists():
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": "The linkfire record has been already exists.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        LinkfireLinkSettings.objects.create(
            scraper_group_id=scraper_group_id,
            mediaserviceid=mediaserviceid,
            mediaservicename=mediaservicename,
            heading=heading,
            caption=caption,
            artwork=linkfire_group.profile_url,
        )
        LinkfireUrl.objects.create(
            scraper_group_id=scraper_group_id,
            mediaServiceId=mediaserviceid,
            isoCode="Default",
        )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Your Linkfire links have successfully been added.",
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        LinkfireUrl.objects.filter(
            scraper_group_id=instance.scraper_group_id,
            mediaServiceId=instance.mediaserviceid,
        ).delete()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "The linkfire record has been deleted with linkfire urls.",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    def perform_destroy(self, instance):
        instance.delete()


class BulkLinkfireLinkSettingUpdateAPIView(APIView):
    """
    This is the BulkLinkfireLinkSettingUpdateAPIView class that handles the updating of linkfire link settings in bulk.
    The post method updates the linkfire url, default url, sort order, custom cta text, heading, and caption for the specified linkfire group and media service id.
    It returns a response with a message indicating the success of the update.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(
        validate_api_parameters=["scraper_group_id", "bulk_linkfire_link_setting_data"]
    )
    def post(self, request, *args, **kwargs):
        scraper_group_id = request.data.get("scraper_group_id")
        bulk_linkfire_link_setting_data = request.data.get(
            "bulk_linkfire_link_setting_data"
        )
        for linkfirelink_setting_object in bulk_linkfire_link_setting_data:
            media_service_id = linkfirelink_setting_object.get("mediaserviceid")
            LinkfireUrl.objects.filter(
                scraper_group_id=scraper_group_id,
                mediaServiceId=media_service_id,
                isoCode="Default",
            ).update(
                url=linkfirelink_setting_object.get("default_url"), updated_at=dt.now()
            )

            count_isocode_with_default = (
                LinkfireUrl.objects.only("id")
                .filter(
                    scraper_group_id=scraper_group_id,
                    mediaServiceId=media_service_id,
                    isoCode="Default",
                    url__isnull=False,
                )
                .count()
            )
            if count_isocode_with_default == 0:
                LinkfireLinkSettings.objects.only("id").filter(
                    scraper_group_id=scraper_group_id, mediaserviceid=media_service_id
                ).update(default_url="No", updated_at=dt.now())

            if count_isocode_with_default > 0:
                LinkfireLinkSettings.objects.only("id").filter(
                    scraper_group_id=scraper_group_id, mediaserviceid=media_service_id
                ).update(default_url="Yes", updated_at=dt.now())

            LinkfireLinkSettings.objects.filter(
                scraper_group_id=scraper_group_id, mediaserviceid=media_service_id
            ).update(
                sortorder=linkfirelink_setting_object.get("sort_order"),
                customctatext=linkfirelink_setting_object.get("customctatext"),
                heading=linkfirelink_setting_object.get("heading"),
                caption=linkfirelink_setting_object.get("caption"),
                updated_at=dt.now(),
            )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "All linkfire link setting record has been updated.",
            },
            status=status.HTTP_200_OK,
        )


class LinkfireDataScraperAPIViewSet(ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = ScrapeLinkfires.objects.filter(
        scraper_connection__is_active=StatusType.YES,
        scraper_connection__ad_platform=ScraperConnectionType.LINKFIRESCRAPER,
    )
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = [
        "url",
        "shorttag",
        "insights_shorttag",
        "scraper_group__group_name",
        "is_active",
    ]
    pagination_class = PageNumberPagination10
    http_method_names = ["get", "put", "post"]

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ScrapeLinkfiresReadSerializer
        elif self.request.method == "put":
            return ScrapeLinkfiresUpdateSerializer

    def get_queryset(self):
        queryset = super(LinkfireDataScraperAPIViewSet, self).get_queryset()
        return queryset.order_by("-created_at")

    @track_error(validate_api_parameters=["urls", "scraper_group_id"])
    def create(self, request, *args, **kwargs):
        urls = request.data.get("urls")
        scraper_group_id = request.data.get("scraper_group_id")
        for url in urls:
            shorttag = url.split("/")[-1]
            check_url = ScrapeLinkfires.objects.filter(url=url).update(
                is_active=StatusType.YES, updated_at=dt.now()
            )
            if check_url == 0:
                scraper_connection = ScraperConnection.objects.filter(
                    ad_platform=ScraperConnectionType.LINKFIRESCRAPER,
                    is_active=StatusType.NO,
                ).first()
                ScrapeLinkfires.objects.create(
                    scraper_connection=scraper_connection,
                    shorttag=shorttag,
                    url=url,
                    scraper_group_id=scraper_group_id,
                    addedon=dt.now(),
                )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Your Linkfire links have successfully been added.",
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None):
        instance = self.get_object()
        for attr, value in request.data.items():
            setattr(instance, attr, value)
        instance.save()
        if request.data.get("active"):
            field = "Active status"
        elif request.data.get("scraper_group_id"):
            field = "Scraper Group"
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{field} has been successfully updated.",
            },
            status=status.HTTP_200_OK,
        )


class SpotifyScraperInfoAPIViewSet(ModelViewSet):
    """
    This is the SpotifyScraperInfoAPIViewSet class that presents SpotifyScraperInfo
    and also updates the active status; it creates a new record in the database.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = SpotifyProfiles.objects.filter(
        scraper_connection__is_active=StatusType.YES,
        scraper_connection__ad_platform=ScraperConnectionType.SPOTIFYSCRAPER,
    )
    serializer_class = SpotifyScraperInfoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["profile_id", "profile_name"]
    pagination_class = PageNumberPagination10
    http_method_names = ["get", "post", "put"]

    def get_queryset(self):
        queryset = super(SpotifyScraperInfoAPIViewSet, self).get_queryset()
        return queryset.order_by("-created_at")

    @track_error(validate_api_parameters=["profile_id", "scraper_group_id"])
    def create(self, request, *args, **kwargs):
        profile_id = request.data.get("profile_id")
        scraper_group_id = request.data.get("scraper_group_id")
        if SpotifyProfiles.objects.filter(
            profile_id=profile_id, scraper_group_id=scraper_group_id
        ).exists():
            return Response(
                data={
                    "error": True,
                    "data": [],
                    "message": f"{profile_id} has already been connected. Please add a different artist.",
                },
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        scraper_connection = ScraperConnection.objects.filter(
            ad_platform=ScraperConnectionType.SPOTIFYSCRAPER, is_active=StatusType.YES
        ).first()

        SpotifyProfiles.objects.get_or_create(
            profile_id=profile_id,
            scraper_group_id=scraper_group_id,
            scraper_connection=scraper_connection,
        )
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"{profile_id} has been successfully connected.",
            },
            status=status.HTTP_201_CREATED,
        )

    @track_error(validate_api_parameters=["is_active"])
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        for attr, value in request.data.items():
            setattr(instance, attr, value)
        instance.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "Status updated.",
            },
            status=status.HTTP_200_OK,
        )


class LinkfireGeneratorAPIViewSet(ModelViewSet):
    """
    This is the LinkfireGeneratorAPIViewSet class that presents
    Linkfire Generator Right-drawer table.
    """

    authentication_classes = (TokenAuthentication,)
    queryset = LinkfireGeneratedLinks.objects.filter(
        linkfire_board__profile__is_active=StatusType.YES,
        linkfire_board__profile__ad_platform=PlatFormType.LINKFIRE,
    )
    serializer_class = LinkfireGeneratorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = "__all__"
    search_fields = ["domain", "board_id", "link_id", "added_on"]
    pagination_class = PageNumberPagination10
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = super(LinkfireGeneratorAPIViewSet, self).get_queryset()
        return queryset.order_by("-created_at")


class GenerateLinkfirelinkAPIView(APIView):
    """
    This is the GenerateLinkfirelinkAPIView class that generate Linkfire link.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["scraper_group_id"])
    def post(self, request, *args, **kwargs):
        scraper_group_id = request.data.get("scraper_group_id")
        current_obj = AdScheduler.objects.create(
            platform="CUSTOM_LINKFIRE",
            scraper_group_id=scraper_group_id,
            landingpage_url="No",
            objective="Traffic",
        )
        linkfire_api = LinkfireApi(debug_mode=settings.DEBUG)
        linkfire_api.generate_missing_urls(scheduler_id=current_obj.id)
        return Response(
            data={
                "error": False,
                "data": [],
                "message": f"A new link has been created in the following group: {current_obj.scraper_group.group_name}.",
            },
            status=status.HTTP_201_CREATED,
        )


class CreateLinkfireBoardAPIView(APIView):
    """
    This is the CreateLinkfireBoardAPIView class that create linkfire board.
    """

    authentication_classes = (TokenAuthentication,)

    @track_error(validate_api_parameters=["board_id", "name"])
    def post(self, request, *args, **kwargs):
        board_id = request.data.get("board_id")
        name = request.data.get("name")

        profile = Profile.objects.filter(
            ad_platform=PlatFormType.LINKFIRE, is_active=StatusType.YES
        ).first()

        linkfire_bord, created = LinkfireBoards.objects.get_or_create(board_id=board_id)
        linkfire_bord.name = name
        linkfire_bord.profile = profile
        linkfire_bord.save()
        return Response(
            data={
                "error": False,
                "data": [],
                "message": "The Linkfire link board has been created.",
            },
            status=status.HTTP_201_CREATED,
        )
