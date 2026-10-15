from rest_framework import serializers

from apps.tenants.models import Membership, Tenant


class TenantSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = ["id", "name", "timezone", "currency", "role"]

    def get_role(self, obj) -> str:
        return self.context["membership"].role


class MembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "user_id", "name", "role", "active"]

    def get_name(self, obj) -> str:
        return obj.user.get_full_name()
