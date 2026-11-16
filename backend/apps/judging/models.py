from django.conf import settings
from django.db import models
from django.db.models import Q


class Evaluation(models.Model):
    """Оценка одной работы одним судьёй. Подтверждённая оценка (final) заморожена."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        FINAL = "final", "Подтверждена"

    submission = models.ForeignKey(
        "submissions.Submission", on_delete=models.CASCADE, related_name="evaluations"
    )
    judge = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="evaluations"
    )
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    # Итог по шкале 0-10. Считается на сервере в момент подтверждения.
    total = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["submission", "judge"], name="unique_evaluation_per_judge"),
            models.CheckConstraint(
                condition=Q(total__isnull=True) | Q(total__gte=0, total__lte=10),
                name="evaluation_total_0_10",
            ),
        ]
        indexes = [models.Index(fields=["judge", "status"])]

    def __str__(self):
        return f"{self.judge} -> {self.submission} ({self.status})"


class EvaluationScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="scores")
    criterion = models.ForeignKey(
        "contests.JudgingCriterion", on_delete=models.CASCADE, related_name="scores"
    )
    score = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("criterion_id",)
        constraints = [
            models.UniqueConstraint(fields=["evaluation", "criterion"], name="unique_score_per_criterion")
        ]

    def __str__(self):
        return f"{self.criterion}: {self.score}"