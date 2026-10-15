from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.billing.simulation import prepare_company, renew_due
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Habilita empresa ficticia o procesa vencimiento, exclusivamente en simulación local."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["prepare", "renew"])
        parser.add_argument("--tenant-id", required=True)
        parser.add_argument("--actor-email", required=True)
        parser.add_argument("--reason", default="")
        parser.add_argument("--retry-rejected", action="store_true")

    def handle(self, *args, **options):
        actor = User.objects.filter(
            email__iexact=options["actor_email"], is_active=True, is_platform_admin=True
        ).first()
        if not actor:
            raise CommandError("Requiere administrador de plataforma activo.")
        try:
            tenant = Tenant.objects.get(pk=options["tenant_id"], active=True)
            if options["action"] == "prepare":
                prepare_company(actor=actor, tenant=tenant, reason=options["reason"])
                self.stdout.write("Empresa ficticia preparada; no se contrató ni cobró.")
            else:
                attempt = renew_due(actor=actor, tenant=tenant, retry=options["retry_rejected"])
                self.stdout.write(
                    f"Intento simulado: {attempt.pk}"
                    if attempt
                    else "Sin renovación pendiente o cancelación procesada."
                )
        except (Tenant.DoesNotExist, ValidationError, APIException) as exc:
            raise CommandError(str(getattr(exc, "detail", "Empresa inválida."))) from exc
