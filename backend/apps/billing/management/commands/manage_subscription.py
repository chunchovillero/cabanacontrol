import json

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.billing.services import CATALOG, assign_plan, enable_limits, snapshot
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Revisa uso, asigna plan manual o habilita límites por empresa; no cobra."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["review", "assign", "enable"])
        parser.add_argument("--tenant-id")
        parser.add_argument("--actor-email")
        parser.add_argument("--plan", choices=CATALOG)
        parser.add_argument("--reason")

    def handle(self, *args, **options):
        if not options["tenant_id"]:
            if options["action"] != "review":
                raise CommandError("Indica --tenant-id para cambiar una suscripción.")
            for tenant in Tenant.objects.filter(active=True).order_by("id"):
                self.stdout.write(
                    json.dumps(
                        {"tenant_id": str(tenant.pk), **snapshot(tenant)},
                        default=str,
                        ensure_ascii=False,
                    )
                )
            return
        try:
            tenant = Tenant.objects.get(pk=options["tenant_id"], active=True)
        except (Tenant.DoesNotExist, DjangoValidationError) as exc:
            raise CommandError("Empresa activa no encontrada.") from exc
        action = options["action"]
        if action != "review":
            if not options["actor_email"] or not options["reason"]:
                raise CommandError("Indica --actor-email y --reason sin datos personales.")
            actor = User.objects.filter(
                email__iexact=options["actor_email"], is_active=True, is_platform_admin=True
            ).first()
            if not actor:
                raise CommandError("Requiere administrador de plataforma activo.")
            try:
                if action == "assign":
                    if not options["plan"]:
                        raise CommandError("Indica --plan.")
                    assign_plan(
                        actor=actor, tenant=tenant, code=options["plan"], reason=options["reason"]
                    )
                else:
                    enable_limits(actor=actor, tenant=tenant, reason=options["reason"])
            except APIException as exc:
                raise CommandError(str(exc.detail)) from exc
        self.stdout.write(
            json.dumps(
                {"tenant_id": str(tenant.pk), **snapshot(tenant)}, default=str, ensure_ascii=False
            )
        )
