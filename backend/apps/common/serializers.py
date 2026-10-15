from collections.abc import Mapping

from rest_framework import serializers


class StrictInputMixin:
    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        allowed = {name for name, field in self.fields.items() if not field.read_only}
        unexpected = set(data) - allowed
        if unexpected:
            raise serializers.ValidationError(
                {key: "Este campo no se puede enviar." for key in sorted(unexpected)}
            )
        return super().to_internal_value(data)
