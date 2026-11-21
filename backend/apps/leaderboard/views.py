from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsParticipant
from apps.contests.models import Category, Contest
from apps.judging.models import Evaluation, EvaluationScore
from apps.submissions.models import Submission

from .services import average, build_leaderboard, contest_results, fmt


class LeaderboardPagination(PageNumberPagination):
    page_size = 20


class LeaderboardView(APIView):
    """Общий рейтинг участников. ?category=<slug> даёт рейтинг по категории."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        category = None
        slug = request.query_params.get("category")
        if slug:
            category = get_object_or_404(Category, slug=slug)
        items = [
            {
                "place": i["place"],
                "user": {"id": i["user_id"], "username": i["username"]},
                "points": i["points"],
                "contests": i["contests"],
            }
            for i in build_leaderboard(category)
        ]
        paginator = LeaderboardPagination()
        page = paginator.paginate_queryset(items, request, view=self)
        return paginator.get_paginated_response(page)


class ContestResultsView(APIView):
    """Итоги завершённого конкурса."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        contest = get_object_or_404(
            Contest.objects.filter(status=Contest.Status.FINISHED), slug=slug
        )
        prizes = {p.place: p.amount for p in contest.prizes.all()}
        items = contest_results(contest)
        titles = {}
        if contest.public_submissions:
            titles = dict(
                Submission.objects.filter(pk__in=[i["submission_id"] for i in items]).values_list(
                    "id", "title"
                )
            )
        results = []
        for item in items:
            row = {
                "place": item["place"],
                "username": item["username"],
                "score": fmt(item["score"]),
                "points": item["points"],
                "prize": fmt(prizes[item["place"]]) if item["place"] in prizes else None,
            }
            if contest.public_submissions:  # названия работ только если витрина включена
                row["title"] = titles.get(item["submission_id"], "")
            results.append(row)
        return Response(
            {
                "contest": {"id": contest.id, "slug": contest.slug, "title": contest.title},
                "results": results,
            }
        )


class MySubmissionResultView(APIView):
    """Личный результат автора: балл, место, средние по критериям, комментарии жюри."""

    permission_classes = [IsParticipant]

    def get(self, request, pk):
        submission = get_object_or_404(
            Submission.objects.select_related("contest").filter(
                author=request.user,
                status=Submission.Status.ACCEPTED,
                contest__status=Contest.Status.FINISHED,
            ),
            pk=pk,
        )
        contest = submission.contest
        results = contest_results(contest)
        mine = next((r for r in results if r["submission_id"] == submission.id), None)
        if mine is None:
            return Response({"rated": False})

        evaluations = list(
            Evaluation.objects.filter(
                submission=submission,
                status=Evaluation.Status.FINAL,
                judge__jury_assignments__contest=contest,
            ).order_by("finalized_at")
        )
        scores = list(EvaluationScore.objects.filter(evaluation__in=evaluations))
        criteria = []
        for criterion in contest.criteria.all():
            avg = average([s.score for s in scores if s.criterion_id == criterion.id])
            criteria.append(
                {
                    "title": criterion.title,
                    "max_score": criterion.max_score,
                    "average": fmt(avg) if avg is not None else None,
                }
            )
        prize = contest.prizes.filter(place=mine["place"]).first()
        return Response(
            {
                "rated": True,
                "contest": {"slug": contest.slug, "title": contest.title},
                "score": fmt(mine["score"]),
                "points": mine["points"],
                "place": mine["place"],
                "participants": len(results),
                "prize": fmt(prize.amount) if prize else None,
                "criteria": criteria,
                # Имена судей не отдаём: комментарии анонимны
                "comments": [e.comment for e in evaluations if e.comment.strip()],
            }
        )