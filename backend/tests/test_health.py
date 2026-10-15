from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.urls import reverse


@pytest.mark.django_db
def test_health_checks_postgresql(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_without_exposing_database_error(client):
    with patch("config.health.connection.cursor", side_effect=OperationalError("secret")):
        response = client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert b"secret" not in response.content


def test_health_is_read_only(client):
    assert client.post(reverse("health")).status_code == 405
