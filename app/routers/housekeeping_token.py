"""Mobile Housekeeping Token API endpoints (no staff login required)."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import current_org_id, get_db
from app.deps import get_current_org, get_current_user, require_role
from app.models import ActivityLog, HousekeepingTask, Organization, Room, User

router = APIRouter(prefix="/api/housekeeping", tags=["Housekeeping Mobile"])


class GenerateShareTokenResponse(BaseModel):
    token: str
    share_url: str
    expires_at: str


class RoomStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: clean, dirty, inspecting, available")
    notes: Optional[str] = None


class MaintenanceReportRequest(BaseModel):
    notes: str = Field(..., min_length=3, description="Description of the issue")
    priority: str = Field("medium", description="Priority: low, medium, high, urgent")


def verify_hk_token(token: str, db: Session) -> Organization:
    """Validate signed mobile housekeeping token and set tenant context."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("sub") != "mobile_hk":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "invalid_token", "message": "Invalid token type."}},
            )
        org_id = payload.get("org_id")
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": {"code": "invalid_token", "message": "Missing organization in token."}},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "invalid_token", "message": "Housekeeping link has expired or is invalid."}},
        )

    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.deleted_at.is_(None),
    ).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "org_not_found", "message": "Hotel organization not found."}},
        )

    # Set contextvar so tenant isolation selects correct records
    current_org_id.set(org.id)
    return org


@router.post("/generate-share-token", response_model=GenerateShareTokenResponse)
def generate_housekeeping_share_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "manager", "front_desk")),
    org: Organization = Depends(get_current_org),
):
    """Generate a 24-hour signed share link for cleaning staff."""
    expires_delta = timedelta(hours=24)
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": "mobile_hk",
        "org_id": org.id,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    share_url = f"/hk/{token}"

    return GenerateShareTokenResponse(
        token=token,
        share_url=share_url,
        expires_at=expires_at.isoformat(),
    )


@router.get("/token/{token}")
def get_housekeeping_dashboard_by_token(
    token: str,
    db: Session = Depends(get_db),
):
    """Public lightweight housekeeping dashboard grouped by floor for mobile staff."""
    org = verify_hk_token(token, db)

    rooms = (
        db.query(Room)
        .filter(Room.organization_id == org.id, Room.deleted_at.is_(None))
        .order_by(Room.floor.asc(), Room.number.asc())
        .all()
    )

    # Find pending / active tasks for each room
    room_ids = [r.id for r in rooms]
    tasks = (
        db.query(HousekeepingTask)
        .filter(
            HousekeepingTask.room_id.in_(room_ids),
            HousekeepingTask.status.in_(["pending", "in_progress"]),
        )
        .order_by(HousekeepingTask.created_at.desc())
        .all()
    )

    tasks_by_room: Dict[int, HousekeepingTask] = {}
    for t in tasks:
        if t.room_id not in tasks_by_room:
            tasks_by_room[t.room_id] = t

    floors_map: Dict[int, List[Dict[str, Any]]] = {}
    for r in rooms:
        active_t = tasks_by_room.get(r.id)
        room_data = {
            "id": r.id,
            "number": r.number,
            "floor": r.floor,
            "status": r.status,
            "room_type": r.room_type.name if r.room_type else "Standard",
            "notes": r.notes,
            "active_task": {
                "id": active_t.id,
                "task_type": active_t.task_type,
                "status": active_t.status,
                "priority": active_t.priority,
                "notes": active_t.notes,
            } if active_t else None,
        }
        floors_map.setdefault(r.floor, []).append(room_data)

    floors_list = [
        {"floor": f_num, "rooms": rooms_list}
        for f_num, rooms_list in sorted(floors_map.items())
    ]

    return {
        "org": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
        },
        "floors": floors_list,
        "total_rooms": len(rooms),
        "dirty_count": sum(1 for r in rooms if r.status in ["dirty", "cleaning"]),
        "clean_count": sum(1 for r in rooms if r.status in ["clean", "available"]),
    }


@router.post("/token/{token}/room/{room_id}/status")
def update_room_status_by_token(
    token: str,
    room_id: int,
    payload: RoomStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """One-tap status update from mobile cleaning view."""
    org = verify_hk_token(token, db)

    room = db.query(Room).filter(
        Room.id == room_id,
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
    ).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": f"Room {room_id} not found."}},
        )

    old_status = room.status
    target_status = payload.status.lower().strip()
    room.status = target_status
    if payload.notes:
        room.notes = payload.notes.strip()

    # If completed clean, mark any active tasks for this room as done
    if target_status in ["clean", "available"]:
        active_tasks = db.query(HousekeepingTask).filter(
            HousekeepingTask.room_id == room.id,
            HousekeepingTask.status.in_(["pending", "in_progress"]),
        ).all()
        for t in active_tasks:
            t.status = "done"
            t.completed_at = datetime.now(timezone.utc)

    db.add(ActivityLog(
        organization_id=org.id,
        event_type="housekeeping_update",
        description=f"Room {room.number} updated from {old_status} to {target_status} via mobile staff link",
        actor="Housekeeping Mobile",
    ))
    db.commit()
    db.refresh(room)

    return {
        "success": True,
        "room_id": room.id,
        "number": room.number,
        "status": room.status,
    }


@router.post("/token/{token}/room/{room_id}/maintenance")
def report_maintenance_by_token(
    token: str,
    room_id: int,
    payload: MaintenanceReportRequest,
    db: Session = Depends(get_db),
):
    """Report a maintenance issue from mobile view without login."""
    org = verify_hk_token(token, db)

    room = db.query(Room).filter(
        Room.id == room_id,
        Room.organization_id == org.id,
        Room.deleted_at.is_(None),
    ).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": f"Room {room_id} not found."}},
        )

    task = HousekeepingTask(
        organization_id=org.id,
        room_id=room.id,
        task_type="maintenance_repair",
        status="pending",
        priority=payload.priority.lower(),
        notes=payload.notes.strip(),
    )
    db.add(task)

    if room.status != "occupied":
        room.status = "maintenance"

    db.add(ActivityLog(
        organization_id=org.id,
        event_type="maintenance_reported",
        description=f"Maintenance issue reported for Room {room.number}: {payload.notes.strip()}",
        actor="Housekeeping Mobile",
    ))
    db.commit()
    db.refresh(task)

    return {
        "success": True,
        "task_id": task.id,
        "room_number": room.number,
        "priority": task.priority,
        "notes": task.notes,
        "status": task.status,
    }
