"""CSV Bulk Import API Router for Guests and Rooms."""
import csv
import io
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_org, get_current_user, require_role
from app.models import Guest, Organization, Room, RoomType, User

router = APIRouter(prefix="/api/import", tags=["Import"])

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ImportPreviewError(BaseModel):
    row: int
    field: str
    message: str
    value: Optional[str] = None


class ImportPreviewResponse(BaseModel):
    type: str
    total_rows: int
    valid_rows: int
    error_rows: int
    preview: List[Dict[str, Any]]
    errors: List[ImportPreviewError]


class ImportExecuteResponse(BaseModel):
    success: bool
    imported: int
    skipped: int
    message: str


@router.get("/template/{type}")
def get_import_template(
    type: str,
    current_user: User = Depends(get_current_user),
):
    """Download CSV template with headers and realistic sample rows."""
    type_clean = type.strip().lower()
    if type_clean == "guests":
        content = (
            "name,email,phone,vip_tier,notes\r\n"
            "Rahul Sharma,rahul.sharma@example.com,+91 98765 43210,silver,Prefers high floor room\r\n"
            "Priya Patel,priya.patel@example.com,+91 98123 45678,gold,Allergic to feather pillows\r\n"
            "Vikram Malhotra,vikram.m@example.com,+91 99234 56789,none,Frequent business traveler\r\n"
        )
        filename = "guests_import_template.csv"
    elif type_clean == "rooms":
        content = (
            "number,room_type,floor,rate\r\n"
            "101,Deluxe King,1,7500\r\n"
            "102,Deluxe King,1,7500\r\n"
            "201,Executive Suite,2,12000\r\n"
            "301,Presidential Suite,3,25000\r\n"
        )
        filename = "rooms_import_template.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template type '{type}'. Allowed types are 'guests' or 'rooms'.",
        )

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


def _parse_csv_file(file: UploadFile) -> List[Dict[str, str]]:
    content = file.file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    file.file.seek(0)
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        # Strip all keys and values
        clean_row = {
            (k.strip().lower() if k else ""): (v.strip() if v else "")
            for k, v in r.items()
            if k
        }
        if any(clean_row.values()):
            rows.append(clean_row)
    return rows


@router.post("/preview", response_model=ImportPreviewResponse)
def preview_import(
    type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
):
    """Validate CSV rows without committing changes."""
    type_clean = type.strip().lower()
    if type_clean not in ["guests", "rooms"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type must be 'guests' or 'rooms'",
        )

    rows = _parse_csv_file(file)
    errors: List[ImportPreviewError] = []
    valid_preview: List[Dict[str, Any]] = []
    valid_count = 0

    if type_clean == "guests":
        existing_emails = {
            g.email.lower()
            for g in db.query(Guest.email).filter(
                Guest.organization_id == org.id,
                Guest.deleted_at.is_(None),
            ).all()
            if g.email
        }
        seen_emails_in_csv = set()

        for idx, row in enumerate(rows, start=2):  # Row 1 is header
            row_has_error = False
            name = row.get("name", "")
            first_name = row.get("first_name", "")
            email = row.get("email", "")

            # If name provided, parse to first/last
            if not name and not first_name:
                errors.append(ImportPreviewError(
                    row=idx,
                    field="name",
                    message="Guest name is required",
                    value="",
                ))
                row_has_error = True

            if email:
                if not EMAIL_REGEX.match(email):
                    errors.append(ImportPreviewError(
                        row=idx,
                        field="email",
                        message="Invalid email address format",
                        value=email,
                    ))
                    row_has_error = True
                elif email.lower() in existing_emails:
                    errors.append(ImportPreviewError(
                        row=idx,
                        field="email",
                        message=f"Guest with email '{email}' already exists in database",
                        value=email,
                    ))
                    row_has_error = True
                elif email.lower() in seen_emails_in_csv:
                    errors.append(ImportPreviewError(
                        row=idx,
                        field="email",
                        message=f"Duplicate email '{email}' found inside CSV file",
                        value=email,
                    ))
                    row_has_error = True
                else:
                    seen_emails_in_csv.add(email.lower())

            if not row_has_error:
                valid_count += 1
                if len(valid_preview) < 5:
                    valid_preview.append(row)

    elif type_clean == "rooms":
        existing_room_numbers = {
            r.number.lower()
            for r in db.query(Room.number).filter(
                Room.organization_id == org.id,
                Room.deleted_at.is_(None),
            ).all()
        }
        seen_numbers_in_csv = set()

        for idx, row in enumerate(rows, start=2):
            row_has_error = False
            number = row.get("number", "")
            floor_val = row.get("floor", "1")
            rate_val = row.get("rate", "")

            if not number:
                errors.append(ImportPreviewError(
                    row=idx,
                    field="number",
                    message="Room number is required",
                    value="",
                ))
                row_has_error = True
            elif number.lower() in existing_room_numbers:
                errors.append(ImportPreviewError(
                    row=idx,
                    field="number",
                    message=f"Room number '{number}' already exists in this property",
                    value=number,
                ))
                row_has_error = True
            elif number.lower() in seen_numbers_in_csv:
                errors.append(ImportPreviewError(
                    row=idx,
                    field="number",
                    message=f"Duplicate room number '{number}' in CSV",
                    value=number,
                ))
                row_has_error = True
            else:
                seen_numbers_in_csv.add(number.lower())

            if floor_val:
                try:
                    int(floor_val)
                except ValueError:
                    errors.append(ImportPreviewError(
                        row=idx,
                        field="floor",
                        message="Floor must be an integer",
                        value=floor_val,
                    ))
                    row_has_error = True

            if rate_val:
                try:
                    r_num = float(rate_val)
                    if r_num < 0:
                        raise ValueError()
                except ValueError:
                    errors.append(ImportPreviewError(
                        row=idx,
                        field="rate",
                        message="Rate must be a positive number",
                        value=rate_val,
                    ))
                    row_has_error = True

            if not row_has_error:
                valid_count += 1
                if len(valid_preview) < 5:
                    valid_preview.append(row)

    return ImportPreviewResponse(
        type=type_clean,
        total_rows=len(rows),
        valid_rows=valid_count,
        error_rows=len(rows) - valid_count,
        preview=valid_preview,
        errors=errors,
    )


@router.post("/execute", response_model=ImportExecuteResponse)
def execute_import(
    type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "manager")),
    org: Organization = Depends(get_current_org),
):
    """Execute import of valid rows in a single atomic transaction."""
    type_clean = type.strip().lower()
    if type_clean not in ["guests", "rooms"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type must be 'guests' or 'rooms'",
        )

    rows = _parse_csv_file(file)
    if not rows:
        return ImportExecuteResponse(
            success=True,
            imported=0,
            skipped=0,
            message="No rows found in uploaded file",
        )

    imported_count = 0
    skipped_count = 0

    if type_clean == "guests":
        existing_emails = {
            g.email.lower()
            for g in db.query(Guest.email).filter(
                Guest.organization_id == org.id,
                Guest.deleted_at.is_(None),
            ).all()
            if g.email
        }
        seen_emails_in_csv = set()

        for row in rows:
            name = row.get("name", "")
            first_name = row.get("first_name", "")
            last_name = row.get("last_name", "")
            email = row.get("email", "").strip() or None
            phone = row.get("phone", "").strip() or None
            vip_tier = row.get("vip_tier", "").strip()
            notes = row.get("notes", "").strip()

            if name and not first_name:
                parts = name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

            if not first_name:
                skipped_count += 1
                continue

            if email:
                if not EMAIL_REGEX.match(email) or email.lower() in existing_emails or email.lower() in seen_emails_in_csv:
                    skipped_count += 1
                    continue
                seen_emails_in_csv.add(email.lower())
                existing_emails.add(email.lower())

            full_notes = []
            if vip_tier:
                full_notes.append(f"VIP Tier: {vip_tier.upper()}")
            if notes:
                full_notes.append(notes)

            guest = Guest(
                organization_id=org.id,
                first_name=first_name,
                last_name=last_name or "",
                email=email,
                phone=phone,
                notes=" | ".join(full_notes) if full_notes else None,
                is_demo=False,
            )
            db.add(guest)
            imported_count += 1

        db.commit()

    elif type_clean == "rooms":
        # Check plan limit
        from app.deps import PLAN_LIMITS
        limits = PLAN_LIMITS.get(org.plan, PLAN_LIMITS["starter"])
        current_room_count = db.query(Room).filter(
            Room.organization_id == org.id,
            Room.deleted_at.is_(None),
        ).count()

        existing_room_numbers = {
            r.number.lower()
            for r in db.query(Room.number).filter(
                Room.organization_id == org.id,
                Room.deleted_at.is_(None),
            ).all()
        }
        seen_numbers_in_csv = set()

        # Cache existing room types
        room_types = {
            rt.name.lower(): rt
            for rt in db.query(RoomType).filter(
                RoomType.organization_id == org.id,
                RoomType.deleted_at.is_(None),
            ).all()
        }
        # Fallback default room type
        default_room_type = next(iter(room_types.values()), None)

        rooms_to_create = []
        for row in rows:
            number = row.get("number", "").strip()
            if not number:
                skipped_count += 1
                continue
            if number.lower() in existing_room_numbers or number.lower() in seen_numbers_in_csv:
                skipped_count += 1
                continue

            seen_numbers_in_csv.add(number.lower())
            existing_room_numbers.add(number.lower())

            floor_str = row.get("floor", "1")
            try:
                floor = int(floor_str)
            except ValueError:
                floor = 1

            room_type_name = row.get("room_type", "").strip()
            rate_str = row.get("rate", "5000")
            try:
                rate = float(rate_str)
            except ValueError:
                rate = 5000.0

            rt = room_types.get(room_type_name.lower()) if room_type_name else None
            if not rt and room_type_name:
                # Auto-create RoomType if not present
                code = re.sub(r"[^A-Za-z0-9]", "", room_type_name)[:6].upper() or "STD"
                rt = RoomType(
                    organization_id=org.id,
                    name=room_type_name,
                    code=code,
                    description=f"{room_type_name} imported via CSV",
                    base_rate=rate,
                    max_occupancy=2,
                    is_demo=False,
                )
                db.add(rt)
                db.flush()
                room_types[room_type_name.lower()] = rt
            elif not rt:
                rt = default_room_type

            if not rt:
                # If still no room type exists in the entire property, create Standard
                rt = RoomType(
                    organization_id=org.id,
                    name="Standard Room",
                    code="STD",
                    description="Standard guest room",
                    base_rate=rate,
                    max_occupancy=2,
                    is_demo=False,
                )
                db.add(rt)
                db.flush()
                room_types["standard room"] = rt

            room = Room(
                organization_id=org.id,
                number=number,
                floor=floor,
                room_type_id=rt.id,
                status="available",
                is_demo=False,
            )
            rooms_to_create.append(room)

        # Enforce room plan limit
        if current_room_count + len(rooms_to_create) > limits["rooms"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": {
                        "code": "plan_limit",
                        "message": (
                            f"Room limit reached for {org.plan.title()} plan (limit: {limits['rooms']}). "
                            f"You currently have {current_room_count} rooms and tried to import {len(rooms_to_create)} more. "
                            "Upgrade to add more rooms."
                        ),
                    }
                },
            )

        for rm in rooms_to_create:
            db.add(rm)
            imported_count += 1

        db.commit()

    return ImportExecuteResponse(
        success=True,
        imported=imported_count,
        skipped=skipped_count,
        message=f"Successfully imported {imported_count} {type_clean}. {skipped_count} invalid or duplicate rows were skipped.",
    )
