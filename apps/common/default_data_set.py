import os
import json
from SF import settings
from django_tenants.utils import tenant_context
from apps.scraper.models import Settings

# set default data(Setting table) if user/company is registered first time
def set_default_data(company, email):
    with tenant_context(company):
        with open(
            os.path.join(settings.BASE_DIR, "apps/common/json/setting_data.json")
        ) as json_file:

            setting_json = json.load(json_file)
            setting_json["notification_recipients"] = setting_json[
                "low_priority_recipients"
            ] = setting_json["high_priority_recipients"] = email

            settings_objects = [
                Settings(variable=variable, value=value)
                for variable, value in setting_json.items()
            ]
            Settings.objects.bulk_create(settings_objects)
