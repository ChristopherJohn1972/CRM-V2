CRM V2

A full-stack CRM and business operations platform built around controlled access, auditable workflows, financial data integrity, customer 360, and event-driven business processes.

This project goes beyond conventional CRUD by implementing the underlying engineering concerns that appear when a business application has multiple users, sensitive records, financial transactions, customer-facing workflows, and long-running business processes.

**What Makes This Project Different**

The system is designed around several problems that are often missing from typical portfolio CRUD applications:
* **Fine-grained authorization** rather than simple role checks
* **Server-side record-level visibility** using ownership, assignment, team, department, and global scopes
* **Explicit permission overrides**, where DENY rules take precedence
* **Customer 360 aggregation** across multiple business domains
* **Immutable audit trails and correlation IDs** for traceability
* **Persistent event outbox processing** with retries and idempotency
* **Optimistic concurrency control** to protect records from conflicting updates
* **Atomic business-number generation** for customer accounts and quotes
* **Decimal-based financial calculations** instead of floating-point arithmetic
* **Versioned documents with SHA-256 integrity checks**
* **Separate internal and customer portal authentication boundaries**
* **Business workflow state machines** rather than unrestricted status updates
* **Provider abstractions** for external services such as messaging and storage

The objective is not simply to demonstrate that the application can create, read, update, and delete records, but to demonstrate how a business system can remain **controlled, traceable, and consistent as complexity increases**.

       ** Supporting infrastructure**

   Audit ── Events ── Outbox ── Storage ── Messaging

** Core Engineering Features**
** 1. Fine-Grained Authorization**__
Authorization is implemented as a backend concern rather than relying on frontend visibility.

_The system supports:_
Role
 └── Permissions
      ├── ALLOW / DENY
      └── Scope
           ├── NONE
           ├── OWN
           ├── ASSIGNED
           ├── TEAM
           ├── DEPARTMENT
           └── ALL

Permission evaluation can therefore answer questions such as:
> Can this user perform this action on this specific record?
rather than only:
> Is this user an administrator?

**Access precedence**
Explicit permission decisions are evaluated with **DENY taking precedence over ALLOW**.
This provides a more realistic authorization model for systems where a user may receive permissions through several roles or assignments.

**Access Review**
The backend also exposes access-review functionality showing the effective permission decision and its source.
This makes authorization more inspectable and easier to troubleshoot than opaque role checks.

**2. Customer 360**
Instead of forcing users to navigate through independent CRM tables, the application builds a consolidated customer view.
A customer can be presented with information spanning:

* Identity
* Contacts
* Addresses
* Relationships
* Activities
* Notes
* Communications
* Documents
* Quotes
* Sales activity
* Accounting information
* Ownership
* Transfer history
* Customer timeline
This creates a **business read model** over multiple domains rather than treating each database table as an isolated screen.

**3. Auditable Business Operations**
Important operations are designed to leave an audit trail.
The system includes:
_* Audit records
* Correlation IDs
* Actor information
* Action information
* Entity references
* Event information
* Request tracing_

This makes it possible to investigate questions such as:
_Who changed this?
What was changed?
Which record was affected?
When did it happen?
Which request caused it?
What business event followed?_

This is particularly important for CRM and financial workflows where silent changes can be difficult to investigate.

**4. Persistent Event Outbox**
The project contains two complementary event mechanisms.

**_Domain events_**
An in-process event bus is used for lightweight application-level domain events.

**_Persistent events_**
The event engine provides a durable outbox-style workflow for events that need persistence.
It supports concepts including:

_* Event persistence
* Idempotency keys
* Retry counts
* Failed-event states
* Event processing
* Cleanup
* Retry handling
* Database locking
* `SKIP LOCKED` processing_

The design avoids claiming that the project uses Kafka or RabbitMQ when it does not.
The important engineering concept demonstrated here is **reliable business-event handling with persistence and retry semantics**.

**5. Concurrency and Data Integrity**
Business systems can fail even when CRUD operations appear correct.
The project therefore includes several mechanisms for protecting important data.

_**Optimistic concurrency**_
Version-based concurrency control helps prevent one user from silently overwriting another user's changes.
User A reads version 4
User B reads version 4

User A → update version 5 ✓
User B → update based on version 4 ✗
This is particularly useful for shared CRM records and workflow-heavy screens.

_**Atomic account numbering**_
Customer account numbers are generated using database locking mechanisms such as:
_sql_
SELECT ... FOR UPDATE
This prevents concurrent requests from generating conflicting business identifiers.

_**Quote numbering**_
Quote identifiers are also generated through controlled sequencing rather than relying on client-side numbering.

_**6. Financial Calculation Integrity**_
Financial values are calculated using `Decimal` rather than binary floating-point arithmetic.
Quote calculations include concepts such as:

Subtotal
    ↓
Discount
    ↓
Tax
    ↓
Additional Charges
    ↓
Grand Total

The calculation logic is kept on the backend so that the client cannot be trusted as the source of financial truth.
This is an important distinction between a UI calculator and a business application.

_**7. Quote Workspace**_
The quotation workflow is implemented as a business process rather than a generic CRUD form.
It includes:
_* Quote numbering
* Customer association
* Line items
* Quantities
* Prices
* Discounts
* Tax
* Additional charges
* Grand totals
* Approval workflow
* Submission
* Sending
* Cancellation
* Client responses
* Quote activity
* Quote events
* Document generation
* Template/version handling_
The frontend provides a dedicated **Quote Workspace** for operating this workflow.

**8. Sales Order and Payment Workflow**
Sales orders contain business states beyond simple database status fields.
The workflow covers:

_* Order creation
* Order items
* State transitions
* Payment information
* Receipt handling
* Receipt verification
* Verification workspace_
This separates business workflow transitions from arbitrary client-side status changes.

**9. Document Integrity and Storage Abstraction**
Documents are handled through a storage abstraction rather than tightly coupling the application to one storage provider.
The document layer supports:

_* Document metadata
* Versioning
* SHA-256 checksums
* Local storage
* S3-compatible storage
* Signed downloads
* Storage interfaces_
The checksum provides an integrity mechanism that can be used to detect whether stored content has changed.

**10. Communication Provider Abstraction**
External communication is isolated behind provider interfaces.
The system supports concepts such as:

Application
     │
     ▼
Communication Service
     │
     ▼
Provider Abstraction
     │
     ├── SMS Provider
     └── Other Providers

Provider responses are normalized into application-level communication states.
Webhook processing is also supported for provider status updates.
This keeps business logic from being tightly coupled to one external messaging service.

# 11. Internal CRM and Customer Portal Separation

The project includes customer-facing portal functionality in addition to the internal CRM.

The portal covers areas such as:

* Customer authentication
* Quotes
* Payments
* Complaints
* Documents
* Notifications
* Profile management
* Support
* Customer activity
* Rewards/momentum functionality

Internal and portal authentication use separate token types and security boundaries.

Portal-specific controls include mechanisms for:

* Temporary onboarding credentials
* Forced password changes
* Password reset tokens
* Login lockout
* Portal-specific permissions
* Customer access isolation
* Portal audit events

The goal is to prevent the customer-facing experience from simply becoming another view of the internal CRM.

# 12. Campaign Command Center

Campaign management goes beyond storing campaigns and descriptions.

The campaign domain includes concepts such as:

* Campaigns
* Products
* Audiences
* Offers
* Creative services
* AI-assisted creative generation
* Launch workflows
* Tracking
* Attribution
* Campaign activity

The frontend provides a dedicated campaign command-center workflow for managing these activities.

# Frontend Engineering

The frontend is built with:

* React 18
* React Router
* Vite
* JavaScript
* CSS

Rather than exposing every backend table as a separate CRUD page, the UI contains workflow-oriented workspaces.

Examples include:

* Customer 360
* Quote Workspace
* Sales Order Workspace
* Campaign Command Center
* Leads management
* Portal workflows

### Centralized API Client

API communication is centralized to handle:

* Bearer authentication
* Request handling
* Error normalization
* HTTP status handling
* Field-level validation errors
* Session expiration
* Consistent API behavior

This prevents every page from implementing its own interpretation of backend errors and authentication failures.

### Protected Routes

Frontend route protection works together with backend authorization.

The frontend controls the user experience, while the backend remains the final authority for access decisions.

# Testing

The backend includes automated tests covering areas such as:

* Authorization
* Permission evaluation
* Roles and rights
* Account-number generation
* Concurrency behavior
* Client contracts
* Portal authentication
* Portal isolation
* Portal dashboards
* Payments
* Complaints
* Notifications
* Rewards/momentum
* Quote workflows
* Administrative operations

# Technology Stack

## Backend

| Technology            | Purpose                  |
| --------------------- | ------------------------ |
| Python                | Application development  |
| Django                | Backend framework        |
| Django REST Framework | API layer                |
| SQLAlchemy            | Domain/data access layer |
| PostgreSQL            | Relational database      |
| JWT                   | Authentication           |
| Gunicorn              | Application server       |

## Frontend

| Technology   | Purpose           |
| ------------ | ----------------- |
| React 18     | UI                |
| React Router | Routing           |
| Vite         | Frontend tooling  |
| JavaScript   | Application logic |
| CSS          | UI styling        |

## Infrastructure

| Technology                   | Purpose                     |
| ---------------------------- | --------------------------- |
| GitHub Actions               | CI/workflows                |
| Render-compatible deployment | Backend hosting             |
| Vercel-compatible deployment | Frontend hosting            |
| PostgreSQL                   | Persistent application data |

# API Design

The API is organized around business domains rather than exposing raw database operations.

Examples include:
/api/auth/
/api/clients/
/api/quotes/
/api/sales-orders/
/api/campaigns/
/api/documents/
/api/communications/
/api/portal/
/api/health

Business logic is kept in service/domain layers instead of placing all application behavior directly inside route handlers.

# Security Model

Security responsibilities are distributed across the application.

Authentication
      ↓
Token Validation
      ↓
User / Portal Boundary
      ↓
Role Permissions
      ↓
ALLOW / DENY Evaluation
      ↓
Record Scope
      ↓
Business Operation
      ↓
Audit / Event

The system does not treat hiding a frontend button as authorization.

Sensitive operations are validated by the backend.


# Engineering Trade-offs

This project deliberately uses abstractions where they provide meaningful separation:

* Storage abstraction instead of hard-coded storage
* Communication provider abstraction
* Domain services instead of controller-heavy business logic
* Persistent events where durability matters
* Separate portal authentication
* Backend-owned financial calculations
* Database-level locking for business identifiers

# Current Hardening Areas

The project is actively suitable for further engineering work.
Areas that can be hardened further include:
* Moving browser authentication toward an HttpOnly/Secure cookie strategy where appropriate
* Production-grade malware scanning for uploaded documents
* Dedicated asynchronous worker infrastructure
* Expanded observability and metrics
* More comprehensive integration/end-to-end test coverage
* Further infrastructure hardening
* Clarification/consolidation of the multiple portal application directories

These are intentionally documented as future hardening areas rather than presented as completed functionality.


# Configuration

Sensitive configuration should be supplied through environment variables.

Secrets should never be committed to source control.

# Portfolio Focus

This project demonstrates practical experience with:

* Backend architecture
* REST API development
* Relational database design
* PostgreSQL
* SQLAlchemy
* Django REST Framework
* JWT authentication
* Fine-grained authorization
* Record-level access control
* Financial calculations
* Concurrency control
* Auditability
* Event-driven architecture
* Idempotency
* Retry processing
* Document integrity
* External service abstractions
* React application architecture
* Customer-facing portals
* Business workflow design
* Automated testing
* Cloud deployment

The central engineering challenge is not creating another CRUD application.

It is designing a system where **different users can perform different actions on different records, business operations remain consistent, important changes remain traceable, and customer-facing workflows remain isolated from internal operations.**

# License

See the [`LICENSE`](LICENSE) file for the applicable license.
