from __future__ import absolute_import, unicode_literals

import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SF.settings")

app = Celery("SF")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(settings.INSTALLED_APPS)

app.conf.beat_schedule = {
    # Executes every day morning at 7:00 A.M
    # "setconversion_update_spend_data": {
    #     "task": "setconversion_update_spend_data",
    #     "schedule": crontab(hour=7, minute=0),
    # },
    # Executes every day morning at 9:00 A.M
    "update_daily_spend_data": {
        "task": "update_daily_spend_data",
        "schedule": crontab(minute=0, hour="*/12"),
    },
    # Executes every 10 minutes
    # "optimizer": {
    #     "task": "optimizer",
    #     "schedule": crontab(minute="*/10"),
    # },
    # Executes every 4 hour
    "initializer": {
        "task": "initializer",
        "schedule": crontab(minute=0, hour="*/12"),
    },
    "scheduler": {
        "task": "scheduler",
        "schedule": crontab(minute=0, hour="*/12"),
    },
    # Executes every hour
    # "linkfire_scraper": {
    #     "task": "linkfire_scraper",
    #     "schedule": crontab(hour="*/1"),
    # },
    # Executes every minutes
    "linkfire_api": {
        "task": "linkfire_api",
        # "schedule": crontab(minute="*/1"),
        "schedule": crontab(minute=0, hour="*/12"),
    },
    # Executes every day
    "linkfire_mediaservice_api": {
        "task": "linkfire_mediaservice_api",
        "schedule": crontab(minute=0, hour=0),
    },
    "facebook_pages_room": {
        "task": "facebook_pages_room",
        "schedule": crontab(minute=0, hour=0),
        # "schedule": crontab(minute=0),
    },
    # "get_view_count": {
    #     "task": "get_view_count",
    #     "schedule": crontab(minute=30),
    # },
    # "set_complete_milestone": {
    #     "task": "set_complete_milestone",
    #     "schedule": crontab(minute=30),
    # },
    # "update_spent_balance": {
    #     "task": "update_spent_balance",
    #     "schedule": crontab(minute=30),
    # },
    "check_free_trial_date": {
        "task": "check_free_trial_date",
        "schedule": crontab(minute=0, hour=0),
    },
    "free_trial_expiry_reminder_email": {
        "task": "free_trial_expiry_reminder_email",
        "schedule": crontab(minute=0, hour=0),
    },
    # "mp_facebook_refresh_token": {
    #     "task": "facebook_refresh_token",
    #     "schedule": crontab(minute=0, hour="*/24"),
    # },
    # "mp_tiktok_refresh_token": {
    #     "task": "tiktok_refresh_token",
    #     "schedule": crontab(minute=0, hour="*/24"),
    # },
}


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
