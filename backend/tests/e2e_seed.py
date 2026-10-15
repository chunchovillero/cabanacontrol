"""Datos ficticios únicamente en una base E2E explícitamente separada."""

import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.tenants.models import Membership, Tenant  # noqa: E402


@transaction.atomic
def seed():
    if (
        os.environ.get("E2E_TEST_MODE") != "true"
        or settings.DATABASES["default"]["NAME"] != "cabanacontrol_e2e"
    ):
        raise RuntimeError("Los datos E2E requieren modo explícito y base cabanacontrol_e2e.")
    for index, variant in enumerate(("chromium", "mobile")):
        user, created = User.objects.get_or_create(
            email=f"e2e-settings-{variant}@example.invalid",
            defaults={"first_name": "Perfil ficticio"},
        )
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        tenant, _ = Tenant.objects.get_or_create(
            pk=f"eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee{index}",
            defaults={"name": f"Empresa configuración {variant}"},
        )
        Membership.objects.get_or_create(user=user, tenant=tenant, defaults={"role": "owner"})
    users = []
    # Isolated commercial fixtures; never assign subscriptions in the main database.
    from apps.billing.models import TenantSubscription
    from apps.billing.services import assign_plan, enable_limits
    from apps.properties.models import Property
    from apps.properties.services import save_property

    billing_actor, created = User.objects.get_or_create(
        email="e2e-billing-platform@example.invalid",
        defaults={"is_platform_admin": True},
    )
    if created:
        billing_actor.set_unusable_password()
        billing_actor.save(update_fields=["password"])
    from apps.billing.simulation import prepare_company

    for variant in ("chromium", "mobile"):
        simulation_user, created = User.objects.get_or_create(
            email=f"e2e-simulation-{variant}@example.invalid",
            defaults={"first_name": "Operador de simulación ficticia"},
        )
        if created:
            simulation_user.set_password("E2E-fictional-passphrase-2026!")
            simulation_user.save(update_fields=["password"])
        # Fresh fictional company per rehearsal; retain all prior contracts and charges.
        simulation_tenant = Tenant.objects.create(
            name=f"Empresa simulación {variant} {timezone.now().strftime('%Y%m%d%H%M%S%f')}"
        )
        Membership.objects.create(user=simulation_user, tenant=simulation_tenant, role="owner")
        assign_plan(
            actor=billing_actor,
            tenant=simulation_tenant,
            code="trial",
            reason="Fixture nuevo ficticio",
        )
        enable_limits(actor=billing_actor, tenant=simulation_tenant, reason="Uso ficticio revisado")
        prepare_company(actor=billing_actor, tenant=simulation_tenant, reason="Solo simulación E2E")
    for index, variant in enumerate(("chromium", "mobile")):
        user, created = User.objects.get_or_create(
            email=f"e2e-billing-{variant}@example.invalid",
            defaults={"first_name": "Propietario comercial ficticio"},
        )
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        tenant, _ = Tenant.objects.get_or_create(
            pk=f"ffffffff-ffff-4fff-8fff-fffffffffff{index}",
            defaults={"name": f"Empresa plan {variant}"},
        )
        Membership.objects.get_or_create(user=user, tenant=tenant, defaults={"role": "owner"})
        if not TenantSubscription.objects.filter(tenant=tenant).exists():
            assign_plan(
                actor=billing_actor,
                tenant=tenant,
                code="trial",
                reason="Fixture comercial ficticio",
            )
            enable_limits(actor=billing_actor, tenant=tenant, reason="Uso ficticio revisado")
            end = timezone.now() - timedelta(minutes=1)
            TenantSubscription.objects.filter(tenant=tenant).update(
                trial_started_at=end - timedelta(days=14),
                trial_ends_at=end,
            )
        if not Property.objects.filter(tenant=tenant).exists():
            save_property(
                actor=user,
                tenant=tenant,
                data={
                    "name": "Cabaña comercial ficticia",
                    "code": "TRIAL-ONE",
                    "capacity": 2,
                    "base_rate": "50000",
                    "check_in_time": "15:00",
                    "check_out_time": "11:00",
                },
            )
    for email, name in [
        ("e2e-owner-a@example.invalid", "Usuario ficticio A"),
        ("e2e-owner-b@example.invalid", "Usuario ficticio B"),
    ]:
        user, created = User.objects.get_or_create(email=email, defaults={"first_name": name})
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        users.append(user)
    companies = []
    for pk, name in [
        ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "Empresa ficticia A"),
        ("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "Empresa ficticia B"),
        ("cccccccc-cccc-4ccc-8ccc-cccccccccccc", "Empresa compartida ficticia"),
    ]:
        tenant, _ = Tenant.objects.get_or_create(pk=pk, defaults={"name": name})
        companies.append(tenant)
    Membership.objects.get_or_create(user=users[0], tenant=companies[0], defaults={"role": "owner"})
    Membership.objects.get_or_create(user=users[1], tenant=companies[1], defaults={"role": "owner"})
    Membership.objects.get_or_create(user=users[0], tenant=companies[2], defaults={"role": "staff"})
    for variant in ("chromium", "mobile"):
        user, created = User.objects.get_or_create(
            email=f"e2e-property-{variant}@example.invalid",
            defaults={"first_name": "Usuario ficticio de cabañas"},
        )
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        Membership.objects.get_or_create(user=user, tenant=companies[0], defaults={"role": "owner"})
        Membership.objects.get_or_create(user=user, tenant=companies[2], defaults={"role": "staff"})
    for variant in ("chromium", "mobile"):
        for who, company in (("a", companies[0]), ("b", companies[1])):
            user, created = User.objects.get_or_create(
                email=f"e2e-identity-{variant}-{who}@example.invalid",
                defaults={"first_name": "Usuario ficticio de identidad"},
            )
            if created:
                user.set_password("E2E-fictional-passphrase-2026!")
                user.save(update_fields=["password"])
            Membership.objects.get_or_create(user=user, tenant=company, defaults={"role": "owner"})
            if who == "a":
                Membership.objects.get_or_create(
                    user=user, tenant=companies[2], defaults={"role": "staff"}
                )
    for variant in ("chromium", "mobile"):
        for prefix, role in (
            ("guest", "owner"),
            ("guest-staff", "staff"),
            ("reservation", "owner"),
            ("reservation-staff", "staff"),
            ("payment-owner", "owner"),
            ("payment-staff", "staff"),
            ("insights", "owner"),
            ("report-owner", "owner"),
            ("report-staff", "staff"),
            ("operations-owner", "owner"),
            ("operations-staff", "staff"),
        ):
            user, created = User.objects.get_or_create(
                email=f"e2e-{prefix}-{variant}@example.invalid",
                defaults={"first_name": "Usuario ficticio de huéspedes"},
            )
            if created:
                user.set_password("E2E-fictional-passphrase-2026!")
                user.save(update_fields=["password"])
            Membership.objects.get_or_create(
                user=user, tenant=companies[0], defaults={"role": role}
            )
            if role == "owner":
                Membership.objects.get_or_create(
                    user=user, tenant=companies[2], defaults={"role": "staff"}
                )

    # Operational check-out fixtures are restricted by the guard at the start of seed().

    from apps.guests.models import Guest
    from apps.properties.models import Property
    from apps.reservations.models import Reservation
    from apps.reservations.services import local_today

    for variant in ("chromium", "mobile"):
        owner = User.objects.get(email=f"e2e-operations-owner-{variant}@example.invalid")
        prop, _ = Property.objects.get_or_create(
            tenant=companies[0],
            code=f"OPS-{variant}".upper(),
            defaults={
                "name": f"Cabaña ficticia operación {variant}",
                "capacity": 4,
                "base_rate": "50000.00",
                "check_in_time": "15:00",
                "check_out_time": "11:00",
                "created_by": owner,
            },
        )
        guest, _ = Guest.objects.get_or_create(
            tenant=companies[0],
            document_type="passport",
            document_number=f"FAKE-OPS-{variant}".upper(),
            defaults={
                "first_name": "Persona ficticia operación",
                "last_name": variant,
                "created_by": owner,
            },
        )
        today = local_today(companies[0])
        if not Reservation.objects.filter(
            tenant=companies[0], property=prop, status="checked_in", check_out=today
        ).exists():
            Reservation.objects.create(
                tenant=companies[0],
                property=prop,
                primary_guest=guest,
                check_in=today - timedelta(days=2),
                check_out=today,
                adults=2,
                children=0,
                status="checked_in",
                total_amount="50000.00",
                currency="CLP",
                source="direct",
                created_by=owner,
            )

    from apps.assistant.models import TenantAISettings

    for variant in ("chromium", "mobile"):
        user, created = User.objects.get_or_create(
            email=f"e2e-assistant-{variant}@example.invalid",
            defaults={"first_name": "Usuario ficticio asistente"},
        )
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        # Each run uses an isolated tenant so earlier E2E quota consumption is preserved.
        from uuid import uuid4

        company = Tenant.objects.create(name=f"Empresa asistente {variant} {uuid4().hex[:8]}")
        Membership.objects.create(user=user, tenant=company, role="staff")
        TenantAISettings.objects.create(tenant=company, enabled=True, voice_enabled=True)
        prop = Property.objects.create(
            tenant=company,
            name=f"Cabaña asistente {variant}",
            code="AI",
            capacity=5,
            base_rate="50000.00",
            check_in_time="15:00",
            check_out_time="11:00",
            created_by=user,
        )
        Guest.objects.create(
            tenant=company,
            created_by=user,
            first_name="Persona ficticia IA",
            last_name=variant,
            document_type="passport",
            document_number="FAKE-AI",
        )

    from apps.whatsapp.crypto import encrypt_token
    from apps.whatsapp.models import Connection, Template

    for variant in ("chromium", "mobile"):
        user, created = User.objects.get_or_create(
            email=f"e2e-whatsapp-{variant}@example.invalid",
            defaults={"first_name": "Usuario ficticio WhatsApp"},
        )
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        company = Tenant.objects.create(name=f"Empresa WhatsApp {variant} {uuid4().hex[:8]}")
        Membership.objects.create(user=user, tenant=company, role="staff")
        connection = Connection(
            tenant=company,
            business_id=str(company.pk.int),
            phone_number_id=str(company.pk.int + 1),
            display_phone="999000000001",
            enabled=True,
        )
        connection.access_token_ciphertext = encrypt_token(connection, "e2e-token-not-real")
        connection.save()
        Template.objects.create(
            connection=connection,
            name="consulta_ficticia",
            language="es_CL",
            body="Plantilla ficticia de consulta, sin datos personales.",
            approved=True,
            enabled=True,
            verified_at=timezone.now(),
        )

    for variant in ("chromium", "mobile"):
        user, created = User.objects.get_or_create(email=f"e2e-team-{variant}@example.invalid")
        if created:
            user.set_password("E2E-fictional-passphrase-2026!")
            user.save(update_fields=["password"])
        company = Tenant.objects.create(name=f"Empresa equipo {variant}")
        Membership.objects.create(user=user, tenant=company, role="owner")


if __name__ == "__main__":
    seed()
