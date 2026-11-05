from urllib.parse import urlparse

from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.contests.models import Contest

from .models import Submission

DUPLICATE = "Ты уже подал работу на этот конкурс."


class SubmissionSerializer(serializers.ModelSerializer):
    """Работа глазами автора."""

    contest = serializers.SlugRelatedField(
        slug_field="slug", queryset=Contest.objects.filter(status=Contest.Status.PUBLISHED)
    )
    contest_title = serializers.CharField(source="contest.title", read_only=True)
    contest_deadline = serializers.DateTimeField(source="contest.deadline", read_only=True)
    can_edit = serializers.BooleanField(source="is_editable", read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id", "contest", "contest_title", "contest_deadline", "title", "description",
            "link", "status", "moderation_comment", "can_edit", "submitted_at",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "status", "moderation_comment", "submitted_at", "created_at", "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Конкурс выбирается один раз при создании, перенести работу в другой нельзя
        if self.instance is not None:
            self.fields["contest"].read_only = True

    def validate_link(self, value):
        # DRF подменяет валидатор из модели на мягкий, поэтому схему проверяем тут
        if value and urlparse(value).scheme.lower() not in ("http", "https"):
            raise serializers.ValidationError("Разрешены только ссылки http и https.")
        return value

    def validate_contest(self, contest):
        if not contest.is_open:
            raise serializers.ValidationError("Конкурс сейчас не принимает работы.")
        return contest

    def validate(self, attrs):
        if self.instance is None:
            user = self.context["request"].user
            if Submission.objects.filter(contest=attrs["contest"], author=user).exists():
                raise serializers.ValidationError({"contest": [DUPLICATE]})
        elif not self.instance.is_editable:
            raise serializers.ValidationError("Эту работу уже нельзя редактировать.")
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:  # две одновременные заявки
            raise serializers.ValidationError({"contest": [DUPLICATE]})


class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class ManageSubmissionSerializer(serializers.ModelSerializer):
    """Работа глазами организатора."""

    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = (
            "id", "author", "title", "description", "link", "status",
            "moderation_comment", "submitted_at",
        )


class PublicSubmissionSerializer(serializers.ModelSerializer):
    """Публичная витрина: только имя автора, без email."""

    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Submission
        fields = ("id", "title", "description", "link", "author", "submitted_at")


class ModerateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject"])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs.get("comment", "").strip():
            raise serializers.ValidationError({"comment": "Укажи причину отклонения."})
        return attrs