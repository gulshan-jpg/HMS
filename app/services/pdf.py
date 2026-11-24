"""Invoice PDF Generation Engine using ReportLab with Sequential Invoice Numbering."""
from datetime import datetime, date
from decimal import Decimal
import io
import json
import os
from typing import Optional, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from sqlalchemy.orm import Session

from app.models import (
    BusinessDate,
    Folio,
    FolioItem,
    Guest,
    HousekeepingTask,
    InvoiceLog,
    Organization,
    Payment,
    Reservation,
    Room,
)


def generate_invoice_number(org: Organization, db: Session) -> str:
    """Generates sequential unique invoice number per organization: {clean_slug}{org_id}-{year}-{seq:05d}."""
    current_year = date.today().year
    clean_slug = org.slug.upper().replace("-", "")[:6]
    count = (
        db.query(InvoiceLog)
        .filter(InvoiceLog.organization_id == org.id)
        .count()
    ) + 1
    inv_num = f"{clean_slug}{org.id}-{current_year}-{count:05d}"
    while db.query(InvoiceLog).filter(InvoiceLog.invoice_number == inv_num).first():
        count += 1
        inv_num = f"{clean_slug}{org.id}-{current_year}-{count:05d}"
    return inv_num


def get_pdf_currency_symbol(org: Optional[Organization]) -> Tuple[str, str]:
    """Returns (prefix_symbol, column_header_label) compatible with ReportLab standard Type-1 Helvetica fonts.
    Note: Unicode '₹' is not present in standard Helvetica and renders as a black box (■);
    using 'Rs. ' renders crisply on all PDF viewers and printers without missing glyph boxes."""
    code = (org.currency or "INR").upper() if org else "INR"
    if code == "INR":
        return "Rs. ", "Rs."
    elif code == "USD":
        return "$", "$"
    elif code == "EUR":
        return "EUR ", "EUR"
    elif code == "GBP":
        return "GBP ", "GBP"
    elif code == "AED":
        return "AED ", "AED"
    return f"{code} ", code


def build_reservation_invoice_pdf(
    reservation: Reservation,
    org: Organization,
    db: Session,
    generated_by: str = "System",
) -> Tuple[bytes, str]:
    """Generates a complete, high-fidelity PDF invoice for the given reservation."""
    existing_log = (
        db.query(InvoiceLog)
        .filter(InvoiceLog.reservation_id == reservation.id)
        .order_by(InvoiceLog.id.desc())
        .first()
    )
    if existing_log:
        invoice_number = existing_log.invoice_number
    else:
        invoice_number = generate_invoice_number(org, db)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    normal_style.fontSize = 9
    normal_style.leading = 12
    normal_style.textColor = colors.HexColor("#111827")

    bold_style = ParagraphStyle(
        "BoldText",
        parent=normal_style,
        fontName="Helvetica-Bold",
    )

    title_style = ParagraphStyle(
        "TitleText",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#111827"),
    )

    secondary_style = ParagraphStyle(
        "SecondaryText",
        parent=normal_style,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#6B7280"),
    )

    story = []

    # 1. Header: Organization Details left, INVOICE label & metadata right
    org_address = org.address or "Bengaluru, Karnataka, India"
    org_tax_id = f"GSTIN / Tax ID: {org.tax_id}" if org.tax_id else "GSTIN: 29AAAAA0000A1Z5"

    header_left = [
        Paragraph(f"<b>{org.name}</b>", title_style),
        Spacer(1, 4),
        Paragraph(org_address, secondary_style),
        Paragraph(org_tax_id, secondary_style),
    ]

    header_right = [
        Paragraph("TAX INVOICE", ParagraphStyle("InvHead", parent=title_style, alignment=2)),
        Spacer(1, 4),
        Paragraph(f"<b>Invoice #:</b> {invoice_number}", ParagraphStyle("InvMeta", parent=normal_style, alignment=2)),
        Paragraph(f"<b>Date:</b> {date.today().strftime('%B %d, %Y')}", ParagraphStyle("InvDate", parent=secondary_style, alignment=2)),
        Paragraph(f"<b>Confirmation:</b> #{reservation.confirmation_number}", ParagraphStyle("InvConf", parent=secondary_style, alignment=2)),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[300, 220])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceAfter=14))

    # 2. Bill To & Stay Details Grid
    guest = reservation.guest
    room = reservation.room
    guest_name = f"{guest.first_name} {guest.last_name}" if guest else "Valued Guest"
    guest_contact = f"{guest.email} | {guest.phone}" if guest else ""
    guest_address = guest.address if (guest and guest.address) else "India"

    bill_to_content = [
        Paragraph("<b>BILLED TO</b>", ParagraphStyle("BToHead", parent=bold_style, fontSize=8, textColor=colors.HexColor("#6B7280"))),
        Spacer(1, 3),
        Paragraph(f"<b>{guest_name}</b>", normal_style),
        Paragraph(guest_address, secondary_style),
        Paragraph(guest_contact, secondary_style),
    ]

    stay_details_content = [
        Paragraph("<b>STAY DETAILS</b>", ParagraphStyle("StayHead", parent=bold_style, fontSize=8, textColor=colors.HexColor("#6B7280"))),
        Spacer(1, 3),
        Paragraph(f"<b>Room:</b> {room.number} ({room.room_type.name if room and room.room_type else 'Standard'})", normal_style),
        Paragraph(f"<b>Check-In:</b> {reservation.check_in_date.isoformat()} | <b>Check-Out:</b> {reservation.check_out_date.isoformat()}", secondary_style),
        Paragraph(f"<b>Duration:</b> {reservation.nights} Night(s) | <b>Guests:</b> {reservation.adults} Adult(s)", secondary_style),
    ]

    info_table = Table([[bill_to_content, stay_details_content]], colWidths=[260, 260])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))

    # 3. Itemized Line Items Table
    curr_sym, curr_label = get_pdf_currency_symbol(org)

    items = (
        db.query(FolioItem)
        .filter(FolioItem.reservation_id == reservation.id, FolioItem.deleted_at.is_(None))
        .order_by(FolioItem.date.asc(), FolioItem.id.asc())
        .all()
    )

    table_data = [
        [
            Paragraph("<b>DATE</b>", bold_style),
            Paragraph("<b>DESCRIPTION</b>", bold_style),
            Paragraph("<b>CATEGORY</b>", bold_style),
            Paragraph(f"<b>AMOUNT ({curr_label})</b>", ParagraphStyle("RtHead", parent=bold_style, alignment=2)),
        ]
    ]

    subtotal_charges = Decimal("0.00")
    tax_breakdown_map = {}

    for item in items:
        amt = Decimal(str(item.amount))
        subtotal_charges += amt
        cat_label = item.category.replace("_", " ").title()
        safe_desc = (item.description or "").replace("₹", curr_sym)

        table_data.append([
            Paragraph(item.date.strftime("%b %d, %Y"), secondary_style),
            Paragraph(safe_desc, normal_style),
            Paragraph(cat_label, secondary_style),
            Paragraph(f"{amt:,.2f}", ParagraphStyle("AmtVal", parent=normal_style, alignment=2)),
        ])

        # Aggregate tax breakdown
        if item.tax_breakdown:
            try:
                b_list = json.loads(item.tax_breakdown)
                for b in b_list:
                    t_name = b.get("name", "Tax")
                    t_amt = Decimal(str(b.get("amount", 0)))
                    tax_breakdown_map[t_name] = tax_breakdown_map.get(t_name, Decimal("0.00")) + t_amt
            except Exception:
                pass

    if len(table_data) == 1:
        table_data.append([Paragraph("-", secondary_style), Paragraph("No folio charges posted", secondary_style), Paragraph("-", secondary_style), Paragraph("0.00", secondary_style)])

    items_table = Table(table_data, colWidths=[80, 240, 100, 100])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 14))

    # 4. Payments, Taxes & Totals Summary Box
    payments = (
        db.query(Payment)
        .filter(Payment.reservation_id == reservation.id, Payment.deleted_at.is_(None))
        .all()
    )
    total_paid = sum(Decimal(str(p.amount)) for p in payments) if payments else Decimal("0.00")
    balance_due = subtotal_charges - total_paid

    summary_rows = [
        [Paragraph("Subtotal Charges:", normal_style), Paragraph(f"{curr_sym}{subtotal_charges:,.2f}", ParagraphStyle("S1", parent=normal_style, alignment=2))],
    ]

    for t_name, t_amt in tax_breakdown_map.items():
        summary_rows.append([
            Paragraph(f"{t_name}:", secondary_style),
            Paragraph(f"{curr_sym}{t_amt:,.2f}", ParagraphStyle("STax", parent=secondary_style, alignment=2)),
        ])

    summary_rows.extend([
        [Paragraph("<b>Total Charges:</b>", bold_style), Paragraph(f"<b>{curr_sym}{subtotal_charges:,.2f}</b>", ParagraphStyle("GT", parent=bold_style, alignment=2))],
        [Paragraph("Total Payments Received:", normal_style), Paragraph(f"{curr_sym}{total_paid:,.2f}", ParagraphStyle("TP", parent=normal_style, alignment=2))],
        [Paragraph("<b>Balance Due:</b>", bold_style), Paragraph(f"<b>{curr_sym}{balance_due:,.2f}</b>", ParagraphStyle("BD", parent=bold_style, alignment=2))],
    ])

    summary_table = Table(summary_rows, colWidths=[140, 100])
    summary_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F9FAFB")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#E5E7EB")),
        ("LINEBELOW", (0, -2), (-1, -2), 0.5, colors.HexColor("#E5E7EB")),
    ]))

    # Place summary aligned to right
    summary_wrapper = Table([[Paragraph("", normal_style), summary_table]], colWidths=[280, 240])
    summary_wrapper.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(summary_wrapper)
    story.append(Spacer(1, 24))

    # 5. Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=10))
    footer_text = Paragraph(
        "Thank you for your business. For billing queries, contact reservations desk. • <b>CheckinOS PMS · Developed by Gulshan</b>",
        ParagraphStyle("Foot", parent=secondary_style, alignment=1),
    )
    story.append(footer_text)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Save to invoice log if new
    if not existing_log:
        log_record = InvoiceLog(
            organization_id=org.id,
            reservation_id=reservation.id,
            invoice_number=invoice_number,
            generated_by=generated_by,
            pdf_path=f"/static/uploads/{org.slug}/invoices/{invoice_number}.pdf",
        )
        db.add(log_record)
        db.commit()

    return pdf_bytes, invoice_number


def build_daily_run_sheet_pdf(
    org: Organization,
    db: Session,
    target_date: date,
    generated_by: str = "Front Desk Manager",
) -> bytes:
    """Generates an official branded A4 Daily Run Sheet & Operational Report for front desk."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    normal_style.fontSize = 8
    normal_style.leading = 11
    normal_style.textColor = colors.HexColor("#111827")

    bold_style = ParagraphStyle(
        "RunSheetBold",
        parent=normal_style,
        fontName="Helvetica-Bold",
    )

    title_style = ParagraphStyle(
        "RunSheetTitle",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#111827"),
    )

    h2_style = ParagraphStyle(
        "RunSheetH2",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )

    secondary_style = ParagraphStyle(
        "RunSheetSec",
        parent=normal_style,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6B7280"),
    )

    story = []

    # 1. Header: Hotel Brand & Document Type
    header_data = [
        [
            Paragraph(f"<b>{org.name}</b><br/>{org.address or 'India'}<br/><font color='#6B7280'>Currency: {org.currency or 'INR'} · Timezone: {org.timezone or 'Asia/Kolkata'}</font>", normal_style),
            Paragraph(f"<b>DAILY RUN SHEET & ARRIVALS</b><br/><font color='#6B7280'>Date: <b>{target_date.strftime('%A, %d %B %Y')}</b><br/>Generated: {datetime.now().strftime('%d %b %Y %H:%M')}<br/>User: {generated_by}</font>", ParagraphStyle("RightH", parent=normal_style, alignment=2)),
        ]
    ]
    header_table = Table(header_data, colWidths=[280, 240])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#111827"), spaceAfter=12))

    # 2. Key Metrics Snapshot
    rooms = db.query(Room).filter(Room.organization_id == org.id, Room.deleted_at.is_(None)).all()
    total_rooms = len(rooms)
    occupied_rooms = len([r for r in rooms if r.status == "occupied"])
    dirty_rooms = len([r for r in rooms if r.status in ("dirty", "cleaning")])
    occ_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    arrivals = (
        db.query(Reservation)
        .filter(
            Reservation.organization_id == org.id,
            Reservation.check_in_date == target_date,
            Reservation.status.in_(["booked", "checked_in"]),
            Reservation.deleted_at.is_(None),
        )
        .all()
    )

    departures = (
        db.query(Reservation)
        .filter(
            Reservation.organization_id == org.id,
            Reservation.check_out_date == target_date,
            Reservation.status.in_(["checked_in", "checked_out"]),
            Reservation.deleted_at.is_(None),
        )
        .all()
    )

    kpi_data = [
        [
            Paragraph(f"<b>TOTAL ROOMS</b><br/>{total_rooms}", bold_style),
            Paragraph(f"<b>OCCUPIED</b><br/>{occupied_rooms} ({occ_rate}%)", bold_style),
            Paragraph(f"<b>ARRIVALS TODAY</b><br/>{len(arrivals)}", bold_style),
            Paragraph(f"<b>DEPARTURES TODAY</b><br/>{len(departures)}", bold_style),
            Paragraph(f"<b>DIRTY / TURNOVER</b><br/>{dirty_rooms}", bold_style),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[104, 104, 104, 104, 104])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # 3. Expected Arrivals Section
    curr_sym, curr_label = get_pdf_currency_symbol(org)
    story.append(Paragraph(f"<b>Expected Arrivals ({len(arrivals)})</b>", h2_style))
    story.append(Spacer(1, 4))

    arr_header = [
        Paragraph("<b>Room</b>", bold_style),
        Paragraph("<b>Guest Name</b>", bold_style),
        Paragraph("<b>Phone / Email</b>", bold_style),
        Paragraph("<b>Stay Dates</b>", bold_style),
        Paragraph("<b>Rate Plan</b>", bold_style),
        Paragraph(f"<b>Nightly Rate ({curr_label})</b>", ParagraphStyle("R1", parent=bold_style, alignment=2)),
        Paragraph("<b>Status</b>", ParagraphStyle("R2", parent=bold_style, alignment=1)),
    ]
    arr_rows = [arr_header]

    if not arrivals:
        arr_rows.append([Paragraph("No scheduled arrivals for this date.", secondary_style), "", "", "", "", "", ""])
    else:
        for res in arrivals:
            room_no = res.room.number if res.room else "Unassigned"
            guest_name = res.guest.full_name if res.guest else "Unknown"
            contact = res.guest.phone if (res.guest and res.guest.phone) else (res.guest.email if res.guest else "—")
            dates_str = f"{res.check_in_date.strftime('%b %d')} → {res.check_out_date.strftime('%b %d')} ({res.nights}n)"
            plan_name = res.rate_plan.name if res.rate_plan else "Standard Daily"
            rate_str = f"{curr_sym}{res.nightly_rate:,.2f}"
            status_badge = res.status.replace("_", " ").upper()
            arr_rows.append([
                Paragraph(f"<b>{room_no}</b>", normal_style),
                Paragraph(guest_name, normal_style),
                Paragraph(contact, secondary_style),
                Paragraph(dates_str, normal_style),
                Paragraph(plan_name, secondary_style),
                Paragraph(rate_str, ParagraphStyle("RA", parent=normal_style, alignment=2)),
                Paragraph(f"<b>{status_badge}</b>", ParagraphStyle("RB", parent=normal_style, alignment=1)),
            ])

    arr_table = Table(arr_rows, colWidths=[50, 110, 100, 105, 80, 65, 60])
    arr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(arr_table)
    story.append(Spacer(1, 14))

    # 4. Expected Departures Section
    story.append(Paragraph(f"<b>Expected Departures ({len(departures)})</b>", h2_style))
    story.append(Spacer(1, 4))

    dep_header = [
        Paragraph("<b>Room</b>", bold_style),
        Paragraph("<b>Guest Name</b>", bold_style),
        Paragraph("<b>Check-in Date</b>", bold_style),
        Paragraph("<b>Nights Stayed</b>", bold_style),
        Paragraph("<b>Status</b>", ParagraphStyle("R3", parent=bold_style, alignment=1)),
    ]
    dep_rows = [dep_header]

    if not departures:
        dep_rows.append([Paragraph("No departures scheduled for this date.", secondary_style), "", "", "", ""])
    else:
        for res in departures:
            room_no = res.room.number if res.room else "Unassigned"
            guest_name = res.guest.full_name if res.guest else "Unknown"
            cin_str = res.check_in_date.strftime("%b %d, %Y")
            dep_rows.append([
                Paragraph(f"<b>{room_no}</b>", normal_style),
                Paragraph(guest_name, normal_style),
                Paragraph(cin_str, normal_style),
                Paragraph(f"{res.nights} night(s)", normal_style),
                Paragraph(f"<b>{res.status.upper()}</b>", ParagraphStyle("RC", parent=normal_style, alignment=1)),
            ])

    dep_table = Table(dep_rows, colWidths=[60, 160, 120, 90, 90])
    dep_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(dep_table)
    story.append(Spacer(1, 16))

    # 5. Footer Certification
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=8))
    footer_text = Paragraph(
        "<b>CheckinOS PMS · Developed by Gulshan</b> • Official property document for Front Desk and Manager turnover.",
        ParagraphStyle("Foot2", parent=secondary_style, alignment=1),
    )
    story.append(footer_text)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
