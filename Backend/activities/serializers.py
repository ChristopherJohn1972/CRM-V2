from rest_framework import serializers

from common.fields import EnumValueField, EnumValueMixin


class ActivitySerializer(serializers.Serializer):
    activity_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    activity_type = serializers.CharField()
    subject = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    due_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()
    assigned_to = serializers.IntegerField()
    created_by = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ActivityWriteSerializer(serializers.Serializer):
    activity_type = serializers.CharField(max_length=50)
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(max_length=20, required=False, default="OPEN")
    priority = serializers.CharField(max_length=20, required=False, allow_null=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    assigned_to = serializers.IntegerField(required=False, allow_null=True)


class NoteSerializer(serializers.Serializer):
    note_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    activity_id = serializers.IntegerField()
    author_user_id = serializers.IntegerField()
    author_name = serializers.SerializerMethodField()
    visibility = serializers.CharField()
    body = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_author_name(self, obj):
        user = self.context.get("user_map", {}).get(obj.author_user_id)
        if user is None:
            return None
        return f"{user.first_name} {user.last_name}".strip()


class NoteWriteSerializer(serializers.Serializer):
    body = serializers.CharField()
    visibility = serializers.ChoiceField(
        choices=["PRIVATE", "TEAM", "PUBLIC"], required=False, default="TEAM"
    )
    activity_id = serializers.IntegerField(required=False, allow_null=True)


class TimelineEventSerializer(EnumValueMixin, serializers.Serializer):
    event_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    actor_type = EnumValueField()
    actor_user_id = serializers.IntegerField()
    actor_name = serializers.SerializerMethodField()
    actor_label = serializers.CharField()
    source_module = serializers.CharField()
    event_type = serializers.CharField()
    summary = serializers.CharField()
    reference_type = serializers.CharField()
    reference_id = serializers.IntegerField()
    occurred_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()

    def get_actor_name(self, obj):
        user = self.context.get("user_map", {}).get(obj.actor_user_id)
        if user is None:
            return None
        return f"{user.first_name} {user.last_name}".strip()