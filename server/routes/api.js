const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const store = require('../data/store');

const SECRET_KEY = process.env.SECRET_KEY || 'hotel-pms-super-secret-key-change-in-production-min-32-chars';

// Auth middleware
const auth = (req, res, next) => {
  let token = req.cookies?.access_token;
  if (!token && req.headers.authorization && req.headers.authorization.startsWith('Bearer ')) {
    token = req.headers.authorization.slice(7);
  }

  if (!token) {
    req.user = null;
    return next();
  }

  try {
    const decoded = jwt.verify(token, SECRET_KEY);
    req.user = store.findUserById(decoded.sub || decoded.id) || decoded;
  } catch (e) {
    req.user = null;
  }
  next();
};

router.use(auth);

// ── 1. Authentication ────────────────────────────────────────────────────────
router.post('/auth/login', async (req, res) => {
  const { username_or_email, password } = req.body;
  if (!username_or_email || !password) {
    return res.status(400).json({ detail: 'Username/Email and Password are required.' });
  }

  const user = store.findUserByIdent(username_or_email);
  if (!user) {
    return res.status(401).json({ detail: 'Invalid credentials provided.' });
  }

  // Compare bcrypt password
  const isValid = bcrypt.compareSync(password, user.password_hash);
  if (!isValid) {
    return res.status(401).json({ detail: 'Invalid credentials provided.' });
  }

  const token = jwt.sign(
    {
      sub: user.id,
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      organization_id: user.organization_id || 1,
    },
    SECRET_KEY,
    { expiresIn: '8h' }
  );

  res.cookie('access_token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 8 * 3600 * 1000,
  });

  const safeUser = {
    id: user.id,
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    organization_id: user.organization_id || 1,
  };

  return res.json({
    access_token: token,
    token_type: 'bearer',
    user: safeUser,
  });
});

router.post('/auth/logout', (req, res) => {
  res.clearCookie('access_token');
  return res.json({ message: 'Logged out successfully' });
});

router.get('/auth/me', (req, res) => {
  if (!req.user) {
    return res.status(401).json({ detail: 'Not authenticated' });
  }
  const user = store.findUserById(req.user.id || req.user.sub) || req.user;
  const org = store.getOrganization();
  return res.json({
    id: user.id,
    username: user.username,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    organization_id: user.organization_id || 1,
    organization: org,
  });
});

// ── 2. Dashboard & Overview ──────────────────────────────────────────────────
router.get('/dashboard', (req, res) => {
  const data = store.getDashboardMetrics();
  return res.json(data);
});

router.get('/night-audit/business-date', (req, res) => {
  return res.json(store.getBusinessDate());
});

router.get('/night-audit/status', (req, res) => {
  return res.json({
    business_date: store.getBusinessDate(),
    open_audits: [],
    system_status: "open"
  });
});

router.post('/night-audit/execute', (req, res) => {
  return res.json({
    status: "success",
    message: "Night audit executed successfully. Business date rolled.",
    next_date: new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  });
});

// ── 3. Rooms ─────────────────────────────────────────────────────────────────
router.get('/rooms', (req, res) => {
  const { floor, status } = req.query;
  const items = store.getRooms({ floor, status });
  return res.json({ items, total: items.length });
});

router.get('/rooms/:id', (req, res) => {
  const rooms = store.getRooms();
  const room = rooms.find(r => r.id === Number(req.params.id));
  if (!room) return res.status(404).json({ detail: 'Room not found' });
  return res.json(room);
});

router.patch('/rooms/:id/status', (req, res) => {
  const { status } = req.body;
  const updated = store.updateRoomStatus(req.params.id, status);
  if (!updated) return res.status(404).json({ detail: 'Room not found' });
  return res.json(updated);
});

// ── 4. Rate Plans & Quotes ───────────────────────────────────────────────────
router.get('/rate-plans', (req, res) => {
  return res.json(store.getRatePlans());
});

router.get('/rate-plans/quote', (req, res) => {
  const { check_in_date, check_out_date, adults, room_type_id } = req.query;
  const dIn = new Date(check_in_date || new Date());
  const dOut = new Date(check_out_date || new Date(Date.now() + 86400000));
  const nights = Math.max(1, Math.round((dOut - dIn) / (1000 * 60 * 60 * 24)));
  
  const rt = store.getRoomTypes().find(t => t.id === Number(room_type_id)) || store.getRoomTypes()[0];
  const nightly_rate = rt ? rt.base_rate : 4500;
  const subtotal = nights * nightly_rate;
  const tax_amount = Math.round(subtotal * 0.12);

  return res.json({
    nights,
    nightly_rate,
    subtotal,
    tax_amount,
    total: subtotal + tax_amount,
    currency: "INR"
  });
});

// ── 5. Reservations ──────────────────────────────────────────────────────────
router.get('/reservations', (req, res) => {
  const { search } = req.query;
  const items = store.getReservations(search);
  return res.json({ items, total: items.length });
});

router.get('/reservations/:id', (req, res) => {
  const r = store.getReservationById(req.params.id);
  if (!r) return res.status(404).json({ detail: 'Reservation not found' });
  return res.json(r);
});

router.post('/reservations/walk-in', (req, res) => {
  try {
    const created = store.createWalkInReservation(req.body);
    return res.status(201).json(created);
  } catch (e) {
    return res.status(400).json({ detail: e.message || 'Failed to process walk-in check-in' });
  }
});

router.post('/reservations/:id/check-in', (req, res) => {
  const r = store.checkInReservation(req.params.id);
  if (!r) return res.status(404).json({ detail: 'Reservation not found' });
  return res.json(r);
});

router.post('/reservations/:id/check-out', (req, res) => {
  const r = store.checkOutReservation(req.params.id);
  if (!r) return res.status(404).json({ detail: 'Reservation not found' });
  return res.json(r);
});

// ── 6. Folios & Billing ──────────────────────────────────────────────────────
router.get('/reservations/:id/folios', (req, res) => {
  const folios = store.getFoliosByReservationId(req.params.id);
  return res.json(folios);
});

router.post('/billing/reservations/:id/charges', (req, res) => {
  const folio = store.addFolioCharge(req.params.id, req.body);
  return res.json(folio);
});

router.post('/billing/reservations/:id/payments', (req, res) => {
  const folio = store.addFolioPayment(req.params.id, req.body);
  return res.json(folio);
});

router.get('/billing/status', (req, res) => {
  return res.json({
    status: "active",
    plan: "pro",
    trial_active: true,
    payment_method_configured: true
  });
});

router.post('/payments/create-intent', (req, res) => {
  return res.json({ client_secret: "mock_stripe_intent_success_token" });
});

router.post('/folio-items/bulk-move', (req, res) => {
  return res.json({ success: true, count: 1 });
});

router.post('/folios/:id/transfer', (req, res) => {
  return res.json({ success: true });
});

router.patch('/folios/:id', (req, res) => {
  return res.json({ success: true });
});

router.delete('/folios/:id', (req, res) => {
  return res.json({ success: true });
});

// ── 7. Housekeeping ──────────────────────────────────────────────────────────
router.get('/housekeeping', (req, res) => {
  return res.json(store.getHousekeeping());
});

router.post('/housekeeping', (req, res) => {
  const task = store.createHousekeepingTask(req.body);
  return res.status(201).json(task);
});

router.patch('/housekeeping/:id', (req, res) => {
  const { status } = req.body;
  const updated = store.updateHousekeepingTask(req.params.id, status);
  if (!updated) return res.status(404).json({ detail: 'Task not found' });
  return res.json(updated);
});

// ── 8. Guests ────────────────────────────────────────────────────────────────
router.get('/guests', (req, res) => {
  const { search } = req.query;
  const items = store.getGuests(search);
  return res.json({ items, total: items.length });
});

router.get('/guests/:id', (req, res) => {
  const g = store.getGuestById(req.params.id);
  if (!g) return res.status(404).json({ detail: 'Guest not found' });
  return res.json(g);
});

router.post('/guests', (req, res) => {
  const g = store.createGuest(req.body);
  return res.status(201).json(g);
});

// ── 9. Channel Sync & Integrations ───────────────────────────────────────────
router.get('/integrations/feed', (req, res) => {
  return res.json(store.getOtaFeed());
});

router.post('/integrations/inbox-sync', (req, res) => {
  const item = store.simulateOtaInboxSync(req.body);
  return res.json({
    status: "success",
    message: "Inbound email voucher processed and confirmed.",
    parsed_record: item
  });
});

// ── 10. Organization, Property & Policies ────────────────────────────────────
router.get('/org', (req, res) => {
  return res.json(store.getOrganization());
});

router.get('/property', (req, res) => {
  return res.json({
    organization: store.getOrganization(),
    rooms: store.getRooms(),
    room_types: store.getRoomTypes(),
    rate_plans: store.getRatePlans(),
    staff: store.getUsers()
  });
});

router.get('/policies', (req, res) => {
  return res.json([
    { id: 1, name: "Flexible (24h)", description: "Free cancellation up to 24h prior to arrival", active: true },
    { id: 2, name: "Moderate (3-Day)", description: "Free cancellation up to 3 days prior", active: true },
    { id: 3, name: "Strict Non-Refundable", description: "100% first night penalty applies immediately", active: true }
  ]);
});

router.post('/user/complete-tour', (req, res) => {
  return res.json({ success: true });
});

router.delete('/demo-data', (req, res) => {
  return res.json({ success: true, message: "Demo data reset" });
});

// ── 11. Demo Request ─────────────────────────────────────────────────────────
router.post('/demo-request', (req, res) => {
  const saved = store.saveDemoRequest(req.body);
  return res.json({
    status: "success",
    demo_id: saved.id,
    message: "Demo booked successfully"
  });
});

// ── 12. Onboarding Save & Config ─────────────────────────────────────────────
router.post('/onboarding/save', (req, res) => {
  try {
    const result = store.saveOnboardingData(req.body);
    return res.json(result);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
});

router.get('/onboarding/config', (req, res) => {
  return res.json({
    org: store.getOrg(),
    room_types: store.getRoomTypes(),
    rooms: store.getRooms(),
    rate_plans: store.getRatePlans(),
    taxes: store.getTaxes(),
    users: store.getUsers()
  });
});

module.exports = router;
