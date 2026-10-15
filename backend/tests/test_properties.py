from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from PIL import Image, PngImagePlugin
from rest_framework.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.properties.models import Property, PropertyPhoto
from apps.properties.services import save_property
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db
DATA = {
    "name": "Cabaña de prueba",
    "code": "CAB-1",
    "description": "Solo datos ficticios",
    "capacity": 5,
    "address": "",
    "base_rate": "50000.10",
    "check_in_time": "15:00",
    "check_out_time": "11:00",
}


@pytest.fixture(autouse=True)
def private_test_storage(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def properties(identities):
    result = {}
    for name, tenant, user in [("a", "tenant_a", "owner"), ("b", "tenant_b", "other")]:
        data = {**DATA, "base_rate": Decimal(DATA["base_rate"])}
        result[name] = Property.objects.create(
            tenant=identities[tenant], created_by=identities[user], **data
        )
    return result


def enter(client, identities, role="owner"):
    login_client(client, identities[role].email)
    tenant = identities["tenant_b" if role == "other" else "tenant_a"]
    select_company(client, tenant)
    return tenant


def mutation(
    client, tenant, path="/api/v1/properties/", data=None, method="post", format="json", csrf=True
):
    options = {"HTTP_X_TENANT_CONTEXT": str(tenant.pk)}
    if csrf:
        options["HTTP_X_CSRFTOKEN"] = csrf_token(client)
    return getattr(client, method)(path, DATA if data is None else data, format=format, **options)


def photo_file(format="PNG", size=(10, 10), metadata=False):
    stream = BytesIO()
    info = PngImagePlugin.PngInfo()
    if metadata:
        info.add_text("private-gps", "synthetic-sensitive-metadata")
    Image.new("RGB", size, "green").save(
        stream, format=format, **({"pnginfo": info} if format == "PNG" else {})
    )
    return SimpleUploadedFile(
        "untrusted-name.any", stream.getvalue(), content_type="application/octet-stream"
    )


def test_owner_creates_scoped_property_and_audit(csrf_client, identities):
    tenant = enter(csrf_client, identities)
    response = mutation(csrf_client, tenant)
    assert response.status_code == 201
    data = response.json()
    assert data["base_rate"] == "50000.10"
    assert data["currency"] == "CLP"
    saved = Property.objects.get(pk=data["id"])
    assert saved.tenant == tenant and saved.created_by == identities["owner"]
    assert isinstance(saved.base_rate, Decimal)
    event = AuditEvent.objects.get(action="property_created", entity_id=str(saved.pk))
    assert event.after["base_rate"] == "50000.10"
    assert "description" not in event.after and "address" not in event.after
    assert AuditEvent.objects.filter(
        action="property_created", entity_id=str(saved.pk), tenant=tenant
    ).exists()


@pytest.mark.parametrize("role", ["owner", "manager"])
def test_editor_can_update(role, csrf_client, identities, properties):
    tenant = enter(csrf_client, identities, role)
    response = mutation(
        csrf_client,
        tenant,
        f"/api/v1/properties/{properties['a'].pk}/",
        {"capacity": 6, "base_rate": "60000.25"},
        "patch",
    )
    assert response.status_code == 200
    assert response.json()["base_rate"] == "60000.25"


def test_staff_can_read_but_cannot_write(csrf_client, identities, properties):
    tenant = enter(csrf_client, identities, "staff")
    assert csrf_client.get("/api/v1/properties/").json()["count"] == 1
    assert mutation(csrf_client, tenant).status_code == 403
    assert (
        mutation(
            csrf_client,
            tenant,
            f"/api/v1/properties/{properties['a'].pk}/",
            {"capacity": 2},
            "patch",
        ).status_code
        == 403
    )


@pytest.mark.parametrize("role,own,foreign", [("owner", "a", "b"), ("other", "b", "a")])
def test_property_isolation_in_both_directions(
    role, own, foreign, csrf_client, identities, properties
):
    tenant = enter(csrf_client, identities, role)
    response = csrf_client.get(
        f"/api/v1/properties/?tenant_id={properties[foreign].tenant_id}",
        HTTP_X_TENANT_ID=str(properties[foreign].tenant_id),
    )
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(properties[own].pk)
    path = f"/api/v1/properties/{properties[foreign].pk}/"
    assert csrf_client.get(path).status_code == 404
    assert mutation(csrf_client, tenant, path, {"name": "Unauthorized"}, "patch").status_code == 404
    properties[foreign].refresh_from_db()
    assert properties[foreign].name == DATA["name"]


@pytest.mark.parametrize("field", ["tenant", "tenant_id", "id", "created_by", "currency", "photos"])
def test_rejects_client_owned_security_fields(field, csrf_client, identities):
    tenant = enter(csrf_client, identities)
    assert (
        mutation(
            csrf_client, tenant, data={**DATA, field: str(identities["tenant_b"].pk)}
        ).status_code
        == 400
    )
    assert not Property.objects.exists()


def test_context_header_prevents_stale_tab_writes(csrf_client, identities):
    tenant = enter(csrf_client, identities)
    assert (
        csrf_client.post(
            "/api/v1/properties/", DATA, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
        ).status_code
        == 409
    )
    other = identities["tenant_b"]
    assert mutation(csrf_client, other).status_code == 409
    assert (
        csrf_client.get("/api/v1/properties/", HTTP_X_TENANT_CONTEXT=str(other.pk)).status_code
        == 409
    )
    assert mutation(csrf_client, tenant, csrf=False).status_code == 403


@pytest.mark.parametrize(
    "data",
    [
        {"capacity": 0},
        {"capacity": -1},
        {"capacity": 1.2},
        {"capacity": 40000},
        {"base_rate": "-0.01"},
        {"base_rate": 50000.1},
        {"base_rate": "1.001"},
        {"base_rate": "1000000000000.00"},
        {"code": "bad code"},
        {"name": " "},
        {"check_in_time": "24:00"},
        {"check_out_time": "bad"},
    ],
)
def test_server_validations(data, csrf_client, identities):
    tenant = enter(csrf_client, identities)
    assert mutation(csrf_client, tenant, data={**DATA, **data}).status_code == 400


def test_code_unique_per_company_including_inactive(csrf_client, identities, properties):
    tenant = enter(csrf_client, identities)
    assert mutation(csrf_client, tenant, data={**DATA, "code": "cab-1"}).status_code == 400
    mutation(
        csrf_client, tenant, f"/api/v1/properties/{properties['a'].pk}/", {"active": False}, "patch"
    )
    assert mutation(csrf_client, tenant).status_code == 400
    tenant_b = enter(csrf_client, identities, "other")
    assert mutation(csrf_client, tenant_b, data={**DATA, "code": "CAB-2"}).status_code == 201


def test_no_delete_and_deactivation_preserves_rows_and_audit(csrf_client, identities, properties):
    tenant = enter(csrf_client, identities)
    path = f"/api/v1/properties/{properties['a'].pk}/"
    assert mutation(csrf_client, tenant, path, {}, "delete").status_code == 405
    assert mutation(csrf_client, tenant, path, {"active": False}, "patch").status_code == 200
    assert csrf_client.get(path).json()["active"] is False
    assert Property.objects.count() == 2
    assert AuditEvent.objects.filter(action="property_deactivated").exists()
    assert mutation(csrf_client, tenant, path, {"active": True}, "patch").status_code == 200


def test_search_filter_and_pagination_are_scoped(csrf_client, identities, properties):
    enter(csrf_client, identities)
    response = csrf_client.get("/api/v1/properties/?search=CAB-1&active=true")
    assert response.json()["count"] == 1
    assert response.json()["next"] is None
    assert csrf_client.get("/api/v1/properties/?search=missing").json()["count"] == 0


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
def test_upload_decodes_real_format_and_file_is_private(
    format, csrf_client, identities, properties
):
    tenant = enter(csrf_client, identities)
    path = f"/api/v1/properties/{properties['a'].pk}/photos/"
    response = mutation(
        csrf_client,
        tenant,
        path,
        {"file": photo_file(format), "alt": "Imagen ficticia", "order": 1},
        format="multipart",
    )
    assert response.status_code == 201
    photo = PropertyPhoto.objects.get(pk=response.json()["id"])
    assert "untrusted-name" not in photo.file.name
    assert str(tenant.pk) in photo.file.name
    file_response = csrf_client.get(response.json()["url"])
    assert file_response.status_code == 200
    assert file_response["X-Content-Type-Options"] == "nosniff"
    assert file_response["Cache-Control"] == "no-store"
    assert b"".join(file_response.streaming_content)
    other = enter(csrf_client, identities, "other")
    assert other != tenant
    assert csrf_client.get(response.json()["url"]).status_code == 404
    assert (
        mutation(
            csrf_client,
            other,
            path,
            {"file": photo_file(), "alt": "Unauthorized"},
            format="multipart",
        ).status_code
        == 404
    )


def test_image_metadata_is_stripped(csrf_client, identities, properties):
    tenant = enter(csrf_client, identities)
    response = mutation(
        csrf_client,
        tenant,
        f"/api/v1/properties/{properties['a'].pk}/photos/",
        {"file": photo_file(metadata=True), "alt": "Ficticia"},
        format="multipart",
    )
    assert response.status_code == 201
    photo = PropertyPhoto.objects.get(pk=response.json()["id"])
    with Image.open(photo.file) as image:
        assert "private-gps" not in image.info


@pytest.mark.parametrize("kind", ["svg", "gif", "corrupt", "large_dimensions", "oversize"])
def test_rejects_unsafe_images(kind, csrf_client, identities, properties, settings):
    tenant = enter(csrf_client, identities)
    if kind == "svg":
        file = SimpleUploadedFile("safe.png", b'<svg onload="alert(1)"/>', content_type="image/png")
    elif kind == "gif":
        file = photo_file("GIF")
    elif kind == "large_dimensions":
        settings.PROPERTY_PHOTO_MAX_DIMENSION = 9
        file = photo_file()
    elif kind == "oversize":
        settings.PROPERTY_PHOTO_MAX_BYTES = 10
        file = photo_file()
    else:
        file = SimpleUploadedFile("safe.jpg", b"not-an-image", content_type="image/jpeg")
    response = mutation(
        csrf_client,
        tenant,
        f"/api/v1/properties/{properties['a'].pk}/photos/",
        {"file": file, "alt": "Ficticia"},
        format="multipart",
    )
    assert response.status_code == 400
    assert not PropertyPhoto.objects.exists()


def test_photo_limit_order_edit_and_soft_hide(csrf_client, identities, properties, settings):
    settings.PROPERTY_PHOTO_MAX_COUNT = 1
    tenant = enter(csrf_client, identities)
    path = f"/api/v1/properties/{properties['a'].pk}/photos/"
    first = mutation(
        csrf_client, tenant, path, {"file": photo_file(), "alt": "Primera"}, format="multipart"
    )
    assert first.status_code == 201
    second = mutation(
        csrf_client, tenant, path, {"file": photo_file(), "alt": "Segunda"}, format="multipart"
    )
    assert second.status_code == 400
    detail = f"{path}{first.json()['id']}/"
    assert (
        mutation(
            csrf_client, tenant, detail, {"alt": "Texto actualizado", "order": 3}, "patch"
        ).status_code
        == 200
    )
    assert mutation(csrf_client, tenant, detail, {"active": False}, "patch").status_code == 200
    assert csrf_client.get(path).json() == []
    assert csrf_client.get(first.json()["url"]).status_code == 404
    property_response = mutation(
        csrf_client, tenant, f"/api/v1/properties/{properties['a'].pk}/", {"active": False}, "patch"
    )
    assert property_response.json()["photos"] == []
    assert PropertyPhoto.objects.get().file.storage.exists(PropertyPhoto.objects.get().file.name)
    assert mutation(csrf_client, tenant, detail, {}, "delete").status_code == 405
    assert mutation(csrf_client, tenant, detail, {"active": True}, "patch").status_code == 200


def test_no_photo_access_without_session(csrf_client, identities, properties):
    assert csrf_client.get(f"/api/v1/properties/{properties['a'].pk}/photos/").status_code == 403


def test_model_protect_and_database_constraints(identities, properties):
    with pytest.raises(ProtectedError):
        identities["tenant_a"].delete()
    with transaction.atomic(), pytest.raises(IntegrityError):
        Property.objects.filter(pk=properties["a"].pk).update(capacity=0)
    with transaction.atomic(), pytest.raises(IntegrityError):
        Property.objects.filter(pk=properties["a"].pk).update(base_rate=Decimal("-1"))


def test_domain_services_recheck_membership(identities, properties):
    with pytest.raises(PermissionDenied):
        save_property(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            data={"name": "Unauthorized"},
            instance=properties["a"],
        )
    identities["memberships"]["owner"].active = False
    identities["memberships"]["owner"].save()
    with pytest.raises(PermissionDenied):
        save_property(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            data={"name": "Unauthorized"},
            instance=properties["a"],
        )


def test_property_payload_must_be_an_object(csrf_client, identities):
    tenant = enter(csrf_client, identities)
    assert mutation(csrf_client, tenant, data=[{"name": "invalid"}]).status_code == 400


def test_staff_cannot_upload_photos(csrf_client, identities, properties):
    tenant = enter(csrf_client, identities, "staff")
    response = mutation(
        csrf_client,
        tenant,
        f"/api/v1/properties/{properties['a'].pk}/photos/",
        {"file": photo_file(), "alt": "Unauthorized"},
        format="multipart",
    )
    assert response.status_code == 403


def test_update_audit_retains_previous_money_and_capacity(csrf_client, identities, properties):
    tenant = enter(csrf_client, identities)
    response = mutation(
        csrf_client,
        tenant,
        f"/api/v1/properties/{properties['a'].pk}/",
        {"base_rate": "70000.99", "capacity": 8},
        "patch",
    )
    assert response.status_code == 200
    event = AuditEvent.objects.get(action="property_updated", entity_id=str(properties["a"].pk))
    assert event.before["base_rate"] == "50000.10"
    assert event.after["base_rate"] == "70000.99"
    assert event.before["capacity"] == "5" and event.after["capacity"] == "8"
