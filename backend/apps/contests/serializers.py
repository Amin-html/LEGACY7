from rest_framework import serializers

from .models import Category, Contest, JudgingCriterion, Prize


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prize
        fields = ("place", "amount", "description")


class CriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JudgingCriterion
        fields = ("id", "title", "max_score", "weight")


class ContestListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    organizer = serializers.CharField(source="organizer.username", read_only=True)
    prize_pool = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contest
        fields = (
            "id", "slug", "title", "category", "organizer", "cover", "status",
            "is_open", "starts_at", "deadline", "prize_pool", "currency",
        )


class ContestDetailSerializer(ContestListSerializer):
    prizes = PrizeSerializer(many=True, read_only=True)
    criteria = CriterionSerializer(many=True, read_only=True)

    class Meta(ContestListSerializer.Meta):
        fields = ContestListSerializer.Meta.fields + (
            "description", "rules", "public_submissions", "prizes", "criteria",
        )