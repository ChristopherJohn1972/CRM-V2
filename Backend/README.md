# Enterprise CRM v2 — Clients / Customer 360 + Client Portal (Backend)

Python backend for the **Clients phase** and **Client Portal foundation** of Enterprise CRM
v2, built to the project reference specification. Serves the JS frontend (later phase)
through a JSON API.

## Stack

- **Django 5.2 + Django REST Framework** — HTTP layer, routing, serialization, pagination.
- **SQLAlchemy 2.0** — data access. The project deliberately keeps the database layer on
  SQLAlchemy (not the Django ORM) so the schema stays independent of Django conventions.
- **MySQL 8.0** — database (`crm_v2`). The schema starts from the existing
  `crmv2_database.sql` dump, extended by phase-2 migrations in `deploy/sql/`.
- **PyJWT + bcrypt** — stateless Bearer-token auth and password hashing.
- **Object storage** — pluggable. Local filesystem by default, S3 presigned URLs when
  `CRM_STORAGE_BACKEND=s3`.

## Layout

```
Backend/
├── config/            Django settings, URL root, WSGI/ASGI
├── common/            DB engine/session, domain events, audit, exceptions, middleware
├── iam/               RBAC foundation: users/roles/permissions/scope, JWT auth
├── clients/           Customer management, account-number generation, contacts,
│                      addresses, relationships, ownership, lifecycle
├── activities/        Activities, internal notes, timeline projection
├── communications/    SMS / email / call records, provider gateway interface, webhooks
├── documents/         Document metadata + versions + object storage + signed downloads
├── accounting/        Read gateway to the accounting module (graceful degradation)
├── customer360/       Aggregated read model for the single-screen customer view
├── portal/            Client Portal boundary: portal users, auth, customer access links,
│                      portal permissions, forgot/reset, lockout, separate JWT type
├── deploy/sql/        Schema + seed migrations (ordered 00x)
├── tests/             pytest suite (requires a local MySQL)
└── .env.example       All configuration switches
```

## Setup

```powershell
cd "C:\Users\MUTUKU\mu_code\CRM V2\Backend"

py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1) Configure credentials
Copy-Item .env.example .env
#   edit .env -> set CRM_DB_PASSWORD (your MySQL password)

# 2) Import the base schema + phase-2 migrations + seed data
mysql -u root -p crm_v2 < "..\crmv2_database.sql"
mysql -u root -p crm_v2 < "deploy\sql\002_clients_phase_schema.sql"
mysql -u root -p crm_v2 < "deploy\sql\003_seed_clients_phase.sql"
mysql -u root -p crm_v2 < "deploy\sql\004_portal_phase_schema.sql"
mysql -u root -p crm_v2 < "deploy\sql\005_seed_portal_test_roles.sql"
mysql -u root -p crm_v2 < "deploy\sql\006_client_contract_cleanup.sql"
```

The phase-2/3 SQL adds the tables and columns the Clients phase needs and seeds roles,
permissions, access policies and the configuration tables (relationship types, activity
types, document types, contact roles). `003` is safe to re-run (`INSERT IGNORE`).
Migration `004` adds the portal session + password-reset tables (not present in the frozen
baseline) and the portal permission catalog; `005` seeds the four Rights & Authorization
Matrix validation roles (`SYSTEM_ADMINISTRATOR`, `CRM_MANAGER`, `ACCOUNT_MANAGER`,
`CUSTOMER_SERVICE`). Migration `006` is the client **contract cleanup**: it adds the
canonical single-line `customer_addresses.address`, backfills it from the legacy first
line, and makes it NOT NULL; the legacy `address_line_1`/`address_line_2`/`state_province`
and `customers.display_name` / assignment columns remain in place for historical data but
are no longer written through the API. All phase seeds are idempotent, and the DDL phases
(`002`, `006`) carry skip guards in `apply_sql.py`.

```powershell
# Or run migrations from .env credentials without a shell password prompt:
.venv\Scripts\python.exe deploy\apply_sql.py --all
```

## Create an admin and run

```powershell
.venv\Scripts\python.exe manage.py create_admin --username admin --email admin@example.com --password "ChangeM3!"
.venv\Scripts\python.exe manage.py runserver
```

The `create_admin` command creates a `SUPER_ADMIN` user (bcrypt-hashed credential) that is
linked to the `GLOBAL_ALL` access policy and every permission.

The `create_test_accounts` command creates the four Reserved test-domain identities
(`test.admin@crm-v2.test`, `test.manager@crm-v2.test`, `test.accountmanager@crm-v2.test`,
`test.support@crm-v2.test`) · run it **after** migration `005`. A one-time random
temporary password is generated for each and printed to the console; credentials never
live in source code or SQL.

## Tests

`tests/conftest.py` creates a dedicated `crm_v2_test` database on your local MySQL
(host/user/password from the environment or `.env`), applies the full schema, seeds data,
and drives the API through DRF's `APIClient`.

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Coverage: account-number generation (sequential + concurrency), customer CRUD and lifecycle,
sensitive-field masking, contacts, relationships, documents, activities/timeline, SMS,
Customer 360, authorization/scope enforcement (permission + explicit scope, no implicit
`created_by` visibility), client-contract hardening (removed-field rejection, canonical
`legal_name`, single `address` field, transfer-only ownership, list/detail/search scope
consistency), the Rights & Authorization Matrix validation roles, the Client Portal
(onboarding temp credentials, forced password change, lockout, forgot/reset, customer-access
isolation, ALLOW/DENY, portal ⇄ internal token boundaries), and the operator/roles/rights
administration (operator creation with temp password + rights preview, role assignment,
direct ALLOW/DENY exceptions with source tracing, DENY-wins access review, effective scope,
role CRUD with scope policies, multi-right batch assignment, permission catalogue).

## API surface (all JSON, Bearer token)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/login` | Login → access token |
| POST / GET | `/api/auth/logout`, `/api/auth/me` | Session / current user + permissions |
| POST | `/api/portal/auth/login` | **Portal** login (temp credentials flag `must_change_password`) |
| POST | `/api/portal/auth/logout` | **Portal** logout (revokes session) |
| POST | `/api/portal/auth/change-password` | **Portal** set permanent password (current + new) |
| POST | `/api/portal/auth/forgot-password` | **Portal** request reset token (delivered out-of-band; dev echoes it) |
| POST | `/api/portal/auth/reset-password` | **Portal** reset with single-use token |
| GET | `/api/portal/me` | **Portal** profile + effective permissions + linked customer ids |
| GET | `/api/portal/customers` | **Portal** list of linked customers (active links) |
| GET | `/api/portal/customers/{id}` | **Portal** customer summary (denied if not actively linked) |
| POST | `/api/portal/users` | Internal: create portal user (returns one-time temp password) |
| GET | `/api/portal/users/{id}` | Internal: portal user detail |
| PATCH | `/api/portal/users/{id}/status` | Internal: activate / suspend / deactivate |
| POST | `/api/portal/users/{id}/password` | Internal: re-issue temporary credentials |
| GET, POST | `/api/portal/users/{id}/customers` | Internal: list / link customers (relationship type) |
| DELETE | `/api/portal/users/{id}/customers/{link_id}` | Internal: deactivate a customer link |
| GET, POST | `/api/portal/users/{id}/permissions` | Internal: effective grid / grant ALLOW or DENY |
| DELETE | `/api/portal/users/{id}/permissions/{code}` | Internal: revoke a portal permission |
| GET, POST | `/api/iam/operators` | Internal (`iam.user.manage`): list / create operator (returns one-time temp password + rights preview) |
| GET, PATCH | `/api/iam/operators/{id}` | Internal: operator detail (roles, direct exceptions, effective scope) / update |
| PUT | `/api/iam/operators/{id}/roles` | Internal: set operator roles (returns standard rights preview) |
| GET, POST | `/api/iam/operators/{id}/permissions` | Internal: list / set a direct ALLOW or DENY exception (with reason) |
| DELETE | `/api/iam/operators/{id}/permissions/{code}` | Internal: revoke a direct exception |
| GET | `/api/iam/operators/{id}/access-review` | Internal: full access review (effective ALLOW/DENY/NONE per right, source tracing, grouped, effective scope) |
| GET, POST | `/api/iam/roles` | Internal (`iam.role.manage`): list / create role with permissions + scope policies |
| GET, PATCH | `/api/iam/roles/{id}` | Internal: role detail (permissions, scope policies, effective scope) / update |
| GET | `/api/iam/rights` | Internal (`iam.permission.audit`): active permission catalogue |
| GET | `/api/iam/scopes` | Internal: scope catalogue with meanings |
| GET, POST | `/api/clients` | List (search/status/type/segment filter) · Create (generates account number) |
| GET, PATCH | `/api/clients/{id}` | Core details · update (optimistic `version`) |
| POST | `/api/clients/{id}/status` | Lifecycle transitions (business-rule validated) |
| POST | `/api/clients/{id}/close` | Close (account number never reused) |
| POST | `/api/clients/{id}/transfer` | Ownership reassignment |
| GET, POST | `/api/clients/{id}/contacts` | Contacts |
| PATCH, DELETE | `/api/clients/{id}/contacts/{cid}` | Contact update / deactivate |
| GET, POST | `/api/clients/{id}/relationships` | Customer-to-customer relationships |
| DELETE | `/api/clients/{id}/relationships/{rid}` | Remove relationship |
| GET, POST | `/api/clients/{id}/addresses` | Addresses (billing/shipping/office/home) |
| GET, POST | `/api/clients/{id}/activities` | Activities |
| PATCH | `/api/clients/{id}/activities/{aid}` | Update activity |
| POST | `/api/clients/{id}/activities/{aid}/complete` | Complete activity |
| GET, POST | `/api/clients/{id}/notes` | Internal notes (PRIVATE/TEAM/PUBLIC visibility) |
| GET | `/api/clients/{id}/timeline` | Normalized chronological history |
| GET, POST | `/api/clients/{id}/sms`, `/email`, `/calls` | Communication records |
| GET | `/api/clients/{id}/communications` | Combined SMS/email/call history |
| GET, POST | `/api/clients/{id}/documents` | List / upload (multipart) |
| GET | `/api/clients/{id}/documents/{did}/download` | Short-lived signed download URL |
| GET | `/api/clients/{id}/documents/{did}/versions` | History of versions |
| GET | `/api/clients/{id}/accounting-summary` | Financial summary (Accounting module) |
| GET | `/api/clients/{id}/360` | Customer 360 aggregation |
| POST | `/api/communications/webhooks/sms` | Provider status callbacks (`X-Webhook-Token`) |

Creation returns the generated `account_number` plus a `_360_url`; the frontend should
redirect the user straight to the Customer 360 page, per the Add Client flow.

## Client contract & scope

- **Canonical names** — the customer's name is `legal_name` (business) or the
  `first_name`/`middle_name`/`last_name` parts (individual). `display_name` is no longer
  writable, searchable, or exposed by the API; the DB column remains for historical data.
- **Addresses** — a single `address` string per address record (writing a legacy
  `address_line_1`/`address_line_2`/`state_province` payload is rejected). Persisted to
  `customer_addresses.address` (migration `006`); the legacy multiline columns remain but
  are not written. Customer 360 emits the same single field.
- **Assignment** — create does not accept `assigned_user_id`/`assigned_team_id`/`branch_id`;
  ownership is changed only through `POST /api/clients/{id}/transfer`. Customer-supplied
  `account_number` is ignored; the server generator always assigns it.
- **Visibility = permission + scope, never `created_by`** — a user sees the records that
  their role's `clients.customer.read` right plus explicit visibility scope permit
  (ALL / OWN / ASSIGNED / TEAM / DEPARTMENT / NONE). Creating a record does **not** grant
  the creator any implicit visibility; the record is visible once the creator's scope
  admits it (e.g. assignment via transfer for ASSIGNED scope). List, detail, search, count
  and every sub-resource apply the identical server-side scope filter
  (`clients/access.py`).
- **Provenance** — every customer row carries `created_by`/`created_at`/`updated_by` plus
  `audit_logs` rows (retained even when a customer is later removed via migration `007`).
  The pre-cleanup `crm_v2` records traced to real create actions, not seed fixtures.

## RBAC model

`USER → ROLE → RIGHTS / PERMISSIONS → SCOPE → RECORDS & ACTIONS`

- Roles bundle permissions (`role_permissions`); individual exceptions via
  `user_permissions` with `ALLOW`/`DENY` (DENY always wins).
- Scope comes from `access_policies` linked through `role_access_policies` /
  `user_access_policies`. Hierarchy: `NONE < OWN < ASSIGNED < TEAM < DEPARTMENT < ALL`.
- Record-level checks run server-side on every protected endpoint (`clients/access.py`).
  UI hiding is never the enforcement point.

### Portal authorization model

The Client Portal is a separate security boundary from the internal CRM.

- Portal users authenticate with their own JWT type (`typ: portal`); portal tokens are
  rejected by internal admin endpoints and internal tokens by portal endpoints
  (`iam/authentication.py`, `portal/authentication.py`).
- Access requires **both** an effective portal permission (`portal_permissions` +
  `portal_user_permissions`, ALLOW/DENY with DENY winning) **and** an active link in
  `portal_user_customers`. No link → no data, regardless of permissions.
- Relationship type ranks capabilities: `VIEWER < CONTACT < ADMIN < OWNER`
  (`portal/enums.py`); sensitive customer fields are never exposed through the portal.
- Passwords: temporary onboarding credential (must change on first login), bcrypt-hashed,
  10+ chars, company name rejected, 5 failed logins → 15-minute lockout, single-use
  30-minute reset tokens via `portal_password_reset_tokens`.
- Every portal action writes an `audit_logs` row with `actor_type = PORTAL_USER` and
  `actor_portal_user_id` populated.

### Operator / Roles / Rights administration

The `iam` admin API (`api/iam/...`) is the backend surface for managing internal
operators, roles, and access — the Operator/Roles/Rights/Access Review story from the
specification.

- **Operators** are created with identity + roles and receive a one-time random temporary
  password (bcrypt-hashed, printed once). Roles can be reassigned later; every change is
  audited.
- **Direct exceptions** (`user_permissions`) grant a single ALLOW **or** DENY on top of a
  role, always with a mandatory reason. DENY wins over ALLOW; revoking a direct row falls
  back to the role's rights.
- **Access Review** (`/api/iam/operators/{id}/access-review`) is the centrepiece: every
  active permission returns `effective` (`ALLOW`/`DENY`/`NONE`) plus its `sources` — where
  each right came from (role with role id/code/name, or direct with effect + reason). The
  same payload carries `rights_by_resource` (grouped for the RIGHTS panel) and the
  `effective scope` (NONE < OWN < ASSIGNED < TEAM < DEPARTMENT < ALL) with the policies that
  produced it.
- **Roles** bundle permissions and scope policies; `effective_scope` of a role is the
  strongest linked `access_policies` scope. Role and permission changes propagate to every
  member through the same `UserPrincipal` path used by the rest of the API — the frontend
  is never the enforcement point.
- **Multi-right assignment** — `role_permissions` is a many-to-many junction with a unique
  constraint on `(role_id, permission_id)`; duplicate assignments are impossible. The
  roles-rights surface accepts a batch of rights in one transaction:
  `PUT /api/roles/{id}/rights` (replace the complete selection), `POST ...` (add one or
  many, idempotently), `DELETE ...` (remove one or many). Bodies accept `rights` /
  `permission_codes` (codes) and/or `right_ids` (integer IDs); every supplied right is
  validated as existing and active (422 otherwise), the whole request commits atomically,
  and each change writes an audit row (`role.rights.added/removed/replaced`).
- **Effective views** — `GET /api/operators/{id}/effective-rights` returns the rights a
  user inherits from their active roles (with effective scope); `GET
  /api/operators/{id}/effective-access` returns the full access review
  (ALLOW/DENY/NONE per right with sources, grouped by resource, effective scope) and is the
  same source of truth as Role Details and `GET /api/me/permissions`. There is no
  permission cache: effective rights are recomputed from the DB on every authenticated
  request, so a right granted through any path is applied immediately.
- Guards are the existing permission codes: `iam.user.manage` (operators), `iam.role.manage`
  (roles), `iam.permission.audit` (rights catalogue). Internal tokens only — portal tokens
  are rejected at authentication.

## Design notes (per reference section)

1. **Boundaries** — each capability is its own app. Modules talk through domain events
   (`common/events.py`) and explicit services; `customer360` is an aggregation read model,
   not a table.
2. **Account numbers** — `SELECT ... FOR UPDATE` on the `account_number_sequences` counter
   (MySQL has no native sequences). Never `MAX()+1`. Minimum 4 chars, zero-padded (`0001`),
   unbounded growth (`10000` past 9999), never reused after close.
3. **Data model** — a single `customers` record for identity + CLI-side profile fields.
   Sensitive identifiers (`tax_identifier`, `registration_number`) are masked for users
   without `clients.customer.sensitive.read` and every sensitive write is audited.
4. **Contacts / relationships / ownership** — many contacts per customer, configurable
   relationship types, self-links rejected, ownership drives authorization and routing.
5. **Timeline** — projected from domain events; preserves event type, actor, source module,
   occurred-at and a human-readable summary.
6. **Communications** — provider calls sit behind an `SmsGateway` interface; provider
   statuses are normalized (`queued/sent/delivered/failed/rejected/unknown`); webhooks
   append delivery events; inbound SMS is never auto-linked to a customer by phone alone.
7. **Documents** — bytes live outside the DB; metadata + `storage_key` inside. Explicit
   versioning (new version never overwrites), SHA-256 checksums, access classification,
   `scan_status` reserved for malware scanning, and short-lived signed download URLs.
8. **360 query model** — one endpoint returns summary + recent items; full history uses the
   dedicated paginated endpoints via the `urls` block.
9. **Accounting** — a read-only gateway. If the module is unreachable the 360 returns
   `accounting.available = false` with a clear reason; it never fabricates balances.
10. **Production readiness** — server-side authorization everywhere, append-only audit with
    correlation IDs, atomic account-number generation, structured logging, and concurrency
    tests. See `.env.example` for the TLS/secrets/rate-limiting/health-check notes below.

## What is intentionally stubbed for this phase

- **Email sending** records an outbound email with `status=SENT`; wire a gateway like the
  SMS one when an email provider is chosen.
- **SMS provider** defaults to a dev gateway that logs. Set `CRM_SMS_PROVIDER_URL` +
  `CRM_SMS_PROVIDER_TOKEN` to call a real provider.
- **Malware scanning** stores `scan_status=PENDING`; hook your scanner to update it.
- **Accounting** calls `{CRM_ACCOUNTING_BASE_URL}/customers/{id}/financial-summary`; with no
  URL configured the views report `unavailable` (as designed).
- **Encryption at rest** for sensitive identifiers is a deploy-time concern; the schema
  masks and audits them now (see Backend 10).