import re
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from apps.common.tests.helpers import (
    image_bytes,
    jpeg_bytes,
    mp4_bytes,
    pdf_bytes,
    png_bytes,
    upload,
)
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
S = Submission.Status
FILE = "my-submission-file"
DOWNLOAD = "submission-file"


def put(api, sub, f):
    return api.post(reverse(FILE, args=[sub.pk]), {"file": f}, format="multipart")


def attach(sub, content=None, name="a.png", mime="image/png"):
    """Кладёт файл прямо в работу, минуя API."""
    content = content or png_bytes()
    sub.file.save(name, ContentFile(content), save=False)
    sub.file_name, sub.file_type, sub.file_size = name, mime, len(content)
    sub.save()
    return sub


def body(response):
    return b"".join(response.streaming_content)


@pytest.fixture
def draft(me, participant, make_submission):
    return make_submission(participant, status=S.DRAFT, submitted_at=None)


# ---------- загрузка ----------

def test_png_is_stored_privately_under_random_name(me, draft, settings):
    data = png_bytes()
    r = put(me, draft, upload("photo.png", data, "image/png"))
    assert r.status_code == 200, r.data
    assert r.data["has_file"] is True
    assert r.data["file_name"] == "photo.png"
    assert r.data["file_type"] == "image/png"
    assert r.data["file_size"] == len(data)
    assert "file" not in r.data  # путь на диске наружу не отдаём
    draft.refresh_from_db()
    stored = Path(draft.file.path).resolve()
    assert stored.exists()
    assert Path(settings.PRIVATE_MEDIA_ROOT).resolve() in stored.parents
    assert Path(settings.MEDIA_ROOT).resolve() not in stored.parents
    assert re.fullmatch(r"[0-9a-f]{32}", stored.stem)


@pytest.mark.parametrize(
    "name,maker,mime",
    [
        ("a.png", png_bytes, "image/png"),
        ("a.jpg", jpeg_bytes, "image/jpeg"),
        ("a.webp", lambda: image_bytes("WEBP"), "image/webp"),
        ("a.pdf", pdf_bytes, "application/pdf"),
        ("a.mp4", mp4_bytes, "video/mp4"),
    ],
)
def test_allowed_types_are_accepted(me, draft, name, maker, mime):
    r = put(me, draft, upload(name, maker()))  # content_type намеренно безликий
    assert r.status_code == 200, r.data
    assert r.data["file_type"] == mime


@pytest.mark.parametrize(
    "name,content,claimed",
    [
        ("virus.png", b"MZ\x90\x00" + b"\x00" * 100, "image/png"),
        ("page.png", b"<html><script>alert(1)</script></html>", "image/png"),
        ("pic.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "image/svg+xml"),
        ("fake.png", b"\x89PNG\r\n\x1a\n" + b"garbage" * 10, "image/png"),
        ("fake.jpg", b"\xff\xd8\xff" + b"garbage" * 10, "image/jpeg"),
        ("notes.txt", b"hello", "text/plain"),
        ("anim.gif", b"GIF89a" + b"\x00" * 20, "image/gif"),
        ("empty.png", b"", "image/png"),
    ],
)
def test_fake_and_forbidden_files_are_rejected(me, draft, name, content, claimed):
    r = put(me, draft, upload(name, content, claimed))
    assert r.status_code == 400
    assert "file" in r.data
    draft.refresh_from_db()
    assert not draft.file


def test_image_bomb_is_rejected(me, draft):
    bomb = image_bytes("PNG", (10000, 10000), "1")  # 100 мегапикселей, а весит копейки
    assert len(bomb) < 1024 * 1024
    r = put(me, draft, upload("bomb.png", bomb, "image/png"))
    assert r.status_code == 400
    draft.refresh_from_db()
    assert not draft.file


def test_too_big_file_is_rejected(me, draft, settings):
    settings.SUBMISSION_FILE_MAX_MB = 1
    r = put(me, draft, upload("big.pdf", pdf_bytes(extra=1024 * 1024), "application/pdf"))
    assert r.status_code == 400
    draft.refresh_from_db()
    assert not draft.file


def test_missing_file_field_is_rejected(me, draft):
    r = me.post(reverse(FILE, args=[draft.pk]), {}, format="multipart")
    assert r.status_code == 400
    assert "file" in r.data


def test_real_type_wins_over_extension_and_content_type(me, draft):
    r = put(me, draft, upload("photo.png", jpeg_bytes(), "image/png"))  # JPEG под видом PNG
    assert r.status_code == 200
    assert r.data["file_type"] == "image/jpeg"
    assert r.data["file_name"] == "photo.jpg"


def test_path_traversal_in_filename_is_harmless(me, draft, settings):
    r = put(me, draft, upload("../../etc/passwd.png", png_bytes(), "image/png"))
    assert r.status_code == 200
    assert r.data["file_name"] == "passwd.png"
    draft.refresh_from_db()
    stored = Path(draft.file.path).resolve()
    assert Path(settings.PRIVATE_MEDIA_ROOT).resolve() in stored.parents
    assert "passwd" not in stored.name


def test_replace_removes_the_old_file(me, draft):
    put(me, draft, upload("a.png", png_bytes()))
    draft.refresh_from_db()
    first = Path(draft.file.path)
    r = put(me, draft, upload("b.pdf", pdf_bytes()))
    assert r.status_code == 200
    draft.refresh_from_db()
    second = Path(draft.file.path)
    assert second.exists() and not first.exists() and first != second
    assert draft.file_type == "application/pdf"


def test_delete_file(me, draft):
    put(me, draft, upload("a.png", png_bytes()))
    draft.refresh_from_db()
    path = Path(draft.file.path)
    assert me.delete(reverse(FILE, args=[draft.pk])).status_code == 204
    draft.refresh_from_db()
    assert not draft.file
    assert (draft.file_name, draft.file_type, draft.file_size) == ("", "", 0)
    assert not path.exists()


def test_file_metadata_cannot_be_written_through_patch(me, participant, make_submission):
    sub = attach(make_submission(participant))
    r = me.patch(
        reverse("my-submission-detail", args=[sub.pk]),
        {"file_name": "evil.html", "file_type": "text/html", "file_size": 1},
        format="json",
    )
    assert r.status_code == 200
    sub.refresh_from_db()
    assert (sub.file_name, sub.file_type) == ("a.png", "image/png")
    assert sub.file_size != 1


def test_withdrawing_submission_deletes_its_file(me, participant, make_submission):
    sub = attach(make_submission(participant))
    path = Path(sub.file.path)
    assert path.exists()
    assert me.delete(reverse("my-submission-detail", args=[sub.pk])).status_code == 204
    assert not path.exists()


# ---------- кто может менять файл ----------

@pytest.mark.parametrize("method", ["post", "delete"])
def test_foreign_submission_file_is_404(me, make_user, make_submission, method):
    foreign = make_submission(make_user(), status=S.DRAFT, submitted_at=None)
    url = reverse(FILE, args=[foreign.pk])
    if method == "post":
        r = me.post(url, {"file": upload("a.png", png_bytes())}, format="multipart")
    else:
        r = me.delete(url)
    assert r.status_code == 404
    foreign.refresh_from_db()
    assert not foreign.file


def test_closed_contest_blocks_file_changes(me, participant, make_submission):
    sub = make_submission(participant)
    now = timezone.now()
    sub.contest.starts_at, sub.contest.deadline = now - timedelta(days=30), now - timedelta(days=1)
    sub.contest.save()
    assert put(me, sub, upload("a.png", png_bytes())).status_code == 400


@pytest.mark.parametrize("final", [S.ACCEPTED, S.REJECTED])
def test_moderated_work_file_is_locked(me, participant, make_submission, final):
    sub = make_submission(participant, status=final)
    assert put(me, sub, upload("a.png", png_bytes())).status_code == 400


@pytest.mark.parametrize("role", ["organizer", "jury"])
def test_other_roles_cannot_upload(api, make_user, make_submission, role):
    sub = make_submission(make_user(), status=S.DRAFT, submitted_at=None)
    api.force_authenticate(make_user(role=role))
    assert put(api, sub, upload("a.png", png_bytes())).status_code == 403


def test_anonymous_cannot_upload(api, make_submission, make_user):
    sub = make_submission(make_user())
    assert put(api, sub, upload("a.png", png_bytes())).status_code == 401


# ---------- скачивание ----------

@pytest.fixture
def author(make_user):
    return make_user(role="participant", is_email_verified=True)


@pytest.fixture
def organizer(make_user):
    return make_user(role="organizer", is_email_verified=True)


@pytest.fixture
def contest(make_contest, organizer):
    return make_contest(organizer=organizer)


def test_author_downloads_image_inline_with_safe_headers(api, author, contest, make_submission):
    data = png_bytes()
    sub = attach(make_submission(author, contest=contest), data, "photo.png")
    api.force_authenticate(author)
    r = api.get(reverse(DOWNLOAD, args=[sub.pk]))
    assert r.status_code == 200
    assert body(r) == data
    assert r["Content-Type"] == "image/png"
    assert r["X-Content-Type-Options"] == "nosniff"
    assert "sandbox" in r["Content-Security-Policy"]
    assert r["Content-Disposition"].startswith("inline")


def test_pdf_is_always_an_attachment(api, author, contest, make_submission):
    sub = attach(make_submission(author, contest=contest), pdf_bytes(), "report.pdf", "application/pdf")
    api.force_authenticate(author)
    r = api.get(reverse(DOWNLOAD, args=[sub.pk]))
    assert r.status_code == 200
    assert r["Content-Disposition"].startswith("attachment")


def test_anonymous_and_strangers_get_404(api, make_user, author, contest, make_submission):
    sub = attach(make_submission(author, contest=contest))
    url = reverse(DOWNLOAD, args=[sub.pk])
    assert api.get(url).status_code == 404
    api.force_authenticate(make_user(role="participant"))
    assert api.get(url).status_code == 404
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    assert api.get(url).status_code == 404


def test_contest_organizer_sees_submitted_file_but_not_draft(api, organizer, author, contest, make_submission):
    submitted = attach(make_submission(author, contest=contest))
    other_author = organizer.__class__.objects.create_user(
        email="other@example.com", username="other", password="Str0ng-Pass-123"
    )
    draft = attach(make_submission(other_author, contest=contest, status=S.DRAFT, submitted_at=None))
    api.force_authenticate(organizer)
    assert api.get(reverse(DOWNLOAD, args=[submitted.pk])).status_code == 200
    assert api.get(reverse(DOWNLOAD, args=[draft.pk])).status_code == 404


def test_admin_can_download_any_file(api, make_user, author, contest, make_submission):
    sub = attach(make_submission(author, contest=contest, status=S.DRAFT, submitted_at=None))
    api.force_authenticate(make_user(role="admin"))
    assert api.get(reverse(DOWNLOAD, args=[sub.pk])).status_code == 200


@pytest.mark.parametrize(
    "status,public,expected",
    [
        (S.ACCEPTED, True, 200),
        (S.ACCEPTED, False, 404),
        (S.SUBMITTED, True, 404),
        (S.REJECTED, True, 404),
    ],
)
def test_public_access_only_for_accepted_work_on_public_showcase(
    api, make_contest, make_user, make_submission, status, public, expected
):
    sub = attach(make_submission(make_user(), contest=make_contest(public_submissions=public), status=status))
    assert api.get(reverse(DOWNLOAD, args=[sub.pk])).status_code == expected


def test_submission_without_file_is_404(api, author, contest, make_submission):
    sub = make_submission(author, contest=contest)
    api.force_authenticate(author)
    assert api.get(reverse(DOWNLOAD, args=[sub.pk])).status_code == 404