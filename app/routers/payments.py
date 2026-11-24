"""Payments and Stripe Integration with Webhook Idempotency and Manual Mode Fallback."""
from datetime import date
from decimal import Decimal
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    ActivityLog,
    Folio,
    Payment,
    Reservation,
    User,
    WebhookEvent,
)
from app.schemas import (
    PaymentIntentCreateRequest,
    PaymentIntentResponse,
    PaymentRefundRequest,
    PaymentResponse,
)
from app.routers.cancellation import get_current_business_date

logger = logging.getLogger("payments")
router = APIRouter(prefix="/api/payments", tags=["Payments"])

# Lazy / conditional stripe import
try:
    import stripe
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
except ImportError:
    stripe = None


@router.post("/create-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    payload: PaymentIntentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Create a Stripe PaymentIntent or return manual payment token if Stripe keys are not provided."""
    res = db.query(Reservation).filter(Reservation.id == payload.reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {payload.reservation_id} not found",
        )

    # Determine currency
    currency = "inr"

    has_stripe_key = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"))

    if stripe and has_stripe_key:
        try:
            # Stripe amounts in smallest currency unit (paise/cents)
            amount_cents = int(payload.amount * 100)
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                metadata={
                    "reservation_id": str(res.id),
                    "confirmation_number": res.confirmation_number,
                    "folio_id": str(payload.folio_id or ""),
                },
                description=f"CheckinOS Payment for #{res.confirmation_number}",
            )
            return PaymentIntentResponse(
                client_secret=intent.client_secret,
                payment_intent_id=intent.id,
                publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
                amount=payload.amount,
                currency=currency.upper(),
                manual_mode=False,
            )
        except Exception as e:
            logger.warning(f"Stripe PaymentIntent creation failed: {e}. Falling back to manual mode.")

    # Graceful manual mode fallback
    mock_id = f"pi_mock_{uuid.uuid4().hex[:12]}"
    return PaymentIntentResponse(
        client_secret=f"{mock_id}_secret_{uuid.uuid4().hex[:16]}",
        payment_intent_id=mock_id,
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "pk_mock_key",
        amount=payload.amount,
        currency=currency.upper(),
        manual_mode=True,
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Stripe webhook handler with strict idempotency protection via WebhookEvent table."""
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
        # Development / test JSON parsing
        import json
        try:
            event = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

    event_id = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
    event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)

    if not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing event ID")

    # Idempotency Check
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    if existing_event:
        return {"status": "already_processed", "event_id": event_id}

    if event_type == "payment_intent.succeeded":
        data_obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
        metadata = data_obj.get("metadata", {})
        res_id_str = metadata.get("reservation_id")
        folio_id_str = metadata.get("folio_id")
        amount_cents = data_obj.get("amount", 0)
        amount = Decimal(str(amount_cents)) / Decimal("100.00")
        pi_id = data_obj.get("id")

        if res_id_str:
            try:
                res_id = int(res_id_str)
                res = db.query(Reservation).filter(Reservation.id == res_id).first()
                if res:
                    folio_id = int(folio_id_str) if folio_id_str else None
                    if not folio_id:
                        primary_folio = db.query(Folio).filter(Folio.reservation_id == res.id, Folio.is_master.is_(True)).first()
                        folio_id = primary_folio.id if primary_folio else None

                    curr_date = get_current_business_date(db)
                    payment = Payment(
                        organization_id=res.organization_id,
                        reservation_id=res.id,
                        folio_id=folio_id,
                        date=curr_date,
                        amount=amount,
                        method="stripe",
                        reference=f"Stripe PI {pi_id}",
                        stripe_payment_intent_id=pi_id,
                        is_deposit=False,
                        is_refund=False,
                    )
                    db.add(payment)

                    log = ActivityLog(
                        event_type="payment",
                        description=f"Stripe payment received: ₹{amount:.2f} for #{res.confirmation_number}",
                        actor="Stripe Webhook",
                    )
                    db.add(log)
            except Exception as e:
                logger.error(f"Error processing webhook payment: {e}")

    # Mark webhook event as processed
    record = WebhookEvent(
        id=event_id,
        event_type=event_type or "unknown",
    )
    db.add(record)
    db.commit()

    return {"status": "success", "event_id": event_id}


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment(
    payment_id: int,
    payload: PaymentRefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    """Refund an existing payment in full or partial amount, recording a negative payment."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found",
        )

    if payment.amount <= Decimal("0.00") or payment.is_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot refund a credit/refund transaction. Must be an original positive payment.",
        )

    refund_amt = payload.amount if payload.amount is not None else payment.amount
    if refund_amt > payment.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount (₹{refund_amt:.2f}) cannot exceed original payment amount (₹{payment.amount:.2f}).",
        )

    # Attempt Stripe refund if Stripe ID is present and configured
    if stripe and payment.stripe_payment_intent_id and settings.STRIPE_SECRET_KEY:
        try:
            stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=int(refund_amt * 100),
                reason="requested_by_customer",
            )
        except Exception as e:
            logger.warning(f"Stripe gateway refund call failed or skipped: {e}")

    curr_date = get_current_business_date(db)

    refund_record = Payment(
        organization_id=payment.organization_id,
        reservation_id=payment.reservation_id,
        folio_id=payment.folio_id,
        date=curr_date,
        amount=-refund_amt,
        method="refund",
        reference=f"Refund of payment #{payment.id}: {payload.reason or 'Guest refund'}",
        is_deposit=False,
        is_refund=True,
        stripe_payment_intent_id=payment.stripe_payment_intent_id,
    )
    db.add(refund_record)

    # If original was a deposit, adjust deposit_paid
    res = payment.reservation
    if res and payment.is_deposit:
        res.deposit_paid = max(Decimal("0.00"), Decimal(str(res.deposit_paid)) - refund_amt)

    log = ActivityLog(
        event_type="payment",
        description=f"Refund of ₹{refund_amt:.2f} processed for payment #{payment.id} (#{res.confirmation_number if res else ''})",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()
    db.refresh(refund_record)

    return refund_record
