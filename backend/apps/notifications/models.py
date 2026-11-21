from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        SUBMISSION_ACCEPTED = "submission_accepted", "Работа принята"
        SUBMISSION_REJECTED = "submission_rejected", "Работа отклонена"
        JURY_ASSIGNED = "jury_assigned", "Назначение в жюри"
        JUDGING_STARTED = "judging_started", "Началось оценивание"
        RESULTS_PUBLISHED = "results_published", "Результаты опубликованы"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=200)
    text = models.TextField(blank=True)
    # Ссылки для фронта: contest_slug, submission_id. Без секретов и личных данных.
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.user}: {self.title}"