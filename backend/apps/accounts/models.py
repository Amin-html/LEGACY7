from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_email_verified", True)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        PARTICIPANT = "participant", "Участник"
        JURY = "jury", "Жюри"
        ORGANIZER = "organizer", "Организатор"
        ADMIN = "admin", "Администратор"

    # Роли, которые пользователь может выбрать сам. jury и admin выдаёт только админ.
    SELF_ASSIGNABLE_ROLES = (Role.PARTICIPANT, Role.ORGANIZER)

    email = models.EmailField("email", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PARTICIPANT)
    is_email_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to="avatars/", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile({self.user.email})"