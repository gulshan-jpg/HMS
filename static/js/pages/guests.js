/**
 * Hotel OS - Guests Directory & Profile Drawer
 * Manages guest CRM records, contact profiles, lifetime metrics, and stay histories.
 */

window.Pages = window.Pages || {};

window.Pages.Guests = {
  searchQuery: '',

  async render(container) {
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Guest Directory</h1>
          <div class="page-header-desc">
            ${isAdmin
              ? 'Guest contact repository, lifetime revenue tracking, and stay histories.'
              : 'Guest contact repository, stay histories, and guest preferences (Front Desk Directory).'}
          </div>
        </div>
        <div class="toolbar-group">
          ${isAdmin ? `
            <button class="btn btn-primary btn-md" id="add-guest-top-btn">
              ${UI.getIcon('plus', 16)} Add Guest Profile
            </button>
          ` : ''}
        </div>
      </div>

      <!-- Search Toolbar -->
      <div class="toolbar-container card" style="padding: var(--space-3) var(--space-4);">
        <div class="toolbar-group" style="width: 100%; max-width: 420px;">
          <div style="position: relative; width: 100%;">
            <input
              type="text"
              id="guest-search-input"
              class="input-field"
              placeholder="Search by name, email, or telephone number..."
              style="padding-left: 32px; height: 34px;"
            />
            <div style="position: absolute; left: 10px; top: 8px; color: var(--text-tertiary);">
              ${UI.getIcon('search', 16)}
            </div>
          </div>
        </div>
      </div>

      <!-- Guests Table Card -->
      <div class="card">
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">Guest Name</th>
                <th scope="col">Email Address</th>
                <th scope="col">Phone</th>
                <th scope="col">Last Stay</th>
                <th scope="col" class="text-center">Total Stays</th>
                <th scope="col" class="text-right">${isAdmin ? 'Lifetime Spend' : 'Guest Tier'}</th>
                <th scope="col" class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody id="guests-tbody">
              ${UI.skeletonTable(6, 7)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    this.bindEvents(container);
    await this.fetchGuests();
  },

  bindEvents(container) {
    const addBtn = container.querySelector('#add-guest-top-btn');
    if (addBtn) addBtn.onclick = () => window.openAddGuestModal(() => this.fetchGuests());

    const searchInput = container.querySelector('#guest-search-input');
    let searchTimeout = null;
    searchInput.oninput = (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        this.searchQuery = e.target.value.trim();
        this.fetchGuests();
      }, 250);
    };
  },

  async fetchGuests() {
    const tbody = document.getElementById('guests-tbody');
    if (!tbody) return;

    try {
      const res = await API.get('/api/guests', {
        search: this.searchQuery || undefined,
        limit: 100,
      });

      if (res.items.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="padding: 0;">
              ${UI.emptyState({
                icon: 'guests',
                text: 'No guest profiles found matching your search.',
                actionHtml: `<button class="btn btn-secondary btn-sm" onclick="window.Pages.Guests.clearSearch()">Clear Search</button>`,
              })}
            </td>
          </tr>
        `;
        return;
      }

      const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

      tbody.innerHTML = res.items.map(g => `
        <tr data-guest-id="${g.id}">
          <td style="font-weight: 600;">${g.full_name}</td>
          <td>${g.email}</td>
          <td class="font-mono" style="font-size: 12px;">${g.phone}</td>
          <td>${formatDate(g.last_stay)}</td>
          <td class="text-center">
            <span class="badge badge-neutral" style="font-size: 11px;">${g.total_stays} stay(s)</span>
          </td>
          <td class="text-right">
            ${isAdmin ? `
              <span class="tabular font-mono" style="font-weight: 600;">${formatCurrency(g.total_spend)}</span>
            ` : `
              ${g.total_stays > 2 
                ? `<span class="badge badge-info" style="font-size: 10px;">VIP Returning</span>`
                : `<span class="badge badge-neutral" style="font-size: 10px;">Verified Guest</span>`}
            `}
          </td>
          <td class="text-right" onclick="event.stopPropagation()">
            <button class="btn btn-ghost btn-sm view-profile-btn" data-id="${g.id}">
              Profile &rarr;
            </button>
          </td>
        </tr>
      `).join('');

      tbody.querySelectorAll('tr[data-guest-id]').forEach(row => {
        row.onclick = () => {
          const id = row.getAttribute('data-guest-id');
          window.openGuestDrawer(id);
        };
      });

      tbody.querySelectorAll('.view-profile-btn').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const id = btn.getAttribute('data-id');
          window.openGuestDrawer(id);
        };
      });
    } catch (err) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="padding: 24px; text-align: center; color: var(--danger);">
            Failed to load guests: ${err.message}
          </td>
        </tr>
      `;
    }
  },

  clearSearch() {
    this.searchQuery = '';
    const input = document.getElementById('guest-search-input');
    if (input) input.value = '';
    this.fetchGuests();
  },
};

// ── Guest Profile Drawer (Right side, 480px) ──────────────────────────────
window.openGuestDrawer = async (guestId) => {
  UI.drawer({
    title: 'Guest Profile',
    subtitle: 'Loading guest portfolio...',
    contentHtml: '<div class="skeleton" style="height: 240px; width: 100%;"></div>',
  });

  try {
    const detail = await API.get(`/api/guests/${guestId}`);
    const g = detail.guest;
    const reservations = detail.reservations || [];
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    const contentHtml = `
      <!-- Contact Overview Card -->
      <div class="card" style="padding: var(--space-4);">
        <div style="font-size: 16px; font-weight: 700; color: var(--text);">${g.full_name}</div>
        <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px; display: flex; flex-direction: column; gap: 4px;">
          <div><strong>Email:</strong> ${g.email}</div>
          <div><strong>Phone:</strong> ${g.phone}</div>
          ${g.address ? `<div><strong>Address:</strong> ${g.address}</div>` : ''}
          ${g.id_number ? `<div><strong>Gov ID / Passport:</strong> <span class="font-mono">${g.id_number}</span></div>` : ''}
        </div>
      </div>

      <!-- Lifetime Metrics Grid -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="card" style="padding: 12px;">
          <span style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">Lifetime Stays</span>
          <div class="tabular font-mono" style="font-size: 20px; font-weight: 700; color: var(--text); margin-top: 2px;">
            ${g.total_stays}
          </div>
        </div>
        <div class="card" style="padding: 12px;">
          ${isAdmin ? `
            <span style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">Lifetime Spend</span>
            <div class="tabular font-mono" style="font-size: 20px; font-weight: 700; color: var(--success); margin-top: 2px;">
              ${formatCurrency(g.total_spend)}
            </div>
          ` : `
            <span style="font-size: 11px; text-transform: uppercase; color: var(--text-tertiary); font-weight: 600;">Guest Tier</span>
            <div style="font-size: 15px; font-weight: 700; color: var(--info); margin-top: 6px;">
              ${g.total_stays > 2 ? 'VIP Returning' : 'Verified Guest'}
            </div>
          `}
        </div>
      </div>

      <!-- Guest Preferences & Notes -->
      <div class="card" style="padding: var(--space-4);">
        <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-tertiary); margin-bottom: 4px;">Preferences & Notes</div>
        <div style="font-size: 13px; color: var(--text); line-height: 1.4;">
          ${g.notes || 'No recorded dietary restrictions or custom accommodation preferences.'}
        </div>
      </div>

      <!-- Reservation History -->
      <div class="card" style="padding: var(--space-4);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary);">Stay History (${reservations.length})</div>
          ${isAdmin ? `
            <button class="btn btn-primary btn-sm" id="drawer-guest-new-res-btn">
              + New Reservation
            </button>
          ` : ''}
        </div>

        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${reservations.length === 0 ? `
            <div style="font-size: 12px; color: var(--text-tertiary); text-align: center; padding: 12px;">No historical stays recorded.</div>
          ` : reservations.map(r => `
            <div style="padding: 10px; background-color: var(--surface-alt); border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;" class="guest-stay-history-row" data-res-id="${r.id}">
              <div style="display: flex; justify-content: space-between; font-weight: 600;">
                <span class="font-mono">${r.confirmation_number}</span>
                ${UI.statusBadge(r.status)}
              </div>
              <div style="color: var(--text-secondary); margin-top: 2px;">
                Room ${r.room ? r.room.number : '—'} · ${formatDate(r.check_in_date)} &rarr; ${formatDate(r.check_out_date)} (${r.nights}n)
              </div>
              ${isAdmin ? `
                <div style="display: flex; justify-content: space-between; margin-top: 4px; font-family: var(--font-mono);">
                  <span>Billed: ${formatCurrency(r.total_charges)}</span>
                  <span style="${parseFloat(r.balance) > 0 ? 'color: var(--danger); font-weight:600;' : 'color: var(--success);'}">
                    Balance: ${formatCurrency(r.balance)}
                  </span>
                </div>
              ` : `
                <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                  <span style="color: var(--text-secondary);">Folio Status:</span>
                  <span>${parseFloat(r.balance) > 0 ? '<span class="badge badge-warning" style="font-size:10px;">Bal. Pending</span>' : '<span class="badge badge-success" style="font-size:10px;">Settled</span>'}</span>
                </div>
              `}
            </div>
          `).join('')}
        </div>
      </div>
    `;

    const panel = UI.drawer({
      title: g.full_name,
      subtitle: `Guest #${g.id} · Registered ${formatDate(g.created_at)}`,
      contentHtml,
    });

    // New reservation button pre-selecting this guest
    const newResBtn = panel.querySelector('#drawer-guest-new-res-btn');
    if (newResBtn) {
      newResBtn.onclick = () => {
        UI.closeDrawer();
        window.openNewReservationModal();
        setTimeout(() => {
          const select = document.getElementById('new-res-guest');
          if (select) select.value = guestId;
        }, 150);
      };
    }

    // Click stay item to open reservation folio drawer
    panel.querySelectorAll('.guest-stay-history-row').forEach(row => {
      row.onclick = () => {
        const rId = row.getAttribute('data-res-id');
        UI.closeDrawer();
        window.openReservationDrawer(rId);
      };
    });
  } catch (err) {
    UI.drawer({
      title: 'Guest Profile',
      contentHtml: `<div style="padding: 24px; color: var(--danger);">Failed to load guest profile: ${err.message}</div>`,
    });
  }
};

// ── Add Guest Modal ────────────────────────────────────────────────────────
window.openAddGuestModal = (onSuccess = null) => {
  const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');
  if (!isAdmin) {
    UI.toast('Access Denied: Staff accounts do not have permission to register guest profiles.', 'error');
    return;
  }

  const contentHtml = `
    <form id="add-guest-form">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="add-guest-fn">First Name <span class="required-mark">*</span></label>
          <input type="text" id="add-guest-fn" class="input-field" placeholder="e.g. Priya" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="add-guest-ln">Last Name <span class="required-mark">*</span></label>
          <input type="text" id="add-guest-ln" class="input-field" placeholder="e.g. Sharma" required />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="add-guest-em">Email Address <span class="required-mark">*</span></label>
          <input type="email" id="add-guest-em" class="input-field" placeholder="priya@company.com" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="add-guest-ph">Phone Number <span class="required-mark">*</span></label>
          <input type="tel" id="add-guest-ph" class="input-field" placeholder="+1 (415) 555-0199" required />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" for="add-guest-addr">Physical Address</label>
        <input type="text" id="add-guest-addr" class="input-field" placeholder="Street, City, State, Country" />
      </div>

      <div class="form-group">
        <label class="form-label" for="add-guest-idnum">Government ID / Passport Number</label>
        <input type="text" id="add-guest-idnum" class="input-field font-mono" placeholder="e.g. PASSPORT-US-8912" />
      </div>

      <div class="form-group">
        <label class="form-label" for="add-guest-notes">Guest Preferences & Special Requests</label>
        <textarea id="add-guest-notes" class="textarea-field" placeholder="High floor preference, feather allergy..."></textarea>
      </div>
    </form>
  `;

  const footerHtml = `
    <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
    <button class="btn btn-primary btn-md" id="submit-add-guest-btn">Save Guest Profile</button>
  `;

  const panel = UI.modal({
    title: 'Register New Guest Profile',
    contentHtml,
    footerHtml,
  });

  panel.querySelector('#submit-add-guest-btn').onclick = async () => {
    const form = panel.querySelector('#add-guest-form');
    if (!UI.validateForm(form)) return;

    const payload = {
      first_name: panel.querySelector('#add-guest-fn').value.trim(),
      last_name: panel.querySelector('#add-guest-ln').value.trim(),
      email: panel.querySelector('#add-guest-em').value.trim(),
      phone: panel.querySelector('#add-guest-ph').value.trim(),
      address: panel.querySelector('#add-guest-addr').value.trim() || undefined,
      id_number: panel.querySelector('#add-guest-idnum').value.trim() || undefined,
      notes: panel.querySelector('#add-guest-notes').value.trim() || undefined,
    };

    try {
      const created = await API.post('/api/guests', payload);
      UI.toast(`Guest profile created for ${created.full_name}.`, 'success');
      UI.closeModal();
      if (onSuccess) onSuccess(created);
    } catch (err) {
      UI.toast(err.message, 'error');
    }
  };
};
