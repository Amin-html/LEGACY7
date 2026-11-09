from django.apps import AppConfig


class SubmissionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.submissions"
    verbose_name = "Работы"

    def ready(self):
        from . import signals  # noqa: F401