import pytest
from django.urls import reverse

from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
K = Notification.Kind
LIST, COUNT = "notification-list", "notification-unread-count"
READ, READ_ALL = "notification-read", "notification-read-all"


def create(user, title="Привет", **kw):
    return Notification.objects.create(user=user, kind=K.SUBMISSION_ACCEPTED, title=title, **kw)


def test_anonymous_gets_401(api):
    assert api.get(reverse(LIST)).status_code == 401
    assert api.get(reverse(COUNT)).status_code == 401
    assert api.post(reverse(READ_ALL)).status_code == 401
    assert api.post(reverse(READ, args=[1])).status_code == 401


@pytest.mark.parametrize("role", ["participant", "jury", "organizer", "admin"])
def test_every_role_has_a_mailbox(api, make_user, role):
    user = make_user(role=role)
    create(user)
    api.force_authenticate(user)
    assert api.get(reverse(LIST)).data["count"] == 1


def test_list_has_only_mine_newest_first_without_private_fields(api, make_user):
    me, other = make_user(), make_user()
    create(me, "Первое")
    create(me, "Второе")
    create(other, "Чужое")
    api.force_authenticate(me)
    r = api.get(reverse(LIST))
    assert [n["title"] for n in r.data["results"]] == ["Второе", "Первое"]
    assert "user" not in r.data["results"][0]
    assert other.email not in str(r.data)


def test_unread_filter_and_count(api, make_user):
    me = make_user()
    create(me, "Новое")
    create(me, "Старое", is_read=True)
    api.force_authenticate(me)
    assert [n["title"] for n in api.get(reverse(LIST), {"unread": "true"}).data["results"]] == ["Новое"]
    assert api.get(reverse(LIST)).data["count"] == 2
    assert api.get(reverse(COUNT)).data == {"unread": 1}


def test_mark_read(api, make_user):
    me = make_user()
    n = create(me)
    api.force_authenticate(me)
    r = api.post(reverse(READ, args=[n.pk]))
    assert r.status_code == 200
    assert r.data["is_read"] is True
    n.refresh_from_db()
    assert n.is_read is True
    assert api.post(reverse(READ, args=[n.pk])).status_code == 200  # повторный вызов безопасен


def test_foreign_notification_is_404_and_stays_unread(api, make_user):
    n = create(make_user())
    api.force_authenticate(make_user())
    assert api.post(reverse(READ, args=[n.pk])).status_code == 404
    n.refresh_from_db()
    assert n.is_read is False


def test_read_all_touches_only_my_notifications(api, make_user):
    me, other = make_user(), make_user()
    create(me)
    create(me)
    create(me, is_read=True)
    theirs = create(other)
    api.force_authenticate(me)
    assert api.post(reverse(READ_ALL)).data == {"updated": 2}
    assert api.get(reverse(COUNT)).data == {"unread": 0}
    theirs.refresh_from_db()
    assert theirs.is_read is False