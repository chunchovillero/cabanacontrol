from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import Throttled

from apps.accounts.models import AuthThrottleBucket
from apps.accounts.throttling import consume_limit
from apps.audit.models import AuditEvent
from tests.conftest import csrf_token, login_client, select_company


@pytest.mark.django_db(transaction=True)
def test_bruteforce_limit_is_atomic_across_concurrent_requests():
    def attempt(_):
        close_old_connections()
        try:
            consume_limit("concurrent-test", "synthetic-account", 5)
            return True
        except Throttled:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=8) as executor:
        accepted = list(executor.map(attempt, range(8)))
    assert accepted.count(True) == 5
    assert AuthThrottleBucket.objects.get().count == 5


@pytest.mark.django_db
def test_session_fixation_and_old_csrf_token_rejected(csrf_client, identities):
    session = csrf_client.session
    session["test_marker"] = "synthetic"
    session.save()
    previous_key = session.session_key
    previous_csrf = csrf_token(csrf_client)
    login_client(csrf_client)
    assert csrf_client.session.session_key != previous_key
    response = csrf_client.post(
        "/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=previous_csrf
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_reset_email_failure_has_same_response_and_is_audited(csrf_client, identities):
    with patch("apps.accounts.services.send_mail", side_effect=SMTPException("secret smtp error")):
        response = csrf_client.post(
            "/api/v1/auth/password-reset/",
            {"email": "owner@example.invalid"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        )
    assert response.status_code == 200
    assert "secret" not in str(response.json())
    assert AuditEvent.objects.filter(action="password_reset_delivery_failed").exists()


@pytest.mark.django_db
def test_reset_requests_are_rate_limited(csrf_client, identities, settings):
    settings.LOGIN_ACCOUNT_LIMIT = 1
    path = "/api/v1/auth/password-reset/"
    first = csrf_client.post(
        path,
        {"email": "owner@example.invalid"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
    )
    second = csrf_client.post(
        path,
        {"email": "OWNER@EXAMPLE.INVALID"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
    )
    assert first.status_code == 200
    assert second.status_code == 429
    AuthThrottleBucket.objects.update(expires_at=timezone.now() - timedelta(seconds=1))


@pytest.mark.django_db
def test_health_works_with_logged_in_cookie_even_when_database_is_down(csrf_client, identities):
    from django.db import OperationalError

    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    with patch(
        "config.health.connection.cursor",
        side_effect=OperationalError("private connection details"),
    ):
        response = csrf_client.get("/health/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}


@pytest.mark.django_db
def test_session_and_csrf_cookies_are_secure_outside_debug(csrf_client, identities, settings):
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    response = login_client(csrf_client)
    assert response.status_code == 200
    assert response.cookies["sessionid"]["secure"]
    assert response.cookies["csrftoken"]["secure"]


@pytest.mark.django_db
def test_health_and_tenant_endpoints_do_not_accept_writes(csrf_client, identities):
    login_client(csrf_client)
    response = csrf_client.post(
        "/api/v1/tenants/",
        {"name": "Unauthorized company"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
    )
    assert response.status_code == 405
    assert csrf_client.get("/api/v1/auth/me/")["Cache-Control"] == "no-store"
