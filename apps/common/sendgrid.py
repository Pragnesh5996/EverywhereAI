from SF import settings
from SF import tasks
from celery import shared_task
from apps.common.urls_helper import URLHelper
from SF.celery import app

url_hp = URLHelper()




class SendGrid:
    """
    The SendGrid class is used to send emails using the SendGrid API. It provides methods for sending emails to
    invite users and for sending emails with a password reset link.
    """

    def send_email_to_invite_user(self, full_name, email, password):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "full_name": full_name,
                        "password": password,
                    },
                },
            ],
            "template_id": settings.INVITE_USER_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail.delay(payload=payload)

    def send_email_to_forgot_password_link(self, email, username, forgot_password_link):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "username": username.title(),
                        "forgot_password_link": forgot_password_link,
                    },
                },
            ],
            "template_id": settings.FORGOT_PASSWORD_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail.delay(payload=payload)

    def send_email_for_email_verification(
        self, recipient_email, username, email_verification_link
    ):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": recipient_email}],
                    "dynamic_template_data": {
                        "username": username.title(),
                        "email_verification_link": email_verification_link,
                    },
                },
            ],
            "template_id": settings.REGISTRATION_EMAIL_VERIFICATION_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail.apply_async(args=[payload], countdown=4)

    def send_email_for_upload_content(self, email, job_title):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "job_title": job_title,
                    },
                },
            ],
            "template_id": settings.UPLOAD_CONTENT_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail(payload=payload)

    def send_email_for_approval_status_approved(self, email, brand_name, job_title):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "job_title": job_title,
                        "brand_name": brand_name,
                    },
                },
            ],
            "template_id": settings.APPROVED_STATUS_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail(payload=payload)

    def send_email_for_social_post_link(self, email, creator_name):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "creator_name": creator_name,
                    },
                },
            ],
            "template_id": settings.SOCIAL_POST_LINK_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail(payload=payload)

    def send_email_for_approval_status_accepted(self, email, brand_name, job_title):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "job_title": job_title,
                        "brand_name": brand_name,
                    },
                },
            ],
            "template_id": settings.APPROVED_STATUS_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail(payload=payload)

    def send_email_for_approval_status_declined(self, email, brand_name, job_title):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "job_title": job_title,
                        "brand_name": brand_name,
                    },
                },
            ],
            "template_id": settings.DECLINED_STATUS_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail(payload=payload)

    def send_email_for_free_trial_expire_reminder(self,company):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": company.get("email")}],
                    "dynamic_template_data": {
                        "company_name": company.get("name"),
                        "subscription_page_url": url_hp.FE_SUBSCRIPTION_PAGE_URL,
                    },
                },
            ],
            "template_id": settings.FREE_TRIAL_REMINDER_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail.delay(payload=payload)

    def send_email_to_enterprise_plan(email, useremail, firstname, lastname, note, monthly_adspend):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "firstname":firstname,
                        "lastname":lastname,
                        "email_of_registered_user": useremail,
                        "estimated_monthly_adspend":monthly_adspend,
                        "aditional_notes":note
                    },
                },
            ],
            "template_id": settings.ENTERPRISE_EMAIL_NOTIFICATION_ID,
        }
        tasks.send_sendgrid_mail.delay(payload=payload)

    def send_email_for_milestone_reached(self, email,job_title):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "job_title": job_title,
                    },
                },
            ],
            "template_id": settings.MILESTONE_REACHED_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail(payload=payload)

    def adspend_limit_exceeded_email(self, email, overcharge_percentage, username):
        payload = {
            "from": {"email": settings.FROM_EMAIL},
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "dynamic_template_data": {
                        "overcharge_percentage": overcharge_percentage,
                        "username": username,
                        "subscription_page_url": url_hp.FE_SUBSCRIPTION_PAGE_URL,
                    },
                },
            ],
            "template_id": settings.ADSPEND_LIMIT_EXCEEDED_TEMPLATE_ID,
        }
        tasks.send_sendgrid_mail.delay(payload=payload)
