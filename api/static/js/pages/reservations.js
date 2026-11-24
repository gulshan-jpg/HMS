/**
 * CheckinOS - Reservations View, Detail Drawer, Rate Plan Quote, and Group Bookings
 * Comprehensive booking management, deposit tracking, cancellation penalty quoting, and group blocks.
 */

window.Pages = window.Pages || {};

window.Pages.Reservations = {
  activeViewTab: 'individual', // 'individual' | 'groups'
  currentFilter: 'all',
  selectedProperty: '',
  searchQuery: '',
  fromDate: '',
  toDate: '',

  async render(container) {
    this.currentFilter = 'all';
    this.selectedProperty = '';
    this.searchQuery = '';
    this.fromDate = '';
    this.toDate = '';

    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    container.innerHTML = `
      <div class="page-header" style="margin-bottom:16px;">
        <div>
          <h1 class="page-title">
            All Bookings
            <span id="res-total-badge" class="badge badge-neutral" style="font-size:12px; margin-left:8px; vertical-align:middle; font-weight:600;">Loading...</span>
          </h1>
          <div class="page-header-desc">
            ${isAdmin 
              ? 'Complete directory of all guest reservations, stay details, invoices, and payment statuses.' 
              : 'Guest arrivals, departures, in-house stays, and front desk check-in processing.'}
          </div>
        </div>
        <div class="toolbar-group">
          ${isAdmin ? `
            <button class="btn btn-primary btn-md" id="new-res-top-btn">
              ${UI.getIcon('plus', 16)} New Booking
            </button>
            <button class="btn btn-secondary btn-md" id="new-group-top-btn">
              ${UI.getIcon('plus', 16)} New Group Booking
            </button>
          ` : ''}
        </div>
      </div>

      <!-- View Switcher Tabs: Individual Bookings vs Group Bookings -->
      <div class="segmented-control" id="res-main-tabs" style="margin-bottom:16px; width:fit-content;">
        <button class="segmented-btn ${this.activeViewTab === 'individual' ? 'active' : ''}" data-tab="individual">All Bookings</button>
        <button class="segmented-btn ${this.activeViewTab === 'groups' ? 'active' : ''}" data-tab="groups">Group Bookings & Room Blocks</button>
      </div>

      <div id="res-view-container">
        <!-- Rendered based on activeViewTab -->
      </div>
    `;

    this.bindTopEvents(container);
    if (this.activeViewTab === 'individual') {
      await this.renderIndividualView();
    } else {
      await this.renderGroupsView();
    }
  },

  bindTopEvents(container) {
    container.querySelectorAll('#res-main-tabs .segmented-btn').forEach(btn => {
      btn.onclick = async () => {
        container.querySelectorAll('#res-main-tabs .segmented-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeViewTab = btn.getAttribute('data-tab');
        if (this.activeViewTab === 'individual') {
          await this.renderIndividualView();
        } else {
          await this.renderGroupsView();
        }
      };
    });

    const newResBtn = document.getElementById('new-res-top-btn');
    if (newResBtn) newResBtn.onclick = () => window.openNewReservationModal();

    const newGrpBtn = document.getElementById('new-group-top-btn');
    if (newGrpBtn) newGrpBtn.onclick = () => this.openNewGroupModal();
  },

  // ── INDIVIDUAL RESERVATIONS VIEW ──────────────────────────────────────────

  async renderIndividualView() {
    const container = document.getElementById('res-view-container');
    if (!container) return;

    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    container.innerHTML = `
      <!-- Toolbar: Segmented status, Date range, Search -->
      <div class="card" style="padding: 12px 16px; margin-bottom: 16px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
            <div class="segmented-control" id="res-status-segmented">
              <button class="segmented-btn ${this.currentFilter === 'all' ? 'active' : ''}" data-status="all">All</button>
              <button class="segmented-btn ${this.currentFilter === 'booked' ? 'active' : ''}" data-status="booked">Booked</button>
              <button class="segmented-btn ${this.currentFilter === 'checked_in' ? 'active' : ''}" data-status="checked_in">In-House</button>
              <button class="segmented-btn ${this.currentFilter === 'checked_out' ? 'active' : ''}" data-status="checked_out">Departed</button>
              <button class="segmented-btn ${this.currentFilter === 'cancelled' ? 'active' : ''}" data-status="cancelled">Cancelled</button>
            </div>

            <select id="res-property-select" class="form-select" style="height: 32px; font-size: 11.5px; border-radius: 6px; padding: 0 8px; border:1px solid #D1D5DB; background:#FFFFFF;">
              <option value="">All Properties (All Hotels)</option>
              <option value="1">The Grand Palace Bangalore</option>
              <option value="2">Hotel Grand</option>
              <option value="3">Hotel Grand P</option>
            </select>

            <div style="display: flex; align-items: center; gap: 6px;">
              <label style="font-size: 11px; font-weight: 500; color: #6B7280;">From:</label>
              <input type="date" id="res-from-date" class="form-input" style="width: 130px; height: 32px;" value="${this.fromDate}" />
              <label style="font-size: 11px; font-weight: 500; color: #6B7280;">To:</label>
              <input type="date" id="res-to-date" class="form-input" style="width: 130px; height: 32px;" value="${this.toDate}" />
            </div>
          </div>

          <div style="position: relative; width: 260px;">
            <input type="text" id="res-search-input" class="form-input" placeholder="Search guest, room, conf #..." value="${this.searchQuery}" style="padding-left: 32px; height: 32px;" />
            <div style="position: absolute; left: 9px; top: 7px; color: #9CA3AF;">
              ${UI.getIcon('search', 16)}
            </div>
          </div>
        </div>
      </div>

      <!-- Table Container -->
      <div class="card" style="padding:0; overflow:hidden; border:1px solid #E5E7EB;">
        <div class="table-responsive">
          <table class="data-table" style="font-size:12px;">
            <thead>
              <tr>
                <th>CONFIRMATION #</th>
                <th>GUEST</th>
                <th>ROOM</th>
                <th>CHECK-IN</th>
                <th>CHECK-OUT</th>
                <th>NIGHTS</th>
                <th class="text-right">TOTAL</th>
                <th class="text-right">${isAdmin ? 'BALANCE' : 'FOLIO'}</th>
                <th>STATUS</th>
                <th class="text-right" style="min-width: 155px;">ACTIONS</th>
              </tr>
            </thead>
            <tbody id="reservations-tbody">
              ${UI.skeletonTable(6, 10)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    this.bindFilterEvents(container);
    await this.fetchReservations();
  },

  bindFilterEvents(container) {
    container.querySelectorAll('#res-status-segmented .segmented-btn').forEach(btn => {
      btn.onclick = () => {
        container.querySelectorAll('#res-status-segmented .segmented-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentFilter = btn.getAttribute('data-status');
        this.fetchReservations();
      };
    });

    const fromInput = container.querySelector('#res-from-date');
    const toInput = container.querySelector('#res-to-date');

    const handleDateChange = () => {
      this.fromDate = fromInput.value;
      this.toDate = toInput.value;
      this.fetchReservations();
    };

    fromInput.onchange = handleDateChange;
    toInput.onchange = handleDateChange;

    const propSelect = container.querySelector('#res-property-select');
    if (propSelect) {
      propSelect.onchange = (e) => {
        this.selectedProperty = e.target.value;
        this.fetchReservations();
      };
    }

    const searchInput = container.querySelector('#res-search-input');
    searchInput.oninput = UI.debounce((e) => {
      this.searchQuery = e.target.value.trim();
      this.fetchReservations();
    }, 250);
  },

  async fetchReservations() {
    const tbody = document.getElementById('reservations-tbody');
    if (!tbody) return;

    try {
      const params = { limit: 500, all_properties: true };
      if (this.selectedProperty) {
        params.property_id = parseInt(this.selectedProperty);
      }
      if (this.currentFilter && this.currentFilter !== 'all') {
        params.status = this.currentFilter;
      }
      if (this.fromDate) params.from_date = this.fromDate;
      if (this.toDate) params.to_date = this.toDate;
      if (this.searchQuery) params.search = this.searchQuery;

      const data = await API.get('/api/reservations', params);
      const items = data.items;
      const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

      const totalBadge = document.getElementById('res-total-badge');
      if (totalBadge) {
        totalBadge.textContent = `${data.total || (items ? items.length : 0)} Bookings`;
      }

      if (!items || items.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="10" style="text-align: center; padding: 48px;">
              ${UI.emptyState({
                icon: 'calendar',
                text: 'No reservations found matching the selected filter criteria.',
              })}
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = items.map(r => {
        const bal = parseFloat(r.balance || 0);
        const totalAmount = parseFloat(r.total_charges || (r.nightly_rate * r.nights) || 0);
        let balHtml = '';
        if (isAdmin) {
          balHtml = `<span class="font-mono font-bold" style="${bal > 0 ? 'color:#DC2626;' : 'color:#059669;'}">${formatCurrency(bal)}</span>`;
        } else {
          balHtml = bal <= 0 
            ? '<span class="badge badge-success" style="font-size:10px;">Settled</span>' 
            : '<span class="badge badge-warning" style="font-size:10px;">Pending</span>';
        }

        return `
          <tr class="res-table-row" data-id="${r.id}" style="cursor: pointer;">
            <td class="font-mono font-bold" style="color: #111827;">
              <div>${r.confirmation_number}</div>
              ${r.hotel_name ? `
                <div style="margin-top:2px;">
                  <span class="badge" style="font-size:9.5px; background:#F1F5F9; color:#475569; font-weight:500; padding:1px 5px; border-radius:3px;">
                    ${r.hotel_name}
                  </span>
                </div>
              ` : ''}
            </td>
            <td>
              <div style="font-weight: 600; color: #111827;">${r.guest ? r.guest.full_name : '—'}</div>
              <div style="font-size: 11px; color: #6B7280;">${r.guest && r.guest.phone ? r.guest.phone : (r.guest ? r.guest.email : '')}</div>
            </td>
            <td>
              <span class="font-mono font-bold">${r.room ? r.room.number : '—'}</span>
              <span style="font-size: 11px; color: #6B7280; margin-left: 4px;">(${r.room && r.room.room_type ? r.room.room_type.code : '—'})</span>
            </td>
            <td>${formatDate(r.check_in_date)}</td>
            <td>${formatDate(r.check_out_date)}</td>
            <td class="font-mono">${r.nights}n</td>
            <td class="text-right font-mono font-semibold" style="color: #111827;">${formatCurrency(totalAmount)}</td>
            <td class="text-right">${balHtml}</td>
            <td>${UI.statusBadge(r.status)}</td>
            <td class="text-right" onclick="event.stopPropagation();" style="white-space: nowrap;">
              <a href="/api/reservations/${r.id}/invoice.pdf?token=${encodeURIComponent(API.getToken() || '')}" target="_blank" class="btn btn-secondary btn-sm" style="font-size:11px; padding:2px 8px; margin-right: 4px; display:inline-flex; align-items:center; gap:3px;" title="Download PDF Tax Invoice">
                📄 Invoice
              </a>
              <button class="btn btn-secondary btn-sm" onclick="window.openReservationDrawer(${r.id})" style="font-size:11px; padding:2px 8px;">
                Details
              </button>
            </td>
          </tr>
        `;
      }).join('');

      tbody.querySelectorAll('.res-table-row').forEach(tr => {
        tr.onclick = () => {
          const id = tr.getAttribute('data-id');
          window.openReservationDrawer(id);
        };
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="10" style="color:#DC2626; padding:24px; text-align:center;">Failed to load reservations: ${err.message}</td></tr>`;
    }
  },

  // ── GROUP BOOKINGS VIEW ───────────────────────────────────────────────────

  async renderGroupsView() {
    const container = document.getElementById('res-view-container');
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="padding:0; overflow:hidden; border:1px solid #E5E7EB;">
        <div id="groups-table-wrap">
          <div style="padding:48px; text-align:center; color:#6B7280;">Loading group bookings...</div>
        </div>
      </div>
    `;

    try {
      const groups = await API.get('/api/groups');
      const wrap = document.getElementById('groups-table-wrap');

      if (!groups || groups.length === 0) {
        wrap.innerHTML = '<div style="padding:48px; text-align:center; color:#6B7280;">No group bookings found. Click "New Group Booking" to create one.</div>';
        return;
      }

      let html = `
        <table class="data-table" style="width:100%; font-size:12px;">
          <thead>
            <tr>
              <th>GROUP NAME</th>
              <th>PRIMARY CONTACT</th>
              <th>DATES OF STAY</th>
              <th>CUTOFF DATE</th>
              <th>BLOCK ALLOCATION</th>
              <th>PICKED UP</th>
              <th>STATUS</th>
              <th style="text-align:right;">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
      `;

      groups.forEach(g => {
        const blocksSummary = g.room_blocks.map(b => `${b.count}× ${b.room_type_name}`).join(', ');
        const pct = g.rooms_blocked_total > 0 ? Math.round((g.rooms_picked_up_total / g.rooms_blocked_total) * 100) : 0;

        html += `
          <tr style="cursor:pointer;" onclick="window.Pages.Reservations.openGroupDetailDrawer(${g.id})">
            <td>
              <div style="font-weight:700; color:#111827; font-size:13px;">${g.name}</div>
              <div style="font-size:11px; color:#6B7280; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${g.notes || 'Corporate/Event Group'}</div>
            </td>
            <td>
              <div style="font-weight:600; color:#111827;">${g.contact_name}</div>
              <div style="font-size:11px; color:#6B7280;">${g.contact_email} · ${g.contact_phone}</div>
            </td>
            <td>
              <div>${formatDate(g.check_in)} → ${formatDate(g.check_out)}</div>
            </td>
            <td>
              <span class="font-mono font-bold" style="${new Date() > new Date(g.cutoff_date) ? 'color:#DC2626;' : 'color:#111827;'}">
                ${formatDate(g.cutoff_date)}
              </span>
            </td>
            <td style="font-size:11px; color:#4B5563;">${blocksSummary || '—'}</td>
            <td>
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="font-mono font-bold">${g.rooms_picked_up_total} / ${g.rooms_blocked_total}</span>
                <span class="badge ${pct >= 80 ? 'badge-success' : 'badge-neutral'}" style="font-size:9px;">${pct}%</span>
              </div>
            </td>
            <td>
              <span class="badge ${g.status === 'confirmed' ? 'badge-success' : 'badge-warning'}" style="text-transform:uppercase;">
                ${g.status}
              </span>
            </td>
            <td style="text-align:right;" onclick="event.stopPropagation();">
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Reservations.openGroupDetailDrawer(${g.id})" style="font-size:11px; padding:2px 8px;">
                View Group
              </button>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      wrap.innerHTML = html;
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:24px;">Failed to load group bookings: ${e.message}</div>`;
    }
  },

  async openGroupDetailDrawer(groupId) {
    try {
      const g = await API.get(`/api/groups/${groupId}`);

      const blocksHtml = g.room_blocks.map(b => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; font-size:12px;">
          <div>
            <strong>${b.room_type_name}</strong>
            <div style="font-size:11px; color:#6B7280;">Negotiated Rate: ${formatCurrency(b.rate)}/night</div>
          </div>
          <div style="text-align:right;">
            <span class="font-mono font-bold">${b.picked_up_count} of ${b.count} Picked Up</span>
            <div style="font-size:11px; color:#059669;">${b.available_to_pick} Available</div>
          </div>
        </div>
      `).join('');

      const resListHtml = g.reservations.length === 0 ? `
        <div style="padding:16px; text-align:center; color:#6B7280; font-size:12px;">No individual rooms picked up yet.</div>
      ` : g.reservations.map(r => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; border-bottom:1px solid #F3F4F6; font-size:12px;">
          <div>
            <div style="font-weight:600; color:#111827;">${r.guest ? r.guest.full_name : 'Guest'} (#${r.confirmation_number})</div>
            <div style="font-size:11px; color:#6B7280;">Room ${r.room ? r.room.number : '—'} · ${formatDate(r.check_in_date)} to ${formatDate(r.check_out_date)}</div>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="font-mono font-bold">${formatCurrency(r.balance)}</span>
            <button class="btn btn-secondary btn-sm" onclick="window.openReservationDrawer(${r.id})" style="font-size:10px; padding:1px 6px;">Manage</button>
          </div>
        </div>
      `).join('');

      UI.drawer({
        title: g.name,
        subtitle: `Group Booking · ${formatDate(g.check_in)} to ${formatDate(g.check_out)}`,
        contentHtml: `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <!-- Group Summary Header -->
            <div class="card" style="padding:16px; border:1px solid #E5E7EB;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <div style="font-size:14px; font-weight:700; color:#111827;">${g.contact_name}</div>
                  <div style="font-size:12px; color:#6B7280;">${g.contact_email} · ${g.contact_phone}</div>
                </div>
                <span class="badge ${g.status === 'confirmed' ? 'badge-success' : 'badge-warning'}" style="text-transform:uppercase;">${g.status}</span>
              </div>
              <div style="margin-top:12px; font-size:12px; color:#4B5563;">
                Auto-Release Cutoff Date: <strong class="font-mono">${formatDate(g.cutoff_date)}</strong>
              </div>
            </div>

            <!-- Master Folio Financial Aggregates -->
            <div class="card" style="padding:16px; border:1px solid #E5E7EB;">
              <div style="font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; margin-bottom:8px;">Group Master Billing Ledger</div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:13px;">
                <div>
                  <div style="font-size:11px; color:#6B7280;">Total Charges:</div>
                  <div class="font-mono font-bold" style="font-size:15px; color:#111827;">${formatCurrency(g.master_folio_total)}</div>
                </div>
                <div>
                  <div style="font-size:11px; color:#6B7280;">Total Payments:</div>
                  <div class="font-mono font-bold" style="font-size:15px; color:#059669;">${formatCurrency(g.master_folio_paid)}</div>
                </div>
              </div>
              <div style="margin-top:10px; padding-top:10px; border-top:1px solid #F3F4F6; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:600; font-size:13px;">Master Balance Due:</span>
                <span class="font-mono font-bold" style="font-size:16px; color:${parseFloat(g.master_folio_balance) > 0 ? '#DC2626' : '#059669'};">
                  ${formatCurrency(g.master_folio_balance)}
                </span>
              </div>
            </div>

            <!-- Room Blocks Allocation -->
            <div>
              <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:8px;">Allocated Room Blocks</div>
              <div style="display:flex; flex-direction:column; gap:8px;">${blocksHtml}</div>
            </div>

            <!-- Picked Up Member Reservations -->
            <div>
              <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:8px;">
                Picked Up Reservations (${g.reservations.length})
              </div>
              <div class="card" style="padding:0; border:1px solid #E5E7EB; max-height:220px; overflow-y:auto;">
                ${resListHtml}
              </div>
            </div>
          </div>
        `,
      });
    } catch (e) {
      UI.toast(e.message, 'error');
    }
  },

  async openNewGroupModal() {
    let roomTypes = [];
    try {
      roomTypes = await API.get('/api/rooms/types');
    } catch (e) {}

    const today = new Date().toISOString().slice(0, 10);
    const in10 = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10);
    const in13 = new Date(Date.now() + 13 * 86400000).toISOString().slice(0, 10);
    const in5 = new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10);

    const blocksRowsHtml = roomTypes.map((rt, idx) => `
      <div style="display:grid; grid-template-columns:2fr 1fr 1fr; gap:8px; align-items:center;">
        <span style="font-size:12px; font-weight:600;">${rt.name}</span>
        <input type="number" min="0" class="form-input group-block-count font-mono" data-rt-id="${rt.id}" placeholder="0 rooms" style="height:32px;">
        <input type="number" step="100" class="form-input group-block-rate font-mono" data-rt-id="${rt.id}" value="${rt.base_rate}" style="height:32px;">
      </div>
    `).join('');

    UI.modal({
      title: 'Create Corporate / Group Booking',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div class="form-group">
            <label class="form-label">Group Name <span class="required-mark">*</span></label>
            <input type="text" id="grp-name" class="form-input" placeholder="e.g. Apex Global Leadership Summit, Sharma Wedding" required>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
            <div class="form-group">
              <label class="form-label">Contact Name <span class="required-mark">*</span></label>
              <input type="text" id="grp-contact" class="form-input" placeholder="Jane Doe" required>
            </div>
            <div class="form-group">
              <label class="form-label">Email <span class="required-mark">*</span></label>
              <input type="email" id="grp-email" class="form-input" placeholder="jane@apex.com" required>
            </div>
            <div class="form-group">
              <label class="form-label">Phone <span class="required-mark">*</span></label>
              <input type="text" id="grp-phone" class="form-input" placeholder="+91 98840 00000" required>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
            <div class="form-group">
              <label class="form-label">Check-In Date</label>
              <input type="date" id="grp-cin" class="form-input" value="${in10}" required>
            </div>
            <div class="form-group">
              <label class="form-label">Check-Out Date</label>
              <input type="date" id="grp-cout" class="form-input" value="${in13}" required>
            </div>
            <div class="form-group">
              <label class="form-label">Cutoff Date</label>
              <input type="date" id="grp-cutoff" class="form-input" value="${in5}" required>
            </div>
          </div>

          <div>
            <label class="form-label" style="margin-bottom:6px;">Room Block Allocations & Rates</label>
            <div style="display:flex; flex-direction:column; gap:8px; padding:12px; background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px;">
              <div style="display:grid; grid-template-columns:2fr 1fr 1fr; gap:8px; font-size:10px; font-weight:700; color:#6B7280; text-transform:uppercase;">
                <span>Room Type</span>
                <span>Room Count</span>
                <span>Agreed Rate (${getCurrencySymbol()})</span>
              </div>
              ${blocksRowsHtml}
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Notes & Catering Requirements</label>
            <input type="text" id="grp-notes" class="form-input" placeholder="Conference halls, banquet menu, early arrival...">
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="create-group-submit-btn">Create Group</button>
      `,
    });

    document.getElementById('create-group-submit-btn').onclick = async () => {
      const name = document.getElementById('grp-name').value.trim();
      const contact = document.getElementById('grp-contact').value.trim();
      const email = document.getElementById('grp-email').value.trim();
      const phone = document.getElementById('grp-phone').value.trim();
      const cin = document.getElementById('grp-cin').value;
      const cout = document.getElementById('grp-cout').value;
      const cutoff = document.getElementById('grp-cutoff').value;
      const notes = document.getElementById('grp-notes').value.trim();

      if (!name || !contact || !email || !phone) {
        UI.toast('Please fill all required group details.', 'error');
        return;
      }

      const roomBlocks = [];
      document.querySelectorAll('.group-block-count').forEach(cntInput => {
        const count = parseInt(cntInput.value) || 0;
        const rtId = parseInt(cntInput.getAttribute('data-rt-id'));
        if (count > 0) {
          const rateInput = document.querySelector(`.group-block-rate[data-rt-id="${rtId}"]`);
          const rate = rateInput ? parseFloat(rateInput.value) : 5000;
          roomBlocks.push({
            room_type_id: rtId,
            count: count,
            rate: rate,
          });
        }
      });

      try {
        const res = await API.post('/api/groups', {
          name,
          contact_name: contact,
          contact_email: email,
          contact_phone: phone,
          check_in: cin,
          check_out: cout,
          cutoff_date: cutoff,
          notes: notes || undefined,
          room_blocks: roomBlocks,
        });

        UI.toast(`Group '${name}' created successfully.`, 'success');
        UI.closeModal();
        this.renderGroupsView();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },
};

// ── NEW RESERVATION MODAL WITH LIVE RATE PLAN QUOTES & DEPOSITS ──────────────
window.openNewReservationModal = async () => {
  let guests = [];
  let rooms = [];
  let ratePlans = [];

  try {
    const [gRes, rRes, pRes] = await Promise.all([
      API.get('/api/guests?limit=100'),
      API.get('/api/rooms?limit=100'),
      API.get('/api/rate-plans?active_only=true'),
    ]);
    guests = gRes.items;
    rooms = rRes.items;
    ratePlans = pRes;
  } catch (e) {
    UI.toast('Failed to load guest, room, or rate plan inventory', 'error');
    return;
  }

  const today = window.currentBusinessDate || new Date().toISOString().slice(0, 10);
  const tomorrowDate = new Date(today);
  tomorrowDate.setDate(tomorrowDate.getDate() + 1);
  const tomorrow = tomorrowDate.toISOString().slice(0, 10);
  const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

  const contentHtml = `
    <form id="new-res-form" style="display:flex; flex-direction:column; gap: var(--space-3);">
      <!-- Guest Select -->
      <div class="form-group">
        <label class="form-label" for="new-res-guest">Guest <span class="required-mark">*</span></label>
        <select id="new-res-guest" class="select-field" required>
          <option value="">Select a guest...</option>
          ${guests.map(g => `<option value="${g.id}">${g.full_name} (${g.email})</option>`).join('')}
        </select>
      </div>

      <!-- Room Selection -->
      <div class="form-group">
        <label class="form-label" for="new-res-room">Room & Type <span class="required-mark">*</span></label>
        <select id="new-res-room" class="select-field" required>
          <option value="">Select an available room...</option>
          ${rooms.map(r => {
            const isOcc = r.status === 'occupied';
            return `
            <option value="${r.id}" data-type-id="${r.room_type_id}" data-rate="${r.room_type ? r.room_type.base_rate : 4500}" ${isOcc ? 'disabled style="color:#9CA3AF; background:#F3F4F6;"' : ''}>
              Room ${r.number} · ${r.room_type ? r.room_type.name : 'Standard'} (${formatCurrency(r.room_type ? r.room_type.base_rate : 4500)}/n) — [${isOcc ? 'OCCUPIED - Cannot Book' : r.status.toUpperCase()}]
            </option>
          `}).join('')}
        </select>
      </div>

      <!-- Rate Plan Selection -->
      <div class="form-group">
        <label class="form-label" for="new-res-plan">Rate Plan</label>
        <select id="new-res-plan" class="select-field">
          <option value="">Standard Daily Base Rate</option>
          ${ratePlans.map(p => `
            <option value="${p.id}" data-min-stay="${p.min_stay}">
              ${p.name} (${p.code}) — ${p.meal_plan.replace('_', ' ')} ${p.min_stay > 1 ? `(Min ${p.min_stay}n)` : ''}
            </option>
          `).join('')}
        </select>
      </div>

      <!-- Dates -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="new-res-in">Check-in Date <span class="required-mark">*</span></label>
          <input type="date" id="new-res-in" class="input-field" value="${today}" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="new-res-out">Check-out Date <span class="required-mark">*</span></label>
          <input type="date" id="new-res-out" class="input-field" value="${tomorrow}" required />
        </div>
      </div>

      <!-- Occupants & Live Rate -->
      <div style="display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="new-res-adults">Adults <span style="font-size:11px; color:#64748B;">(Max 2)</span></label>
          <select id="new-res-adults" class="select-field" required>
            <option value="1">1 Adult</option>
            <option value="2">2 Adults (Max)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="new-res-children">Children</label>
          <input type="number" id="new-res-children" class="input-field" min="0" max="10" value="0" />
        </div>
        <div class="form-group">
          <label class="form-label" for="new-res-rate">Quoted Rate (${getCurrencySymbol()}/n)</label>
          <input type="number" id="new-res-rate" class="input-field font-mono" step="0.01" min="1" placeholder="4500.00" />
        </div>
      </div>

      <!-- Live Rate Quote & Deposit Box -->
      <div id="new-res-quote-box" style="display:none; padding:10px 14px; background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; font-size:12px; color:#166534;"></div>

      <!-- Advance Payment / Deposit (Optional) -->
      <div style="border-top:1px solid #E2E8F0; padding-top:10px; margin-top:2px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
          <span style="font-size:11.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; color:#0F172A;">
            Advance Payment / Deposit (Optional)
          </span>
          <span style="font-size:11px; color:#059669; font-weight:600;">Folio Credit</span>
        </div>
        <div style="display: grid; grid-template-columns: 1.2fr 1fr 1.4fr; gap: 8px;">
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" for="new-res-advance-amt">Advance Amount (${getCurrencySymbol()})</label>
            <input type="number" id="new-res-advance-amt" class="input-field font-mono" step="0.01" min="0" placeholder="0.00" />
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" for="new-res-advance-method">Method</label>
            <select id="new-res-advance-method" class="select-field">
              <option value="upi">UPI / QR</option>
              <option value="cash" selected>Cash</option>
              <option value="card">Credit / Debit Card</option>
              <option value="net_banking">Net Banking</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" for="new-res-advance-ref">Ref / Trans #</label>
            <input type="text" id="new-res-advance-ref" class="input-field" placeholder="UPI Ref / Last 4" />
          </div>
        </div>
      </div>

      <!-- Special Notes -->
      <div class="form-group">
        <label class="form-label" for="new-res-notes">Special Requests & Notes</label>
        <textarea id="new-res-notes" class="textarea-field" placeholder="Airport pickup, high floor, extra pillows..."></textarea>
      </div>

      <div id="new-res-error-box" style="display:none; color:var(--danger); font-size:12px; padding: 8px; background:var(--danger-bg); border-radius:4px;"></div>
    </form>
  `;

  const panel = UI.modal({
    title: 'Create Reservation',
    contentHtml: contentHtml,
    footerHtml: `
      <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
      <button class="btn btn-primary btn-md" id="submit-new-res-btn">Confirm Booking</button>
    `,
  });

  const roomSelect = panel.querySelector('#new-res-room');
  const planSelect = panel.querySelector('#new-res-plan');
  const cinInput = panel.querySelector('#new-res-in');
  const coutInput = panel.querySelector('#new-res-out');
  const adultsInput = panel.querySelector('#new-res-adults');
  const rateInput = panel.querySelector('#new-res-rate');
  const quoteBox = panel.querySelector('#new-res-quote-box');

  let currentDepositRequired = 0;

  // Live Quote Function
  const updateLiveQuote = async () => {
    const selectedOpt = roomSelect.options[roomSelect.selectedIndex];
    if (!selectedOpt || !selectedOpt.value) return;

    const rtId = selectedOpt.getAttribute('data-type-id');
    const cin = cinInput.value;
    const cout = coutInput.value;
    const planId = planSelect.value;
    const adults = parseInt(adultsInput.value) || 1;

    if (!cin || !cout || cout <= cin) return;

    try {
      const quote = await API.get('/api/rate-plans/quote', {
        room_type_id: rtId,
        check_in: cin,
        check_out: cout,
        plan_id: planId || undefined,
        adults: adults,
      });

      const avgRate = (quote.subtotal / quote.nights).toFixed(2);
      rateInput.value = avgRate;
      currentDepositRequired = quote.deposit_required;

      quoteBox.style.display = 'block';
      quoteBox.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-weight:700;">
          <span>Stay Subtotal (${quote.nights} night(s)):</span>
          <span class="font-mono">${formatCurrency(quote.subtotal)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:2px;">
          <span>Applicable Taxes:</span>
          <span class="font-mono">+${formatCurrency(quote.tax_total)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-weight:700; margin-top:4px; padding-top:4px; border-top:1px solid #BBF7D0;">
          <span>Grand Total:</span>
          <span class="font-mono">${formatCurrency(quote.grand_total)}</span>
        </div>
        ${quote.deposit_required > 0 ? `
          <div style="margin-top:4px; font-weight:600; color:#1E40AF;">
            Deposit Due: <span class="font-mono">${formatCurrency(quote.deposit_required)}</span>
          </div>
        ` : ''}
      `;
    } catch (e) {
      quoteBox.style.display = 'none';
    }
  };

  roomSelect.onchange = updateLiveQuote;
  planSelect.onchange = updateLiveQuote;
  cinInput.onchange = updateLiveQuote;
  coutInput.onchange = updateLiveQuote;
  adultsInput.onchange = updateLiveQuote;

  // Submit Handler
  panel.querySelector('#submit-new-res-btn').onclick = async () => {
    const form = panel.querySelector('#new-res-form');
    const errBox = panel.querySelector('#new-res-error-box');
    errBox.style.display = 'none';

    if (!UI.validateForm(form)) return;

    const checkIn = cinInput.value;
    const checkOut = coutInput.value;

    if (checkOut <= checkIn) {
      errBox.textContent = 'Check-out date must be strictly after check-in date.';
      errBox.style.display = 'block';
      return;
    }

    const advanceAmt = parseFloat(panel.querySelector('#new-res-advance-amt').value) || 0;
    const advanceMethod = panel.querySelector('#new-res-advance-method').value;
    const advanceRef = panel.querySelector('#new-res-advance-ref').value.trim();

    const payload = {
      guest_id: parseInt(panel.querySelector('#new-res-guest').value),
      room_id: parseInt(roomSelect.value),
      rate_plan_id: planSelect.value ? parseInt(planSelect.value) : undefined,
      check_in_date: checkIn,
      check_out_date: checkOut,
      adults: parseInt(adultsInput.value) || 1,
      children: parseInt(panel.querySelector('#new-res-children').value) || 0,
      nightly_rate: rateInput.value ? parseFloat(rateInput.value) : undefined,
      deposit_required: currentDepositRequired > 0 ? currentDepositRequired : undefined,
      advance_amount: advanceAmt > 0 ? advanceAmt : undefined,
      advance_payment_method: advanceAmt > 0 ? advanceMethod : undefined,
      advance_payment_reference: advanceAmt > 0 ? (advanceRef || 'Advance Deposit at Booking') : undefined,
      notes: panel.querySelector('#new-res-notes').value.trim() || undefined,
    };

    try {
      const submitBtn = panel.querySelector('#submit-new-res-btn');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Confirming...';

      const created = await API.post('/api/reservations', payload);
      UI.toast(`Reservation #${created.confirmation_number} confirmed!`, 'success');
      UI.closeModal();

      if (window.Pages.Reservations.fetchReservations) window.Pages.Reservations.fetchReservations();
      if (window.Pages.Dashboard.refresh) window.Pages.Dashboard.refresh();
      window.openReservationDrawer(created.id);
    } catch (err) {
      errBox.textContent = err.message;
      errBox.style.display = 'block';
      const submitBtn = panel.querySelector('#submit-new-res-btn');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Confirm Booking';
    }
  };
};

// ── DETAIL DRAWER WITH DEPOSITS & CANCELLATION QUOTES ────────────────────────
window.openReservationDrawer = async (reservationId) => {
  UI.drawer({
    title: 'Reservation Folio',
    subtitle: 'Loading details...',
    contentHtml: '<div style="padding:24px; text-align:center; color:#6B7280;">Loading stay details...</div>',
  });

  try {
    const [res, folio, depStatus] = await Promise.all([
      API.get(`/api/reservations/${reservationId}`),
      API.get(`/api/billing/reservations/${reservationId}/folio`),
      API.get(`/api/reservations/${reservationId}/deposit-status`),
    ]);

    const bal = parseFloat(folio.balance_due);
    const isCheckedIn = res.status === 'checked_in';
    const isBooked = res.status === 'booked';
    const isCancelled = res.status === 'cancelled';
    const isDeparted = res.status === 'checked_out';
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    const contentHtml = `
      <!-- Guest Profile Card -->
      <div class="card" style="padding: 16px; border:1px solid #E5E7EB;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-weight: 700; font-size: 15px; color:#111827;">${res.guest.full_name}</div>
            <div style="font-size: 12px; color: #6B7280; margin-top: 2px;">
              ${res.guest.email} · ${res.guest.phone}
            </div>
          </div>
          <div>${UI.statusBadge(res.status)}</div>
        </div>
      </div>

      <!-- Stay Specifics & Rate Plan -->
      <div class="card" style="padding: 16px; border:1px solid #E5E7EB; display: flex; flex-direction: column; gap: 8px;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #6B7280;">Stay Overview</div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Confirmation:</span>
          <span class="font-mono font-bold">${res.confirmation_number}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Room Assigned:</span>
          <span style="font-weight: 600;">Room ${res.room.number} (${res.room.room_type ? res.room.room_type.name : 'Standard'})</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Rate Plan:</span>
          <span style="font-weight: 600; color:#2563EB;">${res.rate_plan ? res.rate_plan.name : 'Standard Base Rate'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Stay Dates:</span>
          <span>${formatDate(res.check_in_date)} &rarr; ${formatDate(res.check_out_date)} (${res.nights} nights)</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Nightly Rate:</span>
          <span class="font-mono font-bold">${formatCurrency(res.nightly_rate)}/night</span>
        </div>
      </div>

      <!-- Deposit Status Card -->
      <div class="card" style="padding: 16px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div style="font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase;">Advance Deposit</div>
          <span class="badge ${depStatus.is_satisfied ? 'badge-success' : 'badge-warning'}" style="font-size:10px;">
            ${depStatus.is_satisfied ? 'DEPOSIT SATISFIED' : 'DEPOSIT DUE'}
          </span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:13px;">
          <span style="color:#6B7280;">Required: <strong class="font-mono">${formatCurrency(depStatus.deposit_required)}</strong></span>
          <span style="color:#059669;">Paid: <strong class="font-mono">${formatCurrency(depStatus.deposit_paid)}</strong></span>
        </div>
        ${!depStatus.is_satisfied ? `
          <button class="btn btn-primary btn-sm" id="drawer-record-deposit-btn" style="width:100%; margin-top:10px;">
            + Record Deposit Payment (${formatCurrency(depStatus.balance_due)})
          </button>
        ` : ''}
      </div>

      <!-- Folio Ledger Summary -->
      <div class="card" style="padding: 16px; border:1px solid #E5E7EB; display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display:flex; align-items:center; gap:8px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #6B7280;">Folio Ledger</div>
            ${bal > 0 
              ? `<span class="badge badge-danger font-mono font-bold" style="font-size:10px; padding:1px 6px;">PAYMENT PENDING</span>` 
              : `<span class="badge badge-success font-mono font-bold" style="font-size:10px; padding:1px 6px;">SETTLED / ₹0</span>`}
          </div>
          <div style="display:flex; gap:6px;">
            <a href="/api/reservations/${res.id}/invoice.pdf?token=${encodeURIComponent(API.getToken() || '')}" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 2px 8px; height: 26px; display:inline-flex; align-items:center;">
              Invoice PDF
            </a>
            ${isAdmin ? `
              <button class="btn btn-ghost btn-sm" id="drawer-view-billing-btn" style="color: #2563EB; font-size: 12px; padding: 2px 6px;">
                Full Billing &rarr;
              </button>
            ` : ''}
          </div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Total Charges:</span>
          <span class="font-mono font-bold">${formatCurrency(folio.total_amount)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span style="color: #6B7280;">Total Payments:</span>
          <span class="font-mono font-bold" style="color: #059669;">${formatCurrency(folio.total_paid)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 14px; font-weight: 700; padding-top: 6px; border-top: 1px solid #E5E7EB;">
          <span>Balance Due:</span>
          <span class="font-mono font-bold" style="${bal > 0 ? 'color: #DC2626; font-size: 16px;' : 'color: #059669;'}">
            ${formatCurrency(bal)}
          </span>
        </div>
      </div>

      ${isCheckedIn && bal > 0 ? `
        <!-- Prominent Payment Pending Alert Banner -->
        <div style="background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#DC2626;"></span>
              <strong style="color:#991B1B; font-size:12px; text-transform:uppercase;">Payment Pending</strong>
            </div>
            <span class="badge badge-danger font-mono font-bold" style="font-size:11px;">${formatCurrency(bal)} DUE</span>
          </div>
          <div style="font-size:11px; color:#7F1D1D; line-height:1.4;">
            Guest must settle the outstanding balance before checkout can be performed.
          </div>
          ${isAdmin ? `
            <button class="btn btn-primary btn-sm" id="drawer-collect-pay-btn" style="width:100%; background:#DC2626; border-color:#DC2626; font-weight:600; display:flex; align-items:center; justify-content:center; gap:6px;">
              💳 Clear Payment (${formatCurrency(bal)})
            </button>
          ` : ''}
        </div>
      ` : ''}

      ${isCheckedIn && bal <= 0 ? `
        <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:10px 14px; display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; align-items:center; gap:6px; font-size:12px; font-weight:600; color:#065F46;">
            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#059669;"></span>
            Folio Cleared (Paid in Full)
          </div>
          <span class="badge badge-success" style="font-size:10px;">READY FOR CHECK-OUT</span>
        </div>
      ` : ''}

      <!-- Operational Actions -->
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #6B7280;">Front Desk Actions</div>
        ${isAdmin ? `
          <div style="display: grid; grid-template-columns: 1fr; gap: 8px;">
            ${isBooked ? `
              <button class="btn btn-primary btn-md" id="drawer-checkin-btn">
                ${UI.getIcon('check', 14)} Check in Guest
              </button>
            ` : ''}

            ${isCheckedIn ? (
              bal > 0 ? `
                <button class="btn btn-secondary btn-sm" id="drawer-blocked-checkout-btn" style="opacity:0.6; cursor:not-allowed;" title="Payment must be cleared before checkout" disabled>
                  Check out Guest (Payment Pending)
                </button>
              ` : `
                <button class="btn btn-primary btn-md" id="drawer-checkout-btn" style="background:#000000; font-weight:600;">
                  ✓ Check out Guest
                </button>
              `
            ) : ''}

            ${!isCancelled && !isDeparted ? `
              <button class="btn btn-secondary btn-sm" id="drawer-edit-res-btn" style="display:flex; align-items:center; justify-content:center; gap:6px;">
                ✏️ Edit Stay Dates &amp; Adults
              </button>
            ` : ''}
          </div>

          ${!isCancelled && !isDeparted ? `
            <button class="btn btn-ghost btn-sm" id="drawer-cancel-res-btn" style="color: #DC2626; margin-top: 8px;">
              Cancel Reservation...
            </button>
          ` : ''}
        ` : `
          <div style="padding:8px 12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; font-size:11px; color:#64748B;">
            Guest check-in, checkout, and cancellation are restricted to Front Desk Managers.
          </div>
        `}
      </div>
    `;

    UI.drawer({
      title: `Reservation #${res.confirmation_number}`,
      subtitle: `${res.guest.full_name} · Room ${res.room.number}`,
      contentHtml: contentHtml,
    });

    // Check-in action
    const checkinBtn = document.getElementById('drawer-checkin-btn');
    if (checkinBtn) {
      checkinBtn.onclick = async () => {
        try {
          await API.post(`/api/reservations/${reservationId}/check-in`);
          UI.toast('Guest successfully checked in.', 'success');
          UI.closeDrawer();
          if (window.refreshAllDashboardStats) {
            window.refreshAllDashboardStats();
          }
          window.openReservationDrawer(reservationId);
          if (window.Pages.Reservations.fetchReservations) window.Pages.Reservations.fetchReservations();
        } catch (e) {
          UI.toast(e.message, 'error');
        }
      };
    }

    // Direct Settle & Checkout action buttons
    const settlePayBtn = document.getElementById('drawer-collect-pay-btn');
    const settleCheckoutBtn = document.getElementById('drawer-settle-checkout-btn');
    if (settlePayBtn) {
      settlePayBtn.onclick = () => window.openClearFolioPaymentModal(res, bal);
    }
    if (settleCheckoutBtn) {
      settleCheckoutBtn.onclick = () => window.openCheckoutSettlementModal(res, bal);
    }

    // Standard Check-out action (when bal <= 0)
    const checkoutBtn = document.getElementById('drawer-checkout-btn');
    if (checkoutBtn) {
      checkoutBtn.onclick = async () => {
        try {
          const resData = await API.post(`/api/reservations/${reservationId}/check-out`);
          UI.toast('Guest checked out. Turnover task spawned.', 'success');
          UI.closeDrawer();
          if (window.refreshAllDashboardStats) {
            window.refreshAllDashboardStats();
          } else {
            if (window.Pages.Reservations && window.Pages.Reservations.fetchReservations) {
              window.Pages.Reservations.fetchReservations();
            }
            if (window.Pages.Dashboard && window.Pages.Dashboard.loadDashboardData && window.Pages.Dashboard.containerRef) {
              window.Pages.Dashboard.loadDashboardData(window.Pages.Dashboard.containerRef);
            }
          }
          // Show Checkout Successful modal with stay details and invoice PDF option
          window.showCheckoutSuccessModal(resData, res.room ? res.room.number : '');
        } catch (e) {
          UI.toast(e.message, 'error');
        }
      };
    }

    // Edit Reservation Stay Details action
    const editBtn = document.getElementById('drawer-edit-res-btn');
    if (editBtn) {
      editBtn.onclick = () => {
        UI.modal({
          title: `Edit Stay Details · #${res.confirmation_number}`,
          contentHtml: `
            <div style="display:flex; flex-direction:column; gap:12px;">
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div class="form-group">
                  <label class="form-label">Check-in Date <span class="required-mark">*</span></label>
                  <input type="date" id="edit-cin-date" class="form-input" value="${res.check_in_date}" required>
                </div>
                <div class="form-group">
                  <label class="form-label">Check-out Date <span class="required-mark">*</span></label>
                  <input type="date" id="edit-cout-date" class="form-input" value="${res.check_out_date}" required>
                </div>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div class="form-group">
                  <label class="form-label">Adults <span style="font-size:11px; color:#6B7280;">(Max 2)</span></label>
                  <select id="edit-adults" class="form-select">
                    <option value="1" ${res.adults === 1 ? 'selected' : ''}>1 Adult</option>
                    <option value="2" ${res.adults === 2 ? 'selected' : ''}>2 Adults (Max)</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Children</label>
                  <input type="number" id="edit-children" class="form-input" min="0" max="10" value="${res.children || 0}">
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">Nightly Rate (${getCurrencySymbol()}${getActiveCurrency()})</label>
                <input type="number" step="0.5" id="edit-nightly-rate" class="form-input font-mono" value="${parseFloat(res.nightly_rate).toFixed(2)}" required>
              </div>
              <div class="form-group">
                <label class="form-label">Notes &amp; Preferences</label>
                <textarea id="edit-notes" class="form-textarea" rows="2">${res.notes || ''}</textarea>
              </div>
            </div>
          `,
          footerHtml: `
            <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
            <button class="btn btn-primary btn-md" id="save-edit-res-btn">Save Changes</button>
          `,
        });

        document.getElementById('save-edit-res-btn').onclick = async () => {
          const cin = document.getElementById('edit-cin-date').value;
          const cout = document.getElementById('edit-cout-date').value;
          const adults = parseInt(document.getElementById('edit-adults').value);
          const children = parseInt(document.getElementById('edit-children').value) || 0;
          const rate = parseFloat(document.getElementById('edit-nightly-rate').value);
          const notes = document.getElementById('edit-notes').value.trim();

          if (!cin || !cout) {
            UI.toast('Please provide valid check-in and check-out dates.', 'error');
            return;
          }
          if (cout <= cin) {
            UI.toast('Check-out date must be after check-in date.', 'error');
            return;
          }
          if (isNaN(rate) || rate < 0) {
            UI.toast('Please enter a valid nightly rate.', 'error');
            return;
          }

          try {
            await API.patch(`/api/reservations/${reservationId}`, {
              check_in_date: cin,
              check_out_date: cout,
              adults: adults,
              children: children,
              nightly_rate: rate,
              notes: notes,
            });
            UI.toast('Stay details updated successfully.', 'success');
            UI.closeModal();
            window.openReservationDrawer(reservationId);
            if (window.Pages.Reservations && window.Pages.Reservations.fetchReservations) {
              window.Pages.Reservations.fetchReservations();
            }
          } catch (err) {
            UI.toast(err.message, 'error');
          }
        };
      };
    }

    // Go to billing view
    const viewBillingBtn = document.getElementById('drawer-view-billing-btn');
    if (viewBillingBtn) {
      viewBillingBtn.onclick = () => {
        UI.closeDrawer();
        Router.navigate('/billing');
        setTimeout(() => {
          if (window.Pages.Billing && window.Pages.Billing.selectReservation) {
            window.Pages.Billing.selectReservation(reservationId);
          }
        }, 150);
      };
    }

    // Record Deposit action
    const depBtn = document.getElementById('drawer-record-deposit-btn');
    if (depBtn) {
      depBtn.onclick = () => {
        UI.modal({
          title: `Record Advance Deposit · #${res.confirmation_number}`,
          contentHtml: `
            <div style="display:flex; flex-direction:column; gap:12px;">
              <div class="form-group">
                <label class="form-label">Deposit Amount (${getCurrencySymbol()}${getActiveCurrency()})</label>
                <input type="number" step="0.5" id="rec-dep-amt" class="form-input font-mono" value="${parseFloat(depStatus.balance_due).toFixed(2)}" required>
              </div>
              <div class="form-group">
                <label class="form-label">Payment Method</label>
                <select id="rec-dep-meth" class="form-select">
                  <option value="credit_card">Credit Card</option>
                  <option value="bank_transfer">Bank Wire / IMPS</option>
                  <option value="cash">Cash</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Reference #</label>
                <input type="text" id="rec-dep-ref" class="form-input" placeholder="e.g. AUTH-2918">
              </div>
            </div>
          `,
          footerHtml: `
            <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
            <button class="btn btn-primary btn-md" id="rec-dep-confirm-btn">Record Deposit</button>
          `,
        });

        document.getElementById('rec-dep-confirm-btn').onclick = async () => {
          const amt = parseFloat(document.getElementById('rec-dep-amt').value);
          const meth = document.getElementById('rec-dep-meth').value;
          const ref = document.getElementById('rec-dep-ref').value.trim();

          if (isNaN(amt) || amt <= 0) {
            UI.toast('Please enter a valid deposit amount.', 'error');
            return;
          }

          try {
            await API.post(`/api/reservations/${reservationId}/deposit`, {
              amount: amt,
              payment_method: meth,
              reference: ref || undefined,
            });
            UI.toast('Deposit recorded successfully.', 'success');
            UI.closeModal();
            window.openReservationDrawer(reservationId);
          } catch (err) {
            UI.toast(err.message, 'error');
          }
        };
      };
    }

    // Cancel reservation with Cancellation Quote Preview
    const cancelBtn = document.getElementById('drawer-cancel-res-btn');
    if (cancelBtn) {
      cancelBtn.onclick = async () => {
        try {
          const quote = await API.get(`/api/reservations/${reservationId}/cancellation-quote`);
          const hasPenalty = quote.penalty_amount > 0;

          UI.modal({
            title: `Cancel Reservation #${res.confirmation_number}`,
            contentHtml: `
              <div style="display:flex; flex-direction:column; gap:16px;">
                <div style="padding:12px; background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; font-size:12px;">
                  <div>Policy: <strong>${quote.policy_name}</strong></div>
                  <div>Explanation: <span style="color:#6B7280;">${quote.reason}</span></div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                  <div>
                    <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Penalty Fee</div>
                    <div class="font-mono font-bold" style="font-size:16px; color:${hasPenalty ? '#DC2626' : '#059669'};">
                      ${formatCurrency(quote.penalty_amount)}
                    </div>
                  </div>
                  <div>
                    <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Deposit Refund</div>
                    <div class="font-mono font-bold" style="font-size:16px; color:#059669;">
                      ${formatCurrency(quote.refund_amount)}
                    </div>
                  </div>
                </div>

                ${hasPenalty ? `
                  <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:12px; font-size:12px; color:#991B1B;">
                    <strong>Attention:</strong> This cancellation will charge a fee of ${formatCurrency(quote.penalty_amount)} to the guest folio. Continue?
                  </div>
                ` : ''}
              </div>
            `,
            footerHtml: `
              <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Back</button>
              <button class="btn btn-primary btn-md" id="confirm-cancel-booking-btn" style="background:#DC2626; border-color:#DC2626;">
                Confirm Cancellation
              </button>
            `,
          });

          document.getElementById('confirm-cancel-booking-btn').onclick = async () => {
            try {
              await API.post(`/api/reservations/${reservationId}/cancel`);
              UI.toast('Reservation cancelled.', 'success');
              UI.closeModal();
              UI.closeDrawer();
              if (window.Pages.Reservations.fetchReservations) window.Pages.Reservations.fetchReservations();
            } catch (err) {
              UI.toast(err.message, 'error');
            }
          };
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      };
    }

  } catch (err) {
    UI.toast(`Error loading reservation drawer: ${err.message}`, 'error');
  }
};

window.openClearFolioPaymentModal = (res, bal) => {
  UI.modal({
    title: `Clear Folio Payment: ${res.guest ? res.guest.full_name : ''}`,
    contentHtml: `
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div style="background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:14px; text-align:center;">
          <div style="font-size:11px; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.04em;">Outstanding Folio Balance Due</div>
          <div class="font-mono font-bold" style="font-size:26px; color:#DC2626; margin:4px 0;">${formatCurrency(bal)}</div>
          <div style="font-size:12px; color:#7F1D1D;">Room ${res.room ? res.room.number : 'N/A'} · Confirmation #${res.confirmation_number}</div>
        </div>

        <div>
          <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:4px;">Payment Method *</label>
          <select id="modal-clear-method" class="form-select" style="width:100%;">
            <option value="upi" selected>UPI / QR Code (GPay, PhonePe, Paytm)</option>
            <option value="cash">Cash (Front Desk Counter)</option>
            <option value="card">Credit / Debit Card (Card POS)</option>
            <option value="bank_transfer">Net Banking / Direct Transfer</option>
          </select>
        </div>

        <div>
          <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:4px;">Payment Amount (${getCurrencySymbol()}) *</label>
          <input type="number" id="modal-clear-amount" class="form-input font-mono" value="${parseFloat(bal).toFixed(2)}" step="0.01" style="width:100%; font-weight:600; font-size:15px;" required />
        </div>

        <div>
          <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:4px;">Transaction Reference / Receipt Note (Optional)</label>
          <input type="text" id="modal-clear-ref" class="form-input" placeholder="e.g. UPI Ref #, Card Last 4, or Cash Memo" style="width:100%;" />
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary btn-md" onclick="UI.closeModal();">Cancel</button>
      <button class="btn btn-primary btn-md" id="modal-confirm-clear-btn" style="background:#059669; border-color:#059669; font-weight:600;">
        ✓ Record Payment &amp; Clear Folio
      </button>
    `,
  });

  const confirmBtn = document.getElementById('modal-confirm-clear-btn');
  if (confirmBtn) {
    confirmBtn.onclick = async () => {
      const method = document.getElementById('modal-clear-method').value;
      const amount = parseFloat(document.getElementById('modal-clear-amount').value);
      const ref = document.getElementById('modal-clear-ref').value.trim();

      if (isNaN(amount) || amount <= 0) {
        UI.toast('Please enter a valid payment amount.', 'warning');
        return;
      }

      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Recording Payment...';

      try {
        await API.post(`/api/billing/reservations/${res.id}/payments`, {
          amount: amount,
          method: method,
          reference: ref || 'Cleared via Front Desk Drawer',
          date: new Date().toISOString().split('T')[0],
        });

        UI.toast(`Payment of ${formatCurrency(amount)} recorded successfully!`, 'success');
        UI.closeModal();
        UI.closeDrawer();

        if (window.refreshAllDashboardStats) {
          window.refreshAllDashboardStats();
        } else {
          if (window.Pages.Reservations && window.Pages.Reservations.fetchReservations) {
            window.Pages.Reservations.fetchReservations();
          }
        }
        window.openReservationDrawer(res.id);
      } catch (err) {
        UI.toast(err.message, 'error');
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ Record Payment & Clear Folio';
      }
    };
  }
};

window.openCheckoutSettlementModal = (res, bal) => {
  UI.modal({
    title: `Settle Payment & Check Out: ${res.guest ? res.guest.full_name : ''}`,
    contentHtml: `
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div style="background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:14px; text-align:center;">
          <div style="font-size:11px; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.04em;">Outstanding Folio Balance Due</div>
          <div class="font-mono font-bold" style="font-size:26px; color:#DC2626; margin:4px 0;">${formatCurrency(bal)}</div>
          <div style="font-size:12px; color:#7F1D1D;">Room ${res.room ? res.room.number : 'N/A'} · Confirmation #${res.confirmation_number}</div>
          <div style="font-size:11.5px; color:#991B1B; margin-top:6px; font-weight:500;">
            Check-out can only be finalized if the amount received covers the total pending balance.
          </div>
        </div>

        <div>
          <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:4px;">Payment Method *</label>
          <select id="modal-settle-method" class="form-select" style="width:100%;">
            <option value="upi" selected>UPI / QR Code (GPay, PhonePe, Paytm)</option>
            <option value="cash">Cash (Front Desk Counter)</option>
            <option value="card">Credit / Debit Card (Card POS)</option>
            <option value="bank_transfer">Net Banking / Direct Transfer</option>
          </select>
        </div>

        <div>
          <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:4px;">Amount Received (${getCurrencySymbol()}) *</label>
          <input type="number" id="modal-settle-amount" class="form-input font-mono" value="${parseFloat(bal).toFixed(2)}" step="0.01" style="width:100%; font-weight:600; font-size:15px;" required />
        </div>

        <div>
          <label style="display:block; font-size:12px; font-weight:600; color:#374151; margin-bottom:4px;">Transaction Reference / Receipt Note (Optional)</label>
          <input type="text" id="modal-settle-ref" class="form-input" placeholder="e.g. UPI Ref #, Card Last 4, or Cash Memo" style="width:100%;" />
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary btn-md" onclick="UI.closeModal();">Cancel</button>
      <button class="btn btn-primary btn-md" id="modal-confirm-settle-btn" style="background:#DC2626; border-color:#DC2626; font-weight:600;">
        ✓ Settle ${formatCurrency(bal)} &amp; Check Out Guest
      </button>
    `,
  });

  const confirmBtn = document.getElementById('modal-confirm-settle-btn');
  if (confirmBtn) {
    confirmBtn.onclick = async () => {
      const method = document.getElementById('modal-settle-method').value;
      const amount = parseFloat(document.getElementById('modal-settle-amount').value);
      const ref = document.getElementById('modal-settle-ref').value.trim();

      if (isNaN(amount) || amount <= 0) {
        UI.toast('Please enter a valid payment amount.', 'warning');
        return;
      }

      // Validate amount received >= pending balance
      if (amount < bal) {
        UI.toast(`Cannot check out: Amount entered (${formatCurrency(amount)}) is less than total pending balance (${formatCurrency(bal)}). Full pending amount must be received to check out.`, 'warning');
        return;
      }

      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Processing Checkout...';

      try {
        await API.post(`/api/reservations/${res.id}/check-out`, {
          settle_payment: true,
          payment_method: method,
          reference: ref || 'Settled at check-out',
          amount: amount,
        });

        UI.toast(`Payment of ${formatCurrency(amount)} settled. Guest checked out successfully!`, 'success');
        UI.closeModal();
        UI.closeDrawer();

        if (window.refreshAllDashboardStats) {
          window.refreshAllDashboardStats();
        } else {
          if (window.Pages.Reservations && window.Pages.Reservations.fetchReservations) {
            window.Pages.Reservations.fetchReservations();
          }
          if (window.Pages.Dashboard && window.Pages.Dashboard.loadDashboardData && window.Pages.Dashboard.containerRef) {
            window.Pages.Dashboard.loadDashboardData(window.Pages.Dashboard.containerRef);
          }
        }
      } catch (err) {
        UI.toast(err.message, 'error');
        confirmBtn.disabled = false;
        confirmBtn.textContent = `✓ Settle ${formatCurrency(bal)} & Check Out Guest`;
      }
    };
  }
};
