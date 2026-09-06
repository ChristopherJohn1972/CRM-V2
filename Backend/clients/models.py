import sqlalchemy as sa

from clients.enums import (
    AccountNumberStatus,
    AddressType,
    CustomerStatus,
    CustomerType,
)
from common.base import TimestampMixin
from common.db import Base


class Branch(Base):
    __tablename__ = "branches"

    branch_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(100), nullable=False)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    department_id = sa.Column(sa.BigInteger, sa.ForeignKey("departments.department_id", ondelete="SET NULL"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Customer(Base):
    __tablename__ = "customers"

    customer_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_number = sa.Column(sa.String(50), nullable=False, unique=True)
    account_number_status = sa.Column(
        sa.Enum(AccountNumberStatus), nullable=False, server_default=AccountNumberStatus.ACTIVE.value
    )
    customer_type = sa.Column(sa.Enum(CustomerType), nullable=False, server_default=CustomerType.BUSINESS.value)

    first_name = sa.Column(sa.String(100))
    middle_name = sa.Column(sa.String(100))
    last_name = sa.Column(sa.String(100))
    legal_name = sa.Column(sa.String(255))
    display_name = sa.Column(sa.String(255))

    email = sa.Column(sa.String(255))
    phone = sa.Column(sa.String(50))

    customer_category = sa.Column(sa.String(100))
    segment = sa.Column(sa.String(100))
    industry = sa.Column(sa.String(150))

    registration_number = sa.Column(sa.String(100))
    tax_identifier = sa.Column(sa.String(100))

    status = sa.Column(sa.Enum(CustomerStatus), nullable=False, server_default=CustomerStatus.PROSPECT.value)
    status_reason = sa.Column(sa.String(255))

    assigned_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    assigned_team_id = sa.Column(sa.BigInteger, sa.ForeignKey("teams.team_id", ondelete="SET NULL"))
    branch_id = sa.Column(sa.BigInteger, sa.ForeignKey("branches.branch_id", ondelete="SET NULL"))

    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    deleted_at = sa.Column(sa.DateTime)
    deleted_by = sa.Column(sa.BigInteger)
    version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))

    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    SENSITIVE_FIELDS = ("tax_identifier", "registration_number")

    @property
    def is_individual(self):
        return self.customer_type == CustomerType.INDIVIDUAL.value

    def get_display_name(self):
        if self.is_individual:
            parts = [p for p in (self.first_name, self.middle_name, self.last_name) if p]
            return " ".join(parts) if parts else (self.legal_name or "")
        return self.legal_name or ""


class CustomerAddress(Base, TimestampMixin):
    __tablename__ = "customer_addresses"

    address_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    address_type = sa.Column(sa.Enum(AddressType), nullable=False, server_default=AddressType.OFFICE.value)
    address = sa.Column(sa.String(255), nullable=False)
    # Deprecated columns retained for historical data; no longer written.
    address_line_1 = sa.Column(sa.String(255))
    address_line_2 = sa.Column(sa.String(255))
    city = sa.Column(sa.String(100))
    state_province = sa.Column(sa.String(100))
    postal_code = sa.Column(sa.String(30))
    country = sa.Column(sa.String(100))
    is_primary = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("0"))


class ContactRole(Base):
    __tablename__ = "contact_roles"

    contact_role_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(100), nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CustomerContact(Base, TimestampMixin):
    __tablename__ = "customer_contacts"

    contact_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    first_name = sa.Column(sa.String(100), nullable=False)
    last_name = sa.Column(sa.String(100), nullable=False)
    job_title = sa.Column(sa.String(150))
    email = sa.Column(sa.String(255))
    phone = sa.Column(sa.String(50))
    mobile = sa.Column(sa.String(50))
    role_id = sa.Column(sa.BigInteger, sa.ForeignKey("contact_roles.contact_role_id", ondelete="SET NULL"))
    is_primary = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("0"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))


class RelationshipType(Base):
    __tablename__ = "relationship_types"

    relationship_type_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(100), nullable=False)
    bidirectional = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("0"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CustomerRelationship(Base):
    __tablename__ = "customer_relationships"

    relationship_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    related_customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    relationship_type = sa.Column(sa.String(100), nullable=False)
    description = sa.Column(sa.String(255))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint(
            "customer_id",
            "related_customer_id",
            "relationship_type",
            name="uq_customer_relationship",
        ),
    )


class AccountNumberSequence(Base):
    __tablename__ = "account_number_sequences"

    bucket = sa.Column(sa.String(50), primary_key=True)
    last_value = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))
    min_length = sa.Column(sa.Integer, nullable=False, server_default=sa.text("4"))
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
