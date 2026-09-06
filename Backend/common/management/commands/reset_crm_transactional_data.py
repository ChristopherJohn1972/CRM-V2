"""
Management command: reset_crm_transactional_data

Removes all transactional data from Clients, Quotes, Sales Orders, Leads,
and Campaigns modules, then resets AUTO_INCREMENT counters and custom number
sequences so the system starts from a clean state.

WARNING: This operation is destructive and irreversible without a backup.
"""

import sqlalchemy as sa
from django.core.management.base import BaseCommand, CommandError

from common.db import SessionLocal


# ---------------------------------------------------------------------------
# Tables grouped by module, ordered for safe FK-aware deletion.
#
# Within each module the child tables come before parent tables.
# Across modules, the order is:
#   1. Sales Orders children (receipts depend on order_payments)
#   2. Quotes children
#   3. Leads children
#   4. Campaigns children
#   5. Cross-module children (activities, communications, documents, portal)
#   6. Core parent tables (customers, quotes, sales_orders, leads, campaigns)
# ---------------------------------------------------------------------------

# Step 1 — Deepest leaves (no children of their own in the target set)
STEP_1_TABLES = [
    # Receipt chain
    "receipt_verifications",
    # Creative chain
    "creative_assets",
    # Referral chain (referral_qualifications FK -> referral_events)
    "referral_qualifications",
    # Lead children
    "lead_consents",
    "lead_follow_ups",
    "lead_qualifications",
    # Quote sub-tables
    "quote_documents",
    "quote_items",
    "quote_versions",
    "quote_portal_access",
    "quote_events",
    "quote_approvals",
    "quote_client_responses",
    # Sales Order sub-tables
    "sales_order_items",
    "order_adjustments",
    "sales_order_events",
    "sales_order_documents",
    "sales_order_portal_access",
    # Campaign deepest children
    "campaign_qr_codes",
    "campaign_analytics_events",
    "campaign_launches",
    "campaign_products",
    "campaign_codes",
    "campaign_sources",
    "campaign_short_urls",
    "campaign_state_history",
    "campaign_schedules",
    "campaign_audiences",
    "campaign_offers",
    "campaign_channels",
    "campaign_budgets",
    "ai_generation_jobs",
    "creative_concepts",
    # Cross-module children
    "activity_notes",
    "timeline_events",
    "document_versions",
    "ussd_transactions",
    "momentum_snapshots",
    "momentum_ledger",
    "sms_messages",
    "email_messages",
    "call_logs",
    "customer_addresses",
    "customer_contacts",
    "customer_relationships",
    "complaint_attachments",
    "complaint_messages",
    "complaint_status_history",
    "payment_receipts",
    "notifications",
    "reward_redemptions",
    # Attribution chain
    "attribution_events",
    "attribution_results",
]

# Step 2 — Second-level parents
STEP_2_TABLES = [
    "creatives",
    "receipts",
    "documents",
    "activities",
    "complaints",
    "payments",
    "portal_user_customers",
    "referral_events",
]

# Step 3 — Core parent tables
STEP_3_TABLES = [
    "order_payments",
    "customer_accounts",
    "invoices",
    "leads",
    "referral_codes",
    "quotes",
    "sales_orders",
    "customers",
]

# Step 4 — Campaigns (depends only on users)
STEP_4_TABLES = [
    "campaigns",
]

# All tables in deletion order (for verification)
ALL_TARGET_TABLES = STEP_1_TABLES + STEP_2_TABLES + STEP_3_TABLES + STEP_4_TABLES

# Number-sequence / auto-number tables to reset
SEQUENCE_TABLES = {
    "account_number_sequences": "bucket",       # CUST-XXXX
    "quote_number_sequences": "bucket",         # QNxx-XXXX
    "so_number_sequences": "bucket",            # SO-XXXX
    "receipt_number_sequences": "bucket",       # RCT-XXXX
}

# Auto-increment tables to reset (table_name, pk_column)
AI_RESET_TABLES = [
    # Clients
    ("customers", "customer_id"),
    ("customer_addresses", "address_id"),
    ("customer_contacts", "contact_id"),
    ("customer_relationships", "relationship_id"),
    ("branches", "branch_id"),
    # Quotes
    ("quotes", "quote_id"),
    ("quote_items", "item_id"),
    ("quote_versions", "version_id"),
    ("quote_documents", "document_id"),
    ("quote_approvals", "approval_id"),
    ("quote_events", "event_id"),
    ("quote_portal_access", "portal_access_id"),
    ("quote_client_responses", "response_id"),
    # Sales Orders
    ("sales_orders", "order_id"),
    ("sales_order_items", "item_id"),
    ("order_adjustments", "adjustment_id"),
    ("sales_order_events", "event_id"),
    ("sales_order_documents", "document_id"),
    ("sales_order_portal_access", "portal_access_id"),
    ("order_payments", "payment_id"),
    ("receipts", "receipt_id"),
    ("receipt_verifications", "verification_id"),
    # Leads
    ("leads", "lead_id"),
    ("lead_qualifications", "id"),
    ("lead_follow_ups", "id"),
    ("lead_consents", "id"),
    # Campaigns
    ("campaigns", "campaign_id"),
    ("campaign_products", "id"),
    ("campaign_codes", "id"),
    ("campaign_sources", "id"),
    ("campaign_short_urls", "id"),
    ("campaign_qr_codes", "id"),
    ("campaign_state_history", "id"),
    ("campaign_schedules", "id"),
    ("campaign_audiences", "id"),
    ("campaign_offers", "id"),
    ("campaign_channels", "id"),
    ("campaign_budgets", "id"),
    ("creative_concepts", "id"),
    ("creatives", "id"),
    ("creative_assets", "id"),
    ("ai_generation_jobs", "id"),
    ("campaign_launches", "id"),
    ("campaign_analytics_events", "id"),
    # Activities
    ("activities", "activity_id"),
    ("activity_notes", "note_id"),
    ("timeline_events", "event_id"),
    # Communications
    ("sms_messages", "sms_message_id"),
    ("email_messages", "email_message_id"),
    ("call_logs", "call_log_id"),
    # Documents
    ("documents", "document_id"),
    ("document_versions", "document_version_id"),
    # Portal
    ("customer_accounts", "customer_account_id"),
    ("payments", "payment_id"),
    ("payment_receipts", "receipt_id"),
    ("invoices", "invoice_id"),
    ("complaints", "complaint_id"),
    ("complaint_messages", "message_id"),
    ("complaint_attachments", "attachment_id"),
    ("complaint_status_history", "history_id"),
    ("notifications", "notification_id"),
    ("reward_redemptions", "redemption_id"),
    ("portal_user_customers", "portal_user_customer_id"),
    # Referrals
    ("referral_codes", "id"),
    ("referral_events", "id"),
    ("referral_qualifications", "id"),
    # Attribution
    ("attribution_events", "id"),
    ("attribution_results", "id"),
    # Momentum
    ("momentum_ledger", "id"),
    ("momentum_snapshots", "id"),
    # USSD
    ("ussd_sessions", "id"),
    ("ussd_transactions", "id"),
]


def _table_exists(db, table_name):
    """Check if a table exists in the current database."""
    result = db.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :tname"
        ),
        {"tname": table_name},
    ).scalar()
    return result > 0


def _count_rows(db, table_name):
    """Return row count for a table."""
    try:
        return db.execute(sa.text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar()
    except Exception:
        return 0


def _truncate_table(db, table_name):
    """Delete all rows from a table. Uses DELETE (not TRUNCATE) to avoid
    FK issues in strict mode.  Returns the number of deleted rows."""
    try:
        result = db.execute(sa.text(f"DELETE FROM `{table_name}`"))
        return result.rowcount
    except Exception as exc:
        # If the table doesn't exist or is empty, skip silently
        if "doesn't exist" in str(exc).lower() or "no such table" in str(exc).lower():
            return 0
        raise


def _reset_auto_increment(db, table_name, pk_column):
    """Reset AUTO_INCREMENT for a table to 1."""
    try:
        db.execute(
            sa.text(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = 1")
        )
    except Exception:
        # Table may not exist or may not have AI — skip
        pass


class Command(BaseCommand):
    help = (
        "Remove all CRM transactional data (Clients, Quotes, Sales Orders, "
        "Leads, Campaigns) and reset numbering sequences for deployment."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Must be passed to actually execute the reset.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without making changes.",
        )

    def handle(self, *args, **options):
        confirm = options["confirm"]
        dry_run = options["dry_run"]

        if not confirm and not dry_run:
            raise CommandError(
                "This command requires --confirm to execute, or --dry-run to preview. "
                "This operation is destructive and irreversible without a backup."
            )

        db = SessionLocal()
        try:
            self._run_reset(db, confirm=confirm, dry_run=dry_run)
        finally:
            db.close()

    def _run_reset(self, db, confirm, dry_run):
        mode = "DRY RUN" if dry_run else "EXECUTING"
        self.stdout.write(self.style.WARNING(f"\n{'='*60}"))
        self.stdout.write(self.style.WARNING(f"  CRM DATA RESET — {mode}"))
        self.stdout.write(self.style.WARNING(f"{'='*60}\n"))

        # ── Phase 1: Count existing records ──────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("Phase 1: Counting existing records...\n"))
        totals = {}
        for table in ALL_TARGET_TABLES:
            if _table_exists(db, table):
                count = _count_rows(db, table)
                if count > 0:
                    totals[table] = count
                    self.stdout.write(f"  {table}: {count} rows")

        total_records = sum(totals.values())
        self.stdout.write(self.style.WARNING(f"\n  Total records to delete: {total_records}\n"))

        if total_records == 0:
            self.stdout.write(self.style.SUCCESS("  No transactional data found. System is already clean.\n"))
            if not dry_run:
                self._reset_sequences(db)
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN — no changes made.\n"))
            self._show_sequence_preview(db)
            return

        # ── Phase 2: Delete in FK-safe order ─────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("Phase 2: Deleting records in FK-safe order...\n"))
        deleted = {}

        for step_num, tables in enumerate([STEP_1_TABLES, STEP_2_TABLES, STEP_3_TABLES, STEP_4_TABLES], 1):
            self.stdout.write(f"  Step {step_num}:")
            for table in tables:
                if not _table_exists(db, table):
                    continue
                count = _truncate_table(db, table)
                if count > 0:
                    deleted[table] = count
                    self.stdout.write(f"    {table}: deleted {count} rows")

        # ── Phase 3: Reset AUTO_INCREMENT counters ───────────────────────
        self.stdout.write(self.style.HTTP_INFO("\nPhase 3: Resetting AUTO_INCREMENT counters...\n"))
        for table_name, pk_column in AI_RESET_TABLES:
            if _table_exists(db, table_name):
                _reset_auto_increment(db, table_name, pk_column)
        self.stdout.write("  AUTO_INCREMENT counters reset.\n")

        # ── Phase 4: Reset custom number sequences ───────────────────────
        self.stdout.write(self.style.HTTP_INFO("Phase 4: Resetting custom number sequences...\n"))
        for table_name in SEQUENCE_TABLES:
            if _table_exists(db, table_name):
                try:
                    db.execute(sa.text(f"DELETE FROM `{table_name}`"))
                    self.stdout.write(f"  {table_name}: cleared")
                except Exception:
                    pass
        self.stdout.write("  Number sequences reset.\n")

        # ── Phase 5: Reset portal_sequences if present ───────────────────
        if _table_exists(db, "portal_sequences"):
            try:
                db.execute(sa.text("UPDATE portal_sequences SET last_value = 0, seq_year = 0"))
                self.stdout.write("  portal_sequences: reset\n")
            except Exception:
                pass

        db.commit()

        # ── Phase 6: Verification ────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("Phase 5: Verifying cleanup...\n"))
        all_clean = True
        for table in ALL_TARGET_TABLES:
            if _table_exists(db, table):
                count = _count_rows(db, table)
                if count > 0:
                    self.stdout.write(self.style.ERROR(f"  FAIL: {table} still has {count} rows"))
                    all_clean = False

        if all_clean:
            self.stdout.write(self.style.SUCCESS("  All target tables are empty.\n"))
        else:
            self.stdout.write(self.style.ERROR("  Some tables still have data. Manual inspection required.\n"))

        # ── Summary ──────────────────────────────────────────────────────
        self.stdout.write(self.style.WARNING(f"{'='*60}"))
        self.stdout.write(self.style.WARNING("  RESET COMPLETE"))
        self.stdout.write(self.style.WARNING(f"{'='*60}"))
        self.stdout.write(f"  Tables cleared: {len(deleted)}")
        self.stdout.write(f"  Records deleted: {sum(deleted.values())}")
        self.stdout.write(self.style.WARNING(f"{'='*60}\n"))

    def _show_sequence_preview(self, db):
        """Show what sequences would be reset."""
        self.stdout.write(self.style.HTTP_INFO("  Sequences that would be reset:\n"))
        for table_name in SEQUENCE_TABLES:
            if _table_exists(db, table_name):
                count = _count_rows(db, table_name)
                self.stdout.write(f"    {table_name}: {count} entries → cleared")
        if _table_exists(db, "portal_sequences"):
            self.stdout.write("    portal_sequences: reset to 0")

    def _reset_sequences(self, db):
        """Reset all sequences during dry-run verification."""
        for table_name in SEQUENCE_TABLES:
            if _table_exists(db, table_name):
                try:
                    db.execute(sa.text(f"DELETE FROM `{table_name}`"))
                except Exception:
                    pass
        if _table_exists(db, "portal_sequences"):
            try:
                db.execute(sa.text("UPDATE portal_sequences SET last_value = 0, seq_year = 0"))
            except Exception:
                pass
        db.commit()
