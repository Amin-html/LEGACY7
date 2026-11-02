from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.accounts.permissions import (
    IsAdminRole,
    IsEmailVerified,
    IsJury,
    IsOrganizer,
    IsParticipant,
)

User = get_user_model()
R = User.Role

MATRIX = [
    (IsParticipant, {R.PARTICIPANT, R.ADMIN}),
    (IsJury, {R.JURY, R.ADMIN}),
    (IsOrganizer, {R.ORGANIZER, R.ADMIN}),
    (IsAdminRole, {R.ADMIN}),
]


def request_for(user):
    return SimpleNamespace(user=user)


@pytest.mark.parametrize("perm,allowed", MATRIX)
@pytest.mark.parametrize("role", list(R))
def test_role_matrix(perm, allowed, role):
    user = User(email="x@example.com", role=role)
    assert perm().has_permission(request_for(user), None) == (role in allowed)


@pytest.mark.parametrize("perm,_", MATRIX)
def test_anonymous_is_denied_everywhere(perm, _):
    assert perm().has_permission(request_for(AnonymousUser()), None) is False


def test_email_verified_permission():
    verified = User(email="a@example.com", is_email_verified=True)
    unverified = User(email="b@example.com", is_email_verified=False)
    assert IsEmailVerified().has_permission(request_for(verified), None) is True
    assert IsEmailVerified().has_permission(request_for(unverified), None) is False