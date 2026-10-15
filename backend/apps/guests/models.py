import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.guests.validators import normalize_document, normalize_phone


class Guest(models.Model):
    class DocumentType(models.TextChoices):
        RUT = "rut", "RUT chileno"
        PASSPORT = "passport", "Pasaporte"
        OTHER = "other", "Otro documento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="guests")
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    document_type = models.CharField(max_length=8, choices=DocumentType.choices)
    document_number = models.CharField(max_length=40)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(max_length=2000, blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "document_number"],
                condition=models.Q(document_type="rut"),
                name="guest_tenant_rut_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(document_type__in=["rut", "passport", "other"]),
                name="guest_document_type_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(document_number=""), name="guest_document_not_empty"
            ),
            models.CheckConstraint(
                condition=~models.Q(document_type="rut")
                | models.Q(document_number__regex=r"^[1-9][0-9]{0,7}-[0-9K]$"),
                name="guest_rut_canonical",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "active", "last_name", "first_name"]),
            models.Index(fields=["tenant", "document_type", "document_number"]),
        ]

    def clean(self):
        super().clean()
        for field in ("first_name", "last_name"):
            value = (getattr(self, field) or "").strip()
            if not value or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
                raise ValidationError(
                    {field: "Ingresa un nombre válido, sin caracteres de control."}
                )
            setattr(self, field, value)
        try:
            self.document_number = normalize_document(self.document_type, self.document_number)
        except ValidationError as exc:
            raise ValidationError({"document_number": exc.messages}) from exc
        try:
            self.phone = normalize_phone(self.phone)
        except ValidationError as exc:
            raise ValidationError({"phone": exc.messages}) from exc
        if self.email is None:
            raise ValidationError({"email": "Usa texto vacío cuando no hay correo."})
        self.email = self.email.strip().lower()
        if self.notes is None:
            raise ValidationError({"notes": "Usa texto vacío cuando no hay notas."})
        if self.notes is not None and (
            "\x00" in self.notes or any(0xD800 <= ord(char) <= 0xDFFF for char in self.notes)
        ):
            raise ValidationError({"notes": "Las notas contienen caracteres no permitidos."})

    def __str__(self):
        return str(self.pk)
