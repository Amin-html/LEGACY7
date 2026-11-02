from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsEmailVerified, IsOrganizer, IsParticipant
from apps.contests.manage_serializers import LOCKED_STATUSES
from apps.contests.models import Contest

from .models import Submission
from .serializers import (
    ManageSubmissionSerializer,
    ModerateSerializer,
    PublicSubmissionSerializer,
    SubmissionSerializer,
)

User = get_user_model()


class MySubmissionViewSet(viewsets.ModelViewSet):
    """Кабинет участника: только свои работы."""

    serializer_class = SubmissionSerializer
    permission_classes = [IsParticipant]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_fields = ("status",)
    ordering_fields = ("created_at", "submitted_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        # Чужие работы недоступны ни по какому ID: для них просто 404
        return Submission.objects.filter(author=self.request.user).select_related("contest")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        submission = self.get_object()
        if not submission.is_editable:
            return Response(
                {"detail": "Эту работу уже нельзя отозвать."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submission.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsParticipant, IsEmailVerified])
    def submit(self, request, pk=None):
        submission = self.get_object()
        if submission.status != Submission.Status.DRAFT:
            return Response(
                {"detail": "Работа уже подана."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not submission.contest.is_open:
            return Response(
                {"detail": "Приём работ в этом конкурсе закрыт."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not submission.description.strip():
            return Response(
                {"detail": "Добавь описание работы."}, status=status.HTTP_400_BAD_REQUEST
            )
        submission.status = Submission.Status.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save(update_fields=["status", "submitted_at", "updated_at"])
        return Response(self.get_serializer(submission).data)


class ManageContestSubmissionsView(generics.ListAPIView):
    """Работы одного конкурса для его организатора. Черновики участников не видны."""

    serializer_class = ManageSubmissionSerializer
    permission_classes = [IsOrganizer]
    filterset_fields = ("status",)
    search_fields = ("title", "author__username")
    ordering_fields = ("submitted_at",)
    ordering = ("-submitted_at",)

    def get_queryset(self):
        user = self.request.user
        contests = (
            Contest.objects.all()
            if user.role == User.Role.ADMIN
            else Contest.objects.filter(organizer=user)
        )
        contest = get_object_or_404(contests, pk=self.kwargs["contest_id"])
        return contest.submissions.exclude(status=Submission.Status.DRAFT).select_related(
            "author"
        )


class ModerateSubmissionView(APIView):
    permission_classes = [IsOrganizer]

    def post(self, request, pk):
        user = request.user
        qs = Submission.objects.select_related("contest", "author")
        if user.role != User.Role.ADMIN:
            qs = qs.filter(contest__organizer=user)  # чужая работа: 404
        submission = get_object_or_404(qs, pk=pk)

        serializer = ModerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if submission.contest.status in LOCKED_STATUSES:
            return Response(
                {"detail": "Конкурс завершён или в архиве."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_status = (
            Submission.Status.ACCEPTED
            if data["action"] == "accept"
            else Submission.Status.REJECTED
        )
        # Атомарно: два организатора не перезапишут решение друг друга
        updated = Submission.objects.filter(
            pk=submission.pk, status=Submission.Status.SUBMITTED
        ).update(
            status=new_status,
            moderation_comment=data.get("comment", "").strip(),
            updated_at=timezone.now(),
        )
        if not updated:
            return Response(
                {"detail": "Модерировать можно только работы на проверке."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submission.refresh_from_db()
        return Response(ManageSubmissionSerializer(submission).data)


class PublicSubmissionListView(generics.ListAPIView):
    """Витрина принятых работ. Доступна, только если организатор её включил."""

    serializer_class = PublicSubmissionSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = []

    def get_queryset(self):
        contest = get_object_or_404(
            Contest.objects.filter(
                status__in=Contest.PUBLIC_STATUSES, public_submissions=True
            ),
            slug=self.kwargs["slug"],
        )
        return (
            contest.submissions.filter(status=Submission.Status.ACCEPTED)
            .select_related("author")
            .order_by("-submitted_at")
        )