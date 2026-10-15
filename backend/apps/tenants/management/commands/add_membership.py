from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.billing.services import check_capacity, lock_tenant
from apps.tenants.models import Membership, Tenant


class Command(BaseCommand):
    help = "Agrega una nueva membresía; no modifica ni reemplaza una existente."

    def add_arguments(self, parser):
        parser.add_argument("--user-email", required=True)
        parser.add_argument("--tenant-id", required=True)
        parser.add_argument("--role", required=True, choices=Membership.Role.values)

    @transaction.atomic
    def handle(self, *args, **options):
        user = User.objects.filter(
            email__iexact=options["user_email"].strip(), is_active=True
        ).first()
        try:
            tenant = Tenant.objects.filter(pk=options["tenant_id"], active=True).first()
        except ValidationError as exc:
            raise CommandError("ID de empresa no válido.") from exc
        if user is None or tenant is None:
            raise CommandError("La cuenta y la empresa deben existir y estar activas.")
        lock_tenant(tenant)
        if Membership.objects.filter(user=user, tenant=tenant).exists():
            raise CommandError("La membresía ya existe; no se modificó.")
        try:
            check_capacity(tenant, "members")
        except APIException as exc:
            raise CommandError(str(exc.detail)) from exc
        membership, created = Membership.objects.get_or_create(
            user=user, tenant=tenant, defaults={"role": options["role"]}
        )
        if not created:
            raise CommandError("La membresía ya existe; no se modificó.")
        record_event(
            actor=None,
            tenant=tenant,
            entity="membership",
            entity_id=membership.pk,
            action="membership_created_cli",
        )
        self.stdout.write(self.style.SUCCESS(f"Membresía creada: {membership.pk}"))
