from django.contrib import admin
from django.contrib.admin.decorators import register
from apps import accounts
from apps.facebook import models


# Register your models here.
@register(models.FacebookAccounts)
class FacebookAccountsAdmin(admin.ModelAdmin):
    list_display = ("account_id", "account_name", "scraper_group_id", "instagram_id")


@register(models.FacebookPages)
class FacebookPagesAdmin(admin.ModelAdmin):
    list_display = ("page_name", "page_id", "page_token", "active")


@register(models.FacebookUsers)
class FacebookUsersAdmin(admin.ModelAdmin):
    list_display = ("user_id", "user_access_token")
