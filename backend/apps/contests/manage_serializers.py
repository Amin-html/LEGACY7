from django.db import transaction
from rest_framework import serializers

from .models import Contest, JudgingCriterion, Prize
from .serializers import CriterionSerializer, PrizeSerializer

# В этих статусах конкурс «заморожен»: править нельзя
LOCKED_STATUSES = (Contest.Status.FINISHED, Contest.Status.ARCHIVED)


class ContestManageSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    prizes = PrizeSerializer(many=True, required=False)
    criteria = CriterionSerializer(many=True, required=False)

    class Meta:
        model = Contest
        fields = (
            "id", "slug", "title", "description", "rules", "category", "category_name",
            "status", "is_open", "starts_at", "deadline", "currency", "public_submissions",
            "prizes", "criteria", "created_at", "updated_at",
        )
        # status меняется только через publish/archive, slug стабилен
        read_only_fields = ("id", "slug", "status", "created_at", "updated_at")

    def validate_prizes(self, value):
        places = [p["place"] for p in value]
        if len(places) != len(set(places)):
            raise serializers.ValidationError("Места призов не должны повторяться.")
        if any(p["place"] < 1 for p in value):
            raise serializers.ValidationError("Место должно быть 1 или больше.")
        if any(p["amount"] <= 0 for p in value):
            raise serializers.ValidationError("Сумма приза должна быть больше нуля.")
        return value

    def validate_criteria(self, value):
        titles = [c["title"].strip().lower() for c in value]
        if len(titles) != len(set(titles)):
            raise serializers.ValidationError("Названия критериев не должны повторяться.")
        for c in value:
            if not 1 <= c.get("max_score", 10) <= 100:
                raise serializers.ValidationError("Максимальный балл: от 1 до 100.")
            if c.get("weight", 1) <= 0:
                raise serializers.ValidationError("Вес критерия должен быть больше нуля.")
        return value

    def validate(self, attrs):
        instance = self.instance
        starts = attrs.get("starts_at", getattr(instance, "starts_at", None))
        deadline = attrs.get("deadline", getattr(instance, "deadline", None))
        if starts and deadline and deadline <= starts:
            raise serializers.ValidationError(
                {"deadline": "Дедлайн должен быть позже даты старта."}
            )
        if instance is not None:
            if instance.status in LOCKED_STATUSES:
                raise serializers.ValidationError(
                    "Конкурс завершён или в архиве: редактирование недоступно."
                )
            if instance.status != Contest.Status.DRAFT and (
                "prizes" in attrs or "criteria" in attrs
            ):
                raise serializers.ValidationError(
                    "Призы и критерии можно менять только в черновике."
                )
        return attrs

    @staticmethod
    def _replace_children(contest, prizes, criteria):
        if prizes is not None:
            contest.prizes.all().delete()
            Prize.objects.bulk_create([Prize(contest=contest, **p) for p in prizes])
        if criteria is not None:
            contest.criteria.all().delete()
            JudgingCriterion.objects.bulk_create(
                [JudgingCriterion(contest=contest, **c) for c in criteria]
            )

    @staticmethod
    def _fresh(pk):
        # Свежий объект, чтобы в ответе не остались старые призы из кэша
        return (
            Contest.objects.select_related("category")
            .prefetch_related("prizes", "criteria")
            .get(pk=pk)
        )

    @transaction.atomic
    def create(self, validated_data):
        prizes = validated_data.pop("prizes", None)
        criteria = validated_data.pop("criteria", None)
        contest = Contest.objects.create(**validated_data)
        self._replace_children(contest, prizes, criteria)
        return self._fresh(contest.pk)

    @transaction.atomic
    def update(self, instance, validated_data):
        prizes = validated_data.pop("prizes", None)
        criteria = validated_data.pop("criteria", None)
        instance = super().update(instance, validated_data)
        self._replace_children(instance, prizes, criteria)
        return self._fresh(instance.pk)


class JurySerializer(serializers.Serializer):
    judge_id = serializers.IntegerField(source="judge.id", read_only=True)
    username = serializers.CharField(source="judge.username", read_only=True)


class JuryAssignSerializer(serializers.Serializer):
    email = serializers.EmailField()