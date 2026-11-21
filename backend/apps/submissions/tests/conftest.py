import pytest
from django.utils import timezone

from apps.contests.tests.conftest import category, make_contest  # noqa: F401
from apps.submissions.models import Submission


@pytest.fixture
def participant(make_user):
    return make_user(role="participant", is_email_verified=True)


@pytest.fixture
def me(api, participant):
    """API-клиент, вошедший как участник."""
    api.force_authenticate(participant)
    return api


@pytest.fixture
def make_submission(db, make_contest):
    def factory(author, contest=None, **kw):
        defaults = dict(
            title="Моя работа",
            description="Описание работы",
            status=Submission.Status.SUBMITTED,
            submitted_at=timezone.now(),
        )
        defaults.update(kw)
        return Submission.objects.create(
            contest=contest or make_contest(), author=author, **defaults
        )

    return factory