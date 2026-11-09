from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsParticipant
from apps.common.uploads import (
    KINDS,
    SUBMISSION_KINDS,
    display_name,
    inspect_upload,
    max_bytes,
    random_name,
)
from apps.contests.models import Contest

from .models import Submission
from .serializers import SubmissionSerializer


def can_view_submission_file(user, submission):
    """Кто может скачать файл. В коммите про жюри сюда добавятся назначенные судьи."""
    contest = submission.contest
    if (
        submission.status == Submission.Status.ACCEPTED
        and contest.public_submissions
        and contest.status in Contest.PUBLIC_STATUSES
    ):
        return True
    if not user.is_authenticated:
        return False
    if user.role == User.Role.ADMIN or user.pk == submission.author_id:
        return True
    # Организатор видит файлы только поданных работ своего конкурса, но не черновики
    return contest.organizer_id == user.pk and submission.status != Submission.Status.DRAFT


class SubmissionFileUploadView(APIView):
    """Автор прикрепляет, заменяет и удаляет файл своей работы."""

    permission_classes = [IsParticipant]
    parser_classes = [MultiPartParser]

    def _submission(self, request, pk):
        qs = Submission.objects.select_related("contest").filter(author=request.user)
        return get_object_or_404(qs, pk=pk)  # чужая работа: 404

    def post(self, request, pk):
        submission = self._submission(request, pk)
        if not submission.is_editable:
            return Response(
                {"detail": "Эту работу уже нельзя редактировать."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": ["Прикрепи файл."]})
        try:
            kind = inspect_upload(
                upload, SUBMISSION_KINDS, max_bytes("SUBMISSION_FILE_MAX_MB")
            )
        except ValidationError as exc:
            raise ValidationError({"file": exc.detail})

        old_name = submission.file.name
        shown_name = display_name(upload.name, kind)
        upload.name = random_name(kind)  # в хранилище пишем под случайным именем
        submission.file = upload
        submission.file_name = shown_name
        submission.file_type = KINDS[kind][1]
        submission.file_size = upload.size
        submission.save(
            update_fields=["file", "file_name", "file_type", "file_size", "updated_at"]
        )
        if old_name and old_name != submission.file.name:
            submission.file.storage.delete(old_name)
        return Response(SubmissionSerializer(submission, context={"request": request}).data)

    def delete(self, request, pk):
        submission = self._submission(request, pk)
        if not submission.is_editable:
            return Response(
                {"detail": "Эту работу уже нельзя редактировать."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if submission.file:
            submission.file.delete(save=False)
        submission.file_name = submission.file_type = ""
        submission.file_size = 0
        submission.save(update_fields=["file", "file_name", "file_type", "file_size", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmissionFileDownloadView(APIView):
    permission_classes = [permissions.AllowAny]  # права проверяем ниже

    def get(self, request, pk):
        submission = get_object_or_404(Submission.objects.select_related("contest"), pk=pk)
        # Нет файла и нет доступа: один и тот же 404, чтобы не раскрывать существование
        if not submission.file or not can_view_submission_file(request.user, submission):
            raise Http404
        try:
            handle = submission.file.open("rb")
        except FileNotFoundError:
            raise Http404
        inline = submission.file_type.startswith("image/") or submission.file_type == "video/mp4"
        response = FileResponse(
            handle,
            content_type=submission.file_type,  # наш тип, а не угаданный браузером
            as_attachment=not inline,
            filename=submission.file_name,
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        response["Cache-Control"] = "private, max-age=300"
        return response