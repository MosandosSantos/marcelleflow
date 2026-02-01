from django.apps import AppConfig


class WorkorderConfig(AppConfig):
    name = 'workorder'

    def ready(self):
        from . import signals  # noqa: F401
