from django.db import models
from apps.common.models import Profile, TimeStampModel, AdAccount


# Create your models here.
class FacebookAccounts(models.Model):
    account_id = models.CharField(max_length=45, blank=True, null=True)
    account_name = models.CharField(max_length=45, blank=True, null=True)
    scraper_group = models.ForeignKey(
        "common.ScraperGroup",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="facebook_accounts_scraper_group",
    )
    instagram_id = models.CharField(max_length=450, blank=True, null=True)
    active = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "facebook_accounts"


class FacebookUsers(TimeStampModel):
    user_id = models.CharField(max_length=45, blank=True, null=True)
    user_access_token = models.CharField(max_length=450, blank=True, null=True)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="facebook_users_profile",
    )

    class Meta:
        managed = True
        db_table = "facebook_users"


class FacebookPages(TimeStampModel):
    page_name = models.CharField(max_length=45, blank=True, null=True)
    page_id = models.CharField(max_length=45, blank=True, null=True)
    page_token = models.CharField(max_length=450, blank=True, null=True)
    active = models.CharField(max_length=45, blank=True, null=True)
    facebook_user = models.ForeignKey(
        FacebookUsers,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="facebook_pages_facebook_user",
    )
    facebook_business = models.ForeignKey(
        "common.Business",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="facebook_pages_facebook_business",
    )
    is_published = models.BooleanField(default=False)
    room_left = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "facebook_pages"


class InstagramAccounts(TimeStampModel):
    instagram_account_name = models.CharField(max_length=45, blank=True, null=True)
    instagram_account_id = models.CharField(max_length=45, blank=True, null=True)
    instagram_profile_pic = models.TextField(blank=True, null=True)
    facebook_page = models.ForeignKey(
        FacebookPages,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="instagram_account_facebookpages",
    )
    facebook_business = models.ForeignKey(
        "common.Business",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="InstagramAccounts_facebook_business",
    )

    class Meta:
        managed = True
        db_table = "instagram_accounts"
