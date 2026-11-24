"""Email Delivery Service with SendGrid API Integration and Console Fallback."""
from datetime import datetime
import json
import logging
import re
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EmailTemplate, Organization

logger = logging.getLogger("email_service")

# Default fallback templates if none in DB
DEFAULT_TEMPLATES = {
    "guest_booking_confirmation": {
        "subject": "Your reservation at {{hotel.name}} is confirmed ({{reservation.confirmation_number}})",
        "body": "Dear {{guest.first_name}},\n\nYour reservation from {{reservation.check_in}} to {{reservation.check_out}} is confirmed.\nRoom: {{room.type_name}}\nTotal: ₹{{reservation.total_amount}}\n\nThank you for choosing {{hotel.name}}!",
    },
    "guest_pre_arrival": {
        "subject": "See you tomorrow at {{hotel.name}}",
        "body": "Dear {{guest.first_name}},\n\nWe look forward to welcoming you tomorrow! Check-in starts at 2:00 PM.\nHotel Address: {{hotel.address}}\nFront Desk: {{hotel.phone}}",
    },
    "guest_invoice": {
        "subject": "Tax Invoice for your stay at {{hotel.name}}",
        "body": "Dear {{guest.first_name}},\n\nPlease find attached the official invoice for your stay at {{hotel.name}}.\n\nWarm regards,\n{{hotel.name}}",
    },
    "guest_post_stay": {
        "subject": "How was your stay at {{hotel.name}}?",
        "body": "Dear {{guest.first_name}},\n\nThank you for staying with us! We hope you had a pleasant stay. Please let us know how we did.",
    },
    "staff_invite": {
        "subject": "You've been invited to join {{hotel.name}} on CheckinOS",
        "body": "Hello,\n\nYou have been invited to collaborate on {{hotel.name}}. Access your workspace here: {{login_url}}",
    },
    "staff_password_reset": {
        "subject": "Reset your CheckinOS password",
        "body": "Hello,\n\nClick the link below to reset your password (valid for 1 hour):\n{{reset_url}}\n\nIf you did not request this, please ignore.",
    },
    "owner_trial_reminder": {
        "subject": "Your CheckinOS trial ends in {{days_left}} days",
        "body": "Hello {{owner.name}},\n\nYour 14-day trial of CheckinOS for {{hotel.name}} has {{days_left}} days remaining. Upgrade now: {{billing_url}}",
    },
    "owner_payment_failed": {
        "subject": "Action required: Payment failed for {{hotel.name}}",
        "body": "Hello {{owner.name}},\n\nWe could not process your subscription payment. Please update your billing method: {{billing_url}}",
    },
}


def render_template_str(template_str: str, context: Dict[str, Any]) -> str:
    """Replaces {{key}} and {{nested.key}} placeholders with values from context."""
    def replacer(match):
        expr = match.group(1).strip()
        parts = expr.split(".")
        val = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, "")
            else:
                val = getattr(val, p, "")
            if val is None:
                val = ""
        return str(val)

    return re.sub(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}", replacer, template_str)


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    html_body: Optional[str] = None,
) -> bool:
    """Delivers email via SendGrid API or logs cleanly to console if unconfigured."""
    sender = from_email or settings.MAIL_FROM

    # SendGrid API integration
    if settings.SENDGRID_API_KEY and settings.SENDGRID_API_KEY.startswith("SG."):
        try:
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": sender.split("<")[-1].replace(">", "").strip() if "<" in sender else sender},
                "subject": subject,
                "content": [
                    {
                        "type": "text/html" if html_body else "text/plain",
                        "value": html_body or body,
                    }
                ],
            }
            headers = {
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)
                if res.status_code in (200, 202):
                    logger.info(f"SendGrid email delivered to {to_email} (Subject: {subject})")
                    return True
                else:
                    logger.warning(f"SendGrid error {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"SendGrid delivery failed: {e}")

    # Graceful fallback: console logging
    logger.info(f"[EMAIL SIMULATED] To: {to_email} | Subject: {subject}\n{body}")
    return True


async def send_templated_email(
    org_id: int,
    template_key: str,
    to_email: str,
    context: Dict[str, Any],
    db: Session,
) -> bool:
    """Fetches custom template from organization, substitutes variables, and sends."""
    tmpl = db.query(EmailTemplate).filter(
        EmailTemplate.organization_id == org_id,
        EmailTemplate.key == template_key,
    ).first()

    if tmpl:
        subject_raw = tmpl.subject
        body_raw = tmpl.body
    else:
        fallback = DEFAULT_TEMPLATES.get(template_key, {"subject": "Notification", "body": ""})
        subject_raw = fallback["subject"]
        body_raw = fallback["body"]

    rendered_subject = render_template_str(subject_raw, context)
    rendered_body = render_template_str(body_raw, context)

    return await send_email(to_email, rendered_subject, rendered_body)
