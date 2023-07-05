from apps.main.models import User
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from apps.common.constants import SocialAccountType
from django.contrib.auth.models import Permission, Group


class BusinessAccountSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for business accounts.
    It handles the validation and creation of business accounts,
    including setting the role to ADMIN and encrypting the password.
    """

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "password",
            "reason_to_use_everywhereai",
        )

    def validate(self, attrs):
        attrs["password"] = make_password(attrs.get("password"))
        return attrs

    def is_valid(self, raise_exception=False):
        email = self.initial_data["email"]
        user = User.objects.filter(email=email)
        if user.exists() and (len(user[0].password) == 0 or user[0].password is None):
            social_account = None
            if user[0].social_account == SocialAccountType.GOOGLE:
                social_account = "Google"
            elif user[0].social_account == SocialAccountType.FACEBOOK:
                social_account = "Facebook"
            if social_account:
                raise Exception(f"user is already register via {social_account}")
        elif user.exists() and user[0].password:
            raise Exception("Account already exists.")
        return super(BusinessAccountSerializer, self).is_valid(raise_exception)


class SocialSignupSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for social signup.
    It allows users to sign up with a social account and provides the necessary fields for doing so.
    """

    social_account = serializers.ChoiceField(choices=SocialAccountType.CHOICES)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "social_account")


class UserReadSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for reading user information.
    """

    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    def get_roles(self, user):
        return user.get_roles(user)

    def get_permissions(self, user):
        return user.get_permissions(user)

    class Meta:
        model = User
        exclude = ("groups", "user_permissions")
        depth = 1


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    This class represents a serializer for updating user information.
    It allows for partial updates of the user model fields.
    """

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "country",
            "gender",
        )


class RoleSerializer(serializers.ModelSerializer):
    """
    This class is a serializer for the get all role names endpoint.
    It serializes the `name` field of the Group model and checks that the role name is not blank and does not already exist.
    """

    class Meta:
        model = Group
        fields = ("name",)

    def is_valid(self, raise_exception=False):
        role_name = self.initial_data.get("name")
        if role_name is None or len(role_name.strip()) == 0:
            raise Exception("The role field may not be blank.")
        if Group.objects.filter(name=role_name).exists():
            raise Exception("The role with this name already exists.")
        return super(RoleSerializer, self).is_valid(raise_exception)


class PermissionSerializer(serializers.ModelSerializer):
    """
    This class is a serializer for the get all permissions endpoint.
    It serializes all fields of the Permission model.
    """

    class Meta:
        model = Permission
        fields = "__all__"


class ForgotPasswordSerializer(serializers.Serializer):
    """
    This class is a serializer for the password forgot endpoint.
    It checks that the email field is not blank and that the email is registered to a user.
    It also checks that the user is not a Google or Facebook user, as these users are not eligible for the forgot password feature.
    """

    email = serializers.EmailField()

    def is_valid(self, raise_exception=False):
        email = self.initial_data.get("email")
        if email is None or len(email.strip()) == 0:
            raise Exception("The email field may not be blank.")
        try:
            user = User.objects.get(email__iexact=email)
            self.__class__.user = user
        except User.DoesNotExist:
            raise Exception(f"{'This email has not been registered.'}")

        else:
            if user.social_account == SocialAccountType.GOOGLE:
                raise Exception(
                    "You are not eligible for forgot password because you are a google user"
                )

            if user.social_account == SocialAccountType.FACEBOOK:
                raise Exception(
                    "You are not eligible for forgot password because you are facebook user"
                )

        return email


class PasswordVerifySerializer(serializers.Serializer):
    """
    This class is a serializer for verifying passwords.
    It checks that the two password fields match and are not blank.
    """

    password1 = serializers.CharField(
        label="Password1",
    )
    password2 = serializers.CharField(
        label="Password2",
    )

    def is_valid(self, raise_exception=False):
        password1 = self.initial_data.get("password1")
        password2 = self.initial_data.get("password2")

        if password1 is None or password2 is None or len(password2.strip()) == 0:
            raise Exception("The password field may not be blank.")
        if password1 != password2:
            raise Exception("The password does not match.")

        return super(PasswordVerifySerializer, self).is_valid(raise_exception)


class SendUserInvitationSerializer(serializers.ModelSerializer):
    """
    This class is a serializer for creating invite for users.
    """

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role")


class TypeBusinessUpdateSerializer(serializers.ModelSerializer):
    """
    A serializer for the type of business field in the User model.
    """

    class Meta:
        model = User
        fields = ("reason_to_use_everywhereai",)
