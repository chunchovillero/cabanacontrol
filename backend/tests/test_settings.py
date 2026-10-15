import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from apps.tenants.models import Membership
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db
PROFILE = "/api/v1/auth/profile/"
COMPANY = "/api/v1/company-settings/"


def owner_client(identities):
    client = APIClient(enforce_csrf_checks=True)
    assert login_client(client).status_code == 200
    assert select_company(client, identities["tenant_a"]).status_code == 200
    return client


def company_data(client):
    data = client.get(COMPANY).json()
    return {key: data[key] for key in ("name", "legal_name", "contact_email", "contact_phone")} | {
        "expected_updated_at": data["updated_at"]
    }


def patch_company(client, identities, data, **headers):
    return client.patch(
        COMPANY,
        data,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(client),
        HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
        **headers,
    )


def test_profile_can_change_only_own_names_without_changing_credentials(identities):
    client = owner_client(identities)
    before = client.get(PROFILE).json()
    user = identities["owner"]
    password = user.password
    data = dict(
        first_name="Nuevo nombre",
        last_name="",
        expected_first_name=before["first_name"],
        expected_last_name=before["last_name"],
    )
    response = client.patch(PROFILE, data, format="json", HTTP_X_CSRFTOKEN=csrf_token(client))
    assert response.status_code == 200 and response.json()["first_name"] == "Nuevo nombre"
    user.refresh_from_db()
    assert user.password == password and user.email == before["email"]
    assert client.get("/api/v1/auth/me/").json()["name"] == "Nuevo nombre"
    assert identities["other"].first_name == "Otro"
    assert (
        client.patch(PROFILE, data, format="json", HTTP_X_CSRFTOKEN=csrf_token(client)).status_code
        == 409
    )
    event = AuditEvent.objects.get(action="profile_updated")
    assert "Nuevo nombre" not in str(event.__dict__)


def test_company_changes_are_scoped_audited_and_detect_stale_data(identities):
    client = owner_client(identities)
    data = company_data(client) | dict(
        name="Nombre nuevo",
        legal_name="Sociedad ficticia",
        contact_email="contacto@example.invalid",
        contact_phone="+56 9 1234 5678",
    )
    response = patch_company(client, identities, data)
    assert response.status_code == 200
    assert response.json()["currency"] == "CLP"
    tenant = identities["tenant_a"]
    tenant.refresh_from_db()
    assert tenant.name == "Nombre nuevo" and tenant.contact_email == data["contact_email"]
    identities["tenant_b"].refresh_from_db()
    assert identities["tenant_b"].name == "Empresa ficticia B"
    assert patch_company(client, identities, data).status_code == 409
    event = AuditEvent.objects.get(action="company_settings_updated")
    assert set(event.after["fields"]) == {"name", "legal_name", "contact_email", "contact_phone"}
    assert "contacto@example.invalid" not in str(event.__dict__)


@pytest.mark.parametrize("role", ["staff", "manager", "platform"])
def test_non_owners_cannot_read_or_change_company(identities, role):
    client = APIClient()
    client.force_login(identities[role])
    if role != "platform":
        select_company(client, identities["tenant_a"])
    assert client.get(COMPANY).status_code == 403
    assert patch_company(client, identities, {}).status_code == 403
    assert client.get(PROFILE).status_code == 200


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "USD"),
        ("timezone", "UTC"),
        ("tenant_id", "foreign"),
        ("active", False),
        ("contact_email", "invalid"),
        ("contact_phone", "<script>"),
        ("name", " "),
        ("legal_name", "bad\x00name"),
    ],
)
def test_company_rejects_unknown_and_invalid_fields(identities, field, value):
    client = owner_client(identities)
    assert (
        patch_company(client, identities, company_data(client) | {field: value}).status_code == 400
    )
    assert not AuditEvent.objects.filter(action="company_settings_updated").exists()


def test_company_requires_csrf_and_current_context_and_active_owner(identities):
    client = owner_client(identities)
    data = company_data(client) | {"name": "Cambio"}
    assert client.patch(COMPANY, data, format="json").status_code == 403
    assert (
        client.patch(COMPANY, data, format="json", HTTP_X_CSRFTOKEN=csrf_token(client)).status_code
        == 409
    )
    select_company(client, identities["tenant_b"])
    # Other company is unauthorized, so existing selection remains A.
    assert (
        client.get(COMPANY, HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)).status_code == 409
    )
    Membership.objects.filter(pk=identities["memberships"]["owner"].pk).update(active=False)
    assert patch_company(client, identities, data).status_code == 403


@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "other@example.invalid"),
        ("is_staff", True),
        ("first_name", "bad\x00name"),
        ("first_name", " "),
    ],
)
def test_profile_rejects_extra_or_invalid_fields(identities, field, value):
    client = owner_client(identities)
    data = dict(
        first_name="Persona", last_name="", expected_first_name="Propietario", expected_last_name=""
    )
    response = client.patch(
        PROFILE, data | {field: value}, format="json", HTTP_X_CSRFTOKEN=csrf_token(client)
    )
    assert response.status_code == 400


def test_anonymous_cannot_access_settings():
    client = APIClient()
    for path in (PROFILE, COMPANY):
        assert client.get(path).status_code == 403
        assert client.patch(path, {}, format="json").status_code == 403
