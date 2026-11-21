import uuid

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsOrganizer
from apps.common.uploads import IMAGE_KINDS, inspect_upload, max_bytes, to_webp

from .manage_serializers import LOCKED_STATUSES
from .models import Contest


class ContestCoverView(APIView):
    """Обложка конкурса. Её меняет только организатор этого конкурса (или админ)."""

    permission_classes = [IsOrganizer]
    parser_classes = [MultiPartParser]

    def _contest(self, request, pk):
        qs = Contest.objects.all()
        if request.user.role != User.Role.ADMIN:
            qs = qs.filter(organizer=request.user)  # чужой конкурс: 404
        contest = get_object_or_404(qs, pk=pk)
        if contest.status in LOCKED_STATUSES:
            raise ValidationError("Конкурс завершён или в архиве: изменения недоступны.")
        return contest

    def post(self, request, pk):
        contest = self._contest(request, pk)
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": ["Прикрепи файл."]})
        try:
            inspect_upload(upload, IMAGE_KINDS, max_bytes("COVER_MAX_MB"))
            content = to_webp(upload)  # перекодируем: убираем EXIF и лишнее внутри файла
        except ValidationError as exc:
            raise ValidationError({"file": exc.detail})

        old_name = contest.cover.name
        contest.cover.save(f"{uuid.uuid4().hex}.webp", content, save=False)
        contest.save(update_fields=["cover", "updated_at"])
        if old_name:
            contest.cover.storage.delete(old_name)
        return Response({"cover": request.build_absolute_uri(contest.cover.url)})

    def delete(self, request, pk):
        contest = self._contest(request, pk)
        if contest.cover:
            contest.cover.delete(save=False)
            contest.cover = ""
            contest.save(update_fields=["cover", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)