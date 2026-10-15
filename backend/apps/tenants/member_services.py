import secrets
from datetime import timedelta
from hashlib import sha256

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.billing.services import check_capacity
from apps.tenants.models import Invitation, Membership, Tenant


class MemberConflict(APIException):
    status_code = 409
    default_code = "membership_changed"
    default_detail = "El acceso cambió. Recarga antes de continuar."


def owner_lock(actor, tenant):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied()
    get_object_or_404(Tenant.objects.select_for_update(), pk=tenant.pk, active=True)
    if not Membership.objects.filter(user=actor, tenant=tenant, active=True, role="owner").exists():
        raise PermissionDenied("Solo el propietario puede administrar usuarios.")


@transaction.atomic
def create_invitation(*, actor, tenant, email, role):
    owner_lock(actor, tenant)
    if role not in ("manager", "staff"):
        raise ValidationError("Solo se puede invitar administradores o colaboradores.")
    email = email.strip().lower()
    existing = Membership.objects.filter(tenant=tenant, user__email__iexact=email).first()
    if existing and (existing.active or existing.role == "owner"):
        raise ValidationError("Esta persona ya tiene acceso o una membresía protegida.")
    account = User.objects.filter(email__iexact=email).first()
    if account and not account.is_active:
        raise ValidationError("No se puede invitar esa cuenta. Contacta al administrador.")
    now = timezone.now()
    Invitation.objects.filter(
        tenant=tenant, email=email, state="pending", expires_at__lte=now
    ).update(state="expired")
    if Invitation.objects.filter(tenant=tenant, email=email, state="pending").exists():
        raise ValidationError("Ya hay una invitación pendiente para ese correo. Puedes revocarla.")
    if Invitation.objects.filter(tenant=tenant, state="pending", expires_at__gt=now).count() >= 25:
        raise ValidationError("Hay 25 invitaciones pendientes. Revoca o espera su vencimiento.")
    token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        tenant=tenant,
        email=email,
        role=role,
        created_by=actor,
        token_hash=sha256(token.encode()).hexdigest(),
        expires_at=now + timedelta(hours=72),
    )
    record_event(
        actor=actor,
        tenant=tenant,
        entity="invitation",
        entity_id=invitation.pk,
        action="invitation_created",
        after={"role": role},
    )
    return invitation, token


def available(invitation):
    return (
        invitation.state == "pending"
        and invitation.expires_at > timezone.now()
        and invitation.tenant.active
        and Membership.objects.filter(
            tenant=invitation.tenant,
            user=invitation.created_by,
            user__is_active=True,
            active=True,
            role="owner",
        ).exists()
    )


def lookup_token(token):
    invitation = (
        Invitation.objects.select_related("tenant")
        .filter(token_hash=sha256(token.encode()).hexdigest())
        .first()
    )
    if not invitation or not available(invitation):
        raise ValidationError(
            "La invitación no está disponible. Solicita un nuevo enlace al propietario."
        )
    return invitation


@transaction.atomic
def revoke_invitation(*, actor, tenant, invitation_id):
    owner_lock(actor, tenant)
    invitation = get_object_or_404(
        Invitation.objects.select_for_update(), pk=invitation_id, tenant=tenant
    )
    if invitation.state in ("revoked", "expired"):
        return invitation
    if invitation.state == "accepted":
        raise MemberConflict("La invitación ya fue aceptada. Administra su acceso en Usuarios.")
    invitation.state, invitation.revoked_by, invitation.revoked_at = (
        "revoked",
        actor,
        timezone.now(),
    )
    invitation.save(update_fields=["state", "revoked_by", "revoked_at"])
    record_event(
        actor=actor,
        tenant=tenant,
        entity="invitation",
        entity_id=invitation.pk,
        action="invitation_revoked",
    )
    return invitation


@transaction.atomic
def accept_invitation(*, actor, data):
    initial = lookup_token(data["token"])
    tenant = get_object_or_404(
        Tenant.objects.select_for_update(), pk=initial.tenant_id, active=True
    )
    invitation = Invitation.objects.select_for_update().select_related("tenant").get(pk=initial.pk)
    if not available(invitation):
        raise ValidationError(
            "La invitación no está disponible. Solicita un nuevo enlace al propietario."
        )
    account = User.objects.select_for_update().filter(email__iexact=invitation.email).first()
    if actor.is_authenticated and (not account or actor.pk != account.pk or not actor.is_active):
        raise PermissionDenied("Inicia sesión con la cuenta invitada o cierra tu sesión actual.")
    if data["mode"] == "existing":
        if not actor.is_authenticated or not account or not account.is_active:
            raise PermissionDenied("Inicia sesión con la cuenta invitada para aceptar.")
    else:
        if account:
            raise MemberConflict(
                "Ya tienes una cuenta. Inicia sesión para aceptar sin cambiar tu contraseña."
            )
        account = User(
            email=invitation.email,
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
        )
        try:
            validate_password(data["password"], account)
            account.set_password(data["password"])
            account.full_clean()
            with transaction.atomic():
                account.save()
        except DjangoValidationError as exc:
            raise ValidationError(
                "Revisa tu nombre y usa una contraseña segura de al menos 12 caracteres."
            ) from exc
        except IntegrityError as exc:
            raise MemberConflict("La cuenta ya existe. Inicia sesión para aceptar.") from exc
    membership = Membership.objects.filter(user=account, tenant=tenant).first()
    if membership and (membership.active or membership.role == "owner"):
        raise MemberConflict("Esta cuenta ya tiene acceso o una membresía protegida.")
    check_capacity(tenant, "members")
    if membership:
        membership.role, membership.active = invitation.role, True
        membership.save(update_fields=["role", "active"])
    else:
        membership = Membership.objects.create(user=account, tenant=tenant, role=invitation.role)
    invitation.state, invitation.accepted_by, invitation.accepted_at = (
        "accepted",
        account,
        timezone.now(),
    )
    invitation.membership = membership
    invitation.save(update_fields=["state", "accepted_by", "accepted_at", "membership"])
    record_event(
        actor=account,
        tenant=tenant,
        entity="invitation",
        entity_id=invitation.pk,
        action="invitation_accepted",
        after={"role": membership.role},
    )
    return membership


@transaction.atomic
def change_membership(*, actor, tenant, membership_id, data):
    owner_lock(actor, tenant)
    membership = get_object_or_404(
        Membership.objects.select_for_update(), pk=membership_id, tenant=tenant
    )
    if membership.role == "owner" or membership.user_id == actor.pk:
        raise PermissionDenied("Los propietarios y tu propio acceso están protegidos.")
    if membership.role != data["expected_role"] or membership.active != data["expected_active"]:
        raise MemberConflict()
    if data["role"] not in ("manager", "staff"):
        raise ValidationError("Rol no permitido.")
    if data["active"] and not membership.user.is_active:
        raise ValidationError("La cuenta está desactivada. Contacta al administrador.")
    before = {"role": membership.role, "active": membership.active}
    if data["active"] and not membership.active:
        check_capacity(tenant, "members")
    membership.role, membership.active = data["role"], data["active"]
    membership.save(update_fields=["role", "active"])
    if not membership.active:
        # Do not let an old pending invitation silently restore a revoked access.
        Invitation.objects.filter(
            tenant=tenant, email=membership.user.email, state="pending"
        ).update(
            state="revoked",
            revoked_by=actor,
            revoked_at=timezone.now(),
        )
    record_event(
        actor=actor,
        tenant=tenant,
        entity="membership",
        entity_id=membership.pk,
        action="membership_changed",
        before=before,
        after={"role": membership.role, "active": membership.active},
    )
    return membership
