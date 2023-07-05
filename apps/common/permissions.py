# from django.http import JsonResponse
# from django.contrib.contenttypes.models import ContentType
# from rest_framework.authtoken.models import Token
from rest_framework import permissions
from apps.common.custom_exception import PlainValidationError
from apps.common.constants import RoleType


class AdminPermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        if (
            request.user.is_authenticated
            and user.groups.filter(name=RoleType.ADMIN).exists()
        ):
            return True
        raise PlainValidationError(
            detail={
                "error": True,
                "data": [],
                "message": "You do not have permission to perform this action.",
            }
        )


class SchedulerPermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        if (
            user.is_authenticated
            and user.groups.filter(name=RoleType.SCHEDULER).exists()
            or user.groups.filter(name=RoleType.ADMIN).exists()
        ):
            return True
        raise PlainValidationError(
            detail={
                "error": True,
                "data": [],
                "message": "You do not have permission to perform this action.",
            }
        )


class CustomModelPermissions(permissions.DjangoModelPermissions):
    perms_map = {
        "GET": ["view_%(model_name)s"],
        "POST": ["add_%(model_name)s"],
        "PUT": ["change_%(model_name)s"],
        "PATCH": ["change_%(model_name)s"],
        "DELETE": ["delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        """
        Override has_permission to add the 'view' permission to GET requests.
        Check if user has view permission for the model
        """
        user = request.user
        model_perms = self.get_required_permissions(request.method, view.queryset.model)
        if model_perms[0] in user.get_permissions(user):
            return True
        raise PlainValidationError(
            detail={
                "error": True,
                "data": [],
                "message": "You do not have permission to perform this action.",
            }
        )


# class CheckPermission(object):
#     def __init__(self, model):
#         self.model = model

#     def dispatch(self, request, *args, **kwargs):
#         try:
#             token = Token.objects.get(
#                 key=(request.META.get("HTTP_AUTHORIZATION")).split(" ")[1]
#             )
#         except Exception:
#             return JsonResponse({"error": True, "message": "token is invalid"})

#         perm_codes = {
#             "GET": f"view_{self.model}",
#             "POST": f"add_{self.model}",
#             "PUT": f"change_{self.model}",
#             "DELETE": f"delete_{self.model}",
#         }
#         content_type = ContentType.objects.get(model=self.model)
#         request_method = None
#         user_permissions = []
#         for group in token.user.groups.all():
#             user_permissions = [
#                 permission.codename
#                 for permission in group.permissions.filter(content_type=content_type)
#             ]
#             request_method = perm_codes.get(request.method)
#         if request_method in user_permissions:
#             return super(CheckPermission, self).dispatch(request, *args, **kwargs)
#         else:
#             return JsonResponse({"permission error": "you don't have a permissions"})


# CheckPermission, ModelViewSet
# def __init__(self, *args, **kwargs):
#         model = self.serializer_class.Meta.model.__name__.lower()
#         CheckPermission.__init__(self, model)
