# CheckinOS Commercial Packaging & Pricing Guide

CheckinOS is commercial B2B SaaS designed for independent boutique hotels, bed & breakfasts, luxury resorts, and multi-property hospitality groups.

---

## 1. Subscription Plans & Tiers

All plans include a **14-day free trial** with full access to all features, zero credit card required upfront.

| Plan Tier | Monthly Billing | Annual Billing *(20% off)* | Room Limit | Staff User Limit | Ideal For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Starter** | **₹2,499** / mo | **₹1,999** / mo (₹23,988/yr) | Up to **15 Rooms** | Up to **3 Staff Accounts** | B&Bs, boutique homestays, urban guesthouses |
| **Pro** | **₹6,999** / mo | **₹5,599** / mo (₹67,188/yr) | Up to **50 Rooms** | Up to **10 Staff Accounts** | Boutique hotels, heritage villas, independent resorts |
| **Enterprise**| **₹14,999** / mo | **₹11,999** / mo (₹1,43,988/yr) | **Unlimited** | **Unlimited Accounts** | Hotel chains, large resorts, multi-property operators |

---

## 2. Feature Matrix

| Feature | Starter | Pro | Enterprise |
| :--- | :---: | :---: | :---: |
| **Front Desk Check-in / Checkout** | Included | Included | Included |
| **Room Inventory Management** | Up to 15 | Up to 50 | Unlimited |
| **User Accounts & RBAC** | 3 Users | 10 Users | Unlimited |
| **Availability Timeline (Gantt View)** | Included | Included | Included |
| **Folio Billing & Incidentals** | Included | Included | Included |
| **Night Audit Automation** | Included | Included | Included |
| **Mobile Housekeeping Dashboard (`/hk/{token}`)** | Included | Included | Included |
| **PDF Tax Invoices (ReportLab)** | Included | Included | Included |
| **Rate Plans & Calendar Overrides** | Included | Included | Included |
| **CSV Bulk Importer (Guests & Rooms)** | Included | Included | Included |
| **Full Data Export (ZIP / CSV)** | Included | Included | Included |
| **30-Day Trash & Restoration** | Included | Included | Included |
| **Custom Email Templates** | Standard | Fully Customizable | Fully Customizable |
| **Append-Only Audit Logs** | 7 Days | 90 Days | 365 Days + Export |
| **Custom Domain (`hotel.com`)** | — | Included | Included |
| **Multi-Property Group Management** | — | — | Included |
| **Dedicated Account Manager** | — | — | Included |
| **Custom API & POS Integrations** | — | — | Included |
| **SLA Guarantee** | 99.5% Uptime | 99.9% Uptime | 99.99% Financial SLA |

---

## 3. Plan Enforcement Rules

CheckinOS enforces tier boundaries programmatically at the API gateway layer:

1. **Room Count Limits:**
   - Evaluated during single room creation (`POST /api/rooms`) and CSV bulk imports (`POST /api/import/execute`).
   - If `current_active_rooms + new_rooms > plan_limit`, the API returns `HTTP 402 Payment Required` with error envelope:
     ```json
     {
       "error": {
         "code": "plan_limit",
         "message": "Room limit reached. Upgrade to add more."
       }
     }
     ```
2. **User Account Limits:**
   - Evaluated during team user invitations (`POST /api/org/invite` and `POST /api/users`).
   - If user count exceeds tier threshold, returns `HTTP 402 Payment Required`.

3. **Trial Expiration & Write Locking:**
   - Day 1–14: Full unrestricted read/write access.
   - Day 15+ (without active subscription): Account enters graceful read-only state. Front desk staff can still view existing reservations, guest profiles, and room statuses, but write mutations (creating bookings, changing rates) redirect to `/locked` with one-click upgrade options.
   - **Zero Hostage Policy:** Organization owners can download their complete data archive (`POST /api/admin/export`) even when an account is locked.

---

## 4. Enterprise Service Level Agreement (SLA)

For Enterprise tier customers, CheckinOS provides a contractually binding **99.99% Monthly Uptime SLA**:

| Monthly Uptime Percentage | Service Credit Percentage |
| :--- | :--- |
| **< 99.99% but ≥ 99.5%** | 10% credit applied to next invoice |
| **< 99.5% but ≥ 99.0%** | 25% credit applied to next invoice |
| **< 99.0%** | 50% credit applied to next invoice |

---

## 5. Billing Terms, Cancellations & Refunds

- **Payment Methods:** Major credit and debit cards (Visa, Mastercard, American Express, RuPay), Net Banking, and UPI via Stripe.
- **Taxes:** All stated prices are exclusive of applicable Indian GST (18%) or local digital services tax.
- **Cancellation:** Hoteliers can cancel their subscription at any time with zero penalty from **Settings -> Billing & Plan -> Manage Subscription** (Stripe Customer Portal).
- **Grace Period:** Upon cancellation, the subscription remains active until the end of the current billing cycle. Data is preserved for 90 days following cancellation before permanent scheduled purging.
- **Refund Policy:** CheckinOS offers a 14-day money-back guarantee for initial annual plan purchases if the software does not satisfy operational requirements.
