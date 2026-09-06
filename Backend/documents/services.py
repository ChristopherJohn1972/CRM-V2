import hashlib
import logging

import sqlalchemy as sa

from documents.models import Document, DocumentVersion, DocumentType
from documents.storage import get_storage
from common import audit
from common.exceptions import APIError, NotFoundError

logger = logging.getLogger(__name__)


class DocumentService:
    DISALLOWED_MIME_TYPES_RULE = None
    MAX_SIZE_BYTES = 25 * 1024 * 1024
    ALLOWED_MIME_TYPES = None

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _validate_file(data: bytes, mime_type: str, file_name: str):
        if len(data) > DocumentService.MAX_SIZE_BYTES:
            raise APIError(
                f"File exceeds maximum size of {DocumentService.MAX_SIZE_BYTES} bytes.",
                status_code=413,
                error_code="file_too_large",
            )
        if DocumentService.ALLOWED_MIME_TYPES:
            normalized = mime_type.split(";")[0].strip().lower()
            if normalized not in DocumentService.ALLOWED_MIME_TYPES:
                raise APIError(
                    f"File type '{normalized}' is not allowed.",
                    status_code=415,
                    error_code="unsupported_media_type",
                )

    @classmethod
    def create_document(cls, db, *, customer_id, document_type, file_name, mime_type,
                        data, access_classification, actor_user_id, expires_at=None):
        doc_type = db.execute(
            sa.select(DocumentType).where(
                DocumentType.code == document_type,
                DocumentType.is_active == sa.true(),
            )
        ).scalar_one_or_none()
        if doc_type is None:
            raise NotFoundError(f"Document type '{document_type}' is not configured.")

        cls._validate_file(data, mime_type, file_name)

        document = Document(
            customer_id=customer_id,
            document_type=document_type,
            access_classification=access_classification or "INTERNAL",
            uploaded_by=actor_user_id,
            current_version=1,
        )
        db.add(document)
        db.flush()

        storage_key = (
            f"customers/{customer_id}/documents/{document.document_id}/v1/{file_name}"
        )
        checksum = cls._sha256(data)

        get_storage().put(storage_key, data, content_type=mime_type)

        version = DocumentVersion(
            document_id=document.document_id,
            version_num=1,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=len(data),
            checksum=checksum,
            storage_key=storage_key,
            uploaded_by=actor_user_id,
            expires_at=expires_at,
            is_current=True,
        )
        db.add(version)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="document.uploaded",
            resource_type="documents",
            resource_id=document.document_id,
            description=f"Document {file_name} uploaded (v1)",
            metadata={"file_name": file_name, "size_bytes": len(data), "checksum": checksum},
            request=db.info.get("request"),
        )
        return document, version

    @classmethod
    def add_version(cls, db, *, document, file_name, mime_type, data,
                    access_classification=None, actor_user_id, expires_at=None, request=None):
        if access_classification:
            document.access_classification = access_classification

        cls._validate_file(data, mime_type, file_name)

        old_versions = db.execute(
            sa.select(DocumentVersion).where(DocumentVersion.document_id == document.document_id)
        ).scalars().all()
        new_num = max((v.version_num for v in old_versions), default=0) + 1

        storage_key = (
            f"customers/{document.customer_id}/documents/{document.document_id}/v{new_num}/{file_name}"
        )
        checksum = cls._sha256(data)
        get_storage().put(storage_key, data, content_type=mime_type)

        version = DocumentVersion(
            document_id=document.document_id,
            version_num=new_num,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=len(data),
            checksum=checksum,
            storage_key=storage_key,
            uploaded_by=actor_user_id,
            expires_at=expires_at,
            is_current=True,
        )
        for old in old_versions:
            old.is_current = False
        document.current_version = new_num
        db.add(version)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="document.version_created",
            resource_type="documents",
            resource_id=document.document_id,
            description=f"New version v{new_num} for document {document.document_id}",
            metadata={"file_name": file_name, "size_bytes": len(data)},
            request=request or db.info.get("request"),
        )
        return document, version

    @staticmethod
    def download_url(db, *, document, version_num=None, expires=300, request=None):
        if version_num is None:
            version = db.execute(
                sa.select(DocumentVersion).where(
                    DocumentVersion.document_id == document.document_id,
                    DocumentVersion.is_current == sa.true(),
                )
            ).scalar_one_or_none()
        else:
            version = db.execute(
                sa.select(DocumentVersion).where(
                    DocumentVersion.document_id == document.document_id,
                    DocumentVersion.version_num == version_num,
                )
            ).scalar_one_or_none()
        if version is None:
            raise NotFoundError("Document version not found.")

        url = get_storage().download_url(version.storage_key, expires)

        audit.record_audit(
            db,
            actor_user_id=db.info.get("actor_user_id"),
            action="document.downloaded",
            resource_type="documents",
            resource_id=document.document_id,
            description=f"Download v{version.version_num} of {version.file_name}",
            metadata={"version": version.version_num},
            request=request or db.info.get("request"),
        )
        db.commit()
        return {"url": url, "version": version.version_num, "expires_in": expires}