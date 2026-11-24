"""Seed Database with Realistic Indian Hotel Data, Rooms, Guests, and Reservations in INR (₹)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import sys

from app.auth import get_password_hash
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import (
    ActivityLog,
    BookingGroup,
    BusinessDate,
    CancellationPolicy,
    DailySnapshot,
    Folio,
    FolioItem,
    GroupBlock,
    Guest,
    HousekeepingTask,
    Payment,
    RateOverride,
    RatePlan,
    Reservation,
    Room,
    RoomType,
    TaxRate,
    User,
    WebhookEvent,
)


def seed():
    print(f"[*] Initializing database tables on {settings.DATABASE_URL}...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if database is already seeded
        if "--force" in sys.argv:
            print("[*] Force flag detected: resetting table contents...")
            db.query(ActivityLog).delete()
            db.query(HousekeepingTask).delete()
            db.query(Payment).delete()
            db.query(FolioItem).delete()
            db.query(Folio).delete()
            db.query(Reservation).delete()
            db.query(GroupBlock).delete()
            db.query(BookingGroup).delete()
            db.query(RateOverride).delete()
            db.query(RatePlan).delete()
            db.query(CancellationPolicy).delete()
            db.query(TaxRate).delete()
            db.query(DailySnapshot).delete()
            db.query(BusinessDate).delete()
            db.query(Guest).delete()
            db.query(Room).delete()
            db.query(RoomType).delete()
            db.query(User).delete()
            db.commit()
        elif db.query(User).count() > 0:
            print("[!] Database already populated. Skipping seed to prevent duplicate records.")
            return

        print("[*] Creating staff and administrator credentials...")
        # 1. Users
        admin_user = User(
            email="admin@grandpavilion.in",
            username="admin",
            full_name="Aditi Rao",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        staff_user = User(
            email="staff@grandpavilion.in",
            username="staff",
            full_name="Rahul Verma",
            hashed_password=get_password_hash("staff123"),
            role="front_desk",
            is_active=True,
        )
        housekeeping_lead = User(
            email="sunita.n@grandpavilion.in",
            username="sunita",
            full_name="Sunita Nair",
            hashed_password=get_password_hash("staff123"),
            role="housekeeping",
            is_active=True,
        )
        db.add_all([admin_user, staff_user, housekeeping_lead])
        db.commit()

        print("=" * 68)
        print(" [INFO] SEEDED DEFAULT CREDENTIALS:")
        print("   Administrator: username='admin', password='admin123' (ROLE: admin)")
        print("   Front Desk:    username='staff', password='staff123' (ROLE: front_desk)")
        print("   Housekeeping:  username='sunita', password='staff123' (ROLE: housekeeping)")
        print("   Hotel:         The Grand Pavilion & Palace Hotel (Bengaluru, India)")
        print("   Currency:      INR (₹ Indian Rupee)")
        print("=" * 68)

        # 2. Room Types (3 types with realistic INR rates)
        print("[*] Seeding room categories in INR (₹)...")
        rt_standard = RoomType(
            name="Standard Deluxe Queen",
            code="STD-Q",
            description="Plush Queen bed, marble rain shower, tea lounge, and high-speed fiber Wi-Fi.",
            base_rate=Decimal("4500.00"),
            max_occupancy=2,
        )
        rt_deluxe = RoomType(
            name="Deluxe King",
            code="DLX-K",
            description="Spacious King bed with city skyline views, sitting lounge, Nespresso bar, and jacuzzi tub.",
            base_rate=Decimal("7500.00"),
            max_occupancy=2,
        )
        rt_suite = RoomType(
            name="Executive Heritage Suite",
            code="EXE-S",
            description="Top-floor corner suite with separate parlor, private bar, panoramic views, and dedicated royal butler service.",
            base_rate=Decimal("16500.00"),
            max_occupancy=4,
        )
        db.add_all([rt_standard, rt_deluxe, rt_suite])
        db.commit()

        # 2a. Cancellation Policies
        print("[*] Seeding 3 standard cancellation policies...")
        pol_flex = CancellationPolicy(
            name="Flexible (24h)",
            description="Free cancellation up to 24 hours prior to arrival date.",
            free_cancel_days=1,
            penalty_type="first_night",
            penalty_value=Decimal("100.00"),
            no_show_penalty="first_night",
            active=True,
        )
        pol_mod = CancellationPolicy(
            name="Moderate (3-Day)",
            description="Free cancellation up to 3 days before arrival, then first night penalty.",
            free_cancel_days=3,
            penalty_type="first_night",
            penalty_value=Decimal("100.00"),
            no_show_penalty="first_night",
            active=True,
        )
        pol_strict = CancellationPolicy(
            name="Strict Non-Refundable",
            description="Non-refundable. 100% of first night penalty applies immediately upon cancellation.",
            free_cancel_days=0,
            penalty_type="first_night",
            penalty_value=Decimal("100.00"),
            no_show_penalty="first_night",
            active=True,
        )
        db.add_all([pol_flex, pol_mod, pol_strict])
        db.commit()

        # 2b. Rate Plans
        print("[*] Seeding 4 commercial rate plans...")
        plan_flex = RatePlan(
            code="FLEX",
            name="Flexible Standard",
            description="Standard daily rate with free cancellation up to 24h before arrival.",
            modifier_type="percent",
            modifier_value=Decimal("0.00"),
            meal_plan="room_only",
            min_stay=1,
            cancellation_policy_id=pol_flex.id,
            refundable=True,
            active=True,
        )
        plan_nr = RatePlan(
            code="NR",
            name="Non-Refundable Saver",
            description="Save 10% on your stay with full prepayment, non-refundable.",
            modifier_type="percent",
            modifier_value=Decimal("-10.00"),
            meal_plan="room_only",
            min_stay=1,
            cancellation_policy_id=pol_strict.id,
            refundable=False,
            requires_deposit=True,
            deposit_percent=Decimal("100.00"),
            active=True,
        )
        plan_bb = RatePlan(
            code="BB",
            name="Bed & Breakfast",
            description="Includes daily royal breakfast buffet at The Glasshouse dining room.",
            modifier_type="absolute",
            modifier_value=Decimal("1500.00"),
            meal_plan="breakfast",
            min_stay=1,
            cancellation_policy_id=pol_mod.id,
            refundable=True,
            active=True,
        )
        plan_long = RatePlan(
            code="LONG",
            name="Extended Stay 7+ Nights",
            description="Extended stay discount of 15% off standard rates for 7 nights or longer.",
            modifier_type="percent",
            modifier_value=Decimal("-15.00"),
            meal_plan="room_only",
            min_stay=7,
            cancellation_policy_id=pol_flex.id,
            refundable=True,
            active=True,
        )
        db.add_all([plan_flex, plan_nr, plan_bb, plan_long])
        db.commit()

        # 2c. Taxes
        print("[*] Seeding City and Tourism Taxes...")
        tax_city = TaxRate(
            name="City Municipal Tax",
            rate=Decimal("3.00"),
            fixed_amount=Decimal("0.00"),
            applies_to="rooms",
            type="exclusive",
            per="night",
            active=True,
            sort_order=1,
        )
        tax_tourism = TaxRate(
            name="Tourism Development Levy",
            rate=Decimal("0.00"),
            fixed_amount=Decimal("150.00"),
            applies_to="rooms",
            type="exclusive",
            per="night",
            active=True,
            sort_order=2,
        )
        db.add_all([tax_city, tax_tourism])
        db.commit()

        # 2d. Business Date
        print("[*] Initializing active Business Date...")
        bd_active = BusinessDate(
            date=date.today(),
            status="open",
        )
        db.add(bd_active)
        db.commit()

        # 3. Rooms (20 rooms across 3 floors: 101–110, 201–207, 301–303)
        print("[*] Creating 20 physical rooms across 3 floors...")
        room_data = [
            # Floor 1 (Standard Deluxe Queen - Base ₹4,500)
            ("101", 1, rt_standard.id, "available", "Quiet courtyard garden view"),
            ("102", 1, rt_standard.id, "available", "Near ground floor elevator and lounge"),
            ("103", 1, rt_standard.id, "occupied", "Guest requested extra feather pillows and green tea"),
            ("104", 1, rt_standard.id, "dirty", "Turnover cleaning required"),
            ("105", 1, rt_standard.id, "available", "ADA compliant bathroom with grab bars"),
            ("106", 1, rt_standard.id, "occupied", "Late arrival noted from Kempegowda Airport"),
            ("107", 1, rt_standard.id, "available", "Courtyard fountain facing"),
            ("108", 1, rt_standard.id, "maintenance", "Daikin VRV air-conditioning calibration"),
            ("109", 1, rt_standard.id, "available", "Standard garden layout"),
            ("110", 1, rt_standard.id, "occupied", "Corporate traveler rate (Infosys / Wipro)"),
            # Floor 2 (Deluxe King - Base ₹7,500)
            ("201", 2, rt_deluxe.id, "occupied", "High floor, quiet north wing"),
            ("202", 2, rt_deluxe.id, "cleaning", "Mid-stay housekeeping in progress"),
            ("203", 2, rt_deluxe.id, "available", "City skyline view with soaking tub"),
            ("204", 2, rt_deluxe.id, "occupied", "Anniversary setup - welcome fruit platter provided"),
            ("205", 2, rt_deluxe.id, "dirty", "Departed at 11:00 AM"),
            ("206", 2, rt_deluxe.id, "available", "Refurbished teakwood flooring"),
            ("207", 2, rt_deluxe.id, "occupied", "Connecting door to 206 locked"),
            # Floor 3 (Executive Heritage Suite - Base ₹16,500)
            ("301", 3, rt_suite.id, "available", "Corner penthouse heritage suite"),
            ("302", 3, rt_suite.id, "occupied", "VIP diplomat guest - complimentary vintage wine"),
            ("303", 3, rt_suite.id, "available", "Wrap-around terrace overlooking Cubbon Park"),
        ]

        rooms = []
        for num, flr, rtid, st, notes in room_data:
            r = Room(
                number=num,
                floor=flr,
                room_type_id=rtid,
                status=st,
                notes=notes,
            )
            rooms.append(r)
            db.add(r)
        db.commit()

        rooms_by_num = {r.number: r for r in rooms}

        # 4. Guests (12 authentic Indian & international guests with realistic contacts)
        print("[*] Registering 12 realistic hotel guests...")
        guests_data = [
            ("Aarav", "Sharma", "aarav.sharma@meridian-tech.in", "+91 98201 23456", "Bandra West, Mumbai, Maharashtra 400050", "AADHAAR-8921-4321-9876", "Prefers high floor, allergy to synthetic pillows"),
            ("Priya", "Patel", "priya.patel@patelarchitects.in", "+91 98450 11223", "Lavelle Road, Bengaluru, Karnataka 560001", "DL-KA-8837190", "Corporate direct billing, frequent airport transfers"),
            ("Rohan", "Mehta", "rohan.mehta@delhicapital.in", "+91 99100 88776", "Golf Links, New Delhi 110003", "PASSPORT-IN-66231", "Enjoys sparkling mineral water & Darjeeling First Flush"),
            ("Ananya", "Iyer", "ananya.iyer@chennaidesign.in", "+91 97412 34567", "Poes Garden, Chennai, Tamil Nadu 600086", "PASSPORT-IN-33918", "Quiet room required, non-smoking strictly"),
            ("Vikram", "Malhotra", "vikram.malhotra@corpventure.in", "+91 98111 22334", "DLF Phase 5, Gurugram, Haryana 122009", "DL-HR-4481023", "Executive traveler, frequent minibar and dining orders"),
            ("Dr. Rajesh", "Gupta", "rajesh.gupta@medindia.org", "+91 94150 99881", "Hazratganj, Lucknow, Uttar Pradesh 226001", "PASSPORT-IN-77123", "Requested early check-in for medical conference"),
            ("Neha", "Reddy", "neha.reddy@hyderabadtech.in", "+91 98480 55443", "Jubilee Hills, Hyderabad, Telangana 500033", "PASSPORT-IN-55291", "Prefers organic bath amenities"),
            ("Kavita", "Sen", "kavita.sen@heritagearts.in", "+91 98300 77665", "Alipore, Kolkata, West Bengal 700027", "PASSPORT-IN-11928", "Art curator, needs quiet corner workspace"),
            ("David", "Kim", "david.kim@seoulventures.kr", "+82 10-5555-0199", "Gangnam-gu, Seoul, South Korea", "PASSPORT-KR-44829", "International investor, needs airport pickup"),
            ("Sarah", "Jenkins", "sarah.j@travelworld.co.uk", "+44 7700 900123", "Kensington, London, United Kingdom", "PASSPORT-GB-99201", "Family vacation with 1 child"),
            ("Carlos", "Mendez", "carlos.m@madridconsulting.es", "+34 600 000 123", "Paseo de la Castellana, Madrid, Spain", "PASSPORT-ES-88234", "Attending international bio-tech convention"),
            ("Elena", "Rostova", "elena.rostova@nordictech.fi", "+358 40 1234567", "Mannerheimintie, Helsinki, Finland", "PASSPORT-FI-11492", "Arriving on midnight connecting flight"),
        ]

        guests = []
        for fn, ln, em, ph, addr, idn, notes in guests_data:
            g = Guest(
                first_name=fn,
                last_name=ln,
                email=em,
                phone=ph,
                address=addr,
                id_number=idn,
                notes=notes,
            )
            guests.append(g)
            db.add(g)
        db.commit()

        # 5. Reservations (18 reservations spanning yesterday -> +14 days in INR)
        print("[*] Generating 18 realistic reservations with live folio items in INR (₹)...")
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        three_days_ago = today - timedelta(days=3)
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        in_3_days = today + timedelta(days=3)
        in_5_days = today + timedelta(days=5)
        in_7_days = today + timedelta(days=7)
        in_10_days = today + timedelta(days=10)
        in_14_days = today + timedelta(days=14)

        reservations_blueprint = [
            # 1. Past: Departed yesterday (Rohan Mehta in 104)
            {
                "conf": "HTL-10492",
                "guest": guests[2],  # Rohan Mehta
                "room": rooms_by_num["104"],
                "in": three_days_ago,
                "out": yesterday,
                "status": "checked_out",
                "rate": Decimal("4500.00"),
                "notes": "Seamless corporate stay",
                "charges": [
                    ("Room Charge: 2 night(s) @ ₹4,500.00", Decimal("9000.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("1080.00"), "tax"),
                ],
                "payments": [(yesterday, Decimal("10080.00"), "credit_card", "AUTH-99120")],
            },
            # 2. Departure TODAY: Priya Patel in 103 (Pending checkout, zero balance due!)
            {
                "conf": "HTL-28193",
                "guest": guests[1],  # Priya Patel
                "room": rooms_by_num["103"],
                "in": two_days_ago,
                "out": today,
                "status": "checked_in",  # in-house, checking out today
                "rate": Decimal("4500.00"),
                "notes": "Late departure requested (1:00 PM)",
                "charges": [
                    ("Room Charge: 2 night(s) @ ₹4,500.00", Decimal("9000.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("1080.00"), "tax"),
                    ("Gourmet Minibar - Roasted Cashews & Perrier", Decimal("850.00"), "minibar"),
                ],
                "payments": [(yesterday, Decimal("10930.00"), "credit_card", "AUTH-77192")],  # fully paid! balance = 0
            },
            # 3. Departure TODAY: Sarah Jenkins in 205 (Already checked out this morning)
            {
                "conf": "HTL-39281",
                "guest": guests[9],  # Sarah Jenkins
                "room": rooms_by_num["205"],
                "in": three_days_ago,
                "out": today,
                "status": "checked_out",
                "rate": Decimal("7500.00"),
                "notes": "Checked out at 10:45 AM. Flight to London at 3:00 PM.",
                "charges": [
                    ("Room Charge: 3 night(s) @ ₹7,500.00", Decimal("22500.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("2700.00"), "tax"),
                    ("Royal Awadhi Thali Dining", Decimal("1800.00"), "restaurant"),
                ],
                "payments": [(today, Decimal("27000.00"), "credit_card", "AUTH-88210")],
            },
            # 4. Departure TODAY: Vikram Malhotra in 110 (Has outstanding balance to test blocked checkout!)
            {
                "conf": "HTL-48190",
                "guest": guests[4],  # Vikram Malhotra
                "room": rooms_by_num["110"],
                "in": yesterday,
                "out": today,
                "status": "checked_in",
                "rate": Decimal("4500.00"),
                "notes": "Corporate traveler, minibar item pending settlement",
                "charges": [
                    ("Room Charge: 1 night(s) @ ₹4,500.00", Decimal("4500.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("540.00"), "tax"),
                    ("Minibar - Amrut Single Malt & Chocolates", Decimal("1200.00"), "minibar"),
                ],
                "payments": [(yesterday, Decimal("5040.00"), "credit_card", "AUTH-55214")],  # ₹1,200.00 balance due!
            },
            # 5. Arrival TODAY: Aarav Sharma in 201 (Booked, arriving today, ready to check in!)
            {
                "conf": "HTL-58291",
                "guest": guests[0],  # Aarav Sharma
                "room": rooms_by_num["201"],
                "in": today,
                "out": in_3_days,
                "status": "booked",
                "rate": Decimal("7500.00"),
                "notes": "Flight from Mumbai arriving 2:15 PM, expected at hotel by 4:00 PM",
                "charges": [],
                "payments": [],
            },
            # 6. Arrival TODAY: Carlos Mendez in 106 (Checked in earlier today!)
            {
                "conf": "HTL-67293",
                "guest": guests[10],  # Carlos Mendez
                "room": rooms_by_num["106"],
                "in": today,
                "out": in_5_days,
                "status": "checked_in",
                "rate": Decimal("4500.00"),
                "notes": "Early check-in accommodated at 11:30 AM",
                "charges": [
                    ("Room Charge: 5 night(s) @ ₹4,500.00", Decimal("22500.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("2700.00"), "tax"),
                ],
                "payments": [(today, Decimal("10000.00"), "credit_card", "AUTH-33918")],
            },
            # 7. In-House: Ananya Iyer in 204 (Checked in yesterday, departing in 2 days)
            {
                "conf": "HTL-71928",
                "guest": guests[3],  # Ananya Iyer
                "room": rooms_by_num["204"],
                "in": yesterday,
                "out": in_3_days,
                "status": "checked_in",
                "rate": Decimal("7500.00"),
                "notes": "Anniversary celebratory cake provided compliments of General Manager",
                "charges": [
                    ("Room Charge: 4 night(s) @ ₹7,500.00", Decimal("30000.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("3600.00"), "tax"),
                    ("Room Service Dinner - Chettinad Seafood Curry", Decimal("2400.00"), "restaurant"),
                ],
                "payments": [(yesterday, Decimal("36000.00"), "credit_card", "AUTH-11928")],
            },
            # 8. In-House: Dr. Rajesh Gupta in 207 (Checked in 2 days ago, departing tomorrow)
            {
                "conf": "HTL-82910",
                "guest": guests[5],  # Dr. Rajesh Gupta
                "room": rooms_by_num["207"],
                "in": two_days_ago,
                "out": tomorrow,
                "status": "checked_in",
                "rate": Decimal("7500.00"),
                "notes": "Attending national medical council summit",
                "charges": [
                    ("Room Charge: 3 night(s) @ ₹7,500.00", Decimal("22500.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("2700.00"), "tax"),
                    ("Ayurvedic Wellness Therapy (60m)", Decimal("4500.00"), "service"),
                ],
                "payments": [(two_days_ago, Decimal("29700.00"), "credit_card", "AUTH-44129")],
            },
            # 9. In-House: Neha Reddy in 302 (Executive Heritage Suite, VIP)
            {
                "conf": "HTL-93812",
                "guest": guests[6],  # Neha Reddy
                "room": rooms_by_num["302"],
                "in": yesterday,
                "out": in_5_days,
                "status": "checked_in",
                "rate": Decimal("16500.00"),
                "notes": "Executive suite reservation, private Mercedes airport chauffeur",
                "charges": [
                    ("Room Charge: 6 night(s) @ ₹16,500.00", Decimal("99000.00"), "room"),
                    ("Goods & Services Tax (GST 12%)", Decimal("11880.00"), "tax"),
                    ("Private Dining - Royal Mughlai Banquet", Decimal("6500.00"), "restaurant"),
                ],
                "payments": [(yesterday, Decimal("85000.00"), "bank_transfer", "NEFT-IN-88319")],
            },
            # 10. Upcoming: Kavita Sen in 203 (Checking in tomorrow)
            {
                "conf": "HTL-10293",
                "guest": guests[7],  # Kavita Sen
                "room": rooms_by_num["203"],
                "in": tomorrow,
                "out": in_3_days,
                "status": "booked",
                "rate": Decimal("7500.00"),
                "notes": "Guaranteed with HDFC Corporate Card",
                "charges": [],
                "payments": [],
            },
            # 11. Upcoming: David Kim in 101 (Checking in tomorrow)
            {
                "conf": "HTL-21938",
                "guest": guests[8],  # David Kim
                "room": rooms_by_num["101"],
                "in": tomorrow,
                "out": in_5_days,
                "status": "booked",
                "rate": Decimal("4500.00"),
                "notes": "Direct web reservation via Hotel Portal",
                "charges": [],
                "payments": [],
            },
            # 12. Upcoming: Elena Rostova in 301 (Checking in in 2 days)
            {
                "conf": "HTL-32849",
                "guest": guests[11],  # Elena Rostova
                "room": rooms_by_num["301"],
                "in": day_after,
                "out": in_7_days,
                "status": "booked",
                "rate": Decimal("16500.00"),
                "notes": "Corner penthouse suite. High-speed router test requested.",
                "charges": [],
                "payments": [],
            },
            # 13. Upcoming: Vikram Malhotra in 206 (Checking in in 3 days)
            {
                "conf": "HTL-43920",
                "guest": guests[4],  # Vikram Malhotra
                "room": rooms_by_num["206"],
                "in": in_3_days,
                "out": in_7_days,
                "status": "booked",
                "rate": Decimal("7500.00"),
                "notes": "Second leg of quarterly visit",
                "charges": [],
                "payments": [],
            },
            # 14. Upcoming: Rohan Mehta in 303 (Checking in in 5 days)
            {
                "conf": "HTL-54910",
                "guest": guests[2],  # Rohan Mehta
                "room": rooms_by_num["303"],
                "in": in_5_days,
                "out": in_10_days,
                "status": "booked",
                "rate": Decimal("16500.00"),
                "notes": "Tech summit keynote speaker",
                "charges": [],
                "payments": [],
            },
            # 15. Upcoming: Priya Patel in 107 (Checking in in 7 days)
            {
                "conf": "HTL-65821",
                "guest": guests[1],  # Priya Patel
                "room": rooms_by_num["107"],
                "in": in_7_days,
                "out": in_10_days,
                "status": "booked",
                "rate": Decimal("4500.00"),
                "notes": "Architectural client meeting in Bengaluru",
                "charges": [],
                "payments": [],
            },
            # 16. Upcoming: Aarav Sharma in 109 (Checking in in 10 days)
            {
                "conf": "HTL-76932",
                "guest": guests[0],  # Aarav Sharma
                "room": rooms_by_num["109"],
                "in": in_10_days,
                "out": in_14_days,
                "status": "booked",
                "rate": Decimal("4500.00"),
                "notes": "Return stay",
                "charges": [],
                "payments": [],
            },
            # 17. Upcoming: Sarah Jenkins in 202 (Checking in in 5 days)
            {
                "conf": "HTL-87192",
                "guest": guests[9],  # Sarah Jenkins
                "room": rooms_by_num["202"],
                "in": in_5_days,
                "out": in_7_days,
                "status": "booked",
                "rate": Decimal("7500.00"),
                "notes": "Weekend leisure getaway",
                "charges": [],
                "payments": [],
            },
            # 18. Cancelled: Carlos Mendez in 105 (Cancelled due to schedule change)
            {
                "conf": "HTL-98201",
                "guest": guests[10],  # Carlos Mendez
                "room": rooms_by_num["105"],
                "in": today,
                "out": in_3_days,
                "status": "cancelled",
                "rate": Decimal("4500.00"),
                "notes": "Cancelled by guest 24h prior due to conference flight rescheduling",
                "charges": [],
                "payments": [],
            },
        ]

        for item in reservations_blueprint:
            res = Reservation(
                confirmation_number=item["conf"],
                guest_id=item["guest"].id,
                room_id=item["room"].id,
                rate_plan_id=plan_flex.id,
                check_in_date=item["in"],
                check_out_date=item["out"],
                adults=2 if "Suite" in item["room"].room_type.name else 1,
                children=0,
                nightly_rate=item["rate"],
                status=item["status"],
                deposit_required=Decimal("0.00"),
                deposit_paid=Decimal("0.00"),
                deposit_due_at=item["in"],
                notes=item["notes"],
            )
            db.add(res)
            db.commit()
            db.refresh(res)

            # Create primary folio for reservation
            primary_folio = Folio(
                reservation_id=res.id,
                name="Primary",
                is_master=True,
            )
            db.add(primary_folio)
            db.commit()
            db.refresh(primary_folio)

            for desc, amt, cat in item["charges"]:
                f_item = FolioItem(
                    reservation_id=res.id,
                    folio_id=primary_folio.id,
                    date=item["in"],
                    description=desc,
                    category=cat,
                    amount=amt,
                    subtotal=amt,
                    tax_total=Decimal("0.00"),
                )
                db.add(f_item)

            for p_date, p_amt, p_meth, p_ref in item["payments"]:
                pmt = Payment(
                    reservation_id=res.id,
                    folio_id=primary_folio.id,
                    date=p_date,
                    amount=p_amt,
                    method=p_meth,
                    reference=p_ref,
                )
                db.add(pmt)
            db.commit()

        # 5b. Group Booking (Webb Corporate Retreat)
        print("[*] Seeding corporate group booking with room blocks...")
        group_webb = BookingGroup(
            name="Webb Corporate Retreat",
            contact_name="David Webb",
            contact_email="d.webb@webbconsulting.com",
            contact_phone="+91 98840 12345",
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=13),
            cutoff_date=today + timedelta(days=5),
            status="confirmed",
            notes="Annual executive planning retreat for 15 directors; requires Banquet Hall B setup.",
        )
        db.add(group_webb)
        db.commit()
        db.refresh(group_webb)

        block_dlx = GroupBlock(
            group_id=group_webb.id,
            room_type_id=rt_deluxe.id,
            count=6,
            rate=Decimal("6800.00"),
        )
        block_suite = GroupBlock(
            group_id=group_webb.id,
            room_type_id=rt_suite.id,
            count=2,
            rate=Decimal("14500.00"),
        )
        db.add_all([block_dlx, block_suite])
        db.commit()

        # 6. Housekeeping Tasks (6 assignments)
        print("[*] Dispatching 6 housekeeping assignments...")
        tasks_data = [
            (rooms_by_num["104"].id, "checkout_clean", "pending", "high", "Sunita Nair", "Turnover clean following departure of Rohan Mehta (#HTL-10492)"),
            (rooms_by_num["202"].id, "stayover_clean", "in_progress", "medium", "Sunita Nair", "Daily stayover linens, towel refresh, and tea supplies"),
            (rooms_by_num["301"].id, "deep_clean", "done", "high", "Manoj Kumar", "Quarterly carpet shampoo and Cubbon Park terrace balcony polishing completed"),
            (rooms_by_num["108"].id, "maintenance_repair", "pending", "urgent", "Ramesh Babu", "Daikin VRV air-conditioner sensor display calibration"),
            (rooms_by_num["205"].id, "checkout_clean", "pending", "high", "Sunita Nair", "Turnover clean following departure of Sarah Jenkins (#HTL-39281)"),
            (rooms_by_num["102"].id, "inspection", "done", "low", "Aditi Rao", "Supervisor pre-arrival quality inspection passed with 100% score"),
        ]

        for rid, ttype, st, prio, asgn, notes in tasks_data:
            completed_dt = datetime.now(timezone.utc) - timedelta(hours=2) if st == "done" else None
            t = HousekeepingTask(
                room_id=rid,
                task_type=ttype,
                status=st,
                priority=prio,
                assigned_to=asgn,
                notes=notes,
                completed_at=completed_dt,
            )
            db.add(t)
        db.commit()

        # 7. Realistic Activity Logs (for Dashboard recent activity feed)
        print("[*] Recording hotel operational activity trail in INR (₹)...")
        logs_data = [
            ("check_in", "Carlos Mendez checked into Room 106 (#HTL-67293)", "Rahul Verma", 15),
            ("payment", "Payment of ₹27,000.00 (credit_card) received for Res #HTL-39281", "Rahul Verma", 45),
            ("check_out", "Sarah Jenkins checked out of Room 205. Room marked dirty.", "Rahul Verma", 50),
            ("task_created", "Turnover clean scheduled for Room 205", "System", 50),
            ("charge", "Minibar charge of ₹1,200.00 posted to Room 110 (Vikram Malhotra)", "Sunita Nair", 95),
            ("room_status", "Room 108 status changed to maintenance (Daikin AC calibration)", "Ramesh Babu", 140),
            ("task_completed", "Supervisor inspection on Room 102 marked complete", "Aditi Rao", 180),
            ("reservation_created", "Reservation #HTL-87192 created for Sarah Jenkins", "Aditi Rao", 240),
        ]

        for ev_type, desc, actor, mins_ago in logs_data:
            log_time = datetime.now(timezone.utc) - timedelta(minutes=mins_ago)
            log = ActivityLog(
                event_type=ev_type,
                description=desc,
                actor=actor,
                created_at=log_time,
            )
            db.add(log)
        db.commit()

        print("[+] Hotel PMS seed completed successfully in INR (₹)!")
        print(f"    - Rooms: {len(room_data)}")
        print(f"    - Guests: {len(guests_data)}")
        print(f"    - Reservations: {len(reservations_blueprint)}")
        print(f"    - Housekeeping Tasks: {len(tasks_data)}")

    except Exception as exc:
        db.rollback()
        print(f"[!] Error during seeding: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
