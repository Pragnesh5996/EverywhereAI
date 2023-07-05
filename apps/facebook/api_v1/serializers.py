from apps.facebook.models import FacebookPages, InstagramAccounts
from rest_framework import serializers


class FacebookPagesSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for Facebook pages.
    """

    class Meta:
        model = FacebookPages
        fields = ("page_name", "page_id", "page_token", "active")


class InstagramAccountsSerializer(serializers.ModelSerializer):
    """
    This serializer includes all fields of the InstagramAccounts
    model and sets the depth attribute to 1, which tells Django
    Rest Framework to include related models up to one level deep.
    This can be useful when you want to retrieve related data along
    with the main model.
    """

    class Meta:
        model = InstagramAccounts
        fields = "__all__"
        depth = 1
