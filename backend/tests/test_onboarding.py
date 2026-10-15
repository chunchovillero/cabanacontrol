from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.tenants.models import Membership, Tenant
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db
URL = "/api/v1/auth/register/"
DATA = dict(
    email="New@Example.invalid",
    first_name="Persona",
    last_name="Nueva",
    company_name="Primera empresa",
    password="New-fictional-passphrase-2026!",
)


@pytest.fixture(autouse=True)
def local_registration(settings):
    settings.DEBUG = True
    settings.LOCAL_ONBOARDING_ENABLED = True


def post(client, data=None):
    return client.post(
        URL, DATA if data is None else data, format="json", HTTP_X_CSRFTOKEN=csrf_token(client)
    )


def test_atomic_registration_and_login_scoped_to_own_company(identities):
    client = APIClient(enforce_csrf_checks=True)
    assert post(client).status_code == 201
    user = User.objects.get(email="new@example.invalid")
    member = Membership.objects.get(user=user)
    assert member.role == "owner" and member.active
    assert member.tenant.currency == "CLP" and member.tenant.timezone == "America/Santiago"
    assert not user.is_staff and not user.is_superuser and not user.is_platform_admin
    assert user.check_password(DATA["password"])
    assert "_auth_user_id" not in client.session
    assert login_client(client, user.email, DATA["password"]).status_code == 200
    assert select_company(client, member.tenant).status_code == 200
    assert select_company(client, identities["tenant_b"]).status_code in (403, 404)
    event = AuditEvent.objects.get(action="owner_registered_local")
    assert DATA["password"] not in str(event.__dict__)
    assert user.email not in str(event.__dict__)


@pytest.mark.parametrize(
    "field,value",
    [
        ("password", "short"),
        ("role", "owner"),
        ("tenant_id", "foreign"),
        ("is_superuser", True),
        ("company_name", " "),
        ("first_name", "bad\x00name"),
        ("email", "invalid"),
    ],
)
def test_invalid_registration_has_no_side_effects(field, value):
    client = APIClient(enforce_csrf_checks=True)
    assert post(client, {**DATA, field: value}).status_code == 400
    assert not User.objects.exists() and not Tenant.objects.exists()


def test_existing_account_cannot_be_overwritten_or_receive_another_company():
    client = APIClient(enforce_csrf_checks=True)
    assert post(client).status_code == 201
    user = User.objects.get()
    old_hash = user.password
    assert post(client, {**DATA, "password": "Different-fictional-passphrase!"}).status_code == 400
    user.refresh_from_db()
    assert user.password == old_hash and Tenant.objects.count() == 1


def test_membership_failure_rolls_back_user_and_company():
    with patch("apps.accounts.onboarding.Membership.objects.create", side_effect=RuntimeError):
        client = APIClient()
        with pytest.raises(RuntimeError):
            post(client)
    assert not User.objects.exists() and not Tenant.objects.exists()


def test_csrf_required():
    assert APIClient(enforce_csrf_checks=True).post(URL, DATA, format="json").status_code == 403
    assert not User.objects.exists()


def test_empty_optional_last_name_is_accepted():
    assert post(APIClient(), {**DATA, "last_name": ""}).status_code == 201
    assert User.objects.get().last_name == ""


@pytest.mark.parametrize("flag", ["DEBUG", "LOCAL_ONBOARDING_ENABLED"])
def test_registration_disabled_outside_local_mode(settings, flag):
    setattr(settings, flag, False)
    client = APIClient()
    assert client.get(URL).json() == {"enabled": False}
    assert post(client).status_code == 403
    assert not User.objects.exists()


def test_authenticated_user_cannot_create_other_account(identities):
    client = APIClient()
    client.force_login(identities["owner"])
    assert post(client).status_code == 403
    assert not User.objects.filter(email="new@example.invalid").exists()


def test_registration_has_own_rate_limit():
    client = APIClient()
    for _ in range(5):
        assert post(client, {**DATA, "password": "short"}).status_code == 400
    response = post(client)
    assert response.status_code == 429 and int(response["Retry-After"]) > 0
    assert not User.objects.exists()
