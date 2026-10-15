import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenants.models import Membership, Tenant


@pytest.fixture(autouse=True)
def testing_settings(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.LOGIN_ACCOUNT_LIMIT = 5
    settings.LOGIN_IP_LIMIT = 30


@pytest.fixture
def identities(db):
    owner = User.objects.create_user(
        "owner@example.invalid", "Test-strong-passphrase-2026", first_name="Propietario"
    )
    other = User.objects.create_user(
        "other@example.invalid", "Test-strong-passphrase-2026", first_name="Otro"
    )
    staff = User.objects.create_user("staff@example.invalid", "Test-strong-passphrase-2026")
    manager = User.objects.create_user("manager@example.invalid", "Test-strong-passphrase-2026")
    platform = User.objects.create_superuser(
        "platform@example.invalid", "Test-strong-passphrase-2026"
    )
    tenant_a = Tenant.objects.create(name="Empresa ficticia A")
    tenant_b = Tenant.objects.create(name="Empresa ficticia B")
    memberships = {
        "owner": Membership.objects.create(user=owner, tenant=tenant_a, role="owner"),
        "other": Membership.objects.create(user=other, tenant=tenant_b, role="owner"),
        "staff": Membership.objects.create(user=staff, tenant=tenant_a, role="staff"),
        "manager": Membership.objects.create(user=manager, tenant=tenant_a, role="manager"),
    }
    return dict(
        owner=owner,
        other=other,
        staff=staff,
        manager=manager,
        platform=platform,
        tenant_a=tenant_a,
        tenant_b=tenant_b,
        memberships=memberships,
    )


@pytest.fixture
def csrf_client():
    return APIClient(enforce_csrf_checks=True)


def csrf_token(client):
    return client.get("/api/v1/auth/csrf/").json()["csrf_token"]


def login_client(client, email="owner@example.invalid", password="Test-strong-passphrase-2026"):
    return client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(client),
    )


def select_company(client, tenant):
    return client.post(
        f"/api/v1/tenants/{tenant.pk}/select/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(client),
    )
