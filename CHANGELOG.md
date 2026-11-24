# Changelog

All notable changes to the CheckinOS Hotel Property Management System are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-11-23

### Major Milestone: Commercial B2B SaaS Launch
CheckinOS transitions from a single-property management system into a fully multi-tenant, commercial B2B SaaS platform capable of powering independent boutique hotels, luxury resorts, and multi-property hospitality groups.

### Added
- **Multi-Tenancy Foundation:**
  - Row-level tenant isolation via SQLAlchemy ORM event interceptor (`WHERE organization_id = current_org_id`).
  - Organization data model with plan tiers (`starter`, `pro`, `enterprise`), trial expiration tracking, and subscription states.
  - Subdomain routing (`{slug}.checkinos.io`) and JWT claim-based tenant resolution.
  - Room and user plan limits enforcement (`starter`: 15 rooms, `pro`: 50 rooms, `enterprise`: unlimited) returning `HTTP 402 Payment Required`.
- **Self-Serve Onboarding:**
  - Public registration flow (`/signup`, `POST /api/signup`) creating organization, owner account, 14-day trial, and demo dataset in a single transaction.
  - 7-step interactive onboarding wizard (`/welcome`) guiding new hoteliers through property branding, room types, rooms, tax configuration, staff invitations, and policies.
  - Floating trial countdown banner with one-click upgrade button.
  - Demo data indicator pill with one-click safe purge (`DELETE /api/demo-data`).
  - 6-step guided walkthrough tour engine highlighting core operational views.
- **Stripe Billing & Subscriptions:**
  - Stripe Checkout Session creation (`POST /api/billing/checkout-session`).
  - Stripe Customer Portal integration (`POST /api/billing/portal`).
  - Webhook processing with strict event idempotency guard (`WebhookEvent` table).
  - Write-locking middleware gracefully transitioning expired trials and locked accounts to read-only mode (`/locked`).
- **Data Safety & Compliance:**
  - One-click full data export (`POST /api/admin/export`) packaging reservations, rooms, guests, folios, items, and payments into a ZIP archive with verification manifest.
  - Soft-delete system with 30-day Trash Bin (`/settings` -> Trash & Restore) and single-tap entity restoration.
  - Immutable, append-only audit trail logging (`audit_logs`) tracking before/after JSON states of all mutations.
  - Customizable email communication templates (`/settings` -> Email Templates) with live test sending.
- **CSV Bulk Import Wizard:**
  - Bulk importer for Rooms and Guests (`/import` and `/settings` -> CSV Import).
  - Downloadable CSV templates (`GET /api/import/template/{type}`).
  - Two-stage import workflow: validation preview with detailed row-by-row error diagnostics, followed by atomic transactional insertion.
- **Mobile Housekeeping Experience:**
  - Public, secure floor dashboard (`/hk/{token}`) accessible via mobile browsers without requiring staff authentication.
  - Ephemeral 24-hour signed JWT share tokens (`POST /api/housekeeping/generate-share-token`).
  - Large touch targets, floor-by-floor tabs, one-tap clean status toggle, and quick maintenance issue reporting drawer.
- **PDF Tax Invoice Engine:**
  - ReportLab-powered A4 tax invoice generation (`GET /api/reservations/{id}/invoice.pdf`).
  - Sequential tax invoice numbering scheme: `{org_slug}-{year}-{seq:06d}`.
  - Itemized room tariffs, GST/tax splits, incidental charges, guest details, and hotel branding header.
- **Trust & Marketing Pages:**
  - High-converting SaaS landing page (`/`).
  - Transparent 3-tier pricing page (`/pricing`) with monthly/annual switch and comprehensive comparison matrix.
  - Dedicated security portal (`/security`) detailing encryption, tenant isolation, and SOC 2 alignment.
  - Legal suite: Terms of Service (`/legal/terms`), Privacy Policy (`/legal/privacy`), and Data Processing Agreement (`/legal/dpa`).
  - Public system status page (`/status`) with 90-day historical uptime metrics and incident logs.
  - Public version changelog (`/changelog`).
- **Observability & Health Monitoring:**
  - Liveness probe (`GET /healthz`) verifying database socket connectivity.
  - Readiness probe (`GET /readyz`) evaluating DB health and host disk capacity.
  - Prometheus metrics scraper endpoint (`GET /metrics`).
  - Offline-tolerant Progressive Web App (PWA) manifest (`manifest.json`) and service worker (`sw.js`).

### Changed
- Converted currency formatting across all reports, folios, and UI tables to Indian Rupee (`₹` INR) standard with Indian comma notation (`₹1,50,000.00`).
- Upgraded test suite to 61 automated tests across 26 test files with 100% pass rate.
- Hardened optimistic concurrency control with `version` locking across reservations and rooms.

---

## [0.9.0] — 2026-11-20

### Beta Release: Core PMS Engine
- Core reservation ledger with sub-millisecond date overlap collision protection (`HTTP 409 Conflict`).
- 30-day interactive Gantt-style Availability Timeline with drag-and-drop reservation relocation.
- Kanban-style housekeeping board with turnover workflows (clean, dirty, inspection, out-of-order).
- Folio ledger accounting supporting multi-folio billing splits and itemized incidentals.
- Night Audit automation with daily business closures, rollover room charges, and tax reconciliation.
- Multi-tier rate plans (Flexible, Non-refundable, Bed & Breakfast, Long Stay) and seasonal calendar rate overrides.
- Role-Based Access Control (RBAC) separating administrative views from front-desk staff.
