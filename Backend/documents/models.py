import sqlalchemy as sa

from common.base import TimestampMixin
from common.db import Base


class DocumentType(Base):
    __tablename__ = "document_types"

    document_type_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(100), nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class AccessClassification:
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class ScanStatus:
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    document_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    document_type = sa.Column(sa.String(50), nullable=False)
    current_version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    access_classification = sa.Column(
        sa.String(20), nullable=False, server_default=AccessClassification.INTERNAL
    )
    uploaded_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    document_version_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    document_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False
    )
    version_num = sa.Column(sa.Integer, nullable=False)
    file_name = sa.Column(sa.String(255), nullable=False)
    mime_type = sa.Column(sa.String(120), nullable=False)
    size_bytes = sa.Column(sa.BigInteger, nullable=False)
    checksum = sa.Column(sa.String(64), nullable=False)
    storage_key = sa.Column(sa.String(500), nullable=False)
    uploaded_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    scan_status = sa.Column(sa.String(20), nullable=False, server_default=ScanStatus.PENDING)
    expires_at = sa.Column(sa.DateTime)
    is_current = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
