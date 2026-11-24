"""Housekeeping Management API Endpoints."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models import ActivityLog, HousekeepingTask, Room, User
from app.schemas import (
    HousekeepingTaskCreate,
    HousekeepingTaskResponse,
    HousekeepingTaskUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/housekeeping", tags=["Housekeeping"])


@router.get("", response_model=PaginatedResponse[HousekeepingTaskResponse])
def list_housekeeping_tasks(
    status: Optional[str] = Query(None, description="Filter by status (pending, in_progress, done)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, urgent)"),
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List housekeeping and maintenance tasks with filtering."""
    query = db.query(HousekeepingTask).join(HousekeepingTask.room)

    if status and status.lower() != "all":
        query = query.filter(HousekeepingTask.status == status.lower())
    if priority and priority.lower() != "all":
        query = query.filter(HousekeepingTask.priority == priority.lower())
    if room_id is not None:
        query = query.filter(HousekeepingTask.room_id == room_id)

    total = query.count()
    tasks = (
        query.order_by(
            HousekeepingTask.status.asc(),
            HousekeepingTask.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=[HousekeepingTaskResponse.model_validate(t) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=HousekeepingTaskResponse)
def get_housekeeping_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve single housekeeping task."""
    task = db.query(HousekeepingTask).filter(HousekeepingTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Housekeeping task with ID {task_id} not found",
        )
    return HousekeepingTaskResponse.model_validate(task)


@router.post("", response_model=HousekeepingTaskResponse, status_code=status.HTTP_201_CREATED)
def create_housekeeping_task(
    payload: HousekeepingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new housekeeping or maintenance work order."""
    room = db.query(Room).filter(Room.id == payload.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {payload.room_id} not found",
        )

    task = HousekeepingTask(
        room_id=payload.room_id,
        task_type=payload.task_type,
        status="pending",
        priority=payload.priority,
        assigned_to=payload.assigned_to.strip() if payload.assigned_to else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(task)

    # If maintenance task, optionally tag room status to maintenance
    if payload.task_type == "maintenance_repair" and room.status != "occupied":
        room.status = "maintenance"

    db.commit()
    db.refresh(task)

    # Activity log
    log = ActivityLog(
        event_type="task_created",
        description=f"Task '{task.task_type.replace('_', ' ').title()}' scheduled for Room {room.number}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return HousekeepingTaskResponse.model_validate(task)


@router.patch("/{task_id}/status", response_model=HousekeepingTaskResponse)
def update_task_status(
    task_id: int,
    payload: HousekeepingTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advance or complete a housekeeping task and synchronize room readiness."""
    task = db.query(HousekeepingTask).filter(HousekeepingTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Housekeeping task with ID {task_id} not found",
        )

    if payload.status:
        task.status = payload.status
        if payload.status == "done":
            task.completed_at = datetime.now(timezone.utc)
            # If the room was dirty, cleaning, or maintenance, completing the task flips it to available (unless occupied)
            room = task.room
            if room and room.status in ["dirty", "cleaning", "maintenance"]:
                room.status = "available"
        elif payload.status == "in_progress":
            room = task.room
            if room and room.status == "dirty":
                room.status = "cleaning"

    if payload.priority:
        task.priority = payload.priority
    if payload.assigned_to is not None:
        task.assigned_to = payload.assigned_to.strip() if payload.assigned_to else None
    if payload.notes is not None:
        task.notes = payload.notes.strip() if payload.notes else None

    db.commit()
    db.refresh(task)

    # Activity log
    log = ActivityLog(
        event_type="task_completed" if task.status == "done" else "task_updated",
        description=f"Task '{task.task_type.replace('_', ' ')}' for Room {task.room.number} moved to {task.status}",
        actor=current_user.full_name,
    )
    db.add(log)
    db.commit()

    return HousekeepingTaskResponse.model_validate(task)
