from django.apps import AppConfig


class TiktokConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tiktok"

    def ready(self):
        from apps.tiktok import signals
