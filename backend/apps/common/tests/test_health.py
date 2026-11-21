from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_is_public_and_ok(client):
    r = client.get(reverse("health"))
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_reports_503_when_database_is_down(client):
    with patch("apps.common.views.connection") as conn:
        conn.ensure_connection.side_effect = OperationalError("db down")
        r = client.get(reverse("health"))
    assert r.status_code == 503
    assert r.json() == {"status": "error"}