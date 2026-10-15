import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


def photo_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    directory = f"tenants/{instance.property.tenant_id}/properties/{instance.property_id}"
    return f"{directory}/{uuid.uuid4().hex}.{extension}"


class Property(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.PROTECT, related_name="properties"
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, validators=[RegexValidator(r"^[A-Z0-9_-]+$")])
    description = models.TextField(blank=True, max_length=5000)
    capacity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(32767)]
    )
    address = models.CharField(max_length=300, blank=True)
    base_rate = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    check_in_time = models.TimeField()
    check_out_time = models.TimeField()
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="property_tenant_code_unique"),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1), name="property_capacity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(base_rate__gte=0), name="property_rate_nonnegative"
            ),
        ]
        indexes = [models.Index(fields=["tenant", "active", "name"])]


class PropertyPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="photos")
    file = models.FileField(upload_to=photo_upload_path, max_length=250)
    alt = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)
    content_type = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at", "id"]
        indexes = [models.Index(fields=["property", "active", "order"])]
