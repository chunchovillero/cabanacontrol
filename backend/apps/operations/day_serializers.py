from rest_framework import serializers

from apps.common.serializers import StrictInputMixin


class DayQuerySerializer(StrictInputMixin, serializers.Serializer):
    date = serializers.DateField(required=False)
    kind = serializers.ChoiceField(
        choices=[
            "arrivals",
            "departures",
            "overdue_stays",
            "expired_holds",
            "maintenance",
            "cleaning",
        ],
        default="arrivals",
    )
    property_id = serializers.UUIDField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)


class DayRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    property_name = serializers.CharField()
    property_active = serializers.BooleanField()
    start = serializers.DateField()
    end = serializers.DateField()
    status = serializers.CharField()
    url = serializers.CharField()


class DayResultSerializer(serializers.Serializer):
    date = serializers.DateField()
    timezone = serializers.CharField()
    kind = serializers.CharField()
    counts = serializers.DictField(child=serializers.IntegerField())
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    results = DayRowSerializer(many=True)
