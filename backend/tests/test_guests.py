from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditEvent
from apps.guests.models import Guest
from apps.guests.services import DuplicateRut, save_guest
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db


def test_search_schema_matches_body_pagination():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    response = schema["paths"]["/api/v1/guests/search/"]["post"]["responses"]["200"]
    reference = response["content"]["application/json"]["schema"]["$ref"]
    component = schema["components"]["schemas"][reference.rsplit("/", 1)[1]]
    assert set(component["properties"]) == {"count", "page", "has_next", "has_previous", "results"}


@pytest.mark.parametrize("field", ["first_name", "last_name", "document_number", "phone", "notes"])
def test_domain_null_values_fail_safely(field, identities):
    with pytest.raises(ValidationError):
        save_guest(
            actor=identities["owner"], tenant=identities["tenant_a"], data={**DATA, field: None}
        )


DATA = {
    "first_name": "Persona ficticia",
    "last_name": "De prueba",
    "document_type": "rut",
    "document_number": "12.345.678-5",
    "phone": "+56 9 0000 0000",
    "email": "guest@example.invalid",
    "notes": "Nota privada ficticia",
}


@pytest.fixture
def guests(identities):
    return {
        name: save_guest(actor=identities[user], tenant=identities[tenant], data=DATA)
        for name, tenant, user in [("a", "tenant_a", "owner"), ("b", "tenant_b", "other")]
    }


def enter(client, identities, role="owner"):
    login_client(client, identities[role].email)
    tenant = identities["tenant_b" if role == "other" else "tenant_a"]
    select_company(client, tenant)
    return tenant


def mutate(client, tenant, path="/api/v1/guests/", data=None, method="post", csrf=True):
    headers = {"HTTP_X_TENANT_CONTEXT": str(tenant.pk)}
    if csrf:
        headers["HTTP_X_CSRFTOKEN"] = csrf_token(client)
    return getattr(client, method)(path, DATA if data is None else data, format="json", **headers)


def test_guest_rut_normalized_and_contacts_optional(csrf_client, identities):
    tenant = enter(csrf_client, identities)
    response = mutate(csrf_client, tenant, data={**DATA, "phone": "", "email": ""})
    assert response.status_code == 201
    guest = Guest.objects.get(pk=response.json()["id"])
    assert guest.document_number == "12345678-5"
    assert guest.tenant == tenant and guest.created_by == identities["owner"]
    assert guest.phone == guest.email == ""


@pytest.mark.parametrize("role", ["owner", "manager"])
def test_authorized_editor_can_update_guest(role, csrf_client, identities, guests):
    tenant = enter(csrf_client, identities, role)
    response = mutate(
        csrf_client,
        tenant,
        f"/api/v1/guests/{guests['a'].pk}/",
        {"first_name": "Nombre ficticio actualizado"},
        "patch",
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Nombre ficticio actualizado"


def test_staff_basic_read_no_full_document_or_notes_and_no_write(csrf_client, identities, guests):
    tenant = enter(csrf_client, identities, "staff")
    response = csrf_client.get(f"/api/v1/guests/{guests['a'].pk}/")
    assert response.status_code == 200
    assert response.json()["document_number"] is None
    assert response.json()["notes"] is None
    assert guests["a"].document_number not in response.content.decode()
    assert DATA["notes"] not in response.content.decode()
    assert response.json()["phone"] == "+56900000000"
    assert mutate(csrf_client, tenant).status_code == 403
    assert (
        mutate(
            csrf_client,
            tenant,
            f"/api/v1/guests/{guests['a'].pk}/",
            {"notes": "Unauthorized"},
            "patch",
        ).status_code
        == 403
    )
    assert (
        mutate(csrf_client, tenant, "/api/v1/guests/search/", {"query": "De prueba"}).status_code
        == 200
    )


def test_lists_exclude_document_contacts_and_private_notes(csrf_client, identities, guests):
    enter(csrf_client, identities)
    response = csrf_client.get("/api/v1/guests/")
    item = response.json()["results"][0]
    assert response.json()["count"] == 1
    assert set(item) == {
        "id",
        "first_name",
        "last_name",
        "document_type",
        "document_masked",
        "active",
    }
    assert guests["a"].document_number not in response.content.decode()
    assert DATA["email"] not in response.content.decode()
    assert DATA["notes"] not in response.content.decode()


@pytest.mark.parametrize("role,own,foreign", [("owner", "a", "b"), ("other", "b", "a")])
def test_guest_isolation_in_both_directions(role, own, foreign, csrf_client, identities, guests):
    tenant = enter(csrf_client, identities, role)
    path = f"/api/v1/guests/{guests[foreign].pk}/"
    assert csrf_client.get(path).status_code == 404
    assert (
        mutate(csrf_client, tenant, path, {"first_name": "Unauthorized"}, "patch").status_code
        == 404
    )
    response = csrf_client.get(
        f"/api/v1/guests/?tenant_id={guests[foreign].tenant_id}",
        HTTP_X_TENANT_ID=str(guests[foreign].tenant_id),
    )
    assert response.json()["results"][0]["id"] == str(guests[own].pk)
    response = mutate(
        csrf_client, tenant, "/api/v1/guests/search/", {"query": DATA["document_number"]}
    )
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(guests[own].pk)


@pytest.mark.parametrize("field", ["tenant", "tenant_id", "created_by", "id", "created_at"])
def test_security_fields_rejected(field, csrf_client, identities):
    tenant = enter(csrf_client, identities)
    response = mutate(csrf_client, tenant, data={**DATA, field: str(identities["tenant_b"].pk)})
    assert response.status_code == 400
    assert not Guest.objects.exists()


@pytest.mark.parametrize(
    "overrides",
    [
        {"document_number": "12345678-9"},
        {"document_number": "1000005-0"},
        {"document_type": "unknown"},
        {"document_number": ""},
        {"first_name": " "},
        {"last_name": " "},
        {"phone": "call-me"},
        {"phone": "+123"},
        {"email": "invalid"},
        {"notes": "x" * 2001},
        {"document_type": "passport", "document_number": "<script>"},
    ],
)
def test_guest_server_validation(overrides, csrf_client, identities):
    tenant = enter(csrf_client, identities)
    assert mutate(csrf_client, tenant, data={**DATA, **overrides}).status_code == 400


def test_duplicate_rut_is_scoped_normalized_and_reusable(csrf_client, identities, guests):
    tenant = enter(csrf_client, identities)
    response = mutate(csrf_client, tenant, data={**DATA, "document_number": "123456785"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_document"
    assert response.json()["error"]["details"]["existing_guest_id"] == str(guests["a"].pk)
    assert str(guests["b"].pk) not in response.content.decode()
    assert Guest.objects.count() == 2


@pytest.mark.parametrize("kind", ["passport", "other"])
def test_foreign_document_does_not_require_rut_and_can_repeat(kind, csrf_client, identities):
    tenant = enter(csrf_client, identities)
    for _ in range(2):
        response = mutate(
            csrf_client,
            tenant,
            data={**DATA, "document_type": kind, "document_number": " p-test-0001 "},
        )
        assert response.status_code == 201
        assert response.json()["document_number"] == "P-TEST-0001"
    assert Guest.objects.count() == 2


def test_partial_document_type_change_revalidates_combined_fields(csrf_client, identities, guests):
    tenant = enter(csrf_client, identities)
    path = f"/api/v1/guests/{guests['a'].pk}/"
    assert (
        mutate(
            csrf_client,
            tenant,
            path,
            {"document_type": "passport", "document_number": "P-TEST-002"},
            "patch",
        ).status_code
        == 200
    )
    assert mutate(csrf_client, tenant, path, {"document_type": "rut"}, "patch").status_code == 400
    assert (
        mutate(
            csrf_client,
            tenant,
            path,
            {"document_type": "rut", "document_number": "1.000.005-k"},
            "patch",
        ).status_code
        == 200
    )


def test_csrf_and_context_preconditions(csrf_client, identities):
    tenant = enter(csrf_client, identities)
    assert mutate(csrf_client, tenant, csrf=False).status_code == 403
    assert mutate(csrf_client, identities["tenant_b"]).status_code == 409
    assert (
        csrf_client.post(
            "/api/v1/guests/", DATA, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
        ).status_code
        == 409
    )
    assert (
        mutate(
            csrf_client, tenant, "/api/v1/guests/search/", {"query": "Prueba"}, csrf=False
        ).status_code
        == 403
    )


def test_search_names_exact_document_and_body_pagination(csrf_client, identities, guests):
    tenant = enter(csrf_client, identities)
    path = "/api/v1/guests/search/"
    assert mutate(csrf_client, tenant, path, {"query": "Persona prueba"}).json()["count"] == 1
    assert mutate(csrf_client, tenant, path, {"query": "12.345.678-5"}).json()["count"] == 1
    assert mutate(csrf_client, tenant, path, {"query": "123456"}).json()["count"] == 0
    assert mutate(csrf_client, tenant, path, {"query": "missing"}).json()["count"] == 0
    assert mutate(csrf_client, tenant, path, {"query": "", "page": 9}).status_code == 404
    response = mutate(csrf_client, tenant, path, {"query": "Prueba"})
    assert set(response.json()) == {"count", "page", "has_next", "has_previous", "results"}
    assert "12345678-5" not in response.content.decode()
    assert response["Cache-Control"] == "no-store"


def test_deactivation_preserves_data_and_document_uniqueness(csrf_client, identities, guests):
    tenant = enter(csrf_client, identities)
    path = f"/api/v1/guests/{guests['a'].pk}/"
    assert mutate(csrf_client, tenant, path, {"active": False}, "patch").status_code == 200
    assert csrf_client.get(path).json()["notes"] == DATA["notes"]
    assert Guest.objects.count() == 2
    assert mutate(csrf_client, tenant).status_code == 409
    assert mutate(csrf_client, tenant, path, {}, "delete").status_code == 405
    assert mutate(csrf_client, tenant, path, {"active": True}, "patch").status_code == 200


def test_audit_contains_no_pii_and_sensitive_access_is_traced(csrf_client, identities, guests):
    enter(csrf_client, identities)
    csrf_client.get(f"/api/v1/guests/{guests['a'].pk}/")
    event = AuditEvent.objects.get(action="guest_created", tenant=identities["tenant_a"])
    serialized = str(event.before) + str(event.after)
    for value in [
        DATA["first_name"],
        DATA["last_name"],
        DATA["document_number"],
        DATA["email"],
        DATA["notes"],
    ]:
        assert value not in serialized
    assert AuditEvent.objects.filter(
        action="guest_sensitive_viewed", entity_id=str(guests["a"].pk), actor=identities["owner"]
    ).exists()


def test_platform_has_no_implicit_guest_access(csrf_client, identities, guests):
    login_client(csrf_client, identities["platform"].email)
    assert csrf_client.get(f"/api/v1/guests/{guests['a'].pk}/").status_code == 403


def test_services_reject_staff_revocation_and_tenant_override(identities, guests):
    with pytest.raises(PermissionDenied):
        save_guest(actor=identities["staff"], tenant=identities["tenant_a"], data=DATA)
    identities["memberships"]["owner"].active = False
    identities["memberships"]["owner"].save()
    with pytest.raises(PermissionDenied):
        save_guest(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            data={"phone": ""},
            instance=guests["a"],
        )


def test_database_constraints_and_protection(identities, guests):
    with transaction.atomic(), pytest.raises(IntegrityError):
        Guest.objects.create(
            tenant=identities["tenant_a"],
            created_by=identities["owner"],
            first_name="Ficticio",
            last_name="Prueba",
            document_type="rut",
            document_number="12345678-5",
        )
    with transaction.atomic(), pytest.raises(IntegrityError):
        Guest.objects.filter(pk=guests["a"].pk).update(document_number="12.345.678-5")
    with pytest.raises(ProtectedError):
        identities["tenant_a"].delete()


@pytest.mark.django_db(transaction=True)
def test_concurrent_rut_registration_returns_one_existing_guest(identities):
    def attempt(_):
        close_old_connections()
        try:
            guest = save_guest(actor=identities["owner"], tenant=identities["tenant_a"], data=DATA)
            return (True, str(guest.pk))
        except DuplicateRut as exc:
            return (False, str(exc.detail["existing_guest_id"]))
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        result = list(executor.map(attempt, range(2)))
    assert sum(accepted for accepted, _ in result) == 1
    assert result[0][1] == result[1][1]
    assert Guest.objects.count() == 1


def test_search_query_schema_and_authentication(csrf_client, identities):
    assert csrf_client.get(reverse("guest-list")).status_code == 403
    tenant = enter(csrf_client, identities)
    assert (
        mutate(
            csrf_client,
            tenant,
            "/api/v1/guests/search/",
            {"query": "x", "tenant_id": str(tenant.pk)},
        ).status_code
        == 400
    )
