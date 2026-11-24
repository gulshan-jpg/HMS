"""Folio Split, Item Move, and Balance Transfer Engine."""
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ActivityLog, Folio, FolioItem, Payment, Reservation, User
from app.schemas import (
    FolioCreate,
    FolioItemBulkMoveRequest,
    FolioItemMoveRequest,
    FolioItemResponse,
    FolioResponse,
    FolioTransferRequest,
    FolioUpdate,
)

router = APIRouter(prefix="/api", tags=["Folios & Billing"])


def enrich_folio_response(folio: Folio, db: Session) -> FolioResponse:
    """Enriches Folio with live aggregated totals and items."""
    items = (
        db.query(FolioItem)
        .filter(FolioItem.folio_id == folio.id)
        .order_by(FolioItem.date.asc(), FolioItem.id.asc())
        .all()
    )

    total_amount = sum(Decimal(str(item.amount)) for item in items) if items else Decimal("0.00")

    total_paid = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.folio_id == folio.id)
        .scalar()
    ) or Decimal("0.00")

    total_paid = Decimal(str(total_paid))
    balance_due = total_amount - total_paid

    resp = FolioResponse.model_validate(folio)
    resp.items = [FolioItemResponse.model_validate(it) for it in items]
    resp.total_amount = total_amount
    resp.total_paid = total_paid
    resp.balance_due = balance_due
    return resp


@router.get("/reservations/{reservation_id}/folios", response_model=List[FolioResponse])
def list_folios(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all folios (Primary, Company, Extras) for a reservation with calculated line items and balances."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    # Ensure at least Primary folio exists
    primary = (
        db.query(Folio)
        .filter(Folio.reservation_id == reservation_id, Folio.is_master.is_(True))
        .first()
    )
    if not primary:
        primary = Folio(
            reservation_id=reservation_id,
            name="Primary",
            is_master=True,
        )
        db.add(primary)
        db.commit()

        # Re-link any orphan items belonging to this reservation
        orphan_items = (
            db.query(FolioItem)
            .filter(FolioItem.reservation_id == reservation_id, FolioItem.folio_id.is_(None))
            .all()
        )
        for it in orphan_items:
            it.folio_id = primary.id
        db.commit()

    folios = (
        db.query(Folio)
        .filter(Folio.reservation_id == reservation_id)
        .order_by(Folio.is_master.desc(), Folio.id.asc())
        .all()
    )

    return [enrich_folio_response(f, db) for f in folios]


@router.post("/reservations/{reservation_id}/folios", response_model=FolioResponse, status_code=status.HTTP_201_CREATED)
def create_folio(
    reservation_id: int,
    payload: FolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an additional folio (e.g. 'Company', 'Personal Extras') for item splitting."""
    res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found",
        )

    folio = Folio(
        reservation_id=reservation_id,
        name=payload.name.strip(),
        is_master=False,
    )
    db.add(folio)
    db.commit()
    db.refresh(folio)

    return enrich_folio_response(folio, db)


@router.patch("/folios/{folio_id}", response_model=FolioResponse)
def update_folio(
    folio_id: int,
    payload: FolioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a folio tab."""
    folio = db.query(Folio).filter(Folio.id == folio_id).first()
    if not folio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folio with ID {folio_id} not found",
        )

    folio.name = payload.name.strip()
    db.commit()
    db.refresh(folio)
    return enrich_folio_response(folio, db)


@router.delete("/folios/{folio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folio(
    folio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom folio (Cannot delete primary folio or a folio containing active items)."""
    folio = db.query(Folio).filter(Folio.id == folio_id).first()
    if not folio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folio with ID {folio_id} not found",
        )

    if folio.is_master:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the Primary Master Folio.",
        )

    item_count = db.query(FolioItem).filter(FolioItem.folio_id == folio_id).count()
    if item_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete folio with {item_count} remaining line item(s). Move or delete items first.",
        )

    payment_count = db.query(Payment).filter(Payment.folio_id == folio_id).count()
    if payment_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete folio with {payment_count} remaining payment/credit record(s). Transfer payments first.",
        )

    db.delete(folio)
    db.commit()
    return None


@router.post("/folio-items/{item_id}/move", response_model=FolioItemResponse)
def move_folio_item(
    item_id: int,
    payload: FolioItemMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a single charge or credit item to another folio."""
    item = db.query(FolioItem).filter(FolioItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folio item with ID {item_id} not found",
        )

    target_folio = db.query(Folio).filter(Folio.id == payload.folio_id).first()
    if not target_folio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target folio with ID {payload.folio_id} not found",
        )

    item.folio_id = target_folio.id
    db.commit()
    db.refresh(item)
    return item


@router.post("/folio-items/bulk-move")
def bulk_move_folio_items(
    payload: FolioItemBulkMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move multiple selected folio items to another folio in one action."""
    target_folio = db.query(Folio).filter(Folio.id == payload.folio_id).first()
    if not target_folio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target folio with ID {payload.folio_id} not found",
        )

    items = db.query(FolioItem).filter(FolioItem.id.in_(payload.item_ids)).all()
    for it in items:
        it.folio_id = target_folio.id

    db.commit()
    return {"message": f"Successfully moved {len(items)} item(s) to '{target_folio.name}'", "count": len(items)}


@router.post("/folios/{folio_id}/transfer")
def transfer_folio_balance(
    folio_id: int,
    payload: FolioTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transfer all line items from this folio to a destination folio."""
    source_folio = db.query(Folio).filter(Folio.id == folio_id).first()
    if not source_folio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source folio with ID {folio_id} not found",
        )

    target_folio = db.query(Folio).filter(Folio.id == payload.to_folio_id).first()
    if not target_folio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination folio with ID {payload.to_folio_id} not found",
        )

    if source_folio.id == target_folio.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer folio items to the exact same folio.",
        )

    items = db.query(FolioItem).filter(FolioItem.folio_id == source_folio.id).all()
    count = len(items)
    for it in items:
        it.folio_id = target_folio.id

    payments = db.query(Payment).filter(Payment.folio_id == source_folio.id).all()
    pmt_count = len(payments)
    for p in payments:
        p.folio_id = target_folio.id

    db.commit()
    return {
        "message": f"Transferred {count} item(s) and {pmt_count} payment(s) from '{source_folio.name}' to '{target_folio.name}'",
        "transferred_count": count,
        "transferred_payments": pmt_count,
    }
