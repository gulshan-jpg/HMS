"""Seed rich demo reservations for Organizations 2 and 3."""
from datetime import date, timedelta
from decimal import Decimal
import random
from app.database import SessionLocal
from app.models import (
    Organization, Room, Guest, Reservation, Folio, FolioItem, Payment, RatePlan
)

def run_seed():
    db = SessionLocal()
    demo_guests_data = [
        ('Aditya', 'Kapoor', 'aditya.k@gmail.com', '+91 98201 12345'),
        ('Simran', 'Kaur', 'simran.kaur@outlook.com', '+91 98722 34567'),
        ('Kabir', 'Mehra', 'kabir.mehra@techcorp.in', '+91 98111 98765'),
        ('Pooja', 'Hegde', 'pooja.hegde@luxurytravel.com', '+91 98450 43210'),
        ('Vikramaditya', 'Rao', 'v.rao@consulting.org', '+91 97401 55667'),
        ('Zoya', 'Akhtar', 'zoya.films@creative.in', '+91 99200 88990'),
        ('Manish', 'Malhotra', 'manish.fashion@couture.in', '+91 98210 77889'),
        ('Anushka', 'Sharma', 'anushka.s@ventures.com', '+91 98199 66778'),
    ]

    today = date.today()

    for org in db.query(Organization).filter(Organization.id.in_([2, 3])).all():
        print(f"Seeding demo reservations for Org {org.id}: {org.name}")
        rooms = db.query(Room).filter(Room.organization_id == org.id).all()
        plans = db.query(RatePlan).filter(RatePlan.organization_id == org.id).all()
        if not rooms:
            continue
        
        plan = plans[0] if plans else None
        
        created_guests = []
        for fn, ln, em, ph in demo_guests_data:
            g = db.query(Guest).filter(Guest.organization_id == org.id, Guest.email == em).first()
            if not g:
                g = Guest(
                    organization_id=org.id,
                    first_name=fn,
                    last_name=ln,
                    email=em,
                    phone=ph,
                    address='Mumbai, Maharashtra, India',
                    id_number=f'AADH-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}',
                )
                db.add(g)
                db.flush()
            created_guests.append(g)
        
        # 1. Active Checked-in Guests (In-house right now, ready for checkout / payments)
        checked_in_specs = [
            (rooms[0], created_guests[0], today - timedelta(days=2), today + timedelta(days=1), Decimal('4500.00'), 'Airport pickup completed. High floor requested.'),
            (rooms[1], created_guests[1], today - timedelta(days=1), today, Decimal('5200.00'), 'Departing today at 12 PM. Needs GST tax invoice.'),
            (rooms[2], created_guests[2], today - timedelta(days=3), today, Decimal('3800.00'), 'Extended stay guest. Extra pillows supplied.'),
        ]
        
        for rm, gst, cin, cout, rate, notes in checked_in_specs:
            existing_res = db.query(Reservation).filter(Reservation.organization_id == org.id, Reservation.guest_id == gst.id).first()
            if existing_res:
                continue
            
            nights = (cout - cin).days
            conf = f'DEMO-{org.id}-{rm.number}-{random.randint(100, 999)}'
            res = Reservation(
                organization_id=org.id,
                confirmation_number=conf,
                guest_id=gst.id,
                room_id=rm.id,
                rate_plan_id=plan.id if plan else None,
                check_in_date=cin,
                check_out_date=cout,
                adults=2,
                children=0,
                nightly_rate=rate,
                status='checked_in',
                notes=notes,
                is_demo=True,
            )
            db.add(res)
            db.flush()
            
            rm.status = 'occupied'
            
            folio = Folio(organization_id=org.id, reservation_id=res.id, name='Master Folio', is_master=True)
            db.add(folio)
            db.flush()
            
            total_room_charge = rate * nights
            tax_amt = round(total_room_charge * Decimal('0.12'), 2)
            f_room = FolioItem(organization_id=org.id, reservation_id=res.id, folio_id=folio.id, date=cin, description=f'Room Charge ({nights} nights @ ₹{rate})', category='room', amount=total_room_charge)
            f_tax = FolioItem(organization_id=org.id, reservation_id=res.id, folio_id=folio.id, date=cin, description='GST Tax (12%)', category='tax', amount=tax_amt)
            db.add_all([f_room, f_tax])
            
            if cout == today:
                f_dine = FolioItem(organization_id=org.id, reservation_id=res.id, folio_id=folio.id, date=today, description='In-Room Dining (Dinner & Mocktails)', category='dining', amount=Decimal('1250.00'))
                db.add(f_dine)
                total_bill = total_room_charge + tax_amt + Decimal('1250.00')
                pmt = Payment(organization_id=org.id, reservation_id=res.id, folio_id=folio.id, date=today, amount=total_bill, method='upi', reference=f'UPI-DEMO-{random.randint(10000, 99999)}')
                db.add(pmt)
            else:
                pmt = Payment(organization_id=org.id, reservation_id=res.id, folio_id=folio.id, date=cin, amount=Decimal('3000.00'), method='card', reference=f'CARD-DEMO-{random.randint(1000, 9999)}')
                db.add(pmt)
        
        # 2. Upcoming Booked Reservations
        booked_specs = [
            (rooms[3] if len(rooms) > 3 else rooms[0], created_guests[3], today, today + timedelta(days=2), Decimal('4800.00'), 'Arriving this afternoon by flight. King bed confirmed.'),
            (rooms[4] if len(rooms) > 4 else rooms[1], created_guests[4], today + timedelta(days=1), today + timedelta(days=4), Decimal('6500.00'), 'VIP honeymoon suite booking. Fruit basket requested.'),
            (rooms[5] if len(rooms) > 5 else rooms[2], created_guests[5], today + timedelta(days=2), today + timedelta(days=5), Decimal('4200.00'), 'Corporate booking via Direct Web.'),
        ]
        
        for rm, gst, cin, cout, rate, notes in booked_specs:
            existing_res = db.query(Reservation).filter(Reservation.organization_id == org.id, Reservation.guest_id == gst.id).first()
            if existing_res:
                continue
            conf = f'DEMO-{org.id}-{rm.number}-{random.randint(100, 999)}'
            res = Reservation(
                organization_id=org.id,
                confirmation_number=conf,
                guest_id=gst.id,
                room_id=rm.id,
                rate_plan_id=plan.id if plan else None,
                check_in_date=cin,
                check_out_date=cout,
                adults=1,
                children=0,
                nightly_rate=rate,
                status='booked',
                notes=notes,
                deposit_required=Decimal('2000.00'),
                deposit_paid=Decimal('2000.00'),
                is_demo=True,
            )
            db.add(res)
            db.flush()
            folio = Folio(organization_id=org.id, reservation_id=res.id, name='Primary', is_master=True)
            db.add(folio)
            db.flush()
            pmt = Payment(organization_id=org.id, reservation_id=res.id, folio_id=folio.id, date=today, amount=Decimal('2000.00'), method='card', reference=f'DEP-{random.randint(10000, 99999)}')
            db.add(pmt)
        
        db.commit()
        print(f"Successfully seeded demo reservations for {org.name}!")

    db.close()
    print("Done!")

if __name__ == "__main__":
    run_seed()
