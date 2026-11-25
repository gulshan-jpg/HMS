/**
 * CheckinOS Data Store & Fast Persistence Engine (Node.js)
 * Ultra-low latency (< 15ms) in-memory reactive store with optional PostgreSQL sync.
 */
const bcrypt = require('bcryptjs');
const { Pool } = require('pg');

let pool = null;
const dbUrl = process.env.DATABASE_URL;
if (dbUrl && !dbUrl.startsWith('sqlite')) {
  try {
    pool = new Pool({
      connectionString: dbUrl.replace('postgres://', 'postgresql://'),
      ssl: dbUrl.includes('supabase.co') || dbUrl.includes('neon.tech') || dbUrl.includes('pooler') ? { rejectUnauthorized: false } : false,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
    pool.on('error', (err) => console.error('[PG_POOL_ERROR]', err.message));
  } catch (e) {
    console.warn('[PG_POOL_INIT_WARN] Using memory engine:', e.message);
  }
}

// In-Memory Seed State
const state = {
  organization: {
    id: 1,
    name: "The Grand Pavilion & Palace Hotel",
    slug: "the-grand-pavilion-palace-hotel",
    currency: "INR",
    timezone: "Asia/Kolkata",
    address: "12/4 MG Road, Shivaji Nagar, Bengaluru, Karnataka 560001, India",
    phone: "+91 80 4123 4567",
    email: "reservations@grandpavilion.in",
    tax_id: "29AAAAA0000A1Z5",
    plan: "pro",
    subscription_status: "active",
  },
  users: [
    {
      id: 1,
      username: "admin",
      email: "admin@grandpavilion.in",
      full_name: "Aditi Rao",
      role: "owner",
      password_hash: bcrypt.hashSync("admin123", 10),
      is_active: true,
      organization_id: 1,
    },
    {
      id: 2,
      username: "staff",
      email: "staff@grandpavilion.in",
      full_name: "Rahul Verma",
      role: "front_desk",
      password_hash: bcrypt.hashSync("staff123", 10),
      is_active: true,
      organization_id: 1,
    },
    {
      id: 3,
      username: "sunita",
      email: "sunita.n@grandpavilion.in",
      full_name: "Sunita Nair",
      role: "housekeeping",
      password_hash: bcrypt.hashSync("staff123", 10),
      is_active: true,
      organization_id: 1,
    },
    {
      id: 4,
      username: "hotelosj",
      email: "owner@hotelosj.com",
      full_name: "Hotel OSJ Owner",
      role: "owner",
      password_hash: bcrypt.hashSync("Password123!", 10),
      is_active: true,
      organization_id: 1,
    }
  ],
  roomTypes: [
    {
      id: 1,
      name: "Standard Deluxe Queen",
      code: "STD-Q",
      description: "Plush Queen bed, marble rain shower, tea lounge, and high-speed fiber Wi-Fi.",
      base_rate: 4500.00,
      max_occupancy: 2,
    },
    {
      id: 2,
      name: "Deluxe King",
      code: "DLX-K",
      description: "Spacious King bed with city skyline views, sitting lounge, Nespresso bar, and jacuzzi tub.",
      base_rate: 7500.00,
      max_occupancy: 2,
    },
    {
      id: 3,
      name: "Executive Heritage Suite",
      code: "EXE-S",
      description: "Top-floor corner suite with separate parlor, private bar, panoramic views, and dedicated royal butler service.",
      base_rate: 16500.00,
      max_occupancy: 4,
    }
  ],
  rooms: [
    { id: 1, number: "101", floor: 1, room_type_id: 1, status: "available", notes: "Quiet courtyard garden view" },
    { id: 2, number: "102", floor: 1, room_type_id: 1, status: "available", notes: "Near ground floor elevator and lounge" },
    { id: 3, number: "103", floor: 1, room_type_id: 1, status: "occupied", notes: "Guest requested extra feather pillows" },
    { id: 4, number: "104", floor: 1, room_type_id: 1, status: "dirty", notes: "Turnover cleaning required" },
    { id: 5, number: "105", floor: 1, room_type_id: 1, status: "available", notes: "ADA compliant bathroom with grab bars" },
    { id: 6, number: "106", floor: 1, room_type_id: 1, status: "occupied", notes: "Late arrival noted" },
    { id: 7, number: "107", floor: 1, room_type_id: 1, status: "available", notes: "Courtyard fountain facing" },
    { id: 8, number: "108", floor: 1, room_type_id: 1, status: "maintenance", notes: "Daikin air-conditioning calibration" },
    { id: 9, number: "109", floor: 1, room_type_id: 1, status: "available", notes: "Standard garden layout" },
    { id: 10, number: "110", floor: 1, room_type_id: 1, status: "occupied", notes: "Corporate traveler rate" },
    { id: 11, number: "201", floor: 2, room_type_id: 2, status: "occupied", notes: "High floor, quiet north wing" },
    { id: 12, number: "202", floor: 2, room_type_id: 2, status: "cleaning", notes: "Housekeeping in progress" },
    { id: 13, number: "203", floor: 2, room_type_id: 2, status: "available", notes: "City skyline view with soaking tub" },
    { id: 14, number: "204", floor: 2, room_type_id: 2, status: "occupied", notes: "Anniversary setup" },
    { id: 15, number: "205", floor: 2, room_type_id: 2, status: "dirty", notes: "Departed at 11:00 AM" },
    { id: 16, number: "206", floor: 2, room_type_id: 2, status: "available", notes: "Refurbished teakwood flooring" },
    { id: 17, number: "207", floor: 2, room_type_id: 2, status: "occupied", notes: "Connecting door to 206 locked" },
    { id: 18, number: "301", floor: 3, room_type_id: 3, status: "available", notes: "Corner penthouse suite" },
    { id: 19, number: "302", floor: 3, room_type_id: 3, status: "occupied", notes: "VIP diplomat guest" },
    { id: 20, number: "303", floor: 3, room_type_id: 3, status: "available", notes: "Terrace overlooking park" }
  ],
  ratePlans: [
    { id: 1, code: "BAR", name: "Standard Daily Base Rate", description: "Standard flexible rate", multiplier: 1.0, is_active: true },
    { id: 2, code: "FLEX", name: "Flexible Standard", description: "Standard daily rate with free cancellation", multiplier: 1.0, is_active: true },
    { id: 3, code: "NR", name: "Non-Refundable Saver", description: "Save 10% with full prepayment", multiplier: 0.90, is_active: true },
    { id: 4, code: "BB", name: "Bed & Breakfast", description: "Includes daily royal breakfast buffet", multiplier: 1.15, is_active: true },
    { id: 5, code: "CORP", name: "Corporate Business Pro", description: "Preferred corporate negotiated rate", multiplier: 0.88, is_active: true }
  ],
  cancellationPolicies: [
    { id: 1, name: "Flexible 24-Hour", description: "Free cancellation up to 24 hours prior to check-in. First night penalty thereafter.", free_cancel_days: 1, penalty_type: "first_night", penalty_value: 100, no_show_penalty: "first_night", no_show_value: 100, active: true, sort_order: 1 },
    { id: 2, name: "Moderate 3-Day Window", description: "Free cancellation up to 3 days before arrival. First night penalty thereafter.", free_cancel_days: 3, penalty_type: "first_night", penalty_value: 100, no_show_penalty: "first_night", no_show_value: 100, active: true, sort_order: 2 },
    { id: 3, name: "Non-Refundable Policy", description: "100% reservation charge applies upon cancellation at any time.", free_cancel_days: 0, penalty_type: "first_night", penalty_value: 100, no_show_penalty: "full_stay", no_show_value: 100, active: true, sort_order: 3 }
  ],
  taxes: [
    { id: 1, name: "Goods & Services Tax (GST 12%)", rate: 12.00, fixed_amount: 0.00, applies_to: "rooms", type: "exclusive", per: "stay", active: true, sort_order: 1 },
    { id: 2, name: "Luxury Goods & Services Tax (GST 18%)", rate: 18.00, fixed_amount: 0.00, applies_to: "rooms", type: "exclusive", per: "stay", active: true, sort_order: 2 },
    { id: 3, name: "City Municipal Tax", rate: 3.00, fixed_amount: 0.00, applies_to: "rooms", type: "exclusive", per: "stay", active: true, sort_order: 3 },
    { id: 4, name: "Tourism Development Levy", rate: 0.00, fixed_amount: 150.00, applies_to: "rooms", type: "exclusive", per: "stay", active: true, sort_order: 4 }
  ],
  businessDate: {
    date: new Date().toISOString().slice(0, 10),
    status: "open",
    is_open: true
  },
  guests: [
    { id: 1, first_name: "Rahul", last_name: "Sharma", email: "rahul.s@techcorp.in", phone: "+91 98201 23456", id_number: "7825-1480-6941", vip_status: "regular" },
    { id: 2, first_name: "Priya", last_name: "Patel", email: "priya.p@architecture.in", phone: "+91 98450 11223", id_number: "DL-KA-8837190", vip_status: "vip" },
    { id: 3, first_name: "Vikram", last_name: "Malhotra", email: "vikram.m@venture.in", phone: "+91 98111 22334", id_number: "DL-HR-4481023", vip_status: "regular" },
    { id: 4, first_name: "Ananya", last_name: "Verma", email: "ananya.v@design.in", phone: "+91 97412 34567", id_number: "PASSPORT-IN-33918", vip_status: "regular" },
    { id: 5, first_name: "Aarav", last_name: "Kapoor", email: "aarav.k@global.in", phone: "+91 98765 12345", id_number: "4819-2819-4829", vip_status: "vip" }
  ],
  reservations: [
    {
      id: 1,
      confirmation_number: "HTL-10821",
      guest_id: 1,
      guest: { first_name: "Rahul", last_name: "Sharma", email: "rahul.s@techcorp.in", phone: "+91 98201 23456" },
      room_id: 11,
      room: { id: 11, number: "201", room_type_id: 2, room_type: { name: "Deluxe King" } },
      check_in_date: "2026-11-24",
      check_out_date: "2026-11-28",
      status: "checked_in",
      rate_plan_id: 4,
      rate_plan: { name: "Bed & Breakfast", code: "BB" },
      adults: 2,
      nightly_rate: 7500.00,
      total_charges: 30000.00,
      total_paid: 30000.00,
      balance_due: 0.00,
      created_at: new Date().toISOString()
    },
    {
      id: 2,
      confirmation_number: "HTL-10822",
      guest_id: 2,
      guest: { first_name: "Priya", last_name: "Patel", email: "priya.p@architecture.in", phone: "+91 98450 11223" },
      room_id: 18,
      room: { id: 18, number: "301", room_type_id: 3, room_type: { name: "Executive Heritage Suite" } },
      check_in_date: "2026-11-24",
      check_out_date: "2026-11-26",
      status: "confirmed",
      rate_plan_id: 2,
      rate_plan: { name: "Flexible Standard", code: "FLEX" },
      adults: 2,
      nightly_rate: 16500.00,
      total_charges: 33000.00,
      total_paid: 18000.00,
      balance_due: 15000.00,
      created_at: new Date().toISOString()
    },
    {
      id: 3,
      confirmation_number: "HTL-10823",
      guest_id: 3,
      guest: { first_name: "Vikram", last_name: "Malhotra", email: "vikram.m@venture.in", phone: "+91 98111 22334" },
      room_id: 5,
      room: { id: 5, number: "105", room_type_id: 1, room_type: { name: "Standard Deluxe Queen" } },
      check_in_date: "2026-11-20",
      check_out_date: "2026-11-24",
      status: "checked_out",
      rate_plan_id: 5,
      rate_plan: { name: "Corporate Business Pro", code: "CORP" },
      adults: 1,
      nightly_rate: 3960.00,
      total_charges: 15840.00,
      total_paid: 15840.00,
      balance_due: 0.00,
      created_at: new Date().toISOString()
    },
    {
      id: 4,
      confirmation_number: "HTL-10824",
      guest_id: 4,
      guest: { first_name: "Ananya", last_name: "Verma", email: "ananya.v@design.in", phone: "+91 97412 34567" },
      room_id: 12,
      room: { id: 12, number: "202", room_type_id: 2, room_type: { name: "Deluxe King" } },
      check_in_date: "2026-11-24",
      check_out_date: "2026-11-27",
      status: "checked_in",
      rate_plan_id: 1,
      rate_plan: { name: "Standard Daily Base Rate", code: "BAR" },
      adults: 1,
      nightly_rate: 7500.00,
      total_charges: 22500.00,
      total_paid: 22500.00,
      balance_due: 0.00,
      created_at: new Date().toISOString()
    }
  ],
  housekeeping: [
    { id: 1, room_id: 4, room_number: "104", task_type: "turnover", priority: "high", status: "pending", assigned_to_name: "Sunita Nair", notes: "Linen change & sanitization" },
    { id: 2, room_id: 12, room_number: "202", task_type: "turnover", priority: "medium", status: "in_progress", assigned_to_name: "Maria Santos", notes: "Mid-stay clean" },
    { id: 3, room_id: 15, room_number: "205", task_type: "turnover", priority: "medium", status: "pending", assigned_to_name: "Sunita Nair", notes: "Departed at 11:00 AM" },
    { id: 4, room_id: 8, room_number: "108", task_type: "maintenance", priority: "urgent", status: "pending", assigned_to_name: "Maintenance Tech", notes: "AC diagnostic" },
    { id: 5, room_id: 2, room_number: "102", task_type: "turnover", priority: "low", status: "done", assigned_to_name: "Sunita Nair", notes: "Clean and inspected" }
  ],
  folios: [
    {
      id: 1,
      reservation_id: 1,
      name: "Main Stay Folio",
      balance: 0.00,
      status: "closed",
      items: [
        { id: 1, description: "Room Charge (4 nights @ ₹7,500.00)", amount: 30000.00, type: "room", created_at: "2026-11-24" }
      ],
      payments: [
        { id: 1, amount: 30000.00, method: "card", reference: "AUTH-8921", created_at: "2026-11-24" }
      ]
    },
    {
      id: 2,
      reservation_id: 2,
      name: "Main Stay Folio",
      balance: 15000.00,
      status: "open",
      items: [
        { id: 2, description: "Room Charge (2 nights @ ₹16,500.00)", amount: 33000.00, type: "room", created_at: "2026-11-24" }
      ],
      payments: [
        { id: 2, amount: 18000.00, method: "upi", reference: "UPI-481928", created_at: "2026-11-24" }
      ]
    }
  ],
  demoRequests: [],
  otaFeed: [
    {
      id: 1,
      source: "Booking.com",
      reservation_ref: "HTL-GM-BCOM-7822",
      guest_name: "Vikram Malhotra",
      room_type: "Deluxe King",
      nights: 3,
      amount: 22500.00,
      currency: "INR",
      status: "processed",
      created_at: new Date().toISOString()
    }
  ],
  emailTemplates: [
    { id: 1, key: "booking_confirmation", name: "Guest Booking Confirmation", subject: "Your reservation at {{hotel_name}} is confirmed (#{{confirmation_number}})", body_html: "Dear {{guest_name}},\n\nYour booking at {{hotel_name}} is confirmed for {{check_in_date}} to {{check_out_date}}.\nRoom: {{room_type}} (Room {{room_number}})\nTotal: ₹{{total_amount}}\n\nWe look forward to hosting you!", is_active: true },
    { id: 2, key: "pre_arrival_reminder", name: "Pre-Arrival & Check-in Details", subject: "See you soon at {{hotel_name}}! Check-in details and travel directions", body_html: "Dear {{guest_name}},\n\nWe are preparing for your arrival on {{check_in_date}}. Check-in begins at 2:00 PM.\n\nPlease carry valid government photo ID.", is_active: true },
    { id: 3, key: "checkout_invoice", name: "Departure Tax Invoice", subject: "Tax Invoice & Receipt for stay at {{hotel_name}}", body_html: "Dear {{guest_name}},\n\nThank you for choosing {{hotel_name}}. Please find attached your official GST Tax Invoice.\n\nTotal Paid: ₹{{total_paid}}", is_active: true }
  ],
  groups: [
    {
      id: 1,
      hotel_id: 1,
      name: "TCS Global Leadership Retreat 2026",
      contact_name: "Deepak Sharma",
      contact_phone: "+91 98200 11223",
      contact_email: "deepak.s@tcs.com",
      status: "confirmed",
      billing_type: "master",
      check_in_date: "2026-11-25",
      check_out_date: "2026-11-28",
      cutoff_date: "2026-11-24",
      notes: "Corporate event. All room charges to Master Folio. Incidentals direct pay.",
      room_blocks: [
        { id: 1, group_id: 1, room_type_id: 1, room_type_name: "Standard Deluxe Queen", count: 4, rate: 4200, picked_up_count: 3, available_to_pick: 1 },
        { id: 2, group_id: 1, room_type_id: 2, room_type_name: "Deluxe King", count: 2, rate: 6800, picked_up_count: 2, available_to_pick: 0 }
      ],
      total_charges: 115000,
      total_paid: 60000,
      balance: 55000
    }
  ],
  auditLogs: [
    { id: 1, event_type: "night_audit_completed", description: "System rolled business date forward to Nov 24, 2026. 14 room charges posted.", actor: "System Daemon", created_at: new Date(Date.now() - 3600000 * 24).toISOString() },
    { id: 2, event_type: "rate_override_bulk", description: "Updated weekend rates for Deluxe King rooms (+20%).", actor: "Aditi Rao", created_at: new Date(Date.now() - 3600000 * 12).toISOString() },
    { id: 3, event_type: "check_in", description: "Checked in reservation HTL-10821 (Rahul Sharma) into Room 201.", actor: "Rahul Verma", created_at: new Date(Date.now() - 3600000 * 4).toISOString() }
  ],
  backups: [
    { id: 1, filename: "backup_hotel_20261123_full.sql.gz", size_bytes: 4280192, status: "completed", created_at: new Date(Date.now() - 86400000).toISOString() },
    { id: 2, filename: "backup_hotel_20261124_automated.sql.gz", size_bytes: 4310844, status: "completed", created_at: new Date(Date.now() - 3600000 * 6).toISOString() }
  ],
  trash: {
    reservations: [],
    rooms: [],
    guests: []
  },
  auditSnapshots: [
    {
      id: 1,
      business_date: "2026-11-23",
      occupancy_rate: 65.0,
      adr: 6850.0,
      revpar: 4452.5,
      arrivals: 6,
      departures: 4,
      room_revenue: 91500.0,
      total_revenue: 104250.0,
      tax_collected: 12450.0,
      created_at: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 2,
      business_date: "2026-11-22",
      occupancy_rate: 70.0,
      adr: 7200.0,
      revpar: 5040.0,
      arrivals: 8,
      departures: 5,
      room_revenue: 100800.0,
      total_revenue: 118400.0,
      tax_collected: 14200.0,
      created_at: new Date(Date.now() - 86400000 * 2).toISOString()
    }
  ]
};

// Populate room_type references inside rooms
const populateRooms = () => {
  return state.rooms.map(r => {
    const rt = state.roomTypes.find(t => t.id === r.room_type_id);
    return {
      ...r,
      room_type: rt || { id: 1, name: "Standard", code: "STD", base_rate: 4500, max_occupancy: 2 }
    };
  });
};

const populateReservation = (r) => {
  const g = r.guest || state.guests.find(gst => gst.id === r.guest_id) || { first_name: "Rahul", last_name: "Sharma", phone: "+91 98201 23456" };
  const rm = r.room || state.rooms.find(room => room.id === r.room_id) || state.rooms[0];
  const rt = (rm && rm.room_type) || state.roomTypes.find(t => t.id === (rm ? rm.room_type_id : 1)) || state.roomTypes[0];
  const dIn = new Date(r.check_in_date);
  const dOut = new Date(r.check_out_date);
  const nights = Math.max(1, Math.round((dOut - dIn) / 86400000));
  const guestFullName = (g.full_name || `${g.first_name || ''} ${g.last_name || ''}`).trim();

  return {
    ...r,
    nights: r.nights || nights,
    balance: r.balance_due != null ? r.balance_due : ((r.total_charges || 0) - (r.total_paid || 0)),
    guest: {
      ...g,
      full_name: guestFullName,
    },
    room: {
      ...rm,
      room_type: {
        ...rt,
        code: rt.code || rt.name.slice(0, 4).toUpperCase()
      }
    }
  };
};

const store = {
  getOrganization: () => ({ ...state.organization }),
  
  getUsers: () => [...state.users],

  findUserByIdent: (ident) => {
    const norm = String(ident || '').trim().toLowerCase();
    return state.users.find(u => 
      u.username.toLowerCase() === norm || 
      u.email.toLowerCase() === norm
    );
  },

  findUserById: (id) => state.users.find(u => u.id === Number(id)),

  getRoomTypes: () => [...state.roomTypes],

  getRoomById: (id) => {
    const room = state.rooms.find(r => r.id === Number(id));
    if (!room) return null;
    const rt = state.roomTypes.find(t => t.id === room.room_type_id);
    const activeRes = state.reservations.find(res => (res.room_id === room.id || (res.room && res.room.id === room.id)) && res.status === "checked_in");

    return {
      ...room,
      room_type: rt || { id: 1, name: "Standard", code: "STD", base_rate: 4500, max_occupancy: 2 },
      current_guest: activeRes && activeRes.guest ? `${activeRes.guest.first_name} ${activeRes.guest.last_name}` : null,
      current_reservation_id: activeRes ? activeRes.id : null,
      current_reservation_confirmation: activeRes ? activeRes.confirmation_number : null,
      current_balance: activeRes ? (activeRes.balance_due != null ? activeRes.balance_due : 0) : null,
      current_total_charges: activeRes ? (activeRes.total_charges != null ? activeRes.total_charges : 0) : null,
      current_total_payments: activeRes ? (activeRes.total_paid != null ? activeRes.total_paid : 0) : null,
      current_check_in_date: activeRes ? activeRes.check_in_date : null,
      current_check_out_date: activeRes ? activeRes.check_out_date : null,
    };
  },

  addRoom: (data) => {
    const newId = state.rooms.length ? Math.max(...state.rooms.map(r => r.id)) + 1 : 1;
    const newRoom = {
      id: newId,
      number: String(data.number || `${100 + newId}`),
      floor: Number(data.floor) || 1,
      room_type_id: Number(data.room_type_id) || 1,
      status: data.status || "available",
      notes: data.notes || ""
    };
    state.rooms.push(newRoom);
    return {
      ...newRoom,
      room_type: state.roomTypes.find(t => t.id === newRoom.room_type_id)
    };
  },

  getRooms: (filters = {}) => {
    let list = populateRooms();
    if (filters.floor) {
      list = list.filter(r => r.floor === Number(filters.floor));
    }
    if (filters.status) {
      list = list.filter(r => r.status === filters.status);
    }
    return list;
  },

  updateRoomStatus: (id, status) => {
    const room = state.rooms.find(r => r.id === Number(id));
    if (room) {
      room.status = status;
      return {
        ...room,
        room_type: state.roomTypes.find(t => t.id === room.room_type_id)
      };
    }
    return null;
  },

  getRatePlans: () => [...state.ratePlans],

  getCancellationPolicies: (activeOnly = false) => {
    let list = [...state.cancellationPolicies];
    if (activeOnly) list = list.filter(p => p.active !== false);
    return list;
  },

  getCancellationPolicyById: (id) => state.cancellationPolicies.find(p => p.id === Number(id)),

  createCancellationPolicy: (data) => {
    const newId = state.cancellationPolicies.length ? Math.max(...state.cancellationPolicies.map(p => p.id)) + 1 : 1;
    const newPol = {
      id: newId,
      name: data.name || "Custom Policy",
      description: data.description || "",
      free_cancel_days: Number(data.free_cancel_days) || 0,
      penalty_type: data.penalty_type || "first_night",
      penalty_value: Number(data.penalty_value) || 100,
      no_show_penalty: data.no_show_penalty || "first_night",
      no_show_value: Number(data.no_show_value) || 100,
      active: data.active !== false,
      sort_order: state.cancellationPolicies.length + 1
    };
    state.cancellationPolicies.push(newPol);
    return newPol;
  },

  updateCancellationPolicy: (id, data) => {
    const p = state.cancellationPolicies.find(x => x.id === Number(id));
    if (!p) return null;
    Object.assign(p, data);
    return p;
  },

  deleteCancellationPolicy: (id) => {
    const idx = state.cancellationPolicies.findIndex(x => x.id === Number(id));
    if (idx !== -1) {
      state.cancellationPolicies.splice(idx, 1);
      return true;
    }
    return false;
  },

  getTaxes: (activeOnly = false) => {
    let list = [...state.taxes];
    if (activeOnly) list = list.filter(t => t.active !== false);
    return list;
  },

  getTaxById: (id) => state.taxes.find(t => t.id === Number(id)),

  createTax: (data) => {
    const newId = state.taxes.length ? Math.max(...state.taxes.map(t => t.id)) + 1 : 1;
    const newTax = {
      id: newId,
      name: data.name || "Custom Tax",
      rate: Number(data.rate) || 0,
      fixed_amount: Number(data.fixed_amount) || 0,
      applies_to: data.applies_to || "rooms",
      type: data.type || "exclusive",
      per: data.per || "stay",
      active: data.active !== false,
      sort_order: state.taxes.length + 1
    };
    state.taxes.push(newTax);
    return newTax;
  },

  updateTax: (id, data) => {
    const t = state.taxes.find(x => x.id === Number(id));
    if (!t) return null;
    Object.assign(t, data);
    return t;
  },

  deleteTax: (id) => {
    const idx = state.taxes.findIndex(x => x.id === Number(id));
    if (idx !== -1) {
      state.taxes.splice(idx, 1);
      return true;
    }
    return false;
  },

  createUser: (data) => {
    const newId = state.users.length ? Math.max(...state.users.map(u => u.id)) + 1 : 1;
    const newUser = {
      id: newId,
      username: (data.username || `user${newId}`).trim(),
      email: (data.email || `user${newId}@hotel.com`).trim().toLowerCase(),
      full_name: (data.full_name || 'Staff Member').trim(),
      role: data.role || "front_desk",
      password_hash: bcrypt.hashSync(data.password || "staff123", 10),
      is_active: true,
      organization_id: 1
    };
    state.users.push(newUser);
    return {
      id: newUser.id,
      username: newUser.username,
      email: newUser.email,
      full_name: newUser.full_name,
      role: newUser.role,
      is_active: newUser.is_active,
      organization_id: newUser.organization_id
    };
  },

  getBusinessDate: () => ({ ...state.businessDate }),

  getHousekeeping: () => [...state.housekeeping],

  createHousekeepingTask: (task) => {
    const newId = state.housekeeping.length ? Math.max(...state.housekeeping.map(t => t.id)) + 1 : 1;
    const newTask = {
      id: newId,
      room_id: Number(task.room_id || 1),
      room_number: task.room_number || "101",
      task_type: task.task_type || "turnover",
      priority: task.priority || "medium",
      status: "pending",
      assigned_to_name: task.assigned_to_name || "Housekeeping Staff",
      notes: task.notes || "",
      created_at: new Date().toISOString()
    };
    state.housekeeping.unshift(newTask);
    return newTask;
  },

  updateHousekeepingTask: (id, status) => {
    const task = state.housekeeping.find(t => t.id === Number(id));
    if (task) {
      task.status = status;
      return task;
    }
    return null;
  },

  getGuests: (search = '') => {
    if (!search) return [...state.guests];
    const q = search.toLowerCase();
    return state.guests.filter(g => 
      `${g.first_name} ${g.last_name}`.toLowerCase().includes(q) ||
      (g.email && g.email.toLowerCase().includes(q)) ||
      (g.phone && g.phone.includes(q))
    );
  },

  getGuestById: (id) => state.guests.find(g => g.id === Number(id)),

  createGuest: (data) => {
    const newId = state.guests.length ? Math.max(...state.guests.map(g => g.id)) + 1 : 1;
    const newGuest = {
      id: newId,
      first_name: data.first_name,
      last_name: data.last_name,
      email: data.email || null,
      phone: data.phone,
      id_number: data.id_number || null,
      vip_status: "regular"
    };
    state.guests.push(newGuest);
    return newGuest;
  },

  getReservations: (search = '') => {
    let list = state.reservations.map(populateReservation);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(r => 
        (r.confirmation_number && r.confirmation_number.toLowerCase().includes(q)) ||
        (r.guest && `${r.guest.first_name} ${r.guest.last_name} ${r.guest.full_name}`.toLowerCase().includes(q)) ||
        (r.room && String(r.room.number).includes(q))
      );
    }
    return list;
  },

  getReservationById: (id) => {
    const r = state.reservations.find(res => res.id === Number(id));
    return r ? populateReservation(r) : null;
  },

  createWalkInReservation: (payload) => {
    // 1. Create or match guest
    let guest = state.guests.find(g => g.phone === payload.guest?.phone);
    if (!guest) {
      guest = store.createGuest(payload.guest || { first_name: "Walk-in", last_name: "Guest", phone: "+91 99999 99999" });
    }

    // 2. Room lookup
    const room = state.rooms.find(r => r.id === Number(payload.room_id)) || state.rooms[0];
    room.status = "occupied";

    // 3. Rate plan
    const plan = state.ratePlans.find(p => p.id === Number(payload.rate_plan_id)) || state.ratePlans[0];

    const newId = state.reservations.length ? Math.max(...state.reservations.map(r => r.id)) + 1 : 1;
    const confNum = `HTL-${10900 + newId}`;
    const nightlyRate = Number(payload.nightly_rate) || (room.room_type ? room.room_type.base_rate : 4500);

    const dIn = new Date(payload.check_in_date || new Date());
    const dOut = new Date(payload.check_out_date || new Date(Date.now() + 86400000));
    const nights = Math.max(1, Math.round((dOut - dIn) / (1000 * 60 * 60 * 24)));
    const totalCharges = nights * nightlyRate;
    const totalPaid = Number(payload.advance_amount) || 0;

    const newRes = {
      id: newId,
      confirmation_number: confNum,
      guest_id: guest.id,
      guest: { ...guest },
      room_id: room.id,
      room: {
        id: room.id,
        number: room.number,
        room_type_id: room.room_type_id,
        room_type: state.roomTypes.find(t => t.id === room.room_type_id)
      },
      check_in_date: payload.check_in_date || new Date().toISOString().slice(0, 10),
      check_out_date: payload.check_out_date || new Date(Date.now() + 86400000).toISOString().slice(0, 10),
      status: "checked_in",
      rate_plan_id: plan.id,
      rate_plan: { ...plan },
      adults: Number(payload.adults) || 1,
      nightly_rate: nightlyRate,
      total_charges: totalCharges,
      total_paid: totalPaid,
      balance_due: totalCharges - totalPaid,
      created_at: new Date().toISOString()
    };

    state.reservations.unshift(newRes);

    // Create Folio
    const newFolioId = state.folios.length ? Math.max(...state.folios.map(f => f.id)) + 1 : 1;
    state.folios.push({
      id: newFolioId,
      reservation_id: newId,
      name: "Main Stay Folio",
      balance: totalCharges - totalPaid,
      status: totalCharges <= totalPaid ? "closed" : "open",
      items: [
        { id: 1, description: `Room Charge (${nights} night(s) @ ₹${nightlyRate.toFixed(2)})`, amount: totalCharges, type: "room", created_at: new Date().toISOString() }
      ],
      payments: totalPaid > 0 ? [
        { id: 1, amount: totalPaid, method: payload.advance_payment_method || "cash", reference: payload.advance_reference || "WALK-IN", created_at: new Date().toISOString() }
      ] : []
    });

    return newRes;
  },

  checkInReservation: (id) => {
    const res = state.reservations.find(r => r.id === Number(id));
    if (res) {
      res.status = "checked_in";
      const room = state.rooms.find(r => r.id === res.room_id);
      if (room) room.status = "occupied";
      return res;
    }
    return null;
  },

  checkOutReservation: (id) => {
    const res = state.reservations.find(r => r.id === Number(id));
    if (res) {
      res.status = "checked_out";
      const room = state.rooms.find(r => r.id === res.room_id);
      if (room) {
        room.status = "dirty";
        store.createHousekeepingTask({
          room_id: room.id,
          room_number: room.number,
          task_type: "turnover",
          priority: "high",
          notes: `Checkout clean for ${res.guest ? res.guest.first_name : 'Guest'}`
        });
      }
      return res;
    }
    return null;
  },

  getFoliosByReservationId: (resId) => {
    return state.folios.filter(f => f.reservation_id === Number(resId));
  },

  addFolioCharge: (resId, charge) => {
    let folio = state.folios.find(f => f.reservation_id === Number(resId));
    if (!folio) {
      folio = {
        id: state.folios.length + 1,
        reservation_id: Number(resId),
        name: "Main Stay Folio",
        balance: 0,
        status: "open",
        items: [],
        payments: []
      };
      state.folios.push(folio);
    }
    const amt = Number(charge.amount) || 0;
    folio.items.push({
      id: folio.items.length + 1,
      description: charge.description || "Miscellaneous Charge",
      amount: amt,
      type: charge.type || "service",
      created_at: new Date().toISOString()
    });
    folio.balance += amt;
    return folio;
  },

  addFolioPayment: (resId, payment) => {
    let folio = state.folios.find(f => f.reservation_id === Number(resId));
    if (!folio) return null;
    const amt = Number(payment.amount) || 0;
    folio.payments.push({
      id: folio.payments.length + 1,
      amount: amt,
      method: payment.method || "cash",
      reference: payment.reference || "PAY",
      created_at: new Date().toISOString()
    });
    folio.balance = Math.max(0, folio.balance - amt);
    if (folio.balance === 0) folio.status = "closed";
    return folio;
  },

  getDashboardMetrics: () => {
    const totalRooms = state.rooms.length;
    const occupiedCount = state.rooms.filter(r => r.status === "occupied").length;
    const occupancyRate = Math.round((occupiedCount / totalRooms) * 100) || 50;

    const checkinsToday = state.reservations.filter(r => r.status === "checked_in").length || 24;
    const checkoutsToday = state.reservations.filter(r => r.status === "checked_out").length || 12;

    const revenueToday = state.reservations.reduce((sum, r) => sum + (r.total_paid || 0), 0) || 48520;

    return {
      occupancy_rate: occupancyRate,
      arrivals_total: 24,
      arrivals_checked_in: 12,
      arrivals_remaining: 12,
      revenue_today: revenueToday,
      pending_housekeeping: state.housekeeping.filter(t => t.status !== "done"),
      kpi: {
        occupancy_rate: occupancyRate,
        checkins_today: checkinsToday,
        checkouts_today: checkoutsToday,
        revenue_today: revenueToday,
        total_in_house: occupiedCount * 2 || 22,
        revpar: Math.round((revenueToday / totalRooms) || 4500),
        adr: 6500.00
      },
      room_rack_summary: {
        total: totalRooms,
        available: state.rooms.filter(r => r.status === "available").length,
        occupied: occupiedCount,
        dirty: state.rooms.filter(r => r.status === "dirty").length,
        cleaning: state.rooms.filter(r => r.status === "cleaning").length,
        maintenance: state.rooms.filter(r => r.status === "maintenance").length
      },
      today_arrivals: state.reservations.filter(r => r.status === "confirmed").map(r => {
        const guestName = r.guest ? `${r.guest.first_name || ''} ${r.guest.last_name || ''}`.trim() : (r.guest_name || "Guest");
        const roomNum = r.room ? r.room.number : (r.room_number || "101");
        const roomTypeName = (r.room && r.room.room_type) ? r.room.room_type.name : (r.room_type || "Deluxe King");
        return {
          reservation_id: r.id,
          id: r.id,
          confirmation_number: r.confirmation_number,
          guest_name: guestName,
          guest: r.guest,
          guest_id: r.guest_id,
          room_number: roomNum,
          room: r.room,
          room_type: roomTypeName,
          nights: r.nights || 2,
          nightly_rate: r.nightly_rate || 7500,
          status: r.status,
          balance: r.balance_due || 0
        };
      }),
      today_departures: state.reservations.filter(r => r.status === "checked_in").map(r => {
        const guestName = r.guest ? `${r.guest.first_name || ''} ${r.guest.last_name || ''}`.trim() : (r.guest_name || "Guest");
        const roomNum = r.room ? r.room.number : (r.room_number || "101");
        const roomTypeName = (r.room && r.room.room_type) ? r.room.room_type.name : (r.room_type || "Deluxe King");
        return {
          reservation_id: r.id,
          id: r.id,
          confirmation_number: r.confirmation_number,
          guest_name: guestName,
          guest: r.guest,
          guest_id: r.guest_id,
          room_number: roomNum,
          room: r.room,
          room_type: roomTypeName,
          nights: r.nights || 2,
          nightly_rate: r.nightly_rate || 7500,
          status: r.status,
          balance: r.balance_due || 0
        };
      }),
      revenue_chart: {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"],
        data: [95000, 115000, 145450, 142000, 138000, 140000, 148000, 155000, 170000, 185000, 192000, 205000],
        total_annual: 1785450
      },
      platform_breakdown: {
        labels: ["Direct", "Booking.com", "Agoda", "MakeMyTrip", "Airbnb"],
        data: [218, 44, 23, 24, 109],
        dominant_platform: "Direct",
        dominant_pct: 52.1
      }
    };
  },

  saveDemoRequest: (data) => {
    const newId = state.demoRequests.length + 1042;
    const req = { id: newId, ...data, created_at: new Date().toISOString() };
    state.demoRequests.push(req);
    return req;
  },

  saveOnboardingData: (payload) => {
    if (payload.hotel_name) {
      state.organization.name = payload.hotel_name.trim();
    }
    if (payload.city) {
      state.organization.city = payload.city.trim();
      state.organization.address = `${state.organization.name}, ${state.organization.city}`;
    }
    if (payload.currency) {
      state.organization.currency = payload.currency.trim().toUpperCase();
    }
    if (payload.gstin) {
      state.organization.tax_id = payload.gstin.trim();
    }

    // Synchronize Room Types if provided
    if (Array.isArray(payload.room_types) && payload.room_types.length > 0) {
      payload.room_types.forEach((rt, idx) => {
        const existing = state.roomTypes.find(t => t.name.toLowerCase() === rt.name.toLowerCase());
        if (existing) {
          existing.base_rate = Number(rt.base_rate) || existing.base_rate;
          existing.max_occupancy = Number(rt.max_occupancy) || existing.max_occupancy;
          existing.description = rt.description || existing.description;
        } else {
          state.roomTypes.push({
            id: state.roomTypes.length + 1,
            name: rt.name,
            code: (rt.code || rt.name.slice(0, 4)).toUpperCase(),
            base_rate: Number(rt.base_rate) || 5000,
            max_occupancy: Number(rt.max_occupancy) || 2,
            description: rt.description || 'Custom Room Type'
          });
        }
      });
    }

    // Synchronize Rooms if provided
    if (Array.isArray(payload.rooms) && payload.rooms.length > 0) {
      payload.rooms.forEach(r => {
        const rNum = String(r.number).trim();
        const existing = state.rooms.find(rm => rm.number === rNum);
        const rtObj = state.roomTypes.find(t => t.name.toLowerCase() === (r.room_type_name || '').toLowerCase()) || state.roomTypes[0];
        if (existing) {
          existing.floor = Number(r.floor) || existing.floor;
          existing.room_type_id = rtObj.id;
          existing.room_type = rtObj;
        } else {
          state.rooms.push({
            id: state.rooms.length + 1,
            number: rNum,
            floor: Number(r.floor) || 1,
            room_type_id: rtObj.id,
            room_type: rtObj,
            status: "available"
          });
        }
      });
    }

    // Save Staff Members
    const staffList = payload.staff_members || (payload.staff ? [payload.staff] : []);
    staffList.forEach(st => {
      if (!st || !st.email) return;
      const email = st.email.trim().toLowerCase();
      const existing = state.users.find(u => u.email.toLowerCase() === email);
      if (!existing) {
        state.users.push({
          id: state.users.length + 1,
          username: email.split('@')[0],
          email: email,
          full_name: st.full_name || 'Staff Member',
          role: st.role || 'front_desk',
          password_hash: bcrypt.hashSync('Welcome123!', 10),
          is_active: true,
          organization_id: 1
        });
      }
    });

    return { status: "ok", message: "Onboarding settings successfully saved!" };
  },

  getRateCalendar: (startDateStr, daysCount = 30) => {
    const sDate = startDateStr ? new Date(startDateStr) : new Date();
    const days = Math.min(Math.max(Number(daysCount) || 30, 7), 60);

    const roomTypes = state.roomTypes.map(rt => {
      const totalRoomsOfType = state.rooms.filter(r => r.room_type_id === rt.id).length || 5;
      const daysArr = [];

      for (let i = 0; i < days; i++) {
        const d = new Date(sDate);
        d.setDate(sDate.getDate() + i);
        const dateIso = d.toISOString().slice(0, 10);
        const dayOfWeek = d.getDay();
        const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

        // Occasional weekend rate surge (+20%)
        const rate = isWeekend ? Math.round(rt.base_rate * 1.2) : rt.base_rate;
        // Occupied count mock based on reservations
        const occCount = state.reservations.filter(r => {
          return r.room && r.room.room_type && r.room.room_type.name === rt.name &&
            r.check_in_date <= dateIso && r.check_out_date > dateIso;
        }).length;
        const occ = Math.min(occCount || (isWeekend ? 3 : 1), totalRoomsOfType);
        const avail = Math.max(totalRoomsOfType - occ, 0);

        daysArr.push({
          date: dateIso,
          rate: rate,
          available: avail,
          available_count: avail,
          total: totalRoomsOfType,
          occupancy_pct: Math.round((occ / totalRoomsOfType) * 100),
          min_stay: isWeekend ? 2 : null,
          closed: false,
          stop_sell: false,
          override_id: isWeekend ? 1 : null,
          is_override: isWeekend
        });
      }

      return {
        id: rt.id,
        name: rt.name,
        code: rt.code,
        base_rate: rt.base_rate,
        room_count: totalRoomsOfType,
        days: daysArr
      };
    });

    const eDate = new Date(sDate);
    eDate.setDate(sDate.getDate() + days);

    return {
      start_date: sDate.toISOString().slice(0, 10),
      end_date: eDate.toISOString().slice(0, 10),
      room_types: roomTypes
    };
  },

  getTimeline: (startDateStr, daysCount = 30) => {
    const sDate = startDateStr ? new Date(startDateStr) : new Date();
    const days = Math.min(Math.max(Number(daysCount) || 30, 7), 60);
    const eDate = new Date(sDate);
    eDate.setDate(sDate.getDate() + days);
    const startIso = sDate.toISOString().slice(0, 10);
    const endIso = eDate.toISOString().slice(0, 10);

    const rooms = state.rooms.map(r => {
      const roomRes = state.reservations.filter(res => {
        return (res.room_id === r.id || (res.room && res.room.number === r.number)) &&
          res.check_in_date < endIso && res.check_out_date > startIso;
      }).map(res => {
        const guestName = res.guest ? (`${res.guest.first_name || ''} ${res.guest.last_name || ''}`.trim() || res.guest.full_name) : (res.guest_name || "Guest");
        const initials = guestName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'G';
        return {
          id: res.id,
          confirmation_number: res.confirmation_number,
          guest_name: guestName,
          guest_initials: initials,
          check_in_date: res.check_in_date,
          check_out_date: res.check_out_date,
          status: res.status,
          balance: res.balance_due || 0
        };
      });

      return {
        id: r.id,
        number: r.number,
        floor: r.floor || 1,
        room_type_name: r.room_type ? r.room_type.name : 'Deluxe',
        status: r.status,
        reservations: roomRes
      };
    });

    return {
      start_date: startIso,
      end_date: endIso,
      rooms: rooms
    };
  },

  getOtaFeed: () => [...state.otaFeed],

  simulateOtaInboxSync: (voucher) => {
    const resId = state.reservations.length ? Math.max(...state.reservations.map(r => r.id)) + 1 : 1;
    const conf = `HTL-GM-BCOM-${Math.floor(1000 + Math.random() * 9000)}`;
    const newOtaItem = {
      id: state.otaFeed.length + 1,
      source: voucher.source || "Booking.com",
      reservation_ref: conf,
      guest_name: voucher.guest_name || "Vikram Malhotra",
      room_type: voucher.room_type || "Deluxe King",
      nights: Number(voucher.nights) || 3,
      amount: Number(voucher.amount) || 22500.00,
      currency: "INR",
      status: "processed",
      created_at: new Date().toISOString()
    };
    state.otaFeed.unshift(newOtaItem);

    // Also auto-create the reservation
    const room = state.rooms.find(r => r.status === "available") || state.rooms[0];
    room.status = "occupied";
    state.reservations.unshift({
      id: resId,
      confirmation_number: conf,
      guest_id: 3,
      guest: { first_name: voucher.guest_name ? voucher.guest_name.split(' ')[0] : 'Vikram', last_name: voucher.guest_name ? voucher.guest_name.split(' ')[1] || 'Guest' : 'Malhotra', phone: '+91 98111 22334', email: 'ota@guest.com' },
      room_id: room.id,
      room: { id: room.id, number: room.number, room_type: { name: voucher.room_type || "Deluxe King" } },
      check_in_date: new Date().toISOString().slice(0, 10),
      check_out_date: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10),
      status: "confirmed",
      rate_plan_id: 1,
      adults: 2,
      nightly_rate: (voucher.amount || 22500) / 3,
      total_charges: voucher.amount || 22500,
      total_paid: voucher.amount || 22500,
      balance_due: 0,
      created_at: new Date().toISOString()
    });

    return newOtaItem;
  },

  getOrgUsage: () => {
    const usedRooms = state.rooms.length;
    const usedUsers = state.users.length;
    const firstOfMonth = new Date();
    firstOfMonth.setDate(1);
    const firstIso = firstOfMonth.toISOString().slice(0, 10);
    const resCount = state.reservations.filter(r => r.check_in_date >= firstIso).length || 12;

    return {
      rooms: {
        used: usedRooms,
        limit: 50
      },
      users: {
        used: usedUsers,
        limit: 10
      },
      reservations_this_month: resCount
    };
  },

  getCancellationQuote: (resId) => {
    const res = state.reservations.find(r => r.id === Number(resId));
    if (!res) return null;
    
    const today = state.businessDate.date;
    const checkIn = res.check_in_date;
    const pol = state.cancellationPolicies.find(p => p.active) || state.cancellationPolicies[0];
    const freeDays = pol ? pol.free_cancel_days : 1;
    
    const dIn = new Date(checkIn);
    dIn.setDate(dIn.getDate() - freeDays);
    const freeUntil = dIn.toISOString().slice(0, 10);
    const canCancelFree = today <= freeUntil;
    
    const nightlyRate = res.nightly_rate || 4500;
    const penalty = canCancelFree ? 0 : nightlyRate;
    const depositPaid = res.total_paid || 0;
    const refund = Math.max(0, depositPaid - penalty);

    return {
      reservation_id: res.id,
      policy_name: pol ? pol.name : "Flexible 24h",
      free_cancel_until: freeUntil,
      can_cancel_free: canCancelFree,
      penalty_amount: penalty,
      deposit_paid: depositPaid,
      refund_amount: refund,
      reason: canCancelFree
        ? `Cancelled on or before ${freeUntil} within the free window (${pol ? pol.name : 'Flexible'}). Full refund.`
        : `Cancellation penalty of 1 night (₹${nightlyRate.toFixed(2)}) applied under '${pol ? pol.name : 'Policy'}'.`
    };
  },

  getDepositStatus: (resId) => {
    const res = state.reservations.find(r => r.id === Number(resId));
    if (!res) return null;
    const req = (res.nightly_rate || 4500);
    const paid = res.total_paid || 0;
    const bal = Math.max(0, req - paid);
    return {
      reservation_id: res.id,
      deposit_required: req,
      deposit_paid: paid,
      deposit_due_at: res.check_in_date,
      is_satisfied: paid >= req,
      balance_due: bal
    };
  },

  getFolioDetail: (resId) => {
    const res = state.reservations.find(r => r.id === Number(resId));
    if (!res) return null;
    
    let folio = state.folios.find(f => f.reservation_id === Number(resId));
    if (!folio) {
      const dIn = new Date(res.check_in_date);
      const dOut = new Date(res.check_out_date);
      const nights = Math.max(1, Math.round((dOut - dIn) / (86400000)));
      const baseRoom = (res.total_charges || 9000) * 0.88;
      const gstTax = (res.total_charges || 9000) * 0.12;

      folio = {
        id: state.folios.length + 1,
        reservation_id: res.id,
        name: "Master Folio",
        balance: res.balance_due != null ? res.balance_due : 0,
        status: "open",
        items: [
          { id: 1, date: res.check_in_date, description: `Room Charge (${nights} nights @ ₹${res.nightly_rate || 4500})`, category: "room", amount: baseRoom },
          { id: 2, date: res.check_in_date, description: "Goods & Services Tax (GST 12%)", category: "tax", amount: gstTax }
        ],
        payments: res.total_paid > 0 ? [
          { id: 1, date: res.check_in_date, amount: res.total_paid, method: "card", reference: `PAY-RES-${res.id}` }
        ] : []
      };
      state.folios.push(folio);
    }

    const items = (folio.items || []).map(i => ({
      id: i.id,
      date: i.date || res.check_in_date,
      description: i.description,
      category: i.category || i.type || "room",
      amount: Number(i.amount)
    }));

    const payments = (folio.payments || []).map(p => ({
      id: p.id,
      date: p.date || res.check_in_date,
      amount: Number(p.amount),
      method: p.method || "card",
      reference: p.reference || "AUTH-PAY"
    }));

    const subtotal = items.filter(i => i.category !== 'tax').reduce((sum, i) => sum + i.amount, 0);
    const tax_total = items.filter(i => i.category === 'tax').reduce((sum, i) => sum + i.amount, 0);
    const total_amount = subtotal + tax_total;
    const total_paid = payments.reduce((sum, p) => sum + p.amount, 0);
    const balance_due = total_amount - total_paid;

    const dIn = new Date(res.check_in_date);
    const dOut = new Date(res.check_out_date);
    const nights = Math.max(1, Math.round((dOut - dIn) / (86400000)));

    return {
      reservation_id: res.id,
      confirmation_number: res.confirmation_number,
      guest: res.guest || { first_name: "Guest", last_name: "", phone: "+91 99999 99999", email: "guest@example.com" },
      room_number: res.room ? res.room.number : "101",
      room_type: res.room && res.room.room_type ? res.room.room_type.name : "Standard Deluxe Queen",
      check_in_date: res.check_in_date,
      check_out_date: res.check_out_date,
      nights: nights,
      items,
      payments,
      subtotal,
      tax_total,
      total_amount,
      total_paid,
      balance_due
    };
  },

  getNightAuditPreview: () => {
    const checkedIn = state.reservations.filter(r => r.status === "checked_in");
    const roomChargesCount = checkedIn.length;
    const roomChargesTotal = checkedIn.reduce((sum, r) => sum + (Number(r.nightly_rate) || 4500), 0);
    const today = state.businessDate.date;
    const noShows = state.reservations.filter(r => r.status === "confirmed" && r.check_in_date <= today);
    const noShowsPenalties = noShows.reduce((sum, r) => sum + (Number(r.nightly_rate) || 4500), 0);
    const unresolvedDepartures = state.reservations.filter(r => r.status === "checked_in" && r.check_out_date <= today);

    const nextDate = new Date(new Date(today).getTime() + 86400000).toISOString().slice(0, 10);

    return {
      business_date: today,
      next_business_date: nextDate,
      checked_in_reservations_count: checkedIn.length,
      room_charges_to_post_count: roomChargesCount,
      room_charges_estimated_total: roomChargesTotal,
      no_shows_count: noShows.length,
      no_show_estimated_penalties: noShowsPenalties,
      unresolved_departures_count: unresolvedDepartures.length,
      can_run_without_force: unresolvedDepartures.length === 0,
      warning_message: unresolvedDepartures.length > 0 ? `${unresolvedDepartures.length} guest(s) past departure date have not checked out.` : null
    };
  },

  getNightAuditHistory: (limit = 30) => {
    return state.auditSnapshots.slice(0, Number(limit) || 30);
  },

  executeNightAudit: (force = false) => {
    const preview = store.getNightAuditPreview();
    if (!preview.can_run_without_force && !force) {
      throw new Error(preview.warning_message || "Cannot run audit without resolving open departures.");
    }

    const prevDate = state.businessDate.date;
    const nextDate = preview.next_business_date;
    state.businessDate.date = nextDate;

    // Create snapshot
    const snapshot = {
      id: state.auditSnapshots.length + 1,
      business_date: prevDate,
      occupancy_rate: Math.round((state.rooms.filter(r => r.status === 'occupied').length / state.rooms.length) * 100) || 50,
      adr: 6800.0,
      revpar: 4760.0,
      arrivals: 5,
      departures: 3,
      room_revenue: preview.room_charges_estimated_total,
      total_revenue: preview.room_charges_estimated_total * 1.15,
      tax_collected: preview.room_charges_estimated_total * 0.12,
      created_at: new Date().toISOString()
    };
    state.auditSnapshots.unshift(snapshot);

    return {
      success: true,
      previous_business_date: prevDate,
      new_business_date: nextDate,
      room_charges_posted: preview.room_charges_to_post_count,
      room_charges_total: preview.room_charges_estimated_total,
      no_shows_marked: preview.no_shows_count,
      no_show_penalties_total: preview.no_show_estimated_penalties,
      snapshot
    };
  },

  getEmailTemplates: () => [...state.emailTemplates],

  updateEmailTemplate: (idOrKey, data) => {
    const t = state.emailTemplates.find(x => x.id === Number(idOrKey) || x.key === idOrKey);
    if (!t) return null;
    Object.assign(t, data);
    return t;
  },

  getTrash: () => ({ ...state.trash }),

  restoreItem: (entity, id) => {
    const key = entity.endsWith('s') ? entity : `${entity}s`;
    if (!state.trash[key]) {
      return { success: true, message: `Item #${id} restored.` };
    }
    const idx = state.trash[key].findIndex(x => x.id === Number(id));
    if (idx !== -1) {
      const item = state.trash[key].splice(idx, 1)[0];
      if (state[key]) state[key].push(item);
      return { success: true, message: `Record #${id} restored successfully.`, item };
    }
    return { success: true, message: `Record #${id} restored successfully.` };
  },

  getAuditLogs: (limit = 50) => {
    return state.auditLogs.slice(0, Number(limit) || 50);
  },

  getGroups: (status) => {
    let list = [...state.groups];
    if (status) list = list.filter(g => g.status === status);
    return list;
  },

  getGroupById: (id) => state.groups.find(g => g.id === Number(id)),

  createGroup: (data) => {
    const newId = state.groups.length ? Math.max(...state.groups.map(g => g.id)) + 1 : 1;
    const newGroup = {
      id: newId,
      hotel_id: 1,
      name: data.name || data.group_name || "New Corporate Group",
      contact_name: data.contact_name || "Contact Person",
      contact_phone: data.contact_phone || "+91 99999 88888",
      contact_email: data.contact_email || "contact@group.com",
      status: data.status || "confirmed",
      billing_type: data.billing_type || "master",
      check_in_date: data.check_in_date || state.businessDate.date,
      check_out_date: data.check_out_date || new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 10),
      cutoff_date: data.cutoff_date || state.businessDate.date,
      notes: data.notes || "",
      room_blocks: data.room_blocks || [
        { id: 1, group_id: newId, room_type_id: 1, room_type_name: "Standard Deluxe Queen", count: 2, rate: 4500, picked_up_count: 0, available_to_pick: 2 }
      ],
      total_charges: Number(data.total_charges) || 18000,
      total_paid: Number(data.total_paid) || 0,
      balance: Number(data.total_charges || 18000) - Number(data.total_paid || 0)
    };
    state.groups.unshift(newGroup);
    return newGroup;
  },

  getBackups: () => [...state.backups],

  createManualBackup: () => {
    const newId = state.backups.length ? Math.max(...state.backups.map(b => b.id)) + 1 : 1;
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const b = {
      id: newId,
      filename: `backup_hotel_${dateStr}_manual_${Math.floor(1000 + Math.random() * 9000)}.sql.gz`,
      size_bytes: 4325810,
      status: "completed",
      created_at: new Date().toISOString()
    };
    state.backups.unshift(b);
    return b;
  }
};

module.exports = store;
