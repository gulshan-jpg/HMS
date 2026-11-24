# CheckinOS Security Policy & Architecture

At CheckinOS, the security, integrity, and confidentiality of our hospitality customers' data is paramount. This document outlines our technical safeguards, tenant data isolation architecture, cryptographic controls, and responsible disclosure policy.

---

## 1. Multi-Tenant Data Isolation Architecture

CheckinOS enforces row-level multi-tenancy at the ORM layer using an automated query interceptor:

```
[ Incoming HTTP Request ]
          │
          ▼
[ Tenant Resolver Middleware ]
  Extracts tenant from Subdomain (*.checkinos.io) or JWT claim (org_id)
          │
          ▼
[ ContextVar: current_org_id ]
  Stores thread-safe / coroutine-safe active organization ID
          │
          ▼
[ SQLAlchemy 2 do_orm_execute Event Hook ]
  Automatically injects: WHERE organization_id = current_org_id AND deleted_at IS NULL
  on EVERY SELECT, UPDATE, and DELETE statement across all tenant-owned models.
```

### Isolation Guarantees:
1. **Zero Cross-Tenant Leakage:** Even if an API endpoint omits an explicit tenant filter, the ORM event hook injects the tenant filter before the SQL statement is compiled or dispatched.
2. **Global Admin Bypass Boundary:** System-level administrators can only view cross-tenant telemetry if explicitly authorized with immutable audit logging.
3. **Database Integrity Constraints:** All tenant-scoped tables (`rooms`, `reservations`, `guests`, `folios`, `payments`, `audit_logs`) carry explicit Foreign Key constraints referencing `organizations(id)` with `ON DELETE CASCADE` or `RESTRICT`.

---

## 2. Authentication & Cryptography

### Passwords
- All user passwords are required to be a minimum of 10 characters and contain at least one numeral and one alphabetical character.
- Hashing is performed using **PBKDF2-HMAC-SHA256** with 100,000 rounds and a cryptographic 16-byte random salt.
- Plaintext passwords are never logged, stored in cache, or returned in error traces.

### Session & Token Security
- Authentication is governed by signed **JSON Web Tokens (JWT)** utilizing HMAC-SHA256 (`HS256`).
- Access tokens expire after 480 minutes (8 hours) by default.
- Tokens are delivered via `Authorization: Bearer <token>` or secure, HTTP-only, `SameSite=Strict` cookies in browser sessions.

### Public Share Tokens (Housekeeping)
- Public floor tokens (`/hk/{token}`) for housekeeping staff use ephemeral, signed JWTs with strict 24-hour expiration windows.
- Share tokens are scoped exclusively to room cleaning status queries and maintenance issue creation. They carry no administrative or billing privileges.

---

## 3. Data Protection & Safety

### Soft Delete & 30-Day Trash Bin
- Entities (`reservations`, `rooms`, `guests`) are never hard-deleted during standard operational workflows.
- Deletions populate the `deleted_at` UTC timestamp.
- Records remain accessible in the **Trash Bin** (`/settings` -> Trash & Restore) for 30 days before permanent purging.
- Hoteliers can restore any accidentally deleted reservation or guest profile with one click.

### Append-Only Audit Logging
- Every administrative change (rate alterations, reservation relocations, room status updates, user role assignments) generates an immutable record in the `audit_logs` table.
- Logs capture:
  - `organization_id` & `user_id` (Actor)
  - `action` (e.g. `room_status_changed`, `reservation_moved`)
  - `entity_type` & `entity_id`
  - `before_json` (previous snapshot state)
  - `after_json` (new snapshot state)
  - `ip_address` & `user_agent`
  - `timestamp` (UTC)
- The audit log is append-only; no user or tenant administrator can alter or delete audit trail records.

### Complete Data Portability
- CheckinOS upholds 100% hotel data ownership.
- Organization owners can download their entire historical database at any moment via **Settings -> Data Safety -> Export All Data** (returns a ZIP archive containing 6 clean CSV files and a verification manifest).

---

## 4. Network Hardening & Threat Mitigation

### Rate Limiting (SlowAPI)
- Critical authentication endpoints (`/api/auth/login`, `/api/signup`, `/api/auth/forgot-password`) are strictly rate-limited to **5 requests per minute per IP address**.
- Rate-limit exceedances trigger `HTTP 429 Too Many Requests` with retry headers.

### Unified Error Envelopes
- Stack traces and internal database schemas are shielded from client responses.
- All errors are formatted into standard, machine-readable envelopes:
  ```json
  {
    "error": {
      "code": "resource_not_found",
      "message": "The requested reservation does not exist."
    }
  }
  ```

### Content Security & Transport
- In production (`ENV=prod`), all connections must use **TLS 1.3** or **TLS 1.2**.
- Standard HTTP security headers enforced:
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
  - `X-Frame-Options: SAMEORIGIN`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. SOC 2 Type II & DPDP / GDPR Compliance Readiness

CheckinOS is engineered to satisfy SOC 2 Type II trust principles and modern privacy legislation (India DPDP Act 2023, EU GDPR):

| Control Category | Implementation in CheckinOS |
| :--- | :--- |
| **CC6.1 - Logical Access** | Role-Based Access Control (RBAC) presets: Owner, Manager, Front Desk, Housekeeping, Accountant. |
| **CC6.6 - Boundary Protection** | Strict row-level tenancy enforcement and IP-based rate limiting on all ingress routes. |
| **CC6.8 - Threat Prevention** | Automated Pydantic input sanitization eliminating SQL injection and buffer overflow risks. |
| **CC7.2 - Change Auditing** | Append-only audit logs capturing before/after JSON states of all mutations. |
| **Privacy - Data Portability** | One-click raw CSV/ZIP full database export available 24/7 to hotel owners. |
| **Privacy - Right to Erasure** | 30-day soft-delete lifecycle followed by permanent hard purging upon explicit request. |

---

## 6. Vulnerability Disclosure Policy

We welcome reports from independent security researchers. If you believe you have discovered a vulnerability in CheckinOS:

1. **Email us directly:** `security@checkinos.io` (PGP key available upon request).
2. **Include details:** Step-by-step reproduction steps, proof-of-concept payload, and affected endpoints.
3. **Coordinated Disclosure:** Please allow 48 hours for our security engineering team to acknowledge your report and 14 days to deploy a verified mitigation before public disclosure.
4. **Safe Harbor:** We commit not to pursue legal action against researchers acting in good faith who avoid data exfiltration, privacy violations, or disruption of production services.
