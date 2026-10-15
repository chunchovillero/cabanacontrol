from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.tenants.models import Membership, Tenant


class Command(BaseCommand):
    help = "Crea una empresa y vincula como propietario una cuenta activa existente."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--owner-email", required=True)
        parser.add_argument("--timezone", default="America/Santiago")

    @transaction.atomic
    def handle(self, *args, **options):
        owner = User.objects.filter(
            email__iexact=options["owner_email"].strip(), is_active=True
        ).first()
        if owner is None:
            raise CommandError("Primero crea una cuenta activa con create_account.")
        tenant = Tenant(name=options["name"], timezone=options["timezone"])
        try:
            tenant.full_clean()
        except ValidationError as exc:
            raise CommandError("Nombre o zona horaria no válidos.") from exc
        tenant.save()
        Membership.objects.create(user=owner, tenant=tenant, role=Membership.Role.OWNER)
        record_event(
            actor=owner,
            tenant=tenant,
            entity="tenant",
            entity_id=tenant.pk,
            action="tenant_created_cli",
        )
        self.stdout.write(self.style.SUCCESS(f"Empresa creada: {tenant.pk}"))
