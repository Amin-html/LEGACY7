from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.contests.models import Category, Contest, JudgingCriterion, Prize

User = get_user_model()

CATEGORIES = ["Фотография", "Дизайн", "Программирование", "Видео", "Спорт"]

# (название, категория, описание, статус, старт (дни от сегодня), дедлайн (дни от сегодня))
DEMO = [
    ("Спортивный кадр", "Фотография", "Покажи эмоции, движение и атмосферу спорта.", "published", -5, 20),
    ("Мир в деталях", "Фотография", "Покажи красоту природы в мелочах.", "published", -10, 12),
    ("Логотип будущего", "Дизайн", "Придумай эмблему для проекта завтрашнего дня.", "published", -3, 25),
    ("AI для лучшего будущего", "Программирование", "Реши задачу с помощью ИИ.", "published", -7, 30),
    ("Креативный фильм", "Видео", "Короткий фильм до трёх минут.", "judging", -40, -3),
    ("Футбольный челлендж", "Спорт", "Создай видео, которое вдохновляет.", "finished", -90, -45),
    ("Городской скетч", "Дизайн", "Нарисуй свой город. Старт скоро.", "published", 5, 30),
    ("Черновик конкурса", "Дизайн", "Этот конкурс виден только организатору.", "draft", 10, 40),
]


class Command(BaseCommand):
    help = "Создаёт демо-категории и конкурсы для разработки (только DEBUG=True)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo разрешён только при DEBUG=True.")

        organizer = User.objects.filter(email="organizer@legacy7.local").first()
        if not organizer:
            organizer = User.objects.create_user(
                email="organizer@legacy7.local",
                username="legacy7_org",
                password="Demo-Pass-123",
                role=User.Role.ORGANIZER,
                is_email_verified=True,
            )

        categories = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
        now = timezone.now()
        created = 0
        for title, cat, description, status, start, end in DEMO:
            if Contest.objects.filter(title=title).exists():
                continue
            contest = Contest.objects.create(
                title=title,
                description=description,
                rules="1. Работа должна быть авторской.\n2. Одна работа на участника.",
                category=categories[cat],
                organizer=organizer,
                status=status,
                starts_at=now + timedelta(days=start),
                deadline=now + timedelta(days=end),
            )
            for place, amount in ((1, 15000), (2, 10000), (3, 5000)):
                Prize.objects.create(contest=contest, place=place, amount=Decimal(amount))
            for name in ("Идея", "Исполнение", "Оригинальность"):
                JudgingCriterion.objects.create(contest=contest, title=name)
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Готово. Новых конкурсов: {created}."))