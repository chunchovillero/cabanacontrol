from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.audit.services import record_event


class Command(BaseCommand):
    help = "Crea una cuenta normal, sin privilegios de plataforma. Contraseña interactiva."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")

    def handle(self, *args, **options):
        user = User(
            email=options["email"].strip().lower(),
            first_name=options["first_name"],
            last_name=options["last_name"],
        )
        password = getpass("Contraseña (mínimo 12 caracteres): ")
        if password != getpass("Repite la contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
            with transaction.atomic():
                user.save()
                record_event(
                    actor=user, entity="user", entity_id=user.pk, action="account_created_cli"
                )
        except (ValidationError, IntegrityError) as exc:
            raise CommandError(
                "No se pudo crear la cuenta. Revisa correo, duplicados y fortaleza de contraseña."
            ) from exc
        self.stdout.write(self.style.SUCCESS(f"Cuenta creada: {user.pk}"))
