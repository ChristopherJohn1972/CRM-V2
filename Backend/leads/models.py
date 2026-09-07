import sqlalchemy as sa
from sqlalchemy import JSON

from common.db import Base
from leads.enums import (
    LeadConsentType,
    LeadFollowUpType,
    LeadStatus,
)


class Lead(Base):
    __tablename__ = "leads"

    lead_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    first_name = sa.Column(sa.String(100))
    last_name = sa.Column(sa.String(100))
    email = sa.Column(sa.String(255))
    phone = sa.Column(sa.String(50))
    company = sa.Column(sa.String(255))
    source_campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="SET NULL"))
    source_channel = sa.Column(sa.String(100))
    status = sa.Column(sa.Enum(LeadStatus), nullable=False, server_default=LeadStatus.NEW.value)
    assigned_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    assigned_team_id = sa.Column(sa.BigInteger, sa.ForeignKey("teams.team_id", ondelete="SET NULL"))
    qualification_score = sa.Column(sa.Integer)
    tags = sa.Column(JSON)
    notes = sa.Column(sa.Text)
    consent_given = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    consent_date = sa.Column(sa.DateTime)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class LeadQualification(Base):
    __tablename__ = "lead_qualifications"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    lead_id = sa.Column(sa.BigInteger, sa.ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    score = sa.Column(sa.Integer, nullable=False)
    criteria = sa.Column(JSON)
    qualified_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    qualified_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    notes = sa.Column(sa.Text)


class LeadFollowUp(Base):
    __tablename__ = "lead_follow_ups"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    lead_id = sa.Column(sa.BigInteger, sa.ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    follow_up_type = sa.Column(sa.Enum(LeadFollowUpType), nullable=False)
    scheduled_at = sa.Column(sa.DateTime, nullable=False)
    completed_at = sa.Column(sa.DateTime)
    outcome = sa.Column(sa.String(255))
    notes = sa.Column(sa.Text)
    assigned_to = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class LeadConsent(Base):
    __tablename__ = "lead_consents"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    lead_id = sa.Column(sa.BigInteger, sa.ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False)
    consent_type = sa.Column(sa.Enum(LeadConsentType), nullable=False)
    granted = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    granted_at = sa.Column(sa.DateTime)
    revoked_at = sa.Column(sa.DateTime)
    ip_address = sa.Column(sa.String(45))
    source = sa.Column(sa.String(100))
