import sqlalchemy as sa
from django.conf import settings
from django.http import HttpResponse
from pathlib import Path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.access import get_customer_for_request
from common import audit
from common.db import SessionLocal
from common.events import DomainEvent, EventBus
from common.exceptions import NotFoundError, PermissionDeniedError
from documents.models import AccessClassification, Document, DocumentVersion
from documents.serializers import (
    DocumentSerializer,
    DocumentUpdateSerializer,
    DocumentVersionSerializer,
    DocumentWriteSerializer,
)
from documents.services import DocumentService
from documents.storage import LocalFilesystemStorage, get_storage, verify_key_sig

PERMISSION_DOCUMENT_READ = "documents.document.read"
PERMISSION_DOCUMENT_CREATE = "documents.document.create"
PERMISSION_DOCUMENT_UPDATE = "documents.document.update"
PERMISSION_DOCUMENT_DOWNLOAD = "documents.document.download"


def _document_permission_ok(principal, classification):
    if principal.has_permission("documents.document.read"):
        return True
    allow_list = {
        AccessClassification.PUBLIC: "documents.document.read.public",
        AccessClassification.INTERNAL: "documents.document.read.internal",
        AccessClassification.RESTRICTED: "documents.document.read.restricted",
        AccessClassification.CONFIDENTIAL: "documents.document.read.confidential",
    }
    return principal.has_permission(allow_list.get(classification or AccessClassification.INTERNAL))


class DocumentListView(APIView):
    def get(self, request, customer_id):
        principal = request.user
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_DOCUMENT_READ)
            base = sa.select(Document).where(Document.customer_id == customer_id)
            total = db.execute(sa.select(sa.func.count()).select_from(base.subquery())).scalar()
            rows = db.execute(
                base.order_by(sa.desc(Document.created_at))
                .limit(100)
            ).scalars().all()

            current = {}
            if rows:
                current = {
                    v.document_id: v
                    for v in db.execute(
                        sa.select(DocumentVersion).where(
                            DocumentVersion.document_id.in_([d.document_id for d in rows]),
                            DocumentVersion.is_current == sa.true(),
                        )
                    ).scalars().all()
                }
            data = DocumentSerializer(rows, many=True, context={"version_map": current}).data
            return Response({"count": total, "results": data})
        finally:
            db.close()

    def post(self, request, customer_id):
        principal = request.user
        db = SessionLocal()
        db.info["request"] = request
        db.info["actor_user_id"] = principal.user_id
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_DOCUMENT_CREATE)

            serializer = DocumentWriteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            file_field = request.FILES.get("file")
            if file_field is None:
                raise NotFoundError("A 'file' multipart field is required.")

            mime_type = file_field.content_type or ""
            file_name = file_field.name or "unnamed"

            document, version = DocumentService.create_document(
                db,
                customer_id=customer_id,
                document_type=serializer.validated_data["document_type"],
                file_name=file_name,
                mime_type=mime_type,
                data=file_field.read(),
                access_classification=serializer.validated_data.get("access_classification"),
                actor_user_id=principal.user_id,
                expires_at=serializer.validated_data.get("expires_at"),
            )
            db.commit()

            EventBus.publish(
                DomainEvent(
                    event_type="DocumentUploaded",
                    customer_id=customer_id,
                    source_module="documents",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"Document {file_name} uploaded (v{version.version_num})",
                    reference_type="documents",
                    reference_id=document.document_id,
                )
            )
            return Response(
                DocumentSerializer(document, context={"version_map": {document.document_id: version}}).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            db.close()


class DocumentDetailView(APIView):
    def _get(self, db, request, customer_id, document_id):
        document = db.get(Document, document_id)
        if document is None or document.customer_id != customer_id:
            raise NotFoundError("Document not found.")
        get_customer_for_request(db, request, customer_id, permission=PERMISSION_DOCUMENT_READ)
        if not _document_permission_ok(request.user, document.access_classification):
            raise PermissionDeniedError()
        return document

    def get(self, request, customer_id, document_id):
        db = SessionLocal()
        try:
            document = self._get(db, request, customer_id, document_id)
            version = db.execute(
                sa.select(DocumentVersion).where(
                    DocumentVersion.document_id == document.document_id,
                    DocumentVersion.is_current == sa.true(),
                )
            ).scalar_one_or_none()
            return Response(
                DocumentSerializer(document, context={"version_map": {document.document_id: version}}).data
            )
        finally:
            db.close()

    def post(self, request, customer_id, document_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_DOCUMENT_CREATE):
            raise PermissionDeniedError()
        db = SessionLocal()
        db.info["request"] = request
        try:
            document = self._get(db, request, customer_id, document_id)

            file_field = request.FILES.get("file")
            if file_field is None:
                raise NotFoundError("A 'file' multipart field is required.")

            serializer = DocumentWriteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            document, version = DocumentService.add_version(
                db,
                document=document,
                file_name=file_field.name or "unnamed",
                mime_type=file_field.content_type or "",
                data=file_field.read(),
                access_classification=serializer.validated_data.get("access_classification"),
                actor_user_id=principal.user_id,
                expires_at=serializer.validated_data.get("expires_at"),
            )
            db.commit()
            EventBus.publish(
                DomainEvent(
                    event_type="DocumentVersionUploaded",
                    customer_id=document.customer_id,
                    source_module="documents",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"New version v{version.version_num} of {version.file_name}",
                    reference_type="documents",
                    reference_id=document.document_id,
                )
            )
            return Response(
                DocumentSerializer(document, context={"version_map": {document.document_id: version}}).data
            )
        finally:
            db.close()

    def patch(self, request, customer_id, document_id):
        principal = request.user
        serializer = DocumentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        db.info["request"] = request
        try:
            document = self._get(db, request, customer_id, document_id)
            if not principal.has_permission(PERMISSION_DOCUMENT_UPDATE):
                raise PermissionDeniedError()
            for key, value in serializer.validated_data.items():
                setattr(document, key, value)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="document.updated",
                resource_type="documents",
                resource_id=document.document_id,
                description=f"Document {document.document_id} metadata updated",
                request=request,
            )
            db.commit()
            version = db.execute(
                sa.select(DocumentVersion).where(
                    DocumentVersion.document_id == document.document_id,
                    DocumentVersion.is_current == sa.true(),
                )
            ).scalar_one_or_none()
            return Response(
                DocumentSerializer(document, context={"version_map": {document.document_id: version}}).data
            )
        finally:
            db.close()


class DocumentDownloadView(APIView):
    def get(self, request, customer_id, document_id, version_num=None):
        principal = request.user
        db = SessionLocal()
        db.info["request"] = request
        db.info["actor_user_id"] = principal.user_id
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_DOCUMENT_DOWNLOAD)
            document = db.get(Document, document_id)
            if document is None or document.customer_id != customer_id:
                raise NotFoundError("Document not found.")
            if not _document_permission_ok(principal, document.access_classification):
                raise PermissionDeniedError()
            url = DocumentService.download_url(
                db,
                document=document,
                version_num=version_num,
                expires=settings.S3_PRESIGNED_URL_TTL,
            )
            return Response(url)
        finally:
            db.close()


class DocumentVersionListView(APIView):
    def get(self, request, customer_id, document_id):
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_DOCUMENT_READ)
            document = db.get(Document, document_id)
            if document is None or document.customer_id != customer_id:
                raise NotFoundError("Document not found.")
            if not _document_permission_ok(request.user, document.access_classification):
                raise PermissionDeniedError()
            versions = db.execute(
                sa.select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.version_num)
            ).scalars().all()
            return Response(DocumentVersionSerializer(versions, many=True).data)
        finally:
            db.close()


class DocumentServeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        db = SessionLocal()
        try:
            storage = get_storage()
            if not isinstance(storage, LocalFilesystemStorage):
                raise NotFoundError("This environment does not serve documents directly.")

            key = request.query_params.get("key")
            expires = request.query_params.get("expires")
            sig = request.query_params.get("sig")
            if not key or not expires or not sig:
                raise NotFoundError("Invalid download link.")

            try:
                expires_epoch = int(expires)
            except (TypeError, ValueError):
                expires_epoch = 0

            import time

            if expires_epoch < int(time.time()):
                raise PermissionDeniedError("Download link has expired.")
            if not verify_key_sig(key, expires_epoch, sig):
                raise PermissionDeniedError("Invalid download link.")

            data = storage.read(key)
            response = HttpResponse(data, content_type="application/octet-stream")
            from urllib.parse import unquote

            response["Content-Disposition"] = (
                f'attachment; filename="{unquote(Path(key).name)}"'
            )
            return response
        finally:
            db.close()