"""Audit Log recording service."""
import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.models import AuditLog


def log_audit(
    db: Session,
    org_id: int,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: int,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Record an audit trail entry with before/after state diffs."""
    entry = AuditLog(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=json.dumps(before_state, default=str) if before_state else None,
        after_json=json.dumps(after_state, default=str) if after_state else None,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
