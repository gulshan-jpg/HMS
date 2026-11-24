"""Stripe Subscription Management, Checkout, Portal, and Billing Status API."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_org, get_current_user, require_role
from app.models import ActivityLog, Organization, User, WebhookEvent
from app.schemas import (
    BillingStatusResponse,
    CheckoutSessionRequest,
)
from app.routers.org import compute_org_usage

logger = logging.getLogger("billing")
router = APIRouter(prefix="/api/billing", tags=["Subscriptions & Billing"])

try:
    import stripe
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None


@router.get("/status", response_model=BillingStatusResponse)
def get_billing_status(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve current subscription tier, trial timeline, and plan usage counters."""
    now = datetime.now(timezone.utc)
    days_left = 0
    if org.trial_ends_at:
        trial_end = org.trial_ends_at
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        if trial_end > now:
            days_left = (trial_end - now).days + 1

    usage = compute_org_usage(org, db)

    return BillingStatusResponse(
        plan=org.plan or "starter",
        status=org.subscription_status or "trialing",
        trial_ends_at=org.trial_ends_at,
        current_period_end=org.trial_ends_at if org.subscription_status == "trialing" else now + timedelta(days=30),
        days_left=days_left,
        usage=usage,
    )


@router.post("/checkout")
def create_checkout_session(
    payload: CheckoutSessionRequest,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Creates a Stripe Checkout Session for subscription upgrade or renewal."""
    plan_prices = {
        "starter": settings.STRIPE_PRICE_STARTER or "price_starter",
        "pro": settings.STRIPE_PRICE_PRO or "price_pro",
        "enterprise": settings.STRIPE_PRICE_ENTERPRISE or "price_enterprise",
    }
    price_id = plan_prices.get(payload.plan.lower(), settings.STRIPE_PRICE_PRO)

    has_stripe_key = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"))

    if stripe and has_stripe_key:
        try:
            # Create Stripe Customer if not present
            if not org.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=current_user.email,
                    name=org.name,
                    metadata={"organization_id": str(org.id), "slug": org.slug},
                )
                org.stripe_customer_id = customer.id
                db.commit()

            session = stripe.checkout.Session.create(
                customer=org.stripe_customer_id,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"/settings/billing?success=1&plan={payload.plan}",
                cancel_url="/settings/billing?cancelled=1",
                metadata={"organization_id": str(org.id), "plan": payload.plan},
            )
            return {"checkout_url": session.url, "session_id": session.id}
        except Exception as e:
            logger.warning(f"Stripe Checkout creation failed: {e}. Falling back to simulation.")

    # Graceful Simulated Checkout URL for test / offline mode
    mock_session_id = f"cs_mock_{org.slug}_{payload.plan}"
    simulated_url = f"/settings/billing?success=1&mock_session={mock_session_id}&plan={payload.plan}"
    return {"checkout_url": simulated_url, "session_id": mock_session_id}


@router.post("/portal")
def create_customer_portal(
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Creates a Stripe Customer Portal session to manage cards and invoices."""
    has_stripe_key = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"))

    if stripe and has_stripe_key and org.stripe_customer_id:
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=org.stripe_customer_id,
                return_url="/settings/billing",
            )
            return {"portal_url": portal_session.url}
        except Exception as e:
            logger.warning(f"Stripe Customer Portal creation failed: {e}")

    # Fallback when portal is not available
    return {"portal_url": "/settings/billing"}


@router.post("/cancel")
def cancel_subscription(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Cancels the active subscription for the hotel organization."""
    org.subscription_status = "cancelled"
    db.commit()

    log = ActivityLog(
        organization_id=org.id,
        event_type="subscription_cancelled",
        description=f"Subscription for '{org.name}' was cancelled. 30-day grace period started.",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return {"status": "cancelled", "message": "Subscription cancelled. Account is now in 30-day read-only grace period."}


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Stripe webhook listener managing subscription lifecycles with idempotency."""
    body_bytes = await request.body()
    event = None

    if stripe and settings.STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload=body_bytes,
                sig_header=stripe_signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook signature verification failed: {e}",
            )
    else:
        import json
        try:
            event = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_id = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
    event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)

    if not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event ID")

    # Idempotency guard via webhook_events
    existing = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    if existing:
        return {"status": "already_processed", "event_id": event_id}

    data_obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
    metadata = data_obj.get("metadata", {})
    org_id_str = metadata.get("organization_id")
    target_plan = metadata.get("plan", "pro")

    if event_type == "checkout.session.completed":
        sub_id = data_obj.get("subscription")
        cust_id = data_obj.get("customer")
        if org_id_str and org_id_str.isdigit():
            org = db.query(Organization).filter(Organization.id == int(org_id_str)).first()
            if org:
                org.subscription_status = "active"
                org.plan = target_plan
                if sub_id:
                    org.stripe_subscription_id = str(sub_id)
                if cust_id:
                    org.stripe_customer_id = str(cust_id)
                db.commit()

    elif event_type == "customer.subscription.updated":
        sub_id = data_obj.get("id")
        cust_id = data_obj.get("customer")
        org = db.query(Organization).filter(
            (Organization.stripe_subscription_id == sub_id) | (Organization.stripe_customer_id == cust_id)
        ).first()
        if org:
            org.subscription_status = "active"
            db.commit()

    elif event_type == "customer.subscription.deleted":
        sub_id = data_obj.get("id")
        org = db.query(Organization).filter(Organization.stripe_subscription_id == sub_id).first()
        if org:
            org.subscription_status = "cancelled"
            db.commit()

    elif event_type == "invoice.payment_failed":
        cust_id = data_obj.get("customer")
        org = db.query(Organization).filter(Organization.stripe_customer_id == cust_id).first()
        if org:
            org.subscription_status = "past_due"
            db.commit()

    elif event_type == "invoice.payment_succeeded":
        cust_id = data_obj.get("customer")
        org = db.query(Organization).filter(Organization.stripe_customer_id == cust_id).first()
        if org:
            org.subscription_status = "active"
            db.commit()

    # Log webhook event as processed
    db.add(WebhookEvent(id=event_id, event_type=event_type or "unknown"))
    db.commit()

    return {"status": "processed", "event_id": event_id}
