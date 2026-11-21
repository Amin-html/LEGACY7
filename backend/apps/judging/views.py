from django.db import transaction
from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsJury
from apps.contests.models import Contest
from apps.submissions.models import Submission

from .models import Evaluation, EvaluationScore
from .serializers import (
    EvaluationInputSerializer,
    EvaluationSerializer,
    JurySubmissionDetailSerializer,
    JurySubmissionListSerializer,
)
from .services import compute_total

MY_STATUSES = ("none", "draft", "final")


def judge_submissions(user):
    """Работы, которые судья вправе оценивать: принятые, в его конкурсах, пока идёт оценивание.

    Всё остальное для него просто не существует (404).
    """
    mine = Evaluation.objects.filter(submission=OuterRef("pk"), judge=user)
    return (
        Submission.objects.filter(
            status=Submission.Status.ACCEPTED,
            contest__status=Contest.Status.JUDGING,
            contest__jury_assignments__judge=user,
        )
        .select_related("contest")
        .annotate(my_status=Coalesce(Subquery(mine.values("status")[:1]), Value("none")))
    )


class JuryContestListView(APIView):
    permission_classes = [IsJury]

    def get(self, request):
        user = request.user
        contests = Contest.objects.filter(
            status=Contest.Status.JUDGING, jury_assignments__judge=user
        ).order_by("deadline")
        data = []
        for contest in contests:
            mine = Evaluation.objects.filter(
                judge=user,
                submission__contest=contest,
                submission__status=Submission.Status.ACCEPTED,
            )
            data.append(
                {
                    "id": contest.id,
                    "slug": contest.slug,
                    "title": contest.title,
                    "deadline": contest.deadline,
                    "total": contest.submissions.filter(status=Submission.Status.ACCEPTED).count(),
                    "evaluated": mine.filter(status=Evaluation.Status.FINAL).count(),
                    "drafts": mine.filter(status=Evaluation.Status.DRAFT).count(),
                }
            )
        return Response(data)


class JurySubmissionListView(generics.ListAPIView):
    serializer_class = JurySubmissionListSerializer
    permission_classes = [IsJury]
    filterset_fields = ("contest",)
    search_fields = ("title",)
    ordering_fields = ("id",)
    ordering = ("id",)

    def get_queryset(self):
        qs = judge_submissions(self.request.user)
        wanted = self.request.query_params.get("my_status")
        if wanted in MY_STATUSES:
            qs = qs.filter(my_status=wanted)
        return qs


class JurySubmissionDetailView(generics.RetrieveAPIView):
    serializer_class = JurySubmissionDetailSerializer
    permission_classes = [IsJury]

    def get_queryset(self):
        return judge_submissions(self.request.user)


class EvaluationView(APIView):
    permission_classes = [IsJury]

    def get(self, request, pk):
        submission = get_object_or_404(judge_submissions(request.user), pk=pk)
        evaluation = (
            Evaluation.objects.filter(submission=submission, judge=request.user)
            .prefetch_related("scores")
            .first()
        )
        if evaluation is None:
            return Response(
                {"status": "none", "comment": "", "total": None, "finalized_at": None, "scores": []}
            )
        return Response(EvaluationSerializer(evaluation).data)

    def put(self, request, pk):
        """Сохраняет черновик. Присланные поля заменяются, неприсланные остаются как были."""
        submission = get_object_or_404(judge_submissions(request.user), pk=pk)
        criteria = list(submission.contest.criteria.all())
        serializer = EvaluationInputSerializer(data=request.data, context={"criteria": criteria})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            evaluation, _ = Evaluation.objects.get_or_create(
                submission=submission, judge=request.user
            )
            # Блокируем строку: подтверждение и правка не должны пересечься
            evaluation = Evaluation.objects.select_for_update().get(pk=evaluation.pk)
            if evaluation.status == Evaluation.Status.FINAL:
                return Response(
                    {"detail": "Оценка уже подтверждена и не меняется."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if "comment" in data:
                evaluation.comment = data["comment"].strip()
                evaluation.save(update_fields=["comment", "updated_at"])
            if "scores" in data:
                evaluation.scores.all().delete()
                EvaluationScore.objects.bulk_create(
                    [
                        EvaluationScore(
                            evaluation=evaluation, criterion_id=s["criterion"], score=s["score"]
                        )
                        for s in data["scores"]
                    ]
                )
                evaluation.save(update_fields=["updated_at"])
        evaluation.refresh_from_db()
        return Response(EvaluationSerializer(evaluation).data)


class FinalizeEvaluationView(APIView):
    permission_classes = [IsJury]

    def post(self, request, pk):
        submission = get_object_or_404(judge_submissions(request.user), pk=pk)
        criteria = list(submission.contest.criteria.all())

        with transaction.atomic():
            evaluation = (
                Evaluation.objects.select_for_update()
                .filter(submission=submission, judge=request.user)
                .first()
            )
            if evaluation is None:
                return Response(
                    {"detail": "Сначала поставь оценки."}, status=status.HTTP_400_BAD_REQUEST
                )
            if evaluation.status == Evaluation.Status.FINAL:
                return Response(
                    {"detail": "Оценка уже подтверждена."}, status=status.HTTP_400_BAD_REQUEST
                )
            scores = {s.criterion_id: s.score for s in evaluation.scores.all()}
            missing = [c.title for c in criteria if c.id not in scores]
            if missing:
                return Response(
                    {"detail": "Не выставлены баллы: " + ", ".join(missing) + "."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            evaluation.total = compute_total(criteria, scores)
            evaluation.status = Evaluation.Status.FINAL
            evaluation.finalized_at = timezone.now()
            evaluation.save()
        return Response(EvaluationSerializer(evaluation).data)