from django.utils import timezone
from rest_framework import serializers

from apps.tenants.models import Invitation, Membership
from apps.tenants.serializers import MembershipSerializer


class TeamMemberSerializer(MembershipSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(MembershipSerializer.Meta):
        fields = ["id", "user_id", "email", "name", "role", "active"]


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError(
                {"non_field_errors": ["La solicitud incluye campos no permitidos."]}
            )
        return super().to_internal_value(data)


class InvitationCreateInput(StrictInput):
    email = serializers.EmailField(max_length=254)
    role = serializers.ChoiceField(choices=[("manager", "Administrador"), ("staff", "Colaborador")])


class MembershipChangeInput(StrictInput):
    role = serializers.ChoiceField(choices=[("manager", "Administrador"), ("staff", "Colaborador")])
    active = serializers.BooleanField()
    expected_role = serializers.ChoiceField(choices=Membership.Role.choices)
    expected_active = serializers.BooleanField()


class InvitationTokenInput(StrictInput):
    token = serializers.RegexField(
        r"^[A-Za-z0-9_-]{43}$", max_length=43, trim_whitespace=False, write_only=True
    )


class InvitationAcceptInput(InvitationTokenInput):
    mode = serializers.ChoiceField(choices=["existing", "new"])
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(
        max_length=256, required=False, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
        if attrs["mode"] == "new":
            if not attrs.get("first_name") or not attrs.get("password"):
                raise serializers.ValidationError("Ingresa tu nombre y contraseña.")
            for field in ("first_name", "last_name"):
                if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in attrs.get(field, "")):
                    raise serializers.ValidationError(
                        "El nombre contiene caracteres no permitidos."
                    )
        elif set(attrs) - {"token", "mode"}:
            raise serializers.ValidationError("Aceptar una cuenta existente no modifica sus datos.")
        return attrs


class InvitationSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = [
            "id",
            "email",
            "role",
            "state",
            "created_at",
            "expires_at",
            "accepted_at",
            "revoked_at",
        ]

    def get_state(self, obj) -> str:
        return (
            "expired" if obj.state == "pending" and obj.expires_at <= timezone.now() else obj.state
        )


class InvitationCreatedSerializer(serializers.Serializer):
    invitation = InvitationSerializer()
    link = serializers.CharField()


class InvitationPreviewSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    role = serializers.CharField()
    email_hint = serializers.CharField()
    expires_at = serializers.DateTimeField()


class InvitationAcceptedSerializer(serializers.Serializer):
    detail = serializers.CharField()
