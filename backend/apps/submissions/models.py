from django.conf import settings
from django.core.validators import URLValidator
from django.db import models

from apps.common.storage import PrivateStorage


def submission_upload_path(instance, filename):
    # К этому моменту filename уже случайный: его задаёт сервер, а не пользователь
    return f"submissions/{instance.contest_id}/{filename}"


class Submission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SUBMITTED = "submitted", "На проверке"
        ACCEPTED = "accepted", "Принята"
        REJECTED = "rejected", "Отклонена"

    # Пока работа в этих статусах и конкурс открыт, автор может её менять
    EDITABLE_STATUSES = (Status.DRAFT, Status.SUBMITTED)

    contest = models.ForeignKey(
        "contests.Contest", on_delete=models.CASCADE, related_name="submissions"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Только http/https: ссылки вида javascript: недопустимы
    link = models.URLField(
        max_length=500, blank=True, validators=[URLValidator(schemes=["http", "https"])]
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    moderation_comment = models.CharField(max_length=1000, blank=True)
    file = models.FileField(
        upload_to=submission_upload_path, storage=PrivateStorage(), blank=True, max_length=255
    )
    file_name = models.CharField(max_length=120, blank=True)  # имя для показа
    file_type = models.CharField(max_length=50, blank=True)  # MIME, определён по содержимому
    file_size = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["contest", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["contest", "author"], name="unique_submission_per_author"
            )
        ]

    @property
    def is_editable(self):
        return self.status in self.EDITABLE_STATUSES and self.contest.is_open

    def __str__(self):
        return f"{self.title} ({self.author})"