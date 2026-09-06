from rest_framework import serializers

from common.fields import EnumValueField

ACCESS_CLASSIFICATIONS = ["PUBLIC", "INTERNAL", "RESTRICTED", "CONFIDENTIAL"]


class DocumentVersionSerializer(serializers.Serializer):
    document_version_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    version_num = serializers.IntegerField()
    file_name = serializers.CharField()
    mime_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    checksum = serializers.CharField()
    uploaded_by = serializers.IntegerField()
    scan_status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    is_current = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class DocumentSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    document_type = serializers.CharField()
    current_version = serializers.IntegerField()
    access_classification = serializers.CharField()
    uploaded_by = serializers.IntegerField()
    current_file_name = serializers.SerializerMethodField()
    current_mime_type = serializers.SerializerMethodField()
    current_size_bytes = serializers.SerializerMethodField()
    current_checksum = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def _current_version(self, obj):
        return self.context.get("version_map", {}).get(obj.document_id)

    def get_current_file_name(self, obj):
        version = self._current_version(obj)
        return version.file_name if version else None

    def get_current_mime_type(self, obj):
        version = self._current_version(obj)
        return version.mime_type if version else None

    def get_current_size_bytes(self, obj):
        version = self._current_version(obj)
        return version.size_bytes if version else None

    def get_current_checksum(self, obj):
        version = self._current_version(obj)
        return version.checksum if version else None

    def get_download_url(self, obj):
        return f"/api/clients/{obj.customer_id}/documents/{obj.document_id}/download"


class DocumentWriteSerializer(serializers.Serializer):
    document_type = serializers.CharField(max_length=50)
    access_classification = serializers.ChoiceField(
        choices=ACCESS_CLASSIFICATIONS, required=False, default="INTERNAL"
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class DocumentUpdateSerializer(serializers.Serializer):
    document_type = serializers.CharField(max_length=50, required=False)
    access_classification = serializers.ChoiceField(
        choices=ACCESS_CLASSIFICATIONS, required=False
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)