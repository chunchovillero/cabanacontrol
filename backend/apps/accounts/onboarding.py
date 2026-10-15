"""Local owner onboarding. Production registration remains disabled."""

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import MessageSerializer
from apps.accounts.throttling import consume_limit
from apps.audit.services import record_event
from apps.tenants.models import Membership, Tenant


def enabled():
    return settings.LOCAL_ONBOARDING_ENABLED and settings.DEBUG


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, default="", allow_blank=True)
    company_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise ValidationError({"non_field_errors": ["Campos no permitidos."]})
        return super().to_internal_value(data)

    def validate(self, data):
        for key in ("first_name", "last_name", "company_name"):
            if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in data[key]):
                raise ValidationError({key: "El texto contiene caracteres no permitidos."})
        data["email"] = data["email"].lower()
        user = User(email=data["email"], first_name=data["first_name"], last_name=data["last_name"])
        try:
            validate_password(data["password"], user)
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages}) from exc
        return data


def register_owner(data):
    try:
        with transaction.atomic():
            if User.objects.filter(email__iexact=data["email"]).exists():
                raise ValidationError(
                    {"email": "No se pudo crear esta cuenta. Inicia sesión o recupera tu acceso."}
                )
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
            )
            tenant = Tenant(name=data["company_name"], timezone="America/Santiago", currency="CLP")
            tenant.full_clean()
            tenant.save()
            Membership.objects.create(user=user, tenant=tenant, role=Membership.Role.OWNER)
            record_event(
                actor=user,
                tenant=tenant,
                entity="tenant",
                entity_id=tenant.pk,
                action="owner_registered_local",
            )
    except IntegrityError as exc:
        raise ValidationError(
            {"email": "No se pudo crear esta cuenta. Inicia sesión o recupera tu acceso."}
        ) from exc


class RegistrationOptionsSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()


@method_decorator(csrf_protect, name="dispatch")
class RegistrationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=RegistrationOptionsSerializer)
    def get(self, request):
        return Response({"enabled": enabled()})

    @extend_schema(request=RegistrationSerializer, responses={201: MessageSerializer})
    def post(self, request):
        if not enabled():
            raise PermissionDenied("El alta web no está disponible en este entorno.")
        if request.user.is_authenticated:
            raise PermissionDenied("Cierra tu sesión para registrar una cuenta nueva.")
        consume_limit("register:ip", request.META.get("REMOTE_ADDR", "unknown"), 5)
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        register_owner(serializer.validated_data)
        return Response(
            {"detail": "Cuenta y empresa creadas. Ya puedes iniciar sesión."}, status=201
        )
