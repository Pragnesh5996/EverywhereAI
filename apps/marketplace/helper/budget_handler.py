import json
from apps.marketplace.models import SocialCPM, JobMilestones
from apps.common.constants import Marketplace


class BudgetCalculation:
    def __init__(self, request):

        self.job_requirements = request.get("job_requirements")
        self.platforms = request.get("platforms")
        self.selected_budget = request.get("selected_budget")

    def get_job_stage(self):
        data = json.loads(self.job_requirements)
        stage = "Easy"
        if len(data):
            if (
                "video_length" in data
                and data["video_length"] > 45
                or ("footage" in data and data["footage"])
            ):
                stage = "Hard"
            elif ("video_length" in data and 21 <= data["video_length"] <= 45) or (
                "sound" and "sound" in data
            ):
                stage = "Medium"
            elif (
                "hashtags" in data
                or "caption" in data
                or "tagged_accounts" in data
                or ("video_length" in data and 5 < data["video_length"] <= 20)
            ):
                stage = "Easy"
        return stage

    def find_percentage(self, number, total):
        return (number * total) / 100

    def find_views(self, cpm, price):
        return (price * 1000) / cpm

    def views_converter(self, value):
        if value >= 1000000:
            return str(round(value / 1000000, 1)) + "m"
        elif value >= 1000:
            return str(round(value / 1000, 1)) + "k"
        else:
            return str(value)

    def get_milestone(self, job_id):
        stage = self.get_job_stage()
        field_name = {
            "easy": "minimum",
            "medium": "balanced",
            "hard": "maximum",
        }
        cpm_value = SocialCPM.objects.filter(
            platform_type=self.platforms.lower()
        ).values()
        cpm_value = cpm_value[0].get(field_name.get(stage.lower(), ""))
        milestone_instances = []

        for index, percent in enumerate(Marketplace.milestone_percentage):
            price = self.find_percentage(percent, int(self.selected_budget))
            views = self.find_views(cpm_value, int(price))
            milestone_instances.append(
                JobMilestones(
                    job_id=job_id,
                    price=price,
                    view_count=views,
                    milestone_number=index + 1,
                )
            )
        JobMilestones.objects.bulk_create(milestone_instances)
