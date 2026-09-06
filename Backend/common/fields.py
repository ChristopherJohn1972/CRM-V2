import enum

from rest_framework import serializers


class EnumValueMixin:
    """Render enum members as their plain values in API output.

    SQLAlchemy native ``sa.Enum`` returns the Python enum member when read back
    from the database; JSON cannot serialize that directly, so every serializer
    exposing an enum-backed column inherits this mixin.
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if isinstance(value, enum.Enum):
                data[key] = value.value
        return data


class EnumValueField(serializers.CharField):
    def to_representation(self, value):
        return value.value if isinstance(value, enum.Enum) else value
