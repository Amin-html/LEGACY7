from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsOrganizer

from .manage_serializers import (
    LOCKED_STATUSES,
    ContestManageSerializer,
    JuryAssignSerializer,
    JurySerializer,
)
from .models import Contest, ContestJury

User = get_user_model()
LOCKED_MESSAGE = "Конкурс завершён или в архиве: изменения недоступны."


class ManageContestViewSet(viewsets.ModelViewSet):
    serializer_class = ContestManageSerializer
    permission_classes = [IsOrganizer]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_fields = ("status",)
    search_fields = ("title",)
    ordering_fields = ("created_at", "starts_at", "deadline")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Contest.objects.select_related("category").prefetch_related("prizes", "criteria")
        user = self.request.user
        # Организатор видит только свои конкурсы, админ видит все.
        # Чужой ID даёт 404, а не 403: так не раскрываем, что он существует.
        return qs if user.role == User.Role.ADMIN else qs.filter(organizer=user)

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    def destroy(self, request, *args, **kwargs):
        contest = self.get_object()
        if contest.status != Contest.Status.DRAFT:
            return Response(
                {"detail": "Удалять можно только черновики. Остальные отправляй в архив."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        contest.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        contest = self.get_object()
        if contest.status != Contest.Status.DRAFT:
            return Response(
                {"detail": "Опубликовать можно только черновик."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.is_email_verified:
            return Response(
                {"detail": "Подтверди email, чтобы публиковать конкурсы."},
                status=status.HTTP_403_FORBIDDEN,
            )
        problems = []
        if not contest.criteria.exists():
            problems.append("Добавь хотя бы один критерий оценки.")
        if contest.deadline <= timezone.now():
            problems.append("Дедлайн уже прошёл.")
        if problems:
            return Response({"detail": problems}, status=status.HTTP_400_BAD_REQUEST)

        contest.status = Contest.Status.PUBLISHED
        contest.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(contest).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        contest = self.get_object()
        if contest.status == Contest.Status.ARCHIVED:
            return Response(
                {"detail": "Конкурс уже в архиве."}, status=status.HTTP_400_BAD_REQUEST
            )
        contest.status = Contest.Status.ARCHIVED
        contest.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(contest).data)

    @action(detail=True, methods=["get", "post"], url_path="jury", url_name="jury")
    def jury(self, request, pk=None):
        contest = self.get_object()
        if request.method == "GET":
            assignments = contest.jury_assignments.select_related("judge")
            return Response(JurySerializer(assignments, many=True).data)

        if contest.status in LOCKED_STATUSES:
            return Response({"detail": LOCKED_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
        serializer = JuryAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = User.objects.filter(
            email__iexact=serializer.validated_data["email"],
            role=User.Role.JURY,
            is_active=True,
        ).first()
        if judge is None:
            # Один и тот же ответ для «нет такого email» и «не судья»:
            # организатор не должен угадывать чужие адреса
            return Response(
                {"email": ["Судья с таким email не найден."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assignment, created = ContestJury.objects.get_or_create(contest=contest, judge=judge)
        return Response(
            JurySerializer(assignment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"jury/(?P<judge_id>[0-9]+)",
        url_name="jury-detail",
    )
    def jury_remove(self, request, pk=None, judge_id=None):
        contest = self.get_object()
        if contest.status in LOCKED_STATUSES:
            return Response({"detail": LOCKED_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = contest.jury_assignments.filter(judge_id=judge_id).delete()
        if not deleted:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)