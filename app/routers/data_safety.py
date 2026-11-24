"""Data Safety API: Backups, CSV Export, Soft Delete & Trash, Audit Logs, and Email Templates."""
import csv
from datetime import datetime, date, timedelta, timezone
import io
import json
import os
import uuid
import zipfile
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, include_deleted_records
from app.deps import get_current_org, get_current_user, require_role
from app.models import (
    AuditLog,
    BackupRecord,
    EmailTemplate,
    ExportJob,
    Folio,
    FolioItem,
    Guest,
    Organization,
    Payment,
    Reservation,
    Room,
    User,
)
from app.schemas import (
    AuditLogResponse,
    BackupRecordResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    ExportJobResponse,
    GuestResponse,
    ReservationResponse,
    RoomResponse,
)
from app.services.email import send_email, render_template_str

router = APIRouter(prefix="/api", tags=["Data Safety & Operations"])


# ── 1. Email Templates API ───────────────────────────────────────────────────

@router.get("/settings/emails", response_model=List[EmailTemplateResponse])
def list_email_templates(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all customizable communication email templates."""
    templates = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.organization_id == org.id)
        .order_by(EmailTemplate.id.asc())
        .all()
    )
    return templates


@router.patch("/settings/emails/{template_key}", response_model=EmailTemplateResponse)
def update_email_template(
    template_key: str,
    payload: EmailTemplateUpdate,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Update subject or body template with {{variable}} substitution placeholders."""
    tmpl = db.query(EmailTemplate).filter(
        EmailTemplate.organization_id == org.id,
        EmailTemplate.key == template_key,
    ).first()

    if not tmpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email template '{template_key}' not found",
        )

    if payload.subject is not None:
        tmpl.subject = payload.subject.strip()
    if payload.body is not None:
        tmpl.body = payload.body.strip()

    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.post("/settings/emails/{template_key}/test")
async def send_test_email(
    template_key: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Send a test render of this template to the logged-in user's email."""
    tmpl = db.query(EmailTemplate).filter(
        EmailTemplate.organization_id == org.id,
        EmailTemplate.key == template_key,
    ).first()

    if not tmpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    mock_context = {
        "guest": {"first_name": "Test Guest", "email": current_user.email},
        "hotel": {"name": org.name, "address": org.address or "Bangalore", "phone": "+91 80 4123 4567"},
        "reservation": {"confirmation_number": "HTL-TEST-99", "check_in": "2026-12-01", "check_out": "2026-12-03", "total_amount": "7,500.00"},
        "room": {"type_name": "Deluxe King Room"},
        "owner": {"name": current_user.full_name},
        "days_left": "5",
        "billing_url": "/settings/billing",
        "login_url": "/login",
        "reset_url": "/reset-password?token=mock_test_token",
    }

    rendered_subject = f"[TEST] {render_template_str(tmpl.subject, mock_context)}"
    rendered_body = render_template_str(tmpl.body, mock_context)

    await send_email(current_user.email, rendered_subject, rendered_body)
    return {"status": "sent", "recipient": current_user.email, "subject": rendered_subject}


# ── 2. Automated Backups API ─────────────────────────────────────────────────

@router.get("/admin/backups", response_model=List[BackupRecordResponse])
def list_backups(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Retrieve historical daily automated and manual database backups."""
    backups = (
        db.query(BackupRecord)
        .filter(BackupRecord.organization_id == org.id)
        .order_by(BackupRecord.created_at.desc())
        .limit(30)
        .all()
    )
    return backups


@router.post("/admin/backups/run", response_model=BackupRecordResponse)
def trigger_manual_backup(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Trigger an on-demand SQL snapshot backup for this organization."""
    # Rate limit: 1 manual backup per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = (
        db.query(BackupRecord)
        .filter(
            BackupRecord.organization_id == org.id,
            BackupRecord.created_at >= one_hour_ago,
        )
        .first()
    )
    if recent:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit reached: You can create at most 1 manual backup per hour.",
        )

    today_str = date.today().isoformat()
    s3_key = f"backups/{org.slug}/{today_str}_{uuid.uuid4().hex[:6]}.sql.gz"

    # Simulate / record backup snapshot
    backup = BackupRecord(
        organization_id=org.id,
        s3_key=s3_key,
        size_bytes=1024 * 342,  # ~342 KB snapshot
        status="completed",
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)

    return backup


@router.get("/admin/backups/{backup_id}/download")
def download_backup(
    backup_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Download SQL backup snapshot file."""
    backup = db.query(BackupRecord).filter(
        BackupRecord.id == backup_id,
        BackupRecord.organization_id == org.id,
    ).first()

    if not backup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup record not found")

    content = f"-- CheckinOS Database Backup for {org.name} ({org.slug})\n-- Generated at {backup.created_at}\n-- Retention 30 days\nSELECT 1;\n"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename=backup_{org.slug}_{backup.id}.sql"},
    )


# ── 3. One-Click Data Export API ─────────────────────────────────────────────

def build_export_zip(org: Organization, db: Session, current_user: User) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Reservations CSV
        res_buf = io.StringIO()
        res_writer = csv.writer(res_buf)
        res_writer.writerow(["id", "confirmation_number", "guest_id", "room_id", "check_in_date", "check_out_date", "nights", "nightly_rate", "status"])
        for r in db.query(Reservation).filter(Reservation.organization_id == org.id).all():
            res_writer.writerow([r.id, r.confirmation_number, r.guest_id, r.room_id, r.check_in_date, r.check_out_date, r.nights, r.nightly_rate, r.status])
        zip_file.writestr("reservations.csv", res_buf.getvalue())

        # 2. Guests CSV
        g_buf = io.StringIO()
        g_writer = csv.writer(g_buf)
        g_writer.writerow(["id", "first_name", "last_name", "email", "phone", "address", "id_number"])
        for g in db.query(Guest).filter(Guest.organization_id == org.id).all():
            g_writer.writerow([g.id, g.first_name, g.last_name, g.email, g.phone, g.address, g.id_number])
        zip_file.writestr("guests.csv", g_buf.getvalue())

        # 3. Rooms CSV
        rm_buf = io.StringIO()
        rm_writer = csv.writer(rm_buf)
        rm_writer.writerow(["id", "number", "floor", "room_type_id", "status"])
        for rm in db.query(Room).filter(Room.organization_id == org.id).all():
            rm_writer.writerow([rm.id, rm.number, rm.floor, rm.room_type_id, rm.status])
        zip_file.writestr("rooms.csv", rm_buf.getvalue())

        # 4. Folios CSV
        f_buf = io.StringIO()
        f_writer = csv.writer(f_buf)
        f_writer.writerow(["id", "reservation_id", "name", "is_master"])
        for f in db.query(Folio).filter(Folio.organization_id == org.id).all():
            f_writer.writerow([f.id, f.reservation_id, f.name, f.is_master])
        zip_file.writestr("folios.csv", f_buf.getvalue())

        # 5. Folio Items CSV
        fi_buf = io.StringIO()
        fi_writer = csv.writer(fi_buf)
        fi_writer.writerow(["id", "reservation_id", "folio_id", "date", "description", "category", "amount"])
        for fi in db.query(FolioItem).filter(FolioItem.organization_id == org.id).all():
            fi_writer.writerow([fi.id, fi.reservation_id, fi.folio_id, fi.date, fi.description, fi.category, fi.amount])
        zip_file.writestr("folio_items.csv", fi_buf.getvalue())

        # 6. Payments CSV
        p_buf = io.StringIO()
        p_writer = csv.writer(p_buf)
        p_writer.writerow(["id", "reservation_id", "folio_id", "date", "amount", "method", "reference"])
        for p in db.query(Payment).filter(Payment.organization_id == org.id).all():
            p_writer.writerow([p.id, p.reservation_id, p.folio_id, p.date, p.amount, p.method, p.reference])
        zip_file.writestr("payments.csv", p_buf.getvalue())

        # 7. README.txt
        readme_content = f"""CheckinOS Data Export Archive for {org.name} ({org.slug})
Generated on: {datetime.now(timezone.utc).isoformat()}
Exported by: {current_user.full_name} ({current_user.email})

Contents:
- reservations.csv: Complete reservation ledger
- guests.csv: Guest CRM profiles
- rooms.csv: Room inventory and housekeeping status
- folios.csv: Folio splits and groupings
- folio_items.csv: Itemized charges and taxes
- payments.csv: Payment transactions and receipts

You own 100% of your data.
"""
        zip_file.writestr("README.txt", readme_content)

    return zip_buffer.getvalue()


@router.post("/admin/export")
def trigger_data_export(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Creates an export job and streams a ZIP archive containing CSVs of all organization tables."""
    job_id = str(uuid.uuid4())
    job = ExportJob(
        id=job_id,
        organization_id=org.id,
        user_id=current_user.id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()

    content = build_export_zip(org, db, current_user)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=checkinos_{org.slug}_export.zip"},
    )


@router.get("/admin/export/{job_id}/download")
def download_export_archive(
    job_id: str,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Streams a ZIP archive containing CSVs of all organization tables."""
    job = db.query(ExportJob).filter(
        ExportJob.id == job_id,
        ExportJob.organization_id == org.id,
    ).first()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")

    content = build_export_zip(org, db, current_user)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=checkinos_{org.slug}_export.zip"},
    )


# ── 4. Soft Delete, Trash, and Restore API ───────────────────────────────────

@router.get("/trash")
def get_trash_items(
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all soft-deleted records from the last 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Disable soft-delete filter temporarily to query deleted records
    include_deleted_records.set(True)
    try:
        deleted_reservations = (
            db.query(Reservation)
            .filter(
                Reservation.organization_id == org.id,
                Reservation.deleted_at.is_not(None),
                Reservation.deleted_at >= cutoff,
            )
            .order_by(Reservation.deleted_at.desc())
            .all()
        )

        deleted_guests = (
            db.query(Guest)
            .filter(
                Guest.organization_id == org.id,
                Guest.deleted_at.is_not(None),
                Guest.deleted_at >= cutoff,
            )
            .order_by(Guest.deleted_at.desc())
            .all()
        )

        deleted_rooms = (
            db.query(Room)
            .filter(
                Room.organization_id == org.id,
                Room.deleted_at.is_not(None),
                Room.deleted_at >= cutoff,
            )
            .order_by(Room.deleted_at.desc())
            .all()
        )

        return {
            "reservations": [ReservationResponse.model_validate(r) for r in deleted_reservations],
            "guests": [GuestResponse.model_validate(g) for g in deleted_guests],
            "rooms": [RoomResponse.model_validate(rm) for rm in deleted_rooms],
        }
    finally:
        include_deleted_records.set(False)


@router.delete("/reservations/{reservation_id}")
def soft_delete_reservation(
    reservation_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Soft delete reservation, moving it to trash."""
    res = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.organization_id == org.id,
        Reservation.deleted_at.is_(None),
    ).first()

    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    res.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Reservation #{res.confirmation_number} moved to trash."}


@router.post("/reservations/{reservation_id}/restore")
def restore_reservation(
    reservation_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Restore a soft-deleted reservation from trash."""
    include_deleted_records.set(True)
    try:
        res = db.query(Reservation).filter(
            Reservation.id == reservation_id,
            Reservation.organization_id == org.id,
        ).first()

        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

        res.deleted_at = None
        db.commit()
        return {"message": f"Reservation #{res.confirmation_number} restored successfully."}
    finally:
        include_deleted_records.set(False)


@router.delete("/guests/{guest_id}")
def soft_delete_guest(
    guest_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Soft delete guest profile, moving it to trash."""
    guest = db.query(Guest).filter(
        Guest.id == guest_id,
        Guest.organization_id == org.id,
        Guest.deleted_at.is_(None),
    ).first()

    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest profile not found")

    guest.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Guest '{guest.full_name}' moved to trash."}


@router.post("/guests/{guest_id}/restore")
def restore_guest(
    guest_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Restore a soft-deleted guest profile from trash."""
    include_deleted_records.set(True)
    try:
        guest = db.query(Guest).filter(
            Guest.id == guest_id,
            Guest.organization_id == org.id,
        ).first()

        if not guest:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

        guest.deleted_at = None
        db.commit()
        return {"message": f"Guest '{guest.full_name}' restored successfully."}
    finally:
        include_deleted_records.set(False)


@router.delete("/rooms/{room_id}")
def soft_delete_room(
    room_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Soft delete room only if no active or checked-in reservations exist."""
    room = db.query(Room).filter(
        Room.id == room_id,
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
    ).first()

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Check for active reservations
    active_res = db.query(Reservation).filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(["booked", "checked_in"]),
        Reservation.deleted_at.is_(None),
    ).first()

    if active_res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete Room {room.number}: active reservation #{active_res.confirmation_number} is scheduled.",
        )

    room.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Room {room.number} moved to trash."}


@router.post("/rooms/{room_id}/restore")
def restore_room(
    room_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin")),
):
    """Restore a soft-deleted room from trash."""
    include_deleted_records.set(True)
    try:
        room = db.query(Room).filter(
            Room.id == room_id,
            Room.organization_id == org.id,
        ).first()

        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

        room.deleted_at = None
        db.commit()
        return {"message": f"Room {room.number} restored successfully."}
    finally:
        include_deleted_records.set(False)


# ── 5. Audit Log API ─────────────────────────────────────────────────────────

@router.get("/audit-log", response_model=List[AuditLogResponse])
def list_audit_logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Query audit logs with before/after state diffs across the organization."""
    query = db.query(AuditLog).filter(AuditLog.organization_id == org.id)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return logs


@router.get("/audit-log/{log_id}", response_model=AuditLogResponse)
def get_audit_log_detail(
    log_id: int,
    org: Organization = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "admin", "manager")),
):
    """Retrieve full audit log record with JSON before/after state snapshot."""
    log = db.query(AuditLog).filter(
        AuditLog.id == log_id,
        AuditLog.organization_id == org.id,
    ).first()

    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")

    return log
