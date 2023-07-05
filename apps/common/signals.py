from apps.common.models import AdScheduler
from django.dispatch import receiver
from django.db.models.signals import post_save
from SF.tasks import scheduler_tenant


@receiver(post_save, sender=AdScheduler)
def save_profile_post_save(sender, instance, created, **kwargs):
    """
    This is a signal receiver function that runs a task using celery when an instance of the AdScheduler model is created.
    The task is responsible for scheduling and posting ads at the specified time.
    It takes the following arguments:

    - instance._uuid: a unique identifier for the task
    - _profile_id: the ID of the profile associated with the ad
    - multiple: a boolean flag indicating whether multiple ads should be posted
    - ad_scheduler_instance_id: the ID of the AdScheduler instance
    """
    if created and (instance.platform != "CUSTOM_LINKFIRE"):
        """
        wait for an update to the scheduler_id field on the adcraetive table
        """
        scheduler_tenant.apply_async(
            args=[instance._uuid, instance._profile_id, False, instance.id],
            countdown=60,
        )
