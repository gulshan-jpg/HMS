# CheckinOS — Commercial Multi-Tenant Hotel Property Management System (PMS)

CheckinOS is an enterprise-grade, multi-tenant Hotel Property Management System engineered to the operational and visual standards of **Cloudbeds, Mews, Little Hotelier, and Opera Cloud**. Designed specifically for independent boutique hotels, luxury resorts, and hospitality chains, CheckinOS provides front-desk operations, room inventory dispatch, multi-folio ledger accounting, night audits, mobile housekeeping, and self-serve B2B SaaS subscription billing.

---

## 1. System Overview & Core Capabilities

CheckinOS is delivered as a turnkey, production-ready SaaS application with strict design tokens, automated data protection, and robust security safeguards:

- **Strict Multi-Tenancy:** Row-level data isolation enforced by an automated SQLAlchemy event interceptor (`WHERE organization_id = current_org_id AND deleted_at IS NULL`) with subdomain-based property routing (`{slug}.checkinos.io`).
- **Front Desk Operations:** Instant check-in/checkout with automated folio posting, stay extensions, and zero-balance departure enforcement.
- **Strict Reservation Guard:** Sub-millisecond room inventory overlap detection returning `HTTP 409 Conflict` upon date collisions.
- **Availability Timeline (Gantt View):** 30-day interactive room rack with drag-and-drop reservation relocation and instant conflict verification.
- **Self-Serve Onboarding:** 2-step registration (`/signup`), 14-day automated free trial, 7-step guided onboarding wizard (`/welcome`), demo data banner with one-click purge, and floating interactive tour engine.
- **Stripe Billing Foundation:** 3-tier subscription packaging (Starter, Pro, Enterprise) with Stripe Checkout, Customer Portal, and idempotent webhook handling.
- **Mobile Housekeeping Dashboard:** Public, responsive floor view (`/hk/{token}`) accessible via mobile browsers with 24h signed share tokens, large touch targets, one-tap clean toggles, and maintenance issue reporting.
- **Data Safety & Compliance:** One-click full database export (ZIP with 6 raw CSVs and verification manifest), 30-day Trash Bin with single-click restoration, and append-only audit trail logging.
- **CSV Bulk Import Wizard:** Transactional bulk importer for Rooms and Guests with row-by-row error diagnostics and downloadable CSV templates.
- **Print Engine:** ReportLab-powered A4 GST/VAT tax invoice generation (`GET /api/reservations/{id}/invoice.pdf`) with sequential numbering (`{org_slug}-{year}-{seq:06d}`).
- **Observability:** Health probes (`/healthz`, `/readyz`), Prometheus metrics exporter (`/metrics`), and offline-tolerant Progressive Web App (PWA) service worker.

---

## 2. Multi-Tenant Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (SPA & PWA)                        │
│  Inter UI · Strict Design Tokens · Chart.js · JetBrains Mono           │
│  Keyboard Shortcuts (⌘K, N, ?) · Offline Service Worker · Print Engine │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / Subdomain ({slug}.checkinos.io)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND RUNTIME                         │
│                                                                        │
│   Subdomain & JWT Tenant Resolver ──► SlowAPI (5/min IP Rate Limiter)  │
│   Unified Error Envelope Handler   ──► Pydantic v2 Validation Schemas  │
│   Write-Locking Subscription Guard──► ReportLab PDF Invoice Engine     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       SQLAlchemy 2 ORM REPOSITORY                      │
│                                                                        │
│   Row-Level Event Interceptor ─────► Append-Only Audit Logging         │
│   30-Day Soft-Delete Filter   ─────► Optimistic Concurrency (Version)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
       Development: SQLite 3             Production: PostgreSQL 16
```

---

## 3. UI Navigation & Route Map

### Public Marketing & Trust Pages
| Path | Page Name | Description |
| :--- | :--- | :--- |
| `/` | **Landing Page** | High-converting SaaS marketing page with feature grid and testimonials. |
| `/pricing` | **Pricing & Plans** | 3-tier commercial packaging with monthly/annual switch and feature table. |
| `/security` | **Security Architecture**| Tenant isolation, encryption, SOC 2 readiness, and responsible disclosure. |
| `/legal/terms` | **Terms of Service** | Hospitality SaaS terms, 99.9% uptime SLA, and 100% data ownership guarantee. |
| `/legal/privacy` | **Privacy Policy** | India DPDP Act 2023 & GDPR compliance, guest rights, data retention rules. |
| `/legal/dpa` | **Data Processing Addendum** | Standard contractual clauses, technical organizational measures (TOMs). |
| `/status` | **System Status** | Live operational status, 90-day uptime indicators, and incident history. |
| `/changelog` | **Changelog** | Public product release notes and version history. |

### Operational App Views
| Path | View | Key Functionality |
| :--- | :--- | :--- |
| `/signup` | **Self-Serve Registration** | Create new hotel organization, owner user, trial, and demo data. |
| `/welcome` | **Onboarding Wizard** | 7-step wizard (Hotel details, room types, rooms, taxes, staff, policies). |
| `/app` / `/` | **Operations Dashboard** | 12-column KPI cards, 14-day velocity chart, arrivals/departures, activity feed. |
| `/reservations`| **Reservation Desk** | Multi-status table, guest drawers, rate plan selection, overlap validation. |
| `/timeline` | **Availability Timeline** | 30-day Gantt rack with live drag-and-drop room/date relocation. |
| `/rooms` | **Room Inventory** | Floor filters, status pills (available, dirty, clean, out-of-order), management modal. |
| `/housekeeping`| **Turnover Dispatch** | 3-column Kanban board synchronizing physical room status with front desk. |
| `/hk/{token}` | **Mobile Housekeeping** | Public floor dashboard for mobile devices with one-tap status toggles. |
| `/billing` | **Folio & Cashiering** | Itemized charges, payments, multi-folio splits, and A4 PDF tax invoices. |
| `/guests` | **Guest CRM Directory** | Lifetime stay statistics, cumulative spend, contact info, and history drawer. |
| `/settings` | **Property Administration**| Property branding, rate plans, email templates, backups, trash, audit logs. |
| `/import` | **CSV Bulk Importer** | Downloadable templates, error preview validation, atomic bulk insertion. |
| `/locked` | **Subscription Paywall** | Graceful read-only state for expired trials with direct checkout buttons. |

---

## 4. Design System Tokens

CheckinOS enforces a strict, zero-elevation commercial design system:

| Token | Hex Value | Application |
| :--- | :--- | :--- |
| `--bg` | `#F9FAFB` | Main workspace background |
| `--surface` | `#FFFFFF` | Cards, modals, drawers, table panels |
| `--surface-alt` | `#F3F4F6` | Table headers, row hover states |
| `--border` | `#E5E7EB` | Subtle 1px structural dividers |
| `--border-strong` | `#D1D5DB` | Focus rings, form input active borders |
| `--text` | `#111827` | Primary headings, high-contrast values |
| `--text-secondary` | `#6B7280` | Subheadings, metadata labels |
| `--text-tertiary` | `#9CA3AF` | Form placeholders, subtle timestamps |
| `--accent` | `#111827` | Primary buttons, active navigation pills |
| `--accent-hover` | `#1F2937` | Button hover and pressed states |
| `--success` | `#059669` | Available rooms, paid folios, active trials |
| `--warning` | `#D97706` | Dirty rooms, pending turnovers, due payments |
| `--danger` | `#DC2626` | Overdue departures, out-of-order rooms, cancellations |
| `--info` | `#2563EB` | In-house stays, informational badges |

---

## 5. Quick Start & Local Setup

### Prerequisites
- Python 3.12+ (tested through Python 3.13)
- SQLite 3 (included with Python) or PostgreSQL 16+

### Setup Instructions

```bash
# 1. Clone repository and navigate to workspace
git clone <repo-url> CheckinOS
cd CheckinOS

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure local environment variables
cp .env.example .env

# 5. Apply database migrations to head
python -m alembic upgrade head

# 6. Seed demo property dataset
python seed.py

# 7. Start development server
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` in your web browser.

---

## 6. Default Credentials (Seed Data)

| Role | Email / Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Organization Owner** | `admin@hotel.com` / `admin` | `admin123` | Full administrative control, billing, exports |
| **Front Desk Staff** | `staff@hotel.com` / `staff` | `staff123` | Check-in, checkout, folios, reservations |
| **Housekeeping Lead** | `maria@hotel.com` / `maria` | `staff123` | Housekeeping dispatch, mobile floor views |

---

## 7. Automated Test Suite

CheckinOS features comprehensive test coverage with automated in-memory SQLite isolation:

```bash
# Run complete test suite across all 26 test files (61 tests)
python -m pytest tests/ -v
```

### Coverage Highlights:
- **Tenant Isolation:** Multi-organization row-level isolation ensuring zero cross-tenant query leaks.
- **Plan Limits & Billing:** 16th room rejection on Starter tier (`HTTP 402 plan_limit`), trial expiration write locks.
- **Optimistic Concurrency:** Concurrent update conflict detection via `version` matching (`HTTP 409 conflict`).
- **Data Safety:** Soft delete and restore lifecycle from Trash Bin; full ZIP export validation with 6 CSVs.
- **Stripe Webhooks:** Checkout session completion and event idempotency (`WebhookEvent`).
- **Mobile Housekeeping:** 24h signed share token generation, unauthenticated public view, and clean status updates.
- **PDF Tax Invoices:** ReportLab binary stream validation (`%PDF-`) with sequential tax invoice numbering.
- **CSV Bulk Import:** Preview validation with error reporting, followed by transactional atomic insertion.

---

## 8. Documentation Sitemap

- [Production Deployment Runbook (LAUNCH.md)](file:///c:/Users/Gulshan/OneDrive/Desktop/HMS/LAUNCH.md)
- [Security Architecture & Policy (SECURITY.md)](file:///c:/Users/Gulshan/OneDrive/Desktop/HMS/SECURITY.md)
- [Commercial Packaging & Pricing Guide (PRICING.md)](file:///c:/Users/Gulshan/OneDrive/Desktop/HMS/PRICING.md)
- [Release History & Changelog (CHANGELOG.md)](file:///c:/Users/Gulshan/OneDrive/Desktop/HMS/CHANGELOG.md)
