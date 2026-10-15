from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.accounts.models import User
from apps.audit.services import record_event


def sign_in(request, *, email: str, password: str):
    user = authenticate(request=request, email=email.strip().lower(), password=password)
    if user is None:
        raise AuthenticationFailed("Correo o contraseña incorrectos.")
    login(request, user)
    # Nunca conservar el contexto de una sesión anterior al cambiar de usuario.
    request.session.pop("active_tenant_id", None)
    request.tenant = None
    request.membership = None
    record_event(actor=user, entity="session", action="login")
    return user


def sign_out(request):
    record_event(actor=request.user, entity="session", action="logout")
    logout(request)
    request.membership = None
    request.tenant = None


def request_password_reset(email: str):
    # Trabajo constante de hash incluso si no existe cuenta; respuesta siempre genérica.
    make_password("reset-request-timing-padding")
    user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if user is None or not user.has_usable_password():
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    fragment = urlencode({"uid": uid, "token": token})
    link = f"{settings.FRONTEND_URL}/restablecer#{fragment}"
    try:
        send_mail(
            "Restablece tu contraseña de CabañaControl",
            f"Para definir una nueva contraseña, abre este enlace:\n\n{link}\n\n"
            "El enlace vence en una hora. Si no lo solicitaste, ignora este correo.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
    except (SMTPException, OSError):
        record_event(
            actor=user, entity="user", entity_id=user.pk, action="password_reset_delivery_failed"
        )
        return
    record_event(actor=user, entity="user", entity_id=user.pk, action="password_reset_requested")


def password_reset_user(uid: str, token: str):
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.filter(pk=pk, is_active=True).first()
    except (ValueError, TypeError, UnicodeDecodeError, OverflowError, DjangoValidationError):
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        raise ValidationError("El enlace no es válido o ha vencido.")
    return user


@transaction.atomic
def confirm_password_reset(user, token: str, password: str):
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if not locked_user.is_active or not default_token_generator.check_token(locked_user, token):
        raise ValidationError("El enlace no es válido o ha vencido.")
    locked_user.set_password(password)
    locked_user.save(update_fields=["password"])
    record_event(
        actor=locked_user, entity="user", entity_id=user.pk, action="password_reset_completed"
    )
