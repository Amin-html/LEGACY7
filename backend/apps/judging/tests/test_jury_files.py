import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.common.tests.helpers import png_bytes
from apps.contests.models import Contest
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
S = Submission.Status


def attach(sub):
    data = png_bytes()
    sub.file.save("a.png", ContentFile(data), save=False)
    sub.file_name, sub.file_type, sub.file_size = "a.png", "image/png", len(data)
    sub.save()
    return sub


def download(api, sub):
    return api.get(reverse("submission-file", args=[sub.pk]))


def test_assigned_judge_downloads_file(jury_api, sub):
    assert download(jury_api, attach(sub)).status_code == 200


def test_judge_keeps_access_after_contest_is_finished(jury_api, contest, sub):
    attach(sub)
    contest.status = Contest.Status.FINISHED
    contest.save()
    assert download(jury_api, sub).status_code == 200


def test_unassigned_judge_gets_404(api, make_user, sub):
    attach(sub)
    api.force_authenticate(make_user(role="jury"))
    assert download(api, sub).status_code == 404


def test_judge_cannot_download_work_that_is_not_accepted(jury_api, contest, make_sub):
    hidden = attach(make_sub(contest, status=S.SUBMITTED))
    assert download(jury_api, hidden).status_code == 404