from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify


def make_unique_slug(model, value, pk=None, max_length=60):
    """Slug из названия (кириллица разрешена). Если занят, добавляем -2, -3 и т.д."""
    base = slugify(value, allow_unicode=True)[:max_length] or "item"
    qs = model.objects.exclude(pk=pk) if pk else model.objects.all()
    candidate, n = base, 1
    while qs.filter(slug=candidate).exists():
        n += 1
        suffix = f"-{n}"
        candidate = base[: max_length - len(suffix)] + suffix
    return candidate


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=60, unique=True, allow_unicode=True, blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "категория"
        verbose_name_plural = "категории"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(Category, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Contest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликован"
        JUDGING = "judging", "Идёт оценивание"
        FINISHED = "finished", "Завершён"
        ARCHIVED = "archived", "В архиве"

    # Эти статусы видны всем. Черновики и архив видит только организатор.
    PUBLIC_STATUSES = (Status.PUBLISHED, Status.JUDGING, Status.FINISHED)

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=60, unique=True, allow_unicode=True, blank=True)
    description = models.TextField()
    rules = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="contests")
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organized_contests"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    starts_at = models.DateTimeField()
    deadline = models.DateTimeField()
    currency = models.CharField(max_length=3, default="KGS")
    cover = models.ImageField(upload_to="contests/covers/", blank=True)
    public_submissions = models.BooleanField(
        default=False, help_text="Показывать список работ всем посетителям"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-starts_at",)
        indexes = [
            models.Index(fields=["status", "deadline"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(deadline__gt=F("starts_at")),
                name="contest_deadline_after_start",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(Contest, self.title, self.pk)
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        """Принимает ли конкурс работы прямо сейчас."""
        now = timezone.now()
        return self.status == self.Status.PUBLISHED and self.starts_at <= now < self.deadline

    def __str__(self):
        return self.title


class Prize(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="prizes")
    place = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("place",)
        constraints = [
            models.UniqueConstraint(fields=["contest", "place"], name="unique_prize_place")
        ]

    def __str__(self):
        return f"{self.contest}: {self.place} место"


class JudgingCriterion(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="criteria")
    title = models.CharField(max_length=120)
    max_score = models.PositiveSmallIntegerField(default=10)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1)

    class Meta:
        ordering = ("id",)
        verbose_name = "критерий оценки"
        verbose_name_plural = "критерии оценки"
        constraints = [
            models.UniqueConstraint(fields=["contest", "title"], name="unique_criterion_title")
        ]

    def __str__(self):
        return f"{self.contest}: {self.title}"


class ContestJury(models.Model):
    """Назначение судьи на конкурс. Оценивать смогут только назначенные."""

    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="jury_assignments"
    )
    judge = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jury_assignments",
        limit_choices_to={"role": "jury"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "contest jury"
        constraints = [
            models.UniqueConstraint(fields=["contest", "judge"], name="unique_contest_judge")
        ]

    def __str__(self):
        return f"{self.judge} @ {self.contest}"