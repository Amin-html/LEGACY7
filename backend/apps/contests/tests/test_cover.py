import os
import re
from pathlib import Path

import pytest
from django.urls import reverse
from PIL import Image

from apps.common.tests.helpers import mp4_bytes, pdf_bytes, png_bytes, upload
from apps.contests.models import Contest

pytestmark = pytest.mark.django_db
COVER = "manage-contest-cover"


@pytest.fixture
def organizer(make_user):
    return make_user(role="organizer", is_email_verified=True)


@pytest.fixture
def contest(make_contest, organizer):
    return make_contest(organizer=organizer)


@pytest.fixture
def org_api(api, organizer):
    api.force_authenticate(organizer)
    return api


def put(api, contest, f):
    return api.post(reverse(COVER, args=[contest.pk]), {"file": f}, format="multipart")


def test_cover_is_resized_reencoded_and_randomly_named(org_api, contest):
    r = put(org_api, contest, upload("my cover.png", png_bytes((3000, 2000)), "image/png"))
    assert r.status_code == 200, r.data
    contest.refresh_from_db()
    path = Path(contest.cover.path)
    assert path.exists()
    assert re.fullmatch(r"[0-9a-f]{32}\.webp", path.name)
    with Image.open(path) as img:
        assert img.format == "WEBP"
        assert max(img.size) == 1600
    assert r.data["cover"].endswith(path.name)


def test_cover_is_visible_in_public_detail(org_api, contest):
    put(org_api, contest, upload("c.png", png_bytes()))
    contest.refresh_from_db()
    detail = org_api.get(reverse("contest-detail", args=[contest.slug]))
    assert detail.data["cover"].endswith(Path(contest.cover.path).name)


@pytest.mark.parametrize(
    "name,content",
    [
        ("doc.pdf", pdf_bytes()),
        ("clip.mp4", mp4_bytes()),
        ("pic.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>'),
        ("fake.png", b"\x89PNG\r\n\x1a\n" + b"garbage" * 10),
        ("page.png", b"<html>hi</html>"),
    ],
)
def test_only_real_images_are_accepted_as_cover(org_api, contest, name, content):
    r = put(org_api, contest, upload(name, content, "image/png"))
    assert r.status_code == 400
    assert "file" in r.data
    contest.refresh_from_db()
    assert not contest.cover


def test_too_big_cover_is_rejected(org_api, contest, settings):
    settings.COVER_MAX_MB = 1
    big = b"\x89PNG\r\n\x1a\n" + os.urandom(1024 * 1024)
    assert put(org_api, contest, upload("big.png", big, "image/png")).status_code == 400


def test_replace_and_delete_remove_files_from_disk(org_api, contest):
    put(org_api, contest, upload("a.png", png_bytes()))
    contest.refresh_from_db()
    first = Path(contest.cover.path)
    put(org_api, contest, upload("b.png", png_bytes()))
    contest.refresh_from_db()
    second = Path(contest.cover.path)
    assert second.exists() and not first.exists()
    assert org_api.delete(reverse(COVER, args=[contest.pk])).status_code == 204
    contest.refresh_from_db()
    assert not contest.cover
    assert not second.exists()


def test_cover_cannot_be_set_through_manage_patch(org_api, contest):
    r = org_api.patch(reverse("manage-contest-detail", args=[contest.pk]), {"cover": "hack.png"}, format="json")
    assert r.status_code == 200
    contest.refresh_from_db()
    assert not contest.cover


def test_anonymous_gets_401(api, contest):
    assert put(api, contest, upload("a.png", png_bytes())).status_code == 401


def test_participant_gets_403(api, make_user, contest):
    api.force_authenticate(make_user(role="participant"))
    assert put(api, contest, upload("a.png", png_bytes())).status_code == 403


def test_other_organizers_contest_is_404(api, make_user, contest):
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    assert put(api, contest, upload("a.png", png_bytes())).status_code == 404
    contest.refresh_from_db()
    assert not contest.cover


def test_archived_contest_cover_is_locked(org_api, organizer, make_contest):
    archived = make_contest(organizer=organizer, status=Contest.Status.ARCHIVED)
    assert put(org_api, archived, upload("a.png", png_bytes())).status_code == 400