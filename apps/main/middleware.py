from django.core.exceptions import ObjectDoesNotExist
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_model,
)
from django_tenants.middleware.main import TenantMainMiddleware
from django.db import connection


class RequestIDTenantMiddleware(TenantMainMiddleware):
    """
    This middleware handles tenant switching for the request based on the `HTTP_UID` header.
    It sets the tenant for the request and activates the tenant's schema in the database connection.
    If no tenant is found, it falls back to the public schema.
    """

    def process_request(self, request):
        # the tenant metadata is stored.
        connection.set_schema_to_public()
        hostname = self.hostname_from_request(request)

        model = get_tenant_model()
        try:
            tenant = self.get_tenant(model, hostname, request)
        except model.DoesNotExist:
            self.no_tenant_found(request, hostname)
            return

        tenant.domain = hostname
        request.tenant = tenant
        connection.set_tenant(request.tenant)
        self.setup_url_routing(request)

    def get_tenant(self, model, hostname, request):
        try:
            tenant_model = model.objects.get(uid=request.META.get("HTTP_UID"))
            print("tenant_model: ", tenant_model)
            return tenant_model
        except ObjectDoesNotExist:
            public_schema = model.objects.get(schema_name=get_public_schema_name())
            return public_schema
