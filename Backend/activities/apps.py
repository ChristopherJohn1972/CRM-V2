from django.apps import AppConfig


class ActivitiesConfig(AppConfig):
    name = "activities"
    label = "activities"

    def ready(self):
        from common.events import EventBus
        from activities.services import TimelineService

        EventBus.register(TimelineService.record_from_domain_event)
