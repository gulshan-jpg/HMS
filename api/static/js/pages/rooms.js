/**
 * Hotel OS - Rooms & Inventory View
 * High-density PMS Data Table & Cards toggle, status counts, floor/category filtering, and detail modal.
 */

window.Pages = window.Pages || {};

window.Pages.Rooms = {
  viewMode: 'table', // default 'table' as requested by user
  statusFilter: 'all',
  typeFilter: 'all',
  floorFilter: 'all',
  searchQuery: '',
  roomTypes: [],
  roomsList: [],

  async render(container) {
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Rooms & Inventory</h1>
          <div class="page-header-desc">
            ${isAdmin 
              ? 'Property inventory, housekeeping readiness, room assignments, and live occupancy rates.'
              : 'Property inventory, housekeeping readiness, and room assignments (Operational View · Read-Only).'}
          </div>
        </div>
        <div class="toolbar-group">
          ${isAdmin ? `
            <button class="btn btn-primary btn-md" id="add-room-top-btn">
              ${UI.getIcon('plus', 16)} Add Room
            </button>
          ` : ''}
        </div>
      </div>

      <!-- Quick Status Filter Pills / Summary Count Bar -->
      <div class="filter-pills-bar" id="rooms-kpi-pills">
        <button class="filter-pill active" data-status="all">
          All Rooms <span class="pill-count" id="count-all">0</span>
        </button>
        <button class="filter-pill" data-status="available">
          Available <span class="pill-count" id="count-available">0</span>
        </button>
        <button class="filter-pill" data-status="occupied">
          Occupied <span class="pill-count" id="count-occupied">0</span>
        </button>
        <button class="filter-pill" data-status="dirty">
          Dirty <span class="pill-count" id="count-dirty">0</span>
        </button>
        <button class="filter-pill" data-status="cleaning">
          Cleaning <span class="pill-count" id="count-cleaning">0</span>
        </button>
        <button class="filter-pill" data-status="maintenance">
          Maintenance <span class="pill-count" id="count-maintenance">0</span>
        </button>
      </div>

      <!-- Toolbar: View toggle, Floor filter, Category filter, Search -->
      <div class="toolbar-container card" style="padding: var(--space-3) var(--space-4);">
        <div class="toolbar-group">
          <!-- View Mode Toggle (Table / Cards) -->
          <div class="segmented-control" id="rooms-view-toggle">
            <button class="segmented-btn active" data-view="table">
              ${UI.getIcon('dashboard', 14)} Table
            </button>
            <button class="segmented-btn" data-view="cards">
              ${UI.getIcon('bed', 14)} Cards
            </button>
          </div>

          <!-- Floor Filter -->
          <select id="rooms-floor-filter" class="select-field" style="width: 130px; height: 34px;">
            <option value="all">All Floors</option>
            <option value="1">Floor 1</option>
            <option value="2">Floor 2</option>
            <option value="3">Floor 3</option>
          </select>

          <!-- Room Type Category Filter -->
          <select id="rooms-type-filter" class="select-field" style="width: 180px; height: 34px;">
            <option value="all">All Categories</option>
          </select>
        </div>

        <div class="toolbar-group">
          <!-- Search Box -->
          <div style="position: relative; width: 260px;">
            <input
              type="text"
              id="rooms-search-input"
              class="input-field"
              placeholder="Search room # or notes..."
              style="padding-left: 32px; height: 34px; width: 100%;"
            />
            <div style="position: absolute; left: 10px; top: 9px; color: var(--text-tertiary);">
              ${UI.getIcon('search', 15)}
            </div>
          </div>
        </div>
      </div>

      <!-- Main Display View Container -->
      <div id="rooms-display-container">
        <div class="card">
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th scope="col">Room #</th>
                  <th scope="col">Floor</th>
                  <th scope="col">Category</th>
                  <th scope="col">Capacity</th>
                  <th scope="col" class="text-right">Base Rate</th>
                  <th scope="col" class="text-center">Status</th>
                  <th scope="col">Guest / Stay</th>
                  <th scope="col">Notes & Amenities</th>
                  <th scope="col" class="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${UI.skeletonTable(8, 9)}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    this.bindEvents(container);
    await this.loadInitialData();
  },

  bindEvents(container) {
    // Add Room button
    const addBtn = container.querySelector('#add-room-top-btn');
    if (addBtn) addBtn.onclick = () => this.openAddRoomModal();

    // KPI status filter pills
    container.querySelectorAll('#rooms-kpi-pills .filter-pill').forEach(pill => {
      pill.onclick = () => {
        container.querySelectorAll('#rooms-kpi-pills .filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        this.statusFilter = pill.getAttribute('data-status');
        this.renderRooms();
      };
    });

    // View toggle (Table vs Cards)
    container.querySelectorAll('#rooms-view-toggle .segmented-btn').forEach(btn => {
      btn.onclick = () => {
        container.querySelectorAll('#rooms-view-toggle .segmented-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.viewMode = btn.getAttribute('data-view');
        this.renderRooms();
      };
    });

    // Floor filter
    const floorSelect = container.querySelector('#rooms-floor-filter');
    if (floorSelect) {
      floorSelect.onchange = () => {
        this.floorFilter = floorSelect.value;
        this.renderRooms();
      };
    }

    // Room Type filter
    const typeSelect = container.querySelector('#rooms-type-filter');
    if (typeSelect) {
      typeSelect.onchange = () => {
        this.typeFilter = typeSelect.value;
        this.renderRooms();
      };
    }

    // Search input
    const searchInput = container.querySelector('#rooms-search-input');
    if (searchInput) {
      let timeout = null;
      searchInput.oninput = (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.searchQuery = e.target.value.trim().toLowerCase();
          this.renderRooms();
        }, 150);
      };
    }
  },

  async loadInitialData() {
    try {
      const [types, roomsRes] = await Promise.all([
        API.get('/api/rooms/types'),
        API.get('/api/rooms', { limit: 100 }),
      ]);
      this.roomTypes = types;
      this.roomsList = roomsRes.items;

      // Update type filter dropdown
      const typeSelect = document.getElementById('rooms-type-filter');
      if (typeSelect) {
        typeSelect.innerHTML = `
          <option value="all">All Categories</option>
          ${this.roomTypes.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
        `;
      }

      // Update floor filter dropdown dynamically based on actual floors in dataset
      const floors = Array.from(new Set(this.roomsList.map(r => r.floor))).sort((a, b) => a - b);
      const floorSelect = document.getElementById('rooms-floor-filter');
      if (floorSelect && floors.length > 0) {
        floorSelect.innerHTML = `
          <option value="all">All Floors</option>
          ${floors.map(f => `<option value="${f}">Floor ${f}</option>`).join('')}
        `;
      }

      this.updateStatusCounts();
      this.renderRooms();
    } catch (e) {
      const display = document.getElementById('rooms-display-container');
      if (display) {
        display.innerHTML = `<div style="padding: 24px; color: var(--danger); text-align: center;">Failed to load room inventory: ${e.message}</div>`;
      }
    }
  },

  updateStatusCounts() {
    const counts = {
      all: this.roomsList.length,
      available: 0,
      occupied: 0,
      dirty: 0,
      cleaning: 0,
      maintenance: 0,
    };

    this.roomsList.forEach(r => {
      const st = (r.status || '').toLowerCase();
      if (counts[st] !== undefined) {
        counts[st]++;
      }
    });

    Object.keys(counts).forEach(k => {
      const el = document.getElementById(`count-${k}`);
      if (el) el.textContent = counts[k];
    });
  },

  renderRooms() {
    const display = document.getElementById('rooms-display-container');
    if (!display) return;

    let filtered = this.roomsList;

    // Filter by status
    if (this.statusFilter !== 'all') {
      filtered = filtered.filter(r => (r.status || '').toLowerCase() === this.statusFilter.toLowerCase());
    }

    // Filter by type
    if (this.typeFilter !== 'all') {
      const tid = parseInt(this.typeFilter);
      filtered = filtered.filter(r => r.room_type_id === tid);
    }

    // Filter by floor
    if (this.floorFilter !== 'all') {
      const fid = parseInt(this.floorFilter);
      filtered = filtered.filter(r => r.floor === fid);
    }

    // Filter by search query
    if (this.searchQuery) {
      filtered = filtered.filter(r => {
        const numMatch = (r.number || '').toLowerCase().includes(this.searchQuery);
        const notesMatch = (r.notes || '').toLowerCase().includes(this.searchQuery);
        const typeMatch = r.room_type && r.room_type.name.toLowerCase().includes(this.searchQuery);
        const guestMatch = (r.current_guest || '').toLowerCase().includes(this.searchQuery);
        return numMatch || notesMatch || typeMatch || guestMatch;
      });
    }

    if (filtered.length === 0) {
      display.innerHTML = UI.emptyState({
        icon: 'bed',
        text: 'No rooms match the selected criteria.',
        actionHtml: `<button class="btn btn-secondary btn-sm" onclick="window.Pages.Rooms.resetFilters()">Reset All Filters</button>`,
      });
      return;
    }

    if (this.viewMode === 'cards') {
      display.innerHTML = `
        <div class="rooms-grid">
          ${filtered.map(r => `
            <div class="room-card" data-room-id="${r.id}">
              <div class="room-card-top">
                <span class="room-number-pill">${r.number}</span>
                ${UI.statusBadge(r.status)}
              </div>
              <div class="room-card-middle">
                <div class="room-card-type">${r.room_type ? r.room_type.name : 'Standard Room'}</div>
                <div class="room-card-rate tabular font-mono">
                  <strong>${r.room_type ? formatCurrency(r.room_type.base_rate) : '—'}</strong>/night
                </div>
              </div>
              <div class="room-card-bottom">
                <span class="floor-chip">Floor ${r.floor}</span>
                <span style="font-size: 11px; color: var(--text-tertiary); max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  ${r.notes || (r.current_guest ? r.current_guest : 'Clean view')}
                </span>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } else {
      // Table view (Organized in high-density, professional PMS data table)
      display.innerHTML = `
        <div class="card" style="padding: 0; overflow: hidden;">
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th scope="col" style="width: 110px;">Room #</th>
                  <th scope="col" style="width: 100px;">Floor</th>
                  <th scope="col">Category</th>
                  <th scope="col">Capacity</th>
                  <th scope="col" class="text-right">Base Rate</th>
                  <th scope="col" class="text-center">Status</th>
                  <th scope="col">Guest / Stay</th>
                  <th scope="col">Notes & Amenities</th>
                  <th scope="col" class="text-right" style="width: 100px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${filtered.map(r => {
                  let guestStatusHtml = `<span style="color: var(--text-tertiary); font-size: 12px;">Vacant · Ready</span>`;
                  if (r.status === 'occupied') {
                    guestStatusHtml = `
                      <div style="display: flex; align-items: center; gap: 6px;">
                        <span class="badge badge-info" style="font-size: 10px; padding: 2px 6px;">IN-HOUSE</span>
                        <span style="font-weight: 600; color: #0F172A; font-size: 13px;">${r.current_guest || 'Occupied Stay'}</span>
                      </div>
                    `;
                  } else if (r.status === 'dirty' || r.status === 'cleaning') {
                    guestStatusHtml = `<span style="color: var(--warning); font-size: 12px; font-weight: 500;">Turnover Cleaning Required</span>`;
                  } else if (r.status === 'maintenance') {
                    guestStatusHtml = `<span style="color: var(--danger); font-size: 12px; font-weight: 500;">Out of Order / Repair</span>`;
                  }

                  return `
                    <tr data-room-id="${r.id}">
                      <td>
                        <span class="room-number-pill">${r.number}</span>
                      </td>
                      <td>
                        <span class="floor-chip">Floor ${r.floor}</span>
                      </td>
                      <td>
                        <strong style="color: #0F172A;">${r.room_type ? r.room_type.name : 'Standard'}</strong>
                      </td>
                      <td>
                        <span style="color: var(--text-secondary); font-size: 12px;">Up to ${r.room_type ? r.room_type.max_occupancy : 2} guests</span>
                      </td>
                      <td class="text-right">
                        <span class="tabular font-mono font-semibold" style="color: #0F172A;">${r.room_type ? formatCurrency(r.room_type.base_rate) : '—'}</span>
                        <span style="font-size: 11px; color: var(--text-tertiary);">/n</span>
                      </td>
                      <td class="text-center">
                        ${UI.statusBadge(r.status)}
                      </td>
                      <td>
                        ${guestStatusHtml}
                      </td>
                      <td>
                        <span style="color: var(--text-secondary); font-size: 12px;">${r.notes || '—'}</span>
                      </td>
                      <td class="text-right" onclick="event.stopPropagation()">
                        <button class="btn btn-secondary btn-sm quick-manage-btn" data-id="${r.id}">
                          Manage
                        </button>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    // Attach click listeners to cards and table rows
    display.querySelectorAll('[data-room-id]').forEach(el => {
      el.onclick = () => {
        const id = el.getAttribute('data-room-id');
        this.openRoomDetailModal(id);
      };
    });

    // Attach click listeners to Manage action buttons specifically
    display.querySelectorAll('.quick-manage-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        this.openRoomDetailModal(id);
      };
    });
  },

  resetFilters() {
    this.statusFilter = 'all';
    this.typeFilter = 'all';
    this.floorFilter = 'all';
    this.searchQuery = '';

    const statusPills = document.querySelectorAll('#rooms-kpi-pills .filter-pill');
    statusPills.forEach(p => {
      if (p.getAttribute('data-status') === 'all') p.classList.add('active');
      else p.classList.remove('active');
    });

    const floorSelect = document.getElementById('rooms-floor-filter');
    const typeSelect = document.getElementById('rooms-type-filter');
    const searchInput = document.getElementById('rooms-search-input');
    if (floorSelect) floorSelect.value = 'all';
    if (typeSelect) typeSelect.value = 'all';
    if (searchInput) searchInput.value = '';

    this.renderRooms();
  },

  // ── Room Detail Modal ────────────────────────────────────────────────────
  async openRoomDetailModal(roomId) {
    try {
      const room = await API.get(`/api/rooms/${roomId}`);
      const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');
      const hasActiveRes = Boolean(room.current_reservation_id);
      const balDue = parseFloat(room.current_balance != null ? room.current_balance : 0);
      const totalCharges = parseFloat(room.current_total_charges != null ? room.current_total_charges : 0);
      const totalPayments = parseFloat(room.current_total_payments != null ? room.current_total_payments : 0);

      const contentHtml = `
        <div style="display: flex; flex-direction: column; gap: var(--space-4);">
          <!-- Top Header Info -->
          <div style="display: flex; justify-content: space-between; align-items: baseline; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
            <div>
              <span class="room-number-pill" style="font-size: 18px; padding: 4px 12px;">${room.number}</span>
              <span style="font-size: 14px; color: var(--text-secondary); margin-left: 8px;">Floor ${room.floor} · ${room.room_type ? room.room_type.name : 'Standard'}</span>
            </div>
            <div id="room-detail-badge-slot">${UI.statusBadge(room.status)}</div>
          </div>

          <!-- Capacity & Pricing -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px;">
            <div class="card" style="padding: 12px;">
              <span style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">
                ${isAdmin ? 'Base Rate' : 'Rack Rate (Locked)'}
              </span>
              <div class="tabular font-mono" style="font-size: 16px; font-weight: 600; color: var(--text); margin-top: 2px;">
                ${room.room_type ? formatCurrency(room.room_type.base_rate) : formatCurrency(4500)}/night
              </div>
            </div>
            <div class="card" style="padding: 12px;">
              <span style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">Occupancy Capacity</span>
              <div style="font-size: 16px; font-weight: 600; color: var(--text); margin-top: 2px;">
                Up to ${room.room_type ? room.room_type.max_occupancy : 2} guests
              </div>
            </div>
          </div>

          <!-- Current Occupancy & In-House Checkout / Payment Management -->
          ${hasActiveRes ? `
            <div class="card" style="padding: 14px; background: var(--surface); border: 1.5px solid ${balDue > 0 ? '#FCA5A5' : 'var(--border)'}; border-radius: 8px;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                  <div style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 700; letter-spacing: 0.5px;">Active In-House Stay</div>
                  <div style="font-size: 15px; font-weight: 700; color: var(--text); margin-top: 2px;">${room.current_guest}</div>
                </div>
                <span class="badge badge-info" style="font-size: 11px; padding: 3px 8px;">
                  ${room.current_reservation_confirmation || ('Res #' + room.current_reservation_id)}
                </span>
              </div>

              <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed var(--border);">
                <span>Stay Dates:</span>
                <span style="font-weight: 500; color: var(--text);">
                  ${room.current_check_in_date ? formatDate(room.current_check_in_date) : 'Today'} &rarr; ${room.current_check_out_date ? formatDate(room.current_check_out_date) : 'Departure'}
                </span>
              </div>

              <!-- Folio Balance Summary -->
              <div style="display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 8px; background: var(--surface-alt); padding: 10px; border-radius: 6px; font-size: 12px;">
                <div>
                  <div style="color: var(--text-tertiary); font-size: 10.5px; text-transform: uppercase;">Total Charges</div>
                  <div class="tabular font-mono" style="font-weight: 600; font-size: 13px; color: var(--text); margin-top: 2px;">${formatCurrency(totalCharges)}</div>
                </div>
                <div>
                  <div style="color: var(--text-tertiary); font-size: 10.5px; text-transform: uppercase;">Total Paid</div>
                  <div class="tabular font-mono" style="font-weight: 600; font-size: 13px; color: #059669; margin-top: 2px;">${formatCurrency(totalPayments)}</div>
                </div>
                <div style="text-align: right;">
                  <div style="color: var(--text-tertiary); font-size: 10.5px; text-transform: uppercase;">Balance Due</div>
                  <div class="tabular font-mono" style="font-weight: 700; font-size: 14px; color: ${balDue > 0 ? '#DC2626' : '#059669'}; margin-top: 2px;">${formatCurrency(balDue)}</div>
                </div>
              </div>

              ${balDue > 0 ? `
                <div style="margin-top: 10px; padding: 10px 12px; background: #FEF2F2; border: 1.5px solid #FCA5A5; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">⚠️</span>
                    <div>
                      <div style="font-weight: 700; color: #991B1B; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Payment Pending</div>
                      <div style="font-size: 11.5px; color: #B91C1C;">Due: <strong style="font-size: 13px;">${formatCurrency(balDue)}</strong></div>
                    </div>
                  </div>
                  <span class="badge" style="background: #FEE2E2; color: #991B1B; font-weight: 700; font-size: 10.5px; padding: 3px 8px; border: 1px solid #F87171;">
                    PAYMENT DUE
                  </span>
                </div>
                <div style="font-size: 11px; color: #7F1D1D; margin-top: 6px;">
                  Outstanding balance must be cleared before guest can be checked out.
                </div>
              ` : `
                <div style="margin-top: 10px; padding: 8px 12px; background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #065F46; font-weight: 600;">
                    <span style="color: #059669; font-size: 14px;">✓</span> Folio Cleared (Paid in Full)
                  </div>
                  <span class="badge badge-success" style="font-size: 10.5px; padding: 2px 8px;">READY FOR CHECK-OUT</span>
                </div>
              `}

              <!-- In-House Operational Actions (Admin / Manager only) -->
              ${isAdmin ? `
                <div style="margin-top: 12px; border-top: 1px solid var(--border); padding-top: 10px; display: flex; flex-direction: column; gap: 8px;">
                  <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-tertiary); letter-spacing: 0.5px;">
                    Reception Actions
                  </div>
                  ${balDue > 0 ? `
                    <button class="btn btn-primary btn-md" id="modal-room-clear-payment-btn" style="width: 100%; justify-content: center; font-weight: 600; background: #DC2626; border-color: #DC2626;">
                      💳 Clear Pending Payment (${formatCurrency(balDue)})
                    </button>
                    <button class="btn btn-secondary btn-sm" disabled style="opacity: 0.6; cursor: not-allowed; width: 100%; justify-content: center;" title="Clear payment first to enable checkout">
                      Check Out Guest (Payment Pending)
                    </button>
                  ` : `
                    <button class="btn btn-primary btn-md" id="modal-room-direct-checkout-btn" style="width: 100%; justify-content: center; font-weight: 600; background: #000000; border-color: #000000;">
                      ✓ Check Out Guest (${room.current_guest})
                    </button>
                  `}
                </div>
              ` : `
                <div style="margin-top: 10px; padding: 6px 10px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; font-size: 11px; color: #64748B;">
                  Guest check-in, check-out, and billing settlement are restricted to Front Desk Managers.
                </div>
              `}
            </div>
          ` : `
            <!-- Current Occupancy / Next Arrival -->
            <div class="card" style="padding: 12px; font-size: 13px;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="color: var(--text-secondary);">Current Guest:</span>
                <span style="font-weight: 600; color: var(--text);"><em style="color: var(--text-tertiary); font-weight: normal;">Vacant</em></span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--text-secondary);">Next Arrival:</span>
                <span>${room.next_arrival ? `${room.next_arrival} (${formatDate(room.next_arrival_date)})` : 'None scheduled'}</span>
              </div>
            </div>
          `}

          <!-- Status Control (Accessible to both Admin & Staff to change status) -->
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">Room Status Override</label>
            <div class="segmented-control" id="room-status-override-segmented" style="width: 100%; display: grid; grid-template-columns: repeat(5, 1fr);">
              <button class="segmented-btn ${room.status === 'available' ? 'active' : ''}" data-new-status="available">Available</button>
              <button class="segmented-btn ${room.status === 'occupied' ? 'active' : ''}" data-new-status="occupied">Occupied</button>
              <button class="segmented-btn ${room.status === 'dirty' ? 'active' : ''}" data-new-status="dirty">Dirty</button>
              <button class="segmented-btn ${room.status === 'cleaning' ? 'active' : ''}" data-new-status="cleaning">Cleaning</button>
              <button class="segmented-btn ${room.status === 'maintenance' ? 'active' : ''}" data-new-status="maintenance">Maint.</button>
            </div>
          </div>

          <!-- Quick Actions Grid -->
          <div style="display: flex; gap: 8px; margin-top: 4px;">
            <button class="btn btn-secondary btn-sm" id="modal-task-btn" style="flex: 1;">
              ${UI.getIcon('housekeeping', 14)} Create Turnover Task
            </button>
          </div>
        </div>
      `;

      const footerHtml = `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Close</button>
      `;

      const panel = UI.modal({
        title: isAdmin ? `Room ${room.number} Management` : `Room ${room.number} Operational Details`,
        contentHtml,
        footerHtml,
      });

      // Status override buttons for Admin & Staff (Optimistic UI)
      panel.querySelectorAll('#room-status-override-segmented .segmented-btn').forEach(btn => {
        btn.onclick = async () => {
          const newStatus = btn.getAttribute('data-new-status');
          const oldStatus = room.status;

          panel.querySelectorAll('#room-status-override-segmented .segmented-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          panel.querySelector('#room-detail-badge-slot').innerHTML = UI.statusBadge(newStatus);

          try {
            await API.patch(`/api/rooms/${roomId}/status`, { status: newStatus });
            UI.toast(`Room ${room.number} status updated to ${newStatus}.`, 'success');

            const found = this.roomsList.find(r => r.id === parseInt(roomId));
            if (found) found.status = newStatus;
            this.updateStatusCounts();
            this.renderRooms();
            if (window.Pages.Dashboard && window.Pages.Dashboard.refresh) {
              window.Pages.Dashboard.refresh();
            }
          } catch (err) {
            UI.toast(`Failed to update status: ${err.message}`, 'error');
            panel.querySelector('#room-detail-badge-slot').innerHTML = UI.statusBadge(oldStatus);
          }
        };
      });

      // Wire up in-house checkout & billing actions
      if (hasActiveRes) {
        const clearPayBtn = panel.querySelector('#modal-room-clear-payment-btn');
        if (clearPayBtn) {
          clearPayBtn.onclick = () => {
            UI.closeModal();
            this.openRoomPaymentModal(room, room.current_reservation_id, balDue, totalCharges, totalPayments);
          };
        }

        const directCheckoutBtn = panel.querySelector('#modal-room-direct-checkout-btn');
        if (directCheckoutBtn) {
          directCheckoutBtn.onclick = async () => {
            directCheckoutBtn.disabled = true;
            directCheckoutBtn.textContent = 'Checking out...';
            try {
              const resData = await API.post(`/api/reservations/${room.current_reservation_id}/check-out`);
              UI.closeModal();
              if (window.refreshAllDashboardStats) {
                window.refreshAllDashboardStats();
              } else {
                await this.loadInitialData();
              }
              // Show Checkout Successful page/modal with stay details and invoice PDF option
              window.showCheckoutSuccessModal(resData, room.number);
            } catch (err) {
              UI.toast(err.message, 'error');
              directCheckoutBtn.disabled = false;
              directCheckoutBtn.textContent = `✓ Check Out Guest (${room.current_guest})`;
            }
          };
        }
      }

      // Create housekeeping task button
      const taskBtn = panel.querySelector('#modal-task-btn');
      if (taskBtn) {
        taskBtn.onclick = () => {
          UI.closeModal();
          window.openNewTaskModal(room.id);
        };
      }
    } catch (e) {
      UI.toast(`Failed to load room details: ${e.message}`, 'error');
    }
  },

  // ── Modal to Clear Payment Only (without Checkout) ────────────────────────
  openRoomPaymentModal(room, resId, balDue, totalCharges, totalPayments) {
    const curSymbol = (window.AppState && window.AppState.currencySymbol) || '₹';
    const panel = UI.modal({
      title: `Clear Payment · Room ${room.number}`,
      subtitle: `${room.current_guest} · ${room.current_reservation_confirmation || ('Res #' + resId)}`,
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: var(--space-4);">
          <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 12px 14px;">
            <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #991B1B;">Pending Balance Due</div>
            <div class="tabular font-mono" style="font-size: 24px; font-weight: 700; color: #991B1B; margin-top: 2px;">
              ${formatCurrency(balDue)}
            </div>
            <div style="font-size: 11.5px; color: #7F1D1D; margin-top: 4px;">
              Recording payment clears the outstanding balance on the guest folio. The guest will remain in-house until checkout is performed.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="room-pay-method">Payment Method <span class="required-mark">*</span></label>
            <select id="room-pay-method" class="select-field">
              <option value="upi">UPI / QR Code / GPay / PhonePe</option>
              <option value="cash" selected>Cash at Desk</option>
              <option value="card">Credit / Debit Card (POS terminal)</option>
              <option value="bank_transfer">Net Banking / Direct Bank Transfer</option>
              <option value="other">Other / Corporate Voucher</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="room-pay-amount">Payment Amount (${curSymbol}) <span class="required-mark">*</span></label>
            <input type="number" id="room-pay-amount" class="input-field tabular font-mono" step="0.01" min="0.01" value="${balDue.toFixed(2)}" required />
            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px;">
              Enter the exact amount collected from the guest.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="room-pay-ref">Transaction Reference / Receipt #</label>
            <input type="text" id="room-pay-ref" class="input-field" placeholder="e.g. UPI Ref #12345678, Card slip #, Cash memo" />
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal(); window.Pages.Rooms.openRoomDetailModal(${room.id});">Cancel</button>
        <button class="btn btn-primary btn-md" id="modal-confirm-room-pay-btn" style="background: #059669; border-color: #059669; font-weight: 600;">
          ✓ Record Payment &amp; Clear Folio
        </button>
      `,
    });

    const confirmBtn = panel.querySelector('#modal-confirm-room-pay-btn');
    if (confirmBtn) {
      confirmBtn.onclick = async () => {
        const method = panel.querySelector('#room-pay-method').value;
        const amount = parseFloat(panel.querySelector('#room-pay-amount').value);
        const ref = panel.querySelector('#room-pay-ref').value.trim();

        if (isNaN(amount) || amount <= 0) {
          UI.toast('Please enter a valid positive payment amount.', 'warning');
          return;
        }

        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Recording Payment...';

        try {
          await API.post(`/api/billing/reservations/${resId}/payments`, {
            amount: amount,
            method: method,
            reference: ref || 'Cleared via Room Management',
            date: new Date().toISOString().split('T')[0],
          });

          UI.toast(`Payment of ${formatCurrency(amount)} recorded successfully. Folio updated!`, 'success');
          UI.closeModal();
          if (window.refreshAllDashboardStats) {
            window.refreshAllDashboardStats();
          } else {
            await this.loadInitialData();
          }
          this.openRoomDetailModal(room.id);
        } catch (err) {
          UI.toast(`Failed to record payment: ${err.message}`, 'error');
          confirmBtn.disabled = false;
          confirmBtn.textContent = '✓ Record Payment & Clear Folio';
        }
      };
    }
  },

  // ── Modal to Settle Payment & Complete Check-Out ───────────────────────────
  openRoomCheckoutModal(room, resId, balDue, totalCharges, totalPayments) {
    const curSymbol = (window.AppState && window.AppState.currencySymbol) || '₹';
    const panel = UI.modal({
      title: `Settle & Check Out · Room ${room.number}`,
      subtitle: `${room.current_guest} · ${room.current_reservation_confirmation || ('Res #' + resId)}`,
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: var(--space-4);">
          <!-- Pending Balance Box -->
          <div style="background: #FEF2F2; border: 1.5px solid #FCA5A5; border-radius: 8px; padding: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
              <div>
                <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #991B1B; letter-spacing: 0.5px;">Total Pending Amount</div>
                <div class="tabular font-mono" style="font-size: 24px; font-weight: 700; color: #991B1B; margin-top: 2px;">
                  ${formatCurrency(balDue)}
                </div>
              </div>
              <div style="text-align: right; font-size: 12px; color: #7F1D1D;">
                <div>Total: ${formatCurrency(totalCharges)}</div>
                <div style="color: #059669;">Paid: ${formatCurrency(totalPayments)}</div>
              </div>
            </div>
            <div style="font-size: 11.5px; color: #991B1B; margin-top: 8px; border-top: 1px dashed #FECACA; padding-top: 6px; font-weight: 500;">
              ⚠️ Check-out will be finalized only when the total amount received matches or exceeds the pending balance (${formatCurrency(balDue)}).
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="room-checkout-method">Settlement Payment Method <span class="required-mark">*</span></label>
            <select id="room-checkout-method" class="select-field">
              <option value="upi">UPI / QR Code / GPay / PhonePe</option>
              <option value="cash" selected>Cash at Reception</option>
              <option value="card">Credit / Debit Card (POS terminal)</option>
              <option value="bank_transfer">Net Banking / Direct Bank Transfer</option>
              <option value="other">Other / Corporate Voucher</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="room-checkout-amount">Amount Received (${curSymbol}) <span class="required-mark">*</span></label>
            <input type="number" id="room-checkout-amount" class="input-field tabular font-mono" step="0.01" min="0.01" value="${balDue.toFixed(2)}" required />
            <div id="room-checkout-amount-hint" style="font-size: 11.5px; color: var(--text-secondary); margin-top: 4px;">
              Enter the exact amount collected to settle the booking balance.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="room-checkout-ref">Transaction Reference / Receipt #</label>
            <input type="text" id="room-checkout-ref" class="input-field" placeholder="e.g. UPI Ref #12345678, Card slip #, Cash memo" />
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal(); window.Pages.Rooms.openRoomDetailModal(${room.id});">Cancel</button>
        <button class="btn btn-primary btn-md" id="modal-confirm-room-checkout-btn" style="background: #DC2626; border-color: #DC2626; font-weight: 600;">
          ✓ Settle ${formatCurrency(balDue)} &amp; Check Out
        </button>
      `,
    });

    const confirmBtn = panel.querySelector('#modal-confirm-room-checkout-btn');
    const amountInput = panel.querySelector('#room-checkout-amount');

    if (amountInput && confirmBtn) {
      amountInput.oninput = () => {
        const val = parseFloat(amountInput.value);
        if (!isNaN(val) && val > 0) {
          confirmBtn.textContent = `✓ Settle ${formatCurrency(val)} & Check Out`;
          if (val < balDue) {
            confirmBtn.style.background = '#9CA3AF';
            confirmBtn.style.borderColor = '#9CA3AF';
          } else {
            confirmBtn.style.background = '#DC2626';
            confirmBtn.style.borderColor = '#DC2626';
          }
        }
      };
    }

    if (confirmBtn) {
      confirmBtn.onclick = async () => {
        const method = panel.querySelector('#room-checkout-method').value;
        const amount = parseFloat(panel.querySelector('#room-checkout-amount').value);
        const ref = panel.querySelector('#room-checkout-ref').value.trim();

        if (isNaN(amount) || amount <= 0) {
          UI.toast('Please enter a valid payment amount.', 'warning');
          return;
        }

        // Strict validation as requested by user:
        // "check out if total amount received equal to booking amount"
        if (amount < balDue) {
          UI.toast(`Cannot check out: Amount received (${formatCurrency(amount)}) is less than total pending amount (${formatCurrency(balDue)}). Full payment must be received to complete check-out.`, 'warning');
          return;
        }

        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Processing Checkout...';

        try {
          await API.post(`/api/reservations/${resId}/check-out`, {
            settle_payment: true,
            payment_method: method,
            reference: ref || 'Settled at check-out (Room Management)',
            amount: amount,
          });

          UI.toast(`Payment of ${formatCurrency(amount)} settled. Room ${room.number} checked out successfully!`, 'success');
          UI.closeModal();
          if (window.refreshAllDashboardStats) {
            window.refreshAllDashboardStats();
          } else {
            await this.loadInitialData();
            if (window.Pages.Dashboard && window.Pages.Dashboard.refresh) {
              window.Pages.Dashboard.refresh();
            }
          }
        } catch (err) {
          UI.toast(`Failed to complete checkout: ${err.message}`, 'error');
          confirmBtn.disabled = false;
          confirmBtn.textContent = `✓ Settle ${formatCurrency(balDue)} & Check Out`;
        }
      };
    }
  },

  // ── Add Room Modal ───────────────────────────────────────────────────────
  openAddRoomModal() {
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');
    if (!isAdmin) {
      UI.toast('Access Denied: Only administrators have permission to add rooms.', 'error');
      return;
    }

    const contentHtml = `
      <form id="add-room-form">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
          <div class="form-group">
            <label class="form-label" for="add-room-num">Room Number <span class="required-mark">*</span></label>
            <input type="text" id="add-room-num" class="input-field" placeholder="e.g. 208, 401" required />
          </div>
          <div class="form-group">
            <label class="form-label" for="add-room-floor">Floor <span class="required-mark">*</span></label>
            <input type="number" id="add-room-floor" class="input-field" min="1" max="100" value="1" required />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="add-room-type">Room Type <span class="required-mark">*</span></label>
          <select id="add-room-type" class="select-field" required>
            ${this.roomTypes.map(t => `<option value="${t.id}">${t.name} (${formatCurrency(t.base_rate)}/n)</option>`).join('')}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="add-room-status">Initial Status</label>
          <select id="add-room-status" class="select-field">
            <option value="available">Available</option>
            <option value="dirty">Dirty</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="add-room-notes">Notes / Special Features</label>
          <textarea id="add-room-notes" class="textarea-field" placeholder="Ocean facing, ADA access, balcony..."></textarea>
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
      <button class="btn btn-primary btn-md" id="submit-add-room-btn">Create Room</button>
    `;

    const panel = UI.modal({
      title: 'Add New Room to Inventory',
      contentHtml,
      footerHtml,
    });

    panel.querySelector('#submit-add-room-btn').onclick = async () => {
      const form = panel.querySelector('#add-room-form');
      if (!UI.validateForm(form)) return;

      const payload = {
        number: panel.querySelector('#add-room-num').value.trim(),
        floor: parseInt(panel.querySelector('#add-room-floor').value),
        room_type_id: parseInt(panel.querySelector('#add-room-type').value),
        status: panel.querySelector('#add-room-status').value,
        notes: panel.querySelector('#add-room-notes').value.trim() || undefined,
      };

      try {
        const created = await API.post('/api/rooms', payload);
        UI.toast(`Room ${created.number} successfully added to inventory.`, 'success');
        UI.closeModal();
        await this.loadInitialData();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },
};
