"""Fictional fixture exclusively for the local production rehearsal."""

import os
from datetime import time, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.guests.models import Guest
from apps.payments.services import record_payment
from apps.properties.models import Property, PropertyPhoto
from apps.reservations.services import local_today, save_reservation
from apps.tenants.models import Membership, Tenant


class Command(BaseCommand):
    help = "Crea dos empresas y una foto ficticias solo en cabanacontrol_pcheck."

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            os.environ.get("P_REHEARSAL") != "true"
            or settings.DATABASES["default"]["NAME"] != "cabanacontrol_pcheck"
            or settings.AI_ENABLED
            or settings.WHATSAPP_REAL_ENABLED
        ):
            raise CommandError("El fixture requiere el entorno ficticio aislado.")
        if Tenant.objects.exists() or User.objects.exists():
            raise CommandError("No se modifica una base con datos existentes.")
        for suffix in ("a", "b"):
            user = User.objects.create_user(
                email=f"p-owner-{suffix}@example.invalid",
                password="P-fictional-passphrase-2026!",
            )
            tenant = Tenant.objects.create(name=f"Empresa ficticia P {suffix}")
            Membership.objects.create(user=user, tenant=tenant, role="owner")
            cabin = Property.objects.create(
                tenant=tenant,
                name=f"Cabaña ficticia {suffix}",
                code=f"P-{suffix.upper()}",
                capacity=4,
                base_rate=50000,
                check_in_time=time(15),
                check_out_time=time(11),
                created_by=user,
            )
            image = BytesIO()
            Image.new("RGB", (16, 16), "blue").save(image, format="PNG")
            photo = PropertyPhoto(property=cabin, alt="Foto ficticia P", content_type="image/png")
            photo.file.save("fictional.png", ContentFile(image.getvalue()), save=True)
            guest = Guest.objects.create(
                tenant=tenant,
                first_name="Huésped ficticio",
                last_name=suffix,
                document_type="passport",
                document_number="P-FICTIONAL-ONLY",
                created_by=user,
            )
            start = local_today(tenant) + timedelta(days=30)
            reservation = save_reservation(
                actor=user,
                tenant=tenant,
                data={
                    "property_id": cabin.pk,
                    "primary_guest_id": guest.pk,
                    "check_in": start,
                    "check_out": start + timedelta(days=2),
                    "adults": 2,
                    "children": 0,
                    "total_amount": Decimal("100000"),
                    "status": "confirmed",
                    "source": "direct",
                    "notes": "Ensayo ficticio P",
                },
            )
            record_payment(
                actor=user,
                tenant=tenant,
                reservation_id=reservation.pk,
                data={
                    "request_id": uuid4(),
                    "amount": Decimal("25000"),
                    "paid_at": timezone.now(),
                    "method": "cash",
                    "reference": "Ensayo ficticio",
                },
            )
        self.stdout.write("Fixture ficticio creado: dos empresas, usuarios, cabañas y fotos.")
