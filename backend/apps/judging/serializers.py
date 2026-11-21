from rest_framework import serializers

from apps.contests.serializers import CriterionSerializer
from apps.submissions.models import Submission
from apps.submissions.serializers import FILE_FIELDS, FileInfoMixin

from .models import Evaluation, EvaluationScore


class ScoreOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationScore
        fields = ("criterion", "score")


class EvaluationSerializer(serializers.ModelSerializer):
    scores = ScoreOutSerializer(many=True, read_only=True)

    class Meta:
        model = Evaluation
        fields = ("status", "comment", "total", "finalized_at", "scores")


class ScoreInSerializer(serializers.Serializer):
    criterion = serializers.IntegerField()
    score = serializers.IntegerField(min_value=0)


class EvaluationInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    scores = ScoreInSerializer(many=True, required=False)

    def validate_scores(self, value):
        ids = [s["criterion"] for s in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Критерии не должны повторяться.")
        criteria = {c.id: c for c in self.context["criteria"]}
        for item in value:
            criterion = criteria.get(item["criterion"])
            if criterion is None:
                raise serializers.ValidationError("Критерий не относится к этому конкурсу.")
            if item["score"] > criterion.max_score:
                raise serializers.ValidationError(
                    f"Балл по критерию «{criterion.title}» не больше {criterion.max_score}."
                )
        return value


class JurySubmissionListSerializer(serializers.ModelSerializer):
    """Слепое судейство: автора здесь нет."""

    contest_title = serializers.CharField(source="contest.title", read_only=True)
    my_status = serializers.CharField(read_only=True)  # none / draft / final

    class Meta:
        model = Submission
        fields = ("id", "contest", "contest_title", "title", "my_status")


class JurySubmissionDetailSerializer(FileInfoMixin, serializers.ModelSerializer):
    contest_title = serializers.CharField(source="contest.title", read_only=True)
    criteria = CriterionSerializer(source="contest.criteria", many=True, read_only=True)
    my_status = serializers.CharField(read_only=True)
    my_evaluation = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = (
            "id", "contest", "contest_title", "title", "description", "link",
            "my_status", "criteria", "my_evaluation",
        ) + FILE_FIELDS

    def get_my_evaluation(self, obj):
        evaluation = (
            Evaluation.objects.filter(submission=obj, judge=self.context["request"].user)
            .prefetch_related("scores")
            .first()
        )
        return EvaluationSerializer(evaluation).data if evaluation else None