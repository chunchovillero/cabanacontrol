from rest_framework import serializers

from apps.common.serializers import StrictInputMixin


class PeriodQuerySerializer(StrictInputMixin, serializers.Serializer):
    property_id = serializers.UUIDField(required=False)

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.DateField()
        fields["to"] = serializers.DateField()
        return fields

    def validate(self, attrs):
        if attrs["to"] <= attrs["from"] or (attrs["to"] - attrs["from"]).days > 366:
            raise serializers.ValidationError(
                "El periodo debe ser positivo y de hasta 366 días, con fin exclusivo."
            )
        return attrs


class CalendarEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    kind = serializers.ChoiceField(choices=["reservation", "block"])
    entity_id = serializers.UUIDField()
    property_id = serializers.UUIDField()
    property_name = serializers.CharField()
    property_active = serializers.BooleanField()
    title = serializers.CharField()
    start = serializers.DateField()
    end = serializers.DateField()
    status = serializers.CharField()
    blocks_inventory = serializers.BooleanField()
    url = serializers.CharField()


class CalendarResultSerializer(serializers.Serializer):
    timezone = serializers.CharField()
    events = CalendarEventSerializer(many=True)


class MoneyMetricsSerializer(serializers.Serializer):
    currency = serializers.CharField()
    collected = serializers.CharField()
    agreed = serializers.CharField()
    outstanding = serializers.CharField()
    credit = serializers.CharField()


class TodayMetricsSerializer(serializers.Serializer):
    date = serializers.DateField()
    active_properties = serializers.IntegerField()
    occupied = serializers.IntegerField()
    retained = serializers.IntegerField()
    blocked = serializers.IntegerField()
    available = serializers.IntegerField()
    arrivals = serializers.IntegerField()
    departures = serializers.IntegerField()


class DashboardResultSerializer(serializers.Serializer):
    timezone = serializers.CharField()
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    today = TodayMetricsSerializer()
    occupied_nights = serializers.IntegerField()
    capacity_nights = serializers.IntegerField()
    occupancy_percent = serializers.CharField()
    blocked_nights = serializers.IntegerField()
    money = MoneyMetricsSerializer(many=True)
