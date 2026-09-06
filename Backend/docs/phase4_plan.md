# Phase 4: Sales & Commerce Extension — Final Plan

## Status: APPROVED FOR IMPLEMENTATION

---

## Context

| Phase | Status | Summary |
|-------|--------|---------|
| Phase 1 | ✅ Complete | Quote Studio — PDF generation, line items, versioning |
| Phase 2 | ✅ Complete | Sales Orders, Payments & Receipts — full order lifecycle |
| Phase 3 | ✅ Complete | Customer Management overhaul — unified customer model |
| **Phase 4** | **🔄 Planning** | **Campaigns, Lead Generation, Real-Time Events, Attribution, Referrals, Momentum** |

**Goal:** Extend the CRM into a full sales & commerce engine with campaign tracking, lead lifecycle management, event-driven attribution, referral programs, and a momentum/rewards ledger.

---

## Architecture Decision: Stay on MySQL

**Decision:** All new tables use MySQL 8.0 InnoDB. No migration to PostgreSQL.

**Rationale:**
- Zero migration risk — no schema export/import, no ORM compatibility issues
- All required features (JSON columns, CTEs, window functions, partial indexes via generated columns) are supported in MySQL 8.0
- Existing team tooling, CI/CD, and deployment scripts remain unchanged
- Laravel/Django ORM support is mature and stable

**MySQL 8.0 Features Leveraged:**
- `JSON` columns for flexible metadata (campaign config, event payloads, rule parameters)
- Window functions (`ROW_NUMBER()`, `RANK()`) for attribution computation
- Common Table Expressions (CTEs) for complex analytics queries
- `GENERATED ALWAYS AS` columns for indexable computed values
- `utf8mb4` character set for full Unicode support

---

## Key Design Decisions

### 1. Queue/Outbox: Database Outbox + Polling Worker

**Decision:** Use a database-backed outbox table with a polling management command. No Redis/RabbitMQ/SQS dependency.

**Rationale:**
- Zero new infrastructure — works on existing MySQL + Django setup
- Transactional guarantees — outbox writes happen in the same transaction as business logic
- Simple deployment — management command runs via cron or `schedule` library
- Sufficient throughput for CRM scale (hundreds to low thousands of events/minute)

**Implementation:**
```
EventOutbox table → management command polls every 5s → processes events → marks COMPLETE/FAILED
```

**Trade-off acknowledged:** Higher latency than message broker (5s polling vs sub-second push). Acceptable for CRM use cases. Can upgrade to Redis Streams later if throughput demands exceed ~1000 events/minute sustained.

### 2. Real-Time: Server-Sent Events (SSE)

**Decision:** Use SSE for real-time push to browser clients. No WebSocket server.

**Rationale:**
- Works with existing Django WSGI server (Gunicorn) — no ASGI migration needed
- Simpler than WebSocket — unidirectional (server→client) is sufficient
- Automatic reconnection built into browser `EventSource` API
- Works through standard HTTP infrastructure (load balancers, CDNs, proxies)
- No new dependency (unlike Django Channels)

**Implementation:**
```
Event processed → write to SSEBuffer table (in-memory alternative considered) → 
long-poll endpoint streams events → client EventSource receives
```

**Trade-off acknowledged:** SSE has connection limits per browser (~6 per domain in HTTP/1.1). Sufficient for CRM dashboard use cases. HTTP/2 multiplexing reduces this concern.

### 3. Attribution Model v1: Last-Touch Only

**Decision:** Phase 4 implements last-touch attribution only. First-touch, linear, time-decay, and position-based models are deferred to Phase 5 (v2).

**Rationale:**
- Last-touch covers ~80% of CRM attribution needs
- Simpler to implement, test, and explain to users
- First-touch/linear require multi-touchpoint storage and weighting logic — defer until core attribution flow is proven
- Data model designed to support additional models in v2 (attribution model column is extensible)

**Implementation:**
- On SalesOrder confirmation, look up most recent touchpoint for the customer
- Write `AttributionResult` with `model=LAST_TOUCH`, `touchpoint_id`, `credit=1.0`
- Analytics views filter by model type for future extensibility

### 4. Campaign State Machine

**Decision:** Enforce campaign lifecycle via explicit state machine with validated transitions.

**States:**
```
DRAFT → SCHEDULED → ACTIVE → PAUSED → COMPLETED → ARCHIVED
         ↓                         ↓
       CANCELLED                COMPLETED
```

**Transition Rules:**
| From | Allowed To | Trigger |
|------|-----------|---------|
| DRAFT | SCHEDULED, CANCELLED | User schedules or cancels |
| SCHEDULED | ACTIVE, CANCELLED | Start date reached or user cancels |
| ACTIVE | PAUSED, COMPLETED | User pauses or end date reached |
| PAUSED | ACTIVE, COMPLETED | User resumes or end date reached |
| COMPLETED | ARCHIVED | User archives |
| ARCHIVED | — | Terminal state |

**Implementation:**
- `Campaign.status` field with choices
- `CampaignTransition` audit table records every state change with timestamp, user, and reason
- `CampaignService.transition()` method validates transitions and raises `InvalidTransition` on illegal moves
- Scheduled transitions handled by management command (`check_scheduled_campaigns`)

---

## Wave Breakdown

### Wave 1: Foundation (Schema + RBAC)

**Duration:** 2–3 days

**Objectives:**
- Create all database schemas for new apps
- Define RBAC permissions and roles
- Set up Django app structure

**Files to Create:**

| File | Purpose |
|------|---------|
| `migrations/019_phase4_foundation_schema.sql` | All new tables (campaigns, leads, referrals, momentum, attribution, event_engine) |
| `migrations/020_phase4_rbac_seed.sql` | Permissions, roles, role-permission mappings |
| `apps/campaigns/models.py` | Campaign, CampaignSource, CampaignCode, CampaignSchedule, CampaignTransition |
| `apps/campaigns/enums.py` | CampaignStatus, CampaignType, CampaignChannel |
| `apps/campaigns/apps.py` | Django app config |
| `apps/leads/models.py` | Lead, LeadSource, LeadQualification, LeadFollowUp, LeadConsent |
| `apps/leads/enums.py` | LeadStatus, LeadRating, LeadSource |
| `apps/leads/apps.py` | Django app config |
| `apps/referrals/models.py` | ReferralCode, ReferralEvent, ReferralQualification, ReferralReward |
| `apps/referrals/enums.py` | ReferralStatus, ReferralEvent |
| `apps/referrals/apps.py` | Django app config |
| `apps/momentum/models.py` | MomentumLedger, MomentumRule, MomentumRuleVersion, MomentumBalance |
| `apps/momentum/enums.py` | MomentumEventType, RuleType |
| `apps/momentum/apps.py` | Django app config |
| `apps/attribution/models.py` | Touchpoint, AttributionEvent, AttributionResult, AttributionModel |
| `apps/attribution/enums.py` | AttributionModelType, TouchpointChannel |
| `apps/attribution/apps.py` | Django app config |
| `apps/event_engine/models.py` | EventEnvelope, EventOutbox, EventIdempotency, EventLog |
| `apps/event_engine/enums.py` | EventStatus, EventType, EventSource |
| `apps/event_engine/apps.py` | Django app config |

**Files to Modify:**

| File | Change |
|------|--------|
| `config/settings.py` | Add 6 new apps to `INSTALLED_APPS` |
| `config/urls.py` | Include new app URL modules |
| `apps/core/permissions.py` | Add Phase 4 permission constants |

**RBAC Permissions (seeded):**

| Permission | Description |
|-----------|-------------|
| `campaigns.view_campaign` | View campaigns |
| `campaigns.create_campaign` | Create/edit campaigns |
| `campaigns.manage_campaign_codes` | Generate/assign campaign codes |
| `campaigns.transition_campaign` | Change campaign state |
| `leads.view_lead` | View leads |
| `leads.create_lead` | Create/edit leads |
| `leads.qualify_lead` | Mark leads as qualified/disqualified |
| `leads.convert_lead` | Convert lead to customer/opportunity |
| `leads.manage_lead_consent` | Manage GDPR consent records |
| `referrals.view_referral` | View referral data |
| `referrals.manage_referral_codes` | Create/manage referral codes |
| `referrals.process_referral` | Process referral events |
| `momentum.view_momentum` | View momentum balances/ledger |
| `momentum.manage_rules` | Create/edit momentum rules |
| `momentum.adjust_balance` | Manual momentum adjustments |
| `attribution.view_attribution` | View attribution data |
| `attribution.configure_models` | Configure attribution models |
| `event_engine.view_events` | View event logs |
| `event_engine.replay_events` | Replay failed events |
| `event_engine.manage_outbox` | Manage outbox (retry, purge) |

**Roles:**
- `sales_manager` — campaign CRUD, lead qualification, attribution config
- `sales_rep` — lead capture, follow-up, referral processing
- `marketing_manager` — campaign scheduling, code generation, analytics
- `admin` — full access to all Phase 4 features
- `viewer` — read-only access across all modules

**Schema Tables (Wave 1):**

```sql
-- Campaigns
campaigns_campaign
campaigns_source
campaigns_code
campaigns_schedule
campaigns_transition

-- Leads
leads_lead
leads_source
leads_qualification
leads_followup
leads_consent

-- Referrals
referrals_code
referrals_event
referrals_qualification
referrals_reward

-- Momentum
momentum_ledger
momentum_rule
momentum_ruleversion
momentum_balance

-- Attribution
attribution_touchpoint
attribution_event
attribution_result

-- Event Engine
event_engine_envelope
event_engine_outbox
event_engine_idempotency
event_engine_log
```

**Deliverables:**
- [ ] All migration files created and tested
- [ ] All new Django apps created with models, enums, apps.py
- [ ] RBAC permissions seeded and verified
- [ ] INSTALLED_APPS updated
- [ ] URL routing configured
- [ ] All models pass `makemigrations --check`

---

### Wave 2: Campaign Core

**Duration:** 3–5 days (parallel with Waves 3, 4)

**Objectives:**
- Campaign CRUD with full state machine
- Campaign code generation (unique, trackable codes)
- Campaign source tracking (where leads come from)
- QR code generation for campaigns
- Campaign scheduling (start/end dates, auto-activation)

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/campaigns/` | List campaigns (filtered, paginated) |
| POST | `/api/campaigns/` | Create campaign |
| GET | `/api/campaigns/{id}/` | Get campaign detail |
| PUT | `/api/campaigns/{id}/` | Update campaign |
| DELETE | `/api/campaigns/{id}/` | Soft-delete/archive campaign |
| POST | `/api/campaigns/{id}/transition/` | Transition campaign state |
| GET | `/api/campaigns/{id}/codes/` | List campaign codes |
| POST | `/api/campaigns/{id}/codes/` | Generate campaign codes |
| GET | `/api/campaigns/{id}/codes/{code}/` | Get code detail |
| POST | `/api/campaigns/{id}/codes/{code}/deactivate/` | Deactivate a code |
| GET | `/api/campaigns/{id}/qr/` | Generate QR code image |
| GET | `/api/campaigns/{id}/analytics/` | Campaign performance metrics |
| GET | `/api/campaigns/sources/` | List campaign sources |
| POST | `/api/campaigns/sources/` | Create campaign source |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `CampaignService` | CRUD, state transitions, validation |
| `CampaignCodeService` | Generate unique codes, QR codes, track usage |
| `CampaignScheduleService` | Schedule activation/deactivation, management command integration |

**Key Behaviors:**
- Campaign codes are unique, case-insensitive, 8-12 character alphanumeric
- QR codes encode campaign URL with tracking parameter (`?campaign_code=XXX`)
- Scheduling uses `AT TIME ZONE` for timezone-aware activation
- State transitions are audit-logged in `CampaignTransition` table
- Campaign analytics include: impressions, clicks, conversions, cost, ROI

**Frontend Pages:**
- `src/pages/campaigns/CampaignList.jsx` — Table view with filters (status, date range, channel)
- `src/pages/campaigns/CampaignDetail.jsx` — Campaign overview, codes, analytics
- `src/pages/campaigns/CampaignCreate.jsx` — Create/edit form
- `src/pages/campaigns/CampaignSchedule.jsx` — Scheduling interface
- `src/pages/campaigns/CampaignCodes.jsx` — Code management, QR generation

**Frontend Components:**
- `src/components/campaigns/CampaignStatusBadge.jsx`
- `src/components/campaigns/CampaignCodeTable.jsx`
- `src/components/campaigns/QRCodeGenerator.jsx`
- `src/components/campaigns/CampaignAnalytics.jsx`

**API Module:**
- `src/api/campaigns.js` — All campaign API calls

**Deliverables:**
- [ ] Campaign CRUD endpoints implemented and tested
- [ ] State machine enforced with audit logging
- [ ] Campaign codes generate and validate correctly
- [ ] QR code generation works
- [ ] Scheduling management command activates/deactivates campaigns
- [ ] Frontend pages complete with all CRUD operations
- [ ] API tests for all endpoints
- [ ] Frontend tests for critical flows

---

### Wave 3: Lead CRM

**Duration:** 3–5 days (parallel with Waves 2, 4)

**Objectives:**
- Lead capture from multiple sources (web, import, manual, campaign codes)
- Lead qualification workflow (score, rating, status progression)
- Lead follow-up tracking (tasks, notes, reminders)
- Lead-to-customer conversion
- GDPR consent management

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leads/` | List leads (filtered, paginated) |
| POST | `/api/leads/` | Create lead |
| GET | `/api/leads/{id}/` | Get lead detail |
| PUT | `/api/leads/{id}/` | Update lead |
| DELETE | `/api/leads/{id}/` | Soft-delete lead |
| POST | `/api/leads/{id}/qualify/` | Qualify/disqualify lead |
| POST | `/api/leads/{id}/convert/` | Convert lead to customer |
| GET | `/api/leads/{id}/followups/` | List follow-ups |
| POST | `/api/leads/{id}/followups/` | Create follow-up |
| PUT | `/api/leads/{id}/followups/{followup_id}/` | Update follow-up |
| POST | `/api/leads/{id}/followups/{followup_id}/complete/` | Mark follow-up complete |
| GET | `/api/leads/{id}/consent/` | Get consent records |
| POST | `/api/leads/{id}/consent/` | Record consent |
| GET | `/api/leads/sources/` | List lead sources |
| POST | `/api/leads/sources/` | Create lead source |
| GET | `/api/leads/import/` | Import template download |
| POST | `/api/leads/import/` | Bulk import leads |
| GET | `/api/leads/analytics/` | Lead pipeline analytics |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `LeadService` | CRUD, assignment, search |
| `LeadQualificationService` | Scoring, rating, status transitions |
| `LeadFollowUpService` | Follow-up scheduling, reminders, completion |
| `LeadConversionService` | Lead → Customer conversion, duplicate detection |
| `LeadConsentService` | GDPR consent recording, audit trail |

**Lead Status Flow:**
```
NEW → CONTACTED → QUALIFIED → CONVERTED
                 ↓
            DISQUALIFIED → ARCHIVED
```

**Key Behaviors:**
- Lead scoring is configurable (weighted fields: source, engagement, company size, budget)
- Follow-up reminders trigger event engine integration (for SSE notifications)
- Lead conversion creates/updates Customer record, links to Source campaign
- Consent records are immutable (append-only log)
- Duplicate detection on email + phone at creation time
- Bulk import supports CSV with validation report

**Frontend Pages:**
- `src/pages/leads/LeadList.jsx` — Pipeline view (Kanban) + table view
- `src/pages/leads/LeadDetail.jsx` — Lead profile, follow-ups, consent, conversion
- `src/pages/leads/LeadCreate.jsx` — Create/edit form
- `src/pages/leads/LeadImport.jsx` — Bulk import interface
- `src/pages/leads/LeadAnalytics.jsx` — Pipeline metrics, conversion rates

**Frontend Components:**
- `src/components/leads/LeadStatusBadge.jsx`
- `src/components/leads/LeadScoreCard.jsx`
- `src/components/leads/LeadFollowUpList.jsx`
- `src/components/leads/LeadConversionDialog.jsx`
- `src/components/leads/LeadPipelineBoard.jsx` (Kanban)

**API Module:**
- `src/api/leads.js` — All lead API calls

**Deliverables:**
- [ ] Lead CRUD endpoints implemented and tested
- [ ] Qualification workflow enforced
- [ ] Follow-up tracking works with reminders
- [ ] Lead-to-customer conversion tested
- [ ] Consent management records immutable audit trail
- [ ] Bulk import with validation report
- [ ] Frontend pipeline view (Kanban + table)
- [ ] API tests for all endpoints
- [ ] Frontend tests for critical flows

---

### Wave 4: Event Engine

**Duration:** 3–5 days (parallel with Waves 2, 3)

**Objectives:**
- Canonical event envelope for all system events
- Idempotent event processing (dedup by event ID)
- Database outbox pattern for reliable delivery
- Event replay for failed/delayed events
- Foundation for attribution, SSE, and analytics integration

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events/` | List events (filtered, paginated) |
| GET | `/api/events/{id}/` | Get event detail |
| GET | `/api/events/outbox/` | List outbox items |
| POST | `/api/events/outbox/{id}/retry/` | Retry failed outbox item |
| POST | `/api/events/outbox/purge/` | Purge completed outbox items |
| GET | `/api/events/{id}/log/` | Get event processing log |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `EventEnvelopeService` | Create canonical event envelopes |
| `EventIngestionService` | Ingest events, validate, write to outbox |
| `EventProcessingService` | Process outbox items, idempotent execution |
| `EventReplayService` | Replay failed events, bulk retry |

**Management Commands:**

| Command | Purpose |
|---------|---------|
| `process_event_outbox` | Poll outbox, process events, retry failures |
| `purge_event_outbox` | Clean completed/failed events older than N days |
| `replay_events` | Replay events by type, date range, or ID list |

**Event Envelope Schema:**
```python
{
    "event_id": "uuid-v4",           # Unique, idempotency key
    "event_type": "ORDER_CONFIRMED",  # Business event type
    "event_source": "sales_orders",   # Originating app
    "payload": { ... },              # Event-specific data
    "metadata": {                    # Traceability
        "user_id": "...",
        "ip_address": "...",
        "timestamp": "ISO8601",
        "correlation_id": "..."
    },
    "created_at": "ISO8601",
    "processed_at": null | "ISO8601",
    "status": "PENDING" | "PROCESSING" | "COMPLETE" | "FAILED"
}
```

**Idempotency:**
- `EventIdempotency` table stores processed `event_id` values
- On ingestion, check for existing `event_id` → skip if exists
- TTL-based cleanup (90 days default)

**Key Behaviors:**
- All events write to outbox in same transaction as business logic
- Outbox processor polls every 5 seconds (configurable)
- Failed events retry up to 3 times with exponential backoff
- Event log records processing steps for debugging
- Events older than 24h that failed are flagged for manual review
- Outbox purge runs daily (configurable retention)

**Frontend Pages:**
- `src/pages/events/EventLog.jsx` — Event browser with filters
- `src/pages/events/EventDetail.jsx` — Event payload, processing log
- `src/pages/events/OutboxMonitor.jsx` — Outbox status, retry controls

**Frontend Components:**
- `src/components/events/EventStatusBadge.jsx`
- `src/components/events/EventPayloadViewer.jsx`
- `src/components/events/OutboxStats.jsx`

**API Module:**
- `src/api/events.js` — All event engine API calls

**Deliverables:**
- [ ] Event envelope creation validated
- [ ] Idempotent processing verified (duplicate event_id → skip)
- [ ] Outbox polling command runs reliably
- [ ] Retry logic with exponential backoff works
- [ ] Event log records all processing steps
- [ ] Management commands tested
- [ ] Frontend monitoring pages complete
- [ ] API tests for all endpoints

---

### Wave 5: Attribution

**Duration:** 2–3 days (depends on Wave 4)

**Objectives:**
- Touchpoint tracking across all customer interactions
- Last-touch attribution computation on order confirmation
- Attribution analytics and reporting
- Hook into SalesOrder confirmation flow

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/attribution/touchpoints/` | List touchpoints |
| POST | `/api/attribution/touchpoints/` | Record touchpoint |
| GET | `/api/attribution/results/` | List attribution results |
| GET | `/api/attribution/results/{order_id}/` | Get attribution for order |
| GET | `/api/attribution/analytics/` | Attribution analytics (by source, campaign, channel) |
| GET | `/api/attribution/models/` | List available attribution models |
| POST | `/api/attribution/compute/{order_id}/` | Trigger attribution computation |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `TouchpointService` | Record and query touchpoints |
| `AttributionService` | Compute attribution on order confirmation |
| `AttributionAnalyticsService` | Generate attribution reports |

**Integration Point:**
- `apps/sales_orders/signals.py` → on `order.status == CONFIRMED`:
  - `AttributionService.compute(order)` runs
  - Looks up most recent touchpoint for `order.customer_id`
  - Writes `AttributionResult` with `model=LAST_TOUCH`, `credit=1.0`
  - Emits `ORDER_ATTRIBUTED` event to Event Engine

**Key Behaviors:**
- Touchpoints recorded on: page visit, form submission, email click, campaign code use, referral code use
- Attribution computed asynchronously on order confirmation (via event)
- Re-computation possible via API for manual adjustments
- Analytics show: conversions by source, campaign ROI, channel effectiveness
- Attribution results are immutable after creation (audit trail)

**Frontend Pages:**
- `src/pages/attribution/AttributionDashboard.jsx` — Overview, charts
- `src/pages/attribution/TouchpointList.jsx` — Touchpoint browser
- `src/pages/attribution/AttributionDetail.jsx` — Order attribution breakdown

**Frontend Components:**
- `src/components/attribution/AttributionChart.jsx`
- `src/components/attribution/TouchpointTimeline.jsx`
- `src/components/attribution/SourcePerformance.jsx`

**API Module:**
- `src/api/attribution.js` — All attribution API calls

**Deliverables:**
- [ ] Touchpoint recording works for all interaction types
- [ ] Last-touch attribution computed on order confirmation
- [ ] Integration with SalesOrder signals verified
- [ ] Analytics dashboards display correct data
- [ ] API tests for all endpoints

---

### Wave 6: Referral Program

**Duration:** 2–3 days (depends on Wave 4)

**Objectives:**
- Referral code generation and management
- Referral event tracking (share, click, signup, purchase)
- Referral qualification rules
- Anti-abuse measures (fraud detection, limits)
- Referral rewards

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/referrals/codes/` | List referral codes |
| POST | `/api/referrals/codes/` | Create referral code |
| GET | `/api/referrals/codes/{code}/` | Get code detail |
| PUT | `/api/referrals/codes/{code}/` | Update code settings |
| POST | `/api/referrals/codes/{code}/deactivate/` | Deactivate code |
| GET | `/api/referrals/events/` | List referral events |
| POST | `/api/referrals/events/` | Record referral event |
| GET | `/api/referrals/qualifications/` | List qualification results |
| POST | `/api/referrals/qualifications/{id}/process/` | Process qualification |
| GET | `/api/referrals/analytics/` | Referral program analytics |
| GET | `/api/referrals/anti-abuse/` | Anti-abuse checks |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `ReferralCodeService` | Generate, manage, validate referral codes |
| `ReferralEventService` | Track referral events through funnel |
| `ReferralQualificationService` | Evaluate referral against qualification rules |
| `ReferralRewardService` | Issue rewards on successful qualification |
| `ReferralAntiAbuseService` | Detect fraud, enforce limits |

**Referral Funnel:**
```
CODE_CREATED → SHARED → CLICKED → SIGNED_UP → QUALIFIED → REWARD_ISSUED
                                   ↓
                              DISQUALIFIED
```

**Anti-Abuse Rules:**
- Max 100 uses per referral code (configurable)
- Max 10 referrals per customer per month
- IP-based duplicate detection
- Email domain blacklisting (throwaway email providers)
- Velocity checks (unusual spike in referrals)

**Key Behaviors:**
- Referral codes are unique, case-insensitive, 8 characters
- Each code linked to a referrer (Customer) and optionally a campaign
- Qualification rules configurable (e.g., "qualify after first purchase > $50")
- Rewards can be: momentum points, discount codes, manual (admin-issued)
- All referral events recorded for analytics and anti-abuse

**Frontend Pages:**
- `src/pages/referrals/ReferralDashboard.jsx` — Program overview, top referrers
- `src/pages/referrals/ReferralCodes.jsx` — Code management
- `src/pages/referrals/ReferralDetail.jsx` — Individual referral tracking
- `src/pages/referrals/ReferralAnalytics.jsx` — Funnel analysis, conversion rates

**Frontend Components:**
- `src/components/referrals/ReferralCodeCard.jsx`
- `src/components/referrals/ReferralFunnel.jsx`
- `src/components/referrals/ReferralStatusBadge.jsx`

**API Module:**
- `src/api/referrals.js` — All referral API calls

**Deliverables:**
- [ ] Referral code generation and validation works
- [ ] Referral funnel tracking recorded
- [ ] Qualification rules evaluated correctly
- [ ] Anti-abuse measures prevent fraudulent referrals
- [ ] Rewards issued on qualification
- [ ] Analytics show funnel metrics
- [ ] API tests for all endpoints

---

### Wave 7: Momentum

**Duration:** 2–3 days (depends on Wave 4)

**Objectives:**
- Ledger-based momentum/rewards system
- Configurable earning and burning rules
- Balance tracking with transaction history
- Rule versioning for audit trail
- Migration from computed momentum to ledger

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/momentum/balances/` | List customer balances |
| GET | `/api/momentum/balances/{customer_id}/` | Get customer balance |
| GET | `/api/momentum/ledger/` | List ledger entries (filtered) |
| POST | `/api/momentum/ledger/` | Manual ledger adjustment |
| GET | `/api/momentum/rules/` | List momentum rules |
| POST | `/api/momentum/rules/` | Create rule |
| PUT | `/api/momentum/rules/{id}/` | Update rule (creates new version) |
| GET | `/api/momentum/rules/{id}/versions/` | Rule version history |
| POST | `/api/momentum/rules/{id}/deactivate/` | Deactivate rule |
| GET | `/api/momentum/analytics/` | Earn/burn analytics |
| POST | `/api/momentum/backfill/` | Trigger backfill migration |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `MomentumLedgerService` | Record earn/burn transactions |
| `MomentumBalanceService` | Calculate and cache balances |
| `MomentumRuleService` | CRUD rules with versioning |
| `MomentumBackfillService` | Migrate computed momentum to ledger |

**Rule Types:**
| Rule | Trigger | Action |
|------|---------|--------|
| `PURCHASE_EARN` | Order confirmed | +1 point per $1 spent |
| `REFERRAL_EARN` | Referral qualified | +500 points |
| `CAMPAIGN_EARN` | Campaign code used | +100 points |
| `SIGNUP_EARN` | Customer created | +200 points |
| `REDEEM_BURN` | Redemption request | -N points |
| `MANUAL_ADJUSTMENT` | Admin action | ±N points |

**Key Behaviors:**
- All point changes recorded in `MomentumLedger` (immutable append-only log)
- Balance computed from ledger (cached in `MomentumBalance` table)
- Rule updates create new version (previous version archived)
- Effective dating on rules (start_date, end_date)
- Backfill migration maps existing computed `momentum_score` to ledger entries
- Balance is always non-negative (validation on burn)

**Frontend Pages:**
- `src/pages/momentum/MomentumDashboard.jsx` — Balance overview, earn/burn trends
- `src/pages/momentum/MomentumLedger.jsx` — Transaction history
- `src/pages/momentum/MomentumRules.jsx` — Rule management
- `src/pages/momentum/MomentumCustomerDetail.jsx` — Customer-specific momentum view

**Frontend Components:**
- `src/components/momentum/BalanceCard.jsx`
- `src/components/momentum/LedgerTable.jsx`
- `src/components/momentum/RuleEditor.jsx`
- `src/components/momentum/EarnBurnChart.jsx`

**API Module:**
- `src/api/momentum.js` — All momentum API calls

**Deliverables:**
- [ ] Ledger records all earn/burn transactions
- [ ] Balance computation from ledger works
- [ ] Rules with versioning functional
- [ ] Backfill migration from computed momentum
- [ ] Balance validation (no negative)
- [ ] Analytics show earn/burn trends
- [ ] API tests for all endpoints

---

### Wave 8: Real-Time (SSE)

**Duration:** 2–3 days (depends on Waves 5, 6, 7)

**Objectives:**
- SSE streaming endpoint for real-time notifications
- Channel-based subscription model
- Authorization (user can only subscribe to their channels)
- Integration with Event Engine (event → SSE notification)

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sse/stream/` | SSE streaming endpoint (long-lived) |
| GET | `/api/sse/channels/` | List available channels |
| POST | `/api/sse/channels/subscribe/` | Subscribe to channel |
| POST | `/api/sse/channels/unsubscribe/` | Unsubscribe from channel |
| GET | `/api/sse/notifications/` | List recent notifications |

**Services:**

| Service | Responsibility |
|---------|---------------|
| `SSEStreamService` | Manage SSE connections, stream events |
| `SSEChannelService` | Manage channel subscriptions |
| `SSENotificationService` | Create and deliver notifications |

**Channel Types:**
- `campaign:{campaign_id}` — Campaign updates
- `lead:{lead_id}` — Lead status changes
- `referral:{customer_id}` — Referral events
- `momentum:{customer_id}` — Momentum balance changes
- `order:{order_id}` — Order status updates
- `system` — System-wide announcements

**Key Behaviors:**
- SSE endpoint uses Django streaming response
- Connection authenticated via session token or API key
- Channels authorized per-user (user can only subscribe to channels they have access to)
- Events buffered in memory (or SSEBuffer table) before streaming
- Automatic reconnection supported by browser `EventSource`
- Heartbeat every 30s to keep connection alive
- Integration: Event Engine processing emits SSE notification for relevant events

**Frontend:**
- `src/hooks/useSSE.js` — React hook for SSE connection management
- `src/components/realtime/NotificationToast.jsx` — Toast notifications from SSE
- `src/components/realtime/LiveIndicator.jsx` — Connection status indicator

**Deliverables:**
- [ ] SSE streaming endpoint works with authentication
- [ ] Channel subscription authorization enforced
- [ ] Event Engine integration emits SSE notifications
- [ ] React hook manages connection lifecycle
- [ ] Toast notifications display in real-time
- [ ] Heartbeat keeps connections alive
- [ ] Reconnection after disconnect works

---

### Wave 9: Portal Integration

**Duration:** 3–5 days (depends on Waves 2–7)

**Objectives:**
- Customer-facing portal APIs for campaign discovery, referrals, momentum
- Portal frontend pages for customer self-service
- Integration with existing customer portal

**Portal API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portal/campaigns/` | Discover active campaigns |
| GET | `/portal/campaigns/{code}/` | Campaign detail (public) |
| POST | `/portal/referrals/` | Generate customer referral code |
| GET | `/portal/referrals/` | Customer's referral history |
| GET | `/portal/referrals/stats/` | Referral statistics |
| GET | `/portal/momentum/` | Customer momentum balance |
| GET | `/portal/momentum/history/` | Transaction history |
| POST | `/portal/momentum/redeem/` | Redeem momentum points |

**Services:**
- `PortalCampaignService` — Public campaign discovery
- `PortalReferralService` — Customer referral management
- `PortalMomentumService` — Customer momentum display and redemption

**Key Behaviors:**
- Portal APIs are authenticated (customer session)
- Only active/completed campaigns shown (no draft/scheduled)
- Referral code generation limited to 1 active code per customer
- Momentum redemption validates sufficient balance
- All portal actions recorded in event engine

**Frontend Pages (Portal):**
- `src/pages/portal/CampaignDiscovery.jsx` — Browse active campaigns
- `src/pages/portal/MyReferrals.jsx` — Referral code, share tools, history
- `src/pages/portal/MomentumCenter.jsx` — Balance, history, redemption
- `src/pages/portal/ReferralShare.jsx` — Shareable referral link

**Frontend Components (Portal):**
- `src/components/portal/CampaignCard.jsx`
- `src/components/portal/ReferralShareButton.jsx`
- `src/components/portal/MomentumBalanceCard.jsx`
- `src/components/portal/RedemptionDialog.jsx`

**Deliverables:**
- [ ] Portal APIs authenticated and authorized
- [ ] Campaign discovery shows only active campaigns
- [ ] Referral code generation and sharing works
- [ ] Momentum display and redemption functional
- [ ] Portal pages responsive and user-friendly
- [ ] Integration with existing customer portal

---

### Wave 10: Hardening

**Duration:** 2–3 days (final wave)

**Objectives:**
- Security hardening (rate limiting, input validation, anti-abuse)
- Performance optimization (indexes, pagination, caching)
- Observability (structured logging, audit trails, monitoring)
- Documentation

**Security:**

| Area | Implementation |
|------|---------------|
| Rate limiting | Django REST framework throttling on all Phase 4 endpoints |
| Input validation | Serializers validate all inputs, sanitize strings |
| Anti-abuse | Referral fraud detection, momentum abuse prevention |
| SQL injection | ORM-only queries, no raw SQL without parameterization |
| XSS | Frontend sanitizes all user-generated content |
| CSRF | Django CSRF protection on all state-changing endpoints |
| Authentication | All Phase 4 endpoints require authentication |
| Authorization | RBAC enforced on every endpoint |

**Performance:**

| Area | Implementation |
|------|---------------|
| Indexes | Composite indexes on frequently queried columns |
| Pagination | Cursor-based pagination for large datasets |
| Caching | Redis caching for analytics aggregations (if available) |
| Select related | Optimize ORM queries to avoid N+1 |
| Bulk operations | Use `bulk_create`, `bulk_update` for batch imports |

**Key Indexes:**
```sql
-- Campaigns
CREATE INDEX idx_campaign_status_start ON campaigns_campaign(status, start_date);
CREATE INDEX idx_campaign_code_code ON campaigns_code(code, is_active);

-- Leads
CREATE INDEX idx_lead_status_source ON leads_lead(status, source_id);
CREATE INDEX idx_lead_email ON leads_lead(email);

-- Referrals
CREATE INDEX idx_referral_code_code ON referrals_code(code, is_active);
CREATE INDEX idx_referral_event_referrer ON referrals_event(referrer_id, event_type);

-- Momentum
CREATE INDEX idx_momentum_ledger_customer ON momentum_ledger(customer_id, created_at);
CREATE INDEX idx_momentum_balance_customer ON momentum_balance(customer_id);

-- Attribution
CREATE INDEX idx_attribution_touchpoint_customer ON attribution_touchpoint(customer_id, created_at);
CREATE INDEX idx_attribution_result_order ON attribution_result(order_id);

-- Events
CREATE INDEX idx_event_outbox_status ON event_engine_outbox(status, created_at);
CREATE INDEX idx_event_idempotency_event_id ON event_engine_idempotency(event_id);
```

**Observability:**

| Area | Implementation |
|------|---------------|
| Structured logging | JSON logs for all Phase 4 operations |
| Audit trails | CampaignTransition, lead changes, referral events logged |
| Metrics | Event processing rate, outbox depth, attribution compute time |
| Alerting | Outbox backlog > 1000, event processing failures > 5% |
| Health checks | Event outbox health endpoint |

**Documentation:**
- API documentation (auto-generated from serializers)
- Wave-by-wave implementation notes
- Deployment checklist
- Rollback procedures

**Deliverables:**
- [ ] Rate limiting configured on all endpoints
- [ ] Input validation complete on all serializers
- [ ] Anti-abuse measures tested
- [ ] Database indexes created and verified
- [ ] Pagination working on list endpoints
- [ ] N+1 queries eliminated
- [ ] Structured logging implemented
- [ ] Audit trails verified
- [ ] Monitoring dashboards configured
- [ ] API documentation complete
- [ ] Deployment checklist created

---

## Frontend Structure

```
src/
├── pages/
│   ├── campaigns/
│   │   ├── CampaignList.jsx
│   │   ├── CampaignDetail.jsx
│   │   ├── CampaignCreate.jsx
│   │   ├── CampaignSchedule.jsx
│   │   └── CampaignCodes.jsx
│   ├── leads/
│   │   ├── LeadList.jsx
│   │   ├── LeadDetail.jsx
│   │   ├── LeadCreate.jsx
│   │   ├── LeadImport.jsx
│   │   └── LeadAnalytics.jsx
│   ├── events/
│   │   ├── EventLog.jsx
│   │   ├── EventDetail.jsx
│   │   └── OutboxMonitor.jsx
│   ├── attribution/
│   │   ├── AttributionDashboard.jsx
│   │   ├── TouchpointList.jsx
│   │   └── AttributionDetail.jsx
│   ├── referrals/
│   │   ├── ReferralDashboard.jsx
│   │   ├── ReferralCodes.jsx
│   │   ├── ReferralDetail.jsx
│   │   └── ReferralAnalytics.jsx
│   ├── momentum/
│   │   ├── MomentumDashboard.jsx
│   │   ├── MomentumLedger.jsx
│   │   ├── MomentumRules.jsx
│   │   └── MomentumCustomerDetail.jsx
│   └── portal/
│       ├── CampaignDiscovery.jsx
│       ├── MyReferrals.jsx
│       ├── MomentumCenter.jsx
│       └── ReferralShare.jsx
├── components/
│   ├── campaigns/
│   │   ├── CampaignStatusBadge.jsx
│   │   ├── CampaignCodeTable.jsx
│   │   ├── QRCodeGenerator.jsx
│   │   └── CampaignAnalytics.jsx
│   ├── leads/
│   │   ├── LeadStatusBadge.jsx
│   │   ├── LeadScoreCard.jsx
│   │   ├── LeadFollowUpList.jsx
│   │   ├── LeadConversionDialog.jsx
│   │   └── LeadPipelineBoard.jsx
│   ├── events/
│   │   ├── EventStatusBadge.jsx
│   │   ├── EventPayloadViewer.jsx
│   │   └── OutboxStats.jsx
│   ├── attribution/
│   │   ├── AttributionChart.jsx
│   │   ├── TouchpointTimeline.jsx
│   │   └── SourcePerformance.jsx
│   ├── referrals/
│   │   ├── ReferralCodeCard.jsx
│   │   ├── ReferralFunnel.jsx
│   │   └── ReferralStatusBadge.jsx
│   ├── momentum/
│   │   ├── BalanceCard.jsx
│   │   ├── LedgerTable.jsx
│   │   ├── RuleEditor.jsx
│   │   └── EarnBurnChart.jsx
│   ├── portal/
│   │   ├── CampaignCard.jsx
│   │   ├── ReferralShareButton.jsx
│   │   ├── MomentumBalanceCard.jsx
│   │   └── RedemptionDialog.jsx
│   └── realtime/
│       ├── NotificationToast.jsx
│       └── LiveIndicator.jsx
├── hooks/
│   └── useSSE.js
├── api/
│   ├── campaigns.js
│   ├── leads.js
│   ├── events.js
│   ├── attribution.js
│   ├── referrals.js
│   └── momentum.js
└── App.jsx (routes added)
    Sidebar.jsx (navigation added)
```

---

## Dependency Graph

```
Wave 1 (Foundation)
    │
    ├──→ Wave 2 (Campaign Core)  ──┐
    │                              │
    ├──→ Wave 3 (Lead CRM)  ──────┤
    │                              │
    └──→ Wave 4 (Event Engine) ───┤
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              Wave 5         Wave 6         Wave 7
            (Attribution)  (Referrals)    (Momentum)
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                            Wave 8 (SSE)
                                  │
                            Wave 9 (Portal)
                                  │
                            Wave 10 (Hardening)
```

**Parallelism:**
- Waves 2, 3, 4 proceed in parallel after Wave 1
- Waves 5, 6, 7 proceed in parallel after Wave 4
- Waves 8, 9, 10 are sequential

---

## Estimated Effort

| Wave | Duration | Dependencies | Parallelizable |
|------|----------|--------------|----------------|
| Wave 1: Foundation | 2–3 days | None | No |
| Wave 2: Campaign Core | 3–5 days | Wave 1 | Yes (with 3, 4) |
| Wave 3: Lead CRM | 3–5 days | Wave 1 | Yes (with 2, 4) |
| Wave 4: Event Engine | 3–5 days | Wave 1 | Yes (with 2, 3) |
| Wave 5: Attribution | 2–3 days | Wave 4 | Yes (with 6, 7) |
| Wave 6: Referral Program | 2–3 days | Wave 4 | Yes (with 5, 7) |
| Wave 7: Momentum | 2–3 days | Wave 4 | Yes (with 5, 6) |
| Wave 8: Real-Time (SSE) | 2–3 days | Waves 5, 6, 7 | No |
| Wave 9: Portal Integration | 3–5 days | Waves 2–7 | No |
| Wave 10: Hardening | 2–3 days | All prior | No |
| **Total** | **4–6 weeks** | | |

---

## Critical Path

```
Wave 1 (Foundation)
    ↓
Wave 4 (Event Engine)
    ↓
Wave 5/6/7 (Attribution/Referrals/Momentum)
    ↓
Wave 8 (Real-Time SSE)
    ↓
Wave 9 (Portal Integration)
    ↓
Wave 10 (Hardening)
```

**Critical path duration:** ~3–4 weeks (2+3+3+3+2 = 13 working days minimum)

**Non-critical waves:** Campaign Core (2) and Lead CRM (3) run in parallel and have float.

---

## Rollback Strategy

Each wave includes:
1. **Migration rollback:** Reverse migration for each schema change
2. **Feature flag:** New endpoints behind `PHASE4_*` settings
3. **Data rollback:** Export before destructive migrations
4. **Code rollback:** Git revert to previous wave commit

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| MySQL JSON query performance | Medium | Index generated columns; test with realistic data volume |
| SSE connection limits | Low | HTTP/2 multiplexing; connection pooling; limit concurrent streams |
| Outbox polling latency | Low | Configurable interval; upgrade path to Redis Streams |
| Event processing backlog | Medium | Monitoring alerts; management command for manual processing |
| Attribution computation delay | Low | Async via event engine; eventual consistency acceptable |
| Referral fraud | Medium | Anti-abuse rules; manual review for flagged accounts |
| Frontend complexity | Medium | Component library; shared patterns across feature modules |

---

*Plan Version: 1.0*
*Last Updated: 2026-08-31*
*Status: APPROVED FOR IMPLEMENTATION*
