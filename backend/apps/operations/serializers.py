from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.operations.models import HousekeepingTask


class TaskSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(read_only=True)
    reservation_id = serializers.UUIDField(read_only=True, allow_null=True)
    assigned_to_id = serializers.UUIDField(read_only=True, allow_null=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    assigned_name = serializers.SerializerMethodField()

    class Meta:
        model = HousekeepingTask
        fields = [
            "id",
            "property_id",
            "property_name",
            "reservation_id",
            "assigned_to_id",
            "assigned_name",
            "source",
            "status",
            "due_at",
            "bathroom",
            "kitchen",
            "bedrooms",
            "inventory",
            "notes",
            "cancel_reason",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assigned_name(self, obj) -> str | None:
        if not obj.assigned_to_id:
            return None
        return obj.assigned_to.user.first_name or "Integrante de la empresa"


class TaskWriteSerializer(StrictInputMixin, serializers.Serializer):
    property_id = serializers.UUIDField(required=False)
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    cancel_reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=HousekeepingTask.Status.choices, required=False)
    bathroom = serializers.BooleanField(required=False)
    kitchen = serializers.BooleanField(required=False)
    bedrooms = serializers.BooleanField(required=False)
    inventory = serializers.BooleanField(required=False)

    def validate_due_at(self, value):
        raw = self.initial_data.get("due_at", "")
        if isinstance(raw, str) and not (raw.endswith("Z") or "+" in raw[10:] or "-" in raw[10:]):
            raise serializers.ValidationError("Incluye zona horaria explícita.")
        return value


class TaskQuerySerializer(StrictInputMixin, serializers.Serializer):
    status = serializers.ChoiceField(choices=HousekeepingTask.Status.choices, required=False)
    property_id = serializers.UUIDField(required=False)
    assigned_to_id = serializers.UUIDField(required=False)
    page = serializers.IntegerField(min_value=1, required=False)


class TaskCreateSerializer(TaskWriteSerializer):
    property_id = serializers.UUIDField()
    due_at = serializers.DateTimeField()


class AssigneeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(source="user.first_name")
