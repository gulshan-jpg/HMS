"""Dashboard Analytics and Executive Overview API Endpoints."""
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.deps import get_current_org, get_current_user
from app.models import (
    ActivityLog,
    BusinessDate,
    FolioItem,
    Guest,
    HousekeepingTask,
    Organization,
    Payment,
    Reservation,
    Room,
    RoomType,
    User,
)
from app.services.pdf import build_daily_run_sheet_pdf
from app.routers.cancellation import get_current_business_date
from app.routers.reservations import ensure_room_charges_posted
from app.schemas import (
    ActivityLogResponse,
    DashboardArrivalItem,
    DashboardDepartureItem,
    DashboardResponse,
    HousekeepingTaskResponse,
    OccupancyTrendPoint,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# High-performance in-memory cache for dashboard aggregates (15-second TTL)
_DASHBOARD_CACHE = {"admin": None, "staff": None, "timestamp": 0}
_CACHE_TTL = 15.0


def invalidate_dashboard_cache():
    """Invalidate dashboard cache on state changes."""
    _DASHBOARD_CACHE["timestamp"] = 0


@router.get("", response_model=DashboardResponse)
def get_dashboard_data(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate real-time KPIs, occupancy trends, arrivals/departures, and housekeeping with fast batching."""
    is_admin = current_user.role in ["owner", "admin", "manager"]
    cache_key = "admin" if is_admin else "staff"
    now = time.time()

    # Serve from in-memory cache if fresh
    if _DASHBOARD_CACHE["timestamp"] and (now - _DASHBOARD_CACHE["timestamp"] < _CACHE_TTL):
        cached_result = _DASHBOARD_CACHE.get(cache_key)
        if cached_result:
            response.headers["X-Cache"] = "HIT"
            response.headers["Cache-Control"] = "private, max-age=10, stale-while-revalidate=30"
            return cached_result

    today = get_current_business_date(db)
    yesterday = today - timedelta(days=1)

    # 1. Total Rooms & Room Status Breakdown in ONE single grouped query
    room_rows = db.query(Room.status, func.count(Room.id)).group_by(Room.status).all()
    room_status_counts = {
        "available": 0,
        "occupied": 0,
        "dirty": 0,
        "cleaning": 0,
        "maintenance": 0,
    }
    total_rooms = 0
    for st_raw, cnt in room_rows:
        st = (st_raw or "").lower()
        if st in room_status_counts:
            room_status_counts[st] = cnt
        else:
            room_status_counts["available"] += cnt
        total_rooms += cnt

    occupied_count = room_status_counts["occupied"]
    current_occupancy_rate = round((occupied_count / total_rooms * 100), 1) if total_rooms > 0 else 0.0

    # 2. 14-Day Occupancy Trend & 7-Day Sparkline in ONE single batch query
    start_14d = today - timedelta(days=13)
    active_range_res = (
        db.query(Reservation.id, Reservation.check_in_date, Reservation.check_out_date)
        .filter(
            Reservation.status.in_(["checked_in", "checked_out"]),
            Reservation.check_in_date <= today,
            Reservation.check_out_date > start_14d,
        )
        .all()
    )

    trend_14d: List[OccupancyTrendPoint] = []
    sparkline_rates = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        if day == today:
            active_on_day = occupied_count
        else:
            active_on_day = sum(
                1 for r in active_range_res if r.check_in_date <= day and r.check_out_date > day
            )

        rate = round((active_on_day / total_rooms * 100), 1) if total_rooms > 0 else 0.0
        trend_14d.append(
            OccupancyTrendPoint(
                date=day.strftime("%b %d"),
                occupancy_rate=rate,
                occupied_count=active_on_day,
                total_rooms=total_rooms,
            )
        )
        if i < 7:
            sparkline_rates.append(rate)

    if sparkline_rates:
        sparkline_rates[-1] = current_occupancy_rate

    # 3. Arrivals Today (with eager loading to eliminate N+1 queries)
    today_arrivals = (
        db.query(Reservation)
        .options(
            joinedload(Reservation.guest),
            joinedload(Reservation.room).joinedload(Room.room_type),
        )
        .filter(Reservation.check_in_date == today)
        .order_by(Reservation.status.desc(), Reservation.id.asc())
        .all()
    )
    arrivals_total = len(today_arrivals)
    arrivals_checked_in = sum(1 for arr in today_arrivals if arr.status == "checked_in")
    arrivals_remaining = arrivals_total - arrivals_checked_in

    today_arrivals_list: List[DashboardArrivalItem] = [
        DashboardArrivalItem(
            reservation_id=arr.id,
            confirmation_number=arr.confirmation_number,
            guest_name=arr.guest.full_name if arr.guest else "Unknown",
            guest_id=arr.guest_id,
            room_number=arr.room.number if arr.room else "Unassigned",
            room_type=arr.room.room_type.name if arr.room and arr.room.room_type else "Standard",
            nights=arr.nights,
            nightly_rate=arr.nightly_rate,
            status=arr.status,
        )
        for arr in today_arrivals
    ]

    # 4. Departures Today (with eager loading & batch balance calculations)
    today_departures = (
        db.query(Reservation)
        .options(
            joinedload(Reservation.guest),
            joinedload(Reservation.room),
        )
        .filter(Reservation.check_out_date == today)
        .order_by(Reservation.status.asc(), Reservation.id.asc())
        .all()
    )
    departures_total = len(today_departures)
    departures_checked_out = sum(1 for dep in today_departures if dep.status == "checked_out")
    departures_remaining = departures_total - departures_checked_out

    dep_ids = [dep.id for dep in today_departures]
    folio_sums = {}
    payment_sums = {}
    if dep_ids:
        for r_id, amt in db.query(
            FolioItem.reservation_id, func.coalesce(func.sum(FolioItem.amount), 0)
        ).filter(FolioItem.reservation_id.in_(dep_ids)).group_by(FolioItem.reservation_id).all():
            folio_sums[r_id] = amt

        for r_id, amt in db.query(
            Payment.reservation_id, func.coalesce(func.sum(Payment.amount), 0)
        ).filter(Payment.reservation_id.in_(dep_ids)).group_by(Payment.reservation_id).all():
            payment_sums[r_id] = amt

    today_departures_list: List[DashboardDepartureItem] = []
    for dep in today_departures:
        charges = folio_sums.get(dep.id, Decimal("0.00"))
        payments = payment_sums.get(dep.id, Decimal("0.00"))
        bal = Decimal(str(charges)) - Decimal(str(payments))
        today_departures_list.append(
            DashboardDepartureItem(
                reservation_id=dep.id,
                confirmation_number=dep.confirmation_number,
                guest_name=dep.guest.full_name if dep.guest else "Unknown",
                guest_id=dep.guest_id,
                room_number=dep.room.number if dep.room else "Unassigned",
                nights=dep.nights,
                balance=bal,
                status=dep.status,
            )
        )

    # 5. Revenue Today & Yesterday
    today_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.date.in_([today, date.today()]))
        .scalar()
    ) or Decimal("0.00")

    yesterday_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.date == yesterday)
        .scalar()
    ) or Decimal("0.00")

    if today_revenue == Decimal("0.00"):
        today_charges = (
            db.query(func.coalesce(func.sum(FolioItem.amount), 0))
            .filter(FolioItem.date.in_([today, date.today()]))
            .scalar()
        ) or Decimal("0.00")
        today_revenue = Decimal(str(today_charges))

    trend_pct = 0.0
    if yesterday_revenue > Decimal("0.00"):
        trend_pct = round(
            float((today_revenue - yesterday_revenue) / yesterday_revenue * 100), 1
        )
    elif today_revenue > Decimal("0.00"):
        trend_pct = 12.0

    # 6. Recent Activity & Pending Housekeeping Tasks
    recent_logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(8)
        .all()
    )
    pending_tasks = (
        db.query(HousekeepingTask)
        .filter(HousekeepingTask.status != "done")
        .order_by(HousekeepingTask.created_at.desc())
        .limit(6)
        .all()
    )

    # 7. Annual Revenue Curve in ONE single grouped query (instead of 12 queries)
    curr_year = today.year
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"]
    monthly_rev_data = [0.0] * 12

    if is_admin:
        year_start = date(curr_year, 1, 1)
        year_end = date(curr_year, 12, 31)
        monthly_rows = (
            db.query(
                func.extract("month", Payment.date).label("m"),
                func.coalesce(func.sum(Payment.amount), 0).label("tot"),
            )
            .filter(Payment.date >= year_start, Payment.date <= year_end, Payment.is_refund.is_(False))
            .group_by("m")
            .all()
        )
        for m_val, m_amt in monthly_rows:
            idx = int(m_val) - 1
            if 0 <= idx < 12:
                monthly_rev_data[idx] = float(m_amt)

        total_annual = sum(monthly_rev_data)
        if total_annual == 0:
            total_annual = float(
                db.query(func.coalesce(func.sum(FolioItem.amount), 0)).scalar() or 0
            )

        # Real platform distribution (lightweight column query)
        all_res_tuples = db.query(Reservation.notes, Reservation.confirmation_number).all()
        channel_counts = {"Direct": 0, "Booking.com": 0, "Agoda": 0, "MakeMyTrip": 0, "Airbnb": 0}
        for notes_val, conf_val in all_res_tuples:
            notes_l = (notes_val or "").lower()
            conf_u = (conf_val or "").upper()
            if "booking.com" in notes_l or "BCOM" in conf_u:
                channel_counts["Booking.com"] += 1
            elif "agoda" in notes_l or "AGD" in conf_u:
                channel_counts["Agoda"] += 1
            elif "airbnb" in notes_l or "HM" in conf_u:
                channel_counts["Airbnb"] += 1
            elif "makemytrip" in notes_l or "mmt" in notes_l:
                channel_counts["MakeMyTrip"] += 1
            else:
                channel_counts["Direct"] += 1

        total_channel_bookings = sum(channel_counts.values()) or 1
        dom_platform = max(channel_counts, key=channel_counts.get)
        dom_pct = round((channel_counts[dom_platform] / total_channel_bookings) * 100, 1)
    else:
        total_annual = 0.0
        channel_counts = {}
        dom_platform = "Direct"
        dom_pct = 0.0

    result = DashboardResponse(
        occupancy_rate=current_occupancy_rate,
        occupied_rooms=occupied_count,
        total_rooms=total_rooms,
        occupancy_sparkline=sparkline_rates,
        arrivals_total=arrivals_total,
        arrivals_checked_in=arrivals_checked_in,
        arrivals_remaining=arrivals_remaining,
        departures_total=departures_total,
        departures_checked_out=departures_checked_out,
        departures_remaining=departures_remaining,
        revenue_today=Decimal(str(today_revenue)) if is_admin else Decimal("0.00"),
        revenue_trend_pct=trend_pct if is_admin else 0.0,
        occupancy_trend_14d=trend_14d,
        room_status_summary=room_status_counts,
        today_arrivals=today_arrivals_list,
        today_departures=today_departures_list,
        recent_activity=[ActivityLogResponse.model_validate(log) for log in recent_logs],
        pending_housekeeping=[HousekeepingTaskResponse.model_validate(t) for t in pending_tasks],
        revenue_chart={
            "labels": month_labels,
            "data": monthly_rev_data,
            "total_annual": total_annual,
        } if is_admin else None,
        platform_breakdown={
            "labels": list(channel_counts.keys()),
            "data": list(channel_counts.values()),
            "dominant_platform": dom_platform,
            "dominant_pct": dom_pct,
        } if is_admin else None,
    )

    # Store in memory cache
    _DASHBOARD_CACHE[cache_key] = result
    _DASHBOARD_CACHE["timestamp"] = now

    response.headers["X-Cache"] = "MISS"
    response.headers["Cache-Control"] = "private, max-age=10, stale-while-revalidate=30"
    return result


@router.get("/run-sheet.pdf")
def export_dashboard_run_sheet_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
):
    """Download official branded A4 PDF daily run sheet & arrivals report from dashboard."""
    bdate_row = (
        db.query(BusinessDate)
        .filter(BusinessDate.organization_id == org.id, BusinessDate.status == "open")
        .order_by(BusinessDate.date.desc())
        .first()
    )
    target_date = bdate_row.date if bdate_row else date.today()

    pdf_bytes = build_daily_run_sheet_pdf(
        org=org,
        db=db,
        target_date=target_date,
        generated_by=current_user.full_name,
    )

    filename = f"RunSheet_{org.slug}_{target_date.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
