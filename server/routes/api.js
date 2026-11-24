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

router.get('/night-audit/preview', (req, res) => {
  return res.json(store.getNightAuditPreview());
});

router.get('/night-audit/history', (req, res) => {
  return res.json(store.getNightAuditHistory(req.query.limit));
});

router.post('/night-audit/run', (req, res) => {
  try {
    const result = store.executeNightAudit(req.body?.force === true);
    return res.json(result);
  } catch (e) {
    return res.status(400).json({ detail: e.message });
  }
});

router.post('/night-audit/execute', (req, res) => {
  return res.json({
    status: "success",
    message: "Night audit executed successfully. Business date rolled.",
    next_date: new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  });
});

// ── 3. Rooms & Room Types ────────────────────────────────────────────────────
router.get('/rooms/types', (req, res) => {
  return res.json(store.getRoomTypes());
});

router.get('/rooms', (req, res) => {
  const { floor, status } = req.query;
  const items = store.getRooms({ floor, status });
  return res.json({ items, total: items.length });
});

router.get('/rooms/:id', (req, res) => {
  const room = store.getRoomById(req.params.id);
  if (!room) return res.status(404).json({ detail: 'Room not found' });
  return res.json(room);
});

router.post('/rooms', (req, res) => {
  const room = store.addRoom(req.body);
  return res.status(201).json(room);
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

router.get('/rate-calendar', (req, res) => {
  const { start_date, days } = req.query;
  const data = store.getRateCalendar(start_date, days);
  return res.json(data);
});

router.get('/timeline', (req, res) => {
  const { start_date, days } = req.query;
  const data = store.getTimeline(start_date, days);
  return res.json(data);
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

router.get('/reservations/:id/cancellation-quote', (req, res) => {
  const quote = store.getCancellationQuote(req.params.id);
  if (!quote) return res.status(404).json({ detail: 'Reservation not found' });
  return res.json(quote);
});

router.get('/reservations/:id/deposit-status', (req, res) => {
  const status = store.getDepositStatus(req.params.id);
  if (!status) return res.status(404).json({ detail: 'Reservation not found' });
  return res.json(status);
});

router.post('/reservations/:id/deposit', (req, res) => {
  const r = store.getReservationById(req.params.id);
  if (!r) return res.status(404).json({ detail: 'Reservation not found' });
  const amt = Number(req.body?.amount) || 0;
  r.total_paid = (r.total_paid || 0) + amt;
  r.balance_due = Math.max(0, (r.total_charges || 0) - r.total_paid);
  return res.json(r);
});

router.post('/reservations/:id/cancel', (req, res) => {
  const r = store.getReservationById(req.params.id);
  if (!r) return res.status(404).json({ detail: 'Reservation not found' });
  r.status = "cancelled";
  const room = store.getRooms().find(rm => rm.id === r.room_id);
  if (room && room.status === "occupied") room.status = "available";
  return res.json(r);
});

// ── 6. Folios & Billing ──────────────────────────────────────────────────────
router.get('/billing/reservations/:id/folio', (req, res) => {
  const folio = store.getFolioDetail(req.params.id);
  if (!folio) return res.status(404).json({ detail: 'Reservation not found' });
  return res.json(folio);
});

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

router.patch('/org', (req, res) => {
  const org = store.getOrganization();
  Object.assign(org, req.body);
  return res.json(org);
});

router.get('/org/usage', (req, res) => {
  return res.json(store.getOrgUsage());
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
  return res.json(store.getCancellationPolicies());
});

// ── Cancellation Policies CRUD ───────────────────────────────────────────────
router.get('/cancellation-policies', (req, res) => {
  const activeOnly = req.query.active_only === 'true';
  return res.json(store.getCancellationPolicies(activeOnly));
});

router.get('/cancellation-policies/:id', (req, res) => {
  const p = store.getCancellationPolicyById(req.params.id);
  if (!p) return res.status(404).json({ detail: 'Policy not found' });
  return res.json(p);
});

router.post('/cancellation-policies', (req, res) => {
  const p = store.createCancellationPolicy(req.body);
  return res.status(201).json(p);
});

router.put('/cancellation-policies/:id', (req, res) => {
  const p = store.updateCancellationPolicy(req.params.id, req.body);
  if (!p) return res.status(404).json({ detail: 'Policy not found' });
  return res.json(p);
});

router.delete('/cancellation-policies/:id', (req, res) => {
  const ok = store.deleteCancellationPolicy(req.params.id);
  if (!ok) return res.status(404).json({ detail: 'Policy not found' });
  return res.json({ success: true, message: 'Policy deleted' });
});

// ── Taxes Engine CRUD ────────────────────────────────────────────────────────
router.get('/taxes', (req, res) => {
  const activeOnly = req.query.active_only === 'true';
  return res.json(store.getTaxes(activeOnly));
});

router.get('/taxes/:id', (req, res) => {
  const t = store.getTaxById(req.params.id);
  if (!t) return res.status(404).json({ detail: 'Tax not found' });
  return res.json(t);
});

router.post('/taxes', (req, res) => {
  const t = store.createTax(req.body);
  return res.status(201).json(t);
});

router.put('/taxes/:id', (req, res) => {
  const t = store.updateTax(req.params.id, req.body);
  if (!t) return res.status(404).json({ detail: 'Tax not found' });
  return res.json(t);
});

router.delete('/taxes/:id', (req, res) => {
  const ok = store.deleteTax(req.params.id);
  if (!ok) return res.status(404).json({ detail: 'Tax not found' });
  return res.json({ success: true, message: 'Tax deleted' });
});

// ── Users & Team Management ─────────────────────────────────────────────────
router.get('/users', (req, res) => {
  return res.json(store.getUsers());
});

router.post('/users', (req, res) => {
  try {
    const user = store.createUser(req.body);
    return res.status(201).json(user);
  } catch (e) {
    return res.status(400).json({ detail: e.message });
  }
});

// ── Settings & Email Templates ───────────────────────────────────────────────
router.get('/settings/emails', (req, res) => {
  return res.json(store.getEmailTemplates());
});

router.put('/settings/emails/:id', (req, res) => {
  const t = store.updateEmailTemplate(req.params.id, req.body);
  if (!t) return res.status(404).json({ detail: 'Email template not found' });
  return res.json(t);
});

router.patch('/settings/emails/:id', (req, res) => {
  const t = store.updateEmailTemplate(req.params.id, req.body);
  if (!t) return res.status(404).json({ detail: 'Email template not found' });
  return res.json(t);
});

router.post('/settings/emails/:id/test', (req, res) => {
  return res.json({ success: true, message: 'Test email successfully sent.' });
});

// ── Backups & Export ─────────────────────────────────────────────────────────
router.get('/admin/backups', (req, res) => {
  return res.json(store.getBackups());
});

router.post('/admin/backups/manual', (req, res) => {
  const b = store.createManualBackup();
  return res.json({ success: true, message: 'Manual backup completed successfully', backup: b });
});

router.post('/admin/backups/run', (req, res) => {
  const b = store.createManualBackup();
  return res.json(b);
});

router.post('/admin/export', (req, res) => {
  return res.json({ success: true, message: 'Data export triggered', download_url: '/api/admin/backups' });
});

// ── Trash & Soft-Delete Restore ─────────────────────────────────────────────
router.get('/trash', (req, res) => {
  return res.json(store.getTrash());
});

router.post('/:entity/:id/restore', (req, res) => {
  const result = store.restoreItem(req.params.entity, req.params.id);
  return res.json(result);
});

router.post('/trash/:id/restore', (req, res) => {
  const result = store.restoreItem('reservations', req.params.id);
  return res.json(result);
});

// ── Audit Logs ──────────────────────────────────────────────────────────────
router.get('/audit-log', (req, res) => {
  return res.json(store.getAuditLogs(req.query.limit));
});

router.get('/audit-log/:id', (req, res) => {
  const log = store.getAuditLogs().find(l => l.id === Number(req.params.id));
  if (!log) return res.status(404).json({ detail: 'Audit log not found' });
  return res.json(log);
});

// ── Groups & Corporate Allocations ──────────────────────────────────────────
router.get('/groups', (req, res) => {
  return res.json(store.getGroups(req.query.status_filter));
});

router.get('/groups/:id', (req, res) => {
  const g = store.getGroupById(req.params.id);
  if (!g) return res.status(404).json({ detail: 'Group not found' });
  return res.json(g);
});

router.post('/groups', (req, res) => {
  const g = store.createGroup(req.body);
  return res.status(201).json(g);
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
