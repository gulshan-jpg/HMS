/**
 * CheckinOS - Billing & Folio Accounting Page
 * Multi-Folio Splitting, Line Item Transfer, Stripe Payments, and Refund Workflows.
 */

window.Pages = window.Pages || {};

window.Pages.Billing = {
  selectedReservationId: null,
  activeFolioId: null,
  reservations: [],
  folios: [],
  currentStatusFilter: 'all',
  searchQuery: '',

  async render(container, selectedId = null) {
    this.currentStatusFilter = 'all';
    this.searchQuery = '';

    container.innerHTML = `
      <div class="page-header no-print" style="margin-bottom:16px;">
        <div>
          <h1 class="page-title">Billing & Folio Ledgers</h1>
          <div class="page-header-desc">Guest accounts, folio ledger transactions, payments, and checkout settlement.</div>
        </div>
        <div class="toolbar-group">
          <button class="btn btn-secondary btn-md" id="print-folio-btn" disabled>
            ${UI.getIcon('printer', 16)} Print Folio Invoice
          </button>
        </div>
      </div>

      <!-- Smart Reservation Selector & Filter Toolbar -->
      <div class="card no-print" style="padding: 14px 18px; margin-bottom: 20px; border:1px solid #E5E7EB;">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
          <!-- Status Filter Pills -->
          <div class="segmented-control" id="billing-status-filter" style="width:fit-content;">
            <button class="segmented-btn active" data-filter="all">All</button>
            <button class="segmented-btn" data-filter="checked_in">In-House</button>
            <button class="segmented-btn" data-filter="booked">Booked</button>
            <button class="segmented-btn" data-filter="checked_out">Departed</button>
          </div>

          <!-- Quick Search Box -->
          <div style="position:relative; width:280px;">
            <input type="text" id="billing-search-input" class="form-input" placeholder="Search guest name, room, or conf #..." style="padding-left:32px; height:34px; font-size:12px;" />
            <svg style="position:absolute; left:10px; top:10px; width:14px; height:14px; color:#9CA3AF;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
          </div>
        </div>

        <div style="display:flex; align-items:center; gap:12px; margin-top:12px; border-top:1px solid #F1F5F9; padding-top:10px;">
          <label style="font-size:12px; font-weight:700; color:#334155; white-space:nowrap; text-transform:uppercase; letter-spacing:0.03em;">Target Reservation:</label>
          <select id="billing-res-select" class="form-select font-mono" style="flex:1; height:36px; font-size:13px; font-weight:600;">
            <option value="">Loading reservations...</option>
          </select>
        </div>
      </div>

      <!-- Main Folio Display Container -->
      <div id="billing-folio-display">
        ${UI.emptyState({
          icon: 'billing',
          text: 'Select an active or historical reservation to view the itemized folio ledger.',
        })}
      </div>
    `;

    this.bindSearchEvents();
    await this.loadReservationsList(selectedId);
  },

  bindSearchEvents() {
    const filterContainer = document.getElementById('billing-status-filter');
    if (filterContainer) {
      filterContainer.querySelectorAll('.segmented-btn').forEach(btn => {
        btn.onclick = () => {
          filterContainer.querySelectorAll('.segmented-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          this.currentStatusFilter = btn.getAttribute('data-filter');
          this.populateBillingSelect();
        };
      });
    }

    const searchInput = document.getElementById('billing-search-input');
    if (searchInput) {
      searchInput.oninput = UI.debounce((e) => {
        this.searchQuery = e.target.value.trim();
        this.populateBillingSelect();
      }, 200);
    }
  },

  async loadReservationsList(preSelectedId = null) {
    try {
      const res = await API.get('/api/reservations', { limit: 500, all_properties: true });
      this.reservations = res.items || [];
      this.populateBillingSelect(preSelectedId);
    } catch (e) {
      UI.toast(`Failed to load reservations for billing: ${e.message}`, 'error');
    }
  },

  populateBillingSelect(preSelectedId = null) {
    const select = document.getElementById('billing-res-select');
    if (!select) return;

    let filtered = this.reservations;
    if (this.currentStatusFilter && this.currentStatusFilter !== 'all') {
      filtered = filtered.filter(r => r.status === this.currentStatusFilter);
    }
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      filtered = filtered.filter(r => 
        (r.confirmation_number && r.confirmation_number.toLowerCase().includes(q)) ||
        (r.guest && r.guest.full_name && r.guest.full_name.toLowerCase().includes(q)) ||
        (r.room && String(r.room.number).toLowerCase().includes(q))
      );
    }

    if (filtered.length === 0) {
      select.innerHTML = '<option value="">No matching reservations found</option>';
      document.getElementById('billing-folio-display').innerHTML = UI.emptyState({
        icon: 'billing',
        text: 'No reservations found matching the selected filter/search.',
      });
      const printBtn = document.getElementById('print-folio-btn');
      if (printBtn) printBtn.disabled = true;
      return;
    }

    select.innerHTML = `
      <option value="">Choose a guest or reservation (${filtered.length} available)...</option>
      ${filtered.map(r => `
        <option value="${r.id}" ${preSelectedId && parseInt(preSelectedId) === r.id ? 'selected' : ''}>
          ${r.confirmation_number} — ${r.guest ? r.guest.full_name : 'Guest'} (Room ${r.room ? r.room.number : '—'}) · [${r.status.toUpperCase()}]
        </option>
      `).join('')}
    `;

    select.onchange = () => {
      const val = select.value;
      if (val) {
        this.selectReservation(val);
      } else {
        document.getElementById('billing-folio-display').innerHTML = UI.emptyState({
          icon: 'billing',
          text: 'Select an active or historical reservation to view the itemized folio ledger.',
        });
        const printBtn = document.getElementById('print-folio-btn');
        if (printBtn) printBtn.disabled = true;
      }
    };

    if (preSelectedId && filtered.find(r => r.id === parseInt(preSelectedId))) {
      select.value = preSelectedId;
      this.selectReservation(preSelectedId);
    } else if (filtered.length > 0) {
      // Default to checked-in guest or first match
      const defaultChoice = filtered.find(r => r.status === 'checked_in') || filtered[0];
      select.value = defaultChoice.id;
      this.selectReservation(defaultChoice.id);
    }
  },

  async selectReservation(reservationId) {
    this.selectedReservationId = reservationId;
    const display = document.getElementById('billing-folio-display');
    const printBtn = document.getElementById('print-folio-btn');
    if (!display) return;

    display.innerHTML = `
      <div style="padding:48px; text-align:center; color:#6B7280;">Loading folios & accounts...</div>
    `;

    try {
      this.folios = await API.get(`/api/reservations/${reservationId}/folios`);
      const resDetail = await API.get(`/api/reservations/${reservationId}`);
      
      if (!this.activeFolioId || !this.folios.find(f => f.id === this.activeFolioId)) {
        this.activeFolioId = this.folios[0]?.id;
      }

      if (printBtn) {
        printBtn.disabled = false;
        printBtn.onclick = () => {
          const token = API.getToken() || '';
          window.open(`/api/reservations/${reservationId}/invoice.pdf?token=${encodeURIComponent(token)}`, '_blank');
        };
      }

      this.renderFoliosView(resDetail);
    } catch (e) {
      display.innerHTML = `<div style="color:#DC2626; padding:24px;">Failed to load billing details: ${e.message}</div>`;
    }
  },

  renderFoliosView(resDetail) {
    const display = document.getElementById('billing-folio-display');
    if (!display) return;

    const currentFolio = this.folios.find(f => f.id === this.activeFolioId) || this.folios[0];

    // Folio Tabs HTML
    const folioTabsHtml = this.folios.map(f => `
      <button class="segmented-btn ${f.id === currentFolio.id ? 'active' : ''} folio-tab-btn" data-folio-id="${f.id}" style="display:flex; align-items:center; gap:6px;">
        <span>${f.name}</span>
        ${f.is_master ? '<span class="badge badge-info" style="font-size:9px; height:16px; padding:0 4px;">MASTER</span>' : ''}
        <span class="font-mono" style="font-size:11px; opacity:0.8;">(${formatCurrency(f.balance_due)})</span>
      </button>
    `).join('');

    // Summary calculation across all folios
    let totalAllFolios = 0;
    let paidAllFolios = 0;
    this.folios.forEach(f => {
      totalAllFolios += parseFloat(f.total_amount);
      paidAllFolios += parseFloat(f.total_paid);
    });
    const netBalanceAll = totalAllFolios - paidAllFolios;

    display.innerHTML = `
      <!-- Stay Particulars Card -->
      <div class="card" style="padding:16px 20px; margin-bottom:16px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="font-size:16px; font-weight:700; color:#111827;">${resDetail.guest ? resDetail.guest.full_name : 'Guest'}</div>
            <div style="font-size:12px; color:#6B7280; margin-top:2px;">
              Room <strong>${resDetail.room ? resDetail.room.number : '—'}</strong> (${resDetail.room && resDetail.room.room_type ? resDetail.room.room_type.name : '—'}) ·
              ${formatDate(resDetail.check_in_date)} to ${formatDate(resDetail.check_out_date)} (${resDetail.nights} nights)
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:12px;">
            <div style="text-align:right;">
              <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Combined Net Balance</div>
              <div class="font-mono font-bold" style="font-size:16px; color:${netBalanceAll > 0 ? '#DC2626' : '#059669'};">
                ${formatCurrency(netBalanceAll)}
              </div>
            </div>
            <span class="badge ${resDetail.status === 'checked_in' ? 'badge-success' : 'badge-info'}" style="text-transform:uppercase;">
              ${resDetail.status}
            </span>
          </div>
        </div>
      </div>

      ${resDetail.status === 'booked' ? `
        <!-- Upcoming Stay Banner -->
        <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px 16px; margin-bottom:16px; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">
          <div style="display:flex; align-items:center; gap:10px;">
            <span style="font-size:22px;">📅</span>
            <div>
              <div style="font-size:13px; font-weight:700; color:#166534;">Upcoming Stay (Not Checked In Yet)</div>
              <div style="font-size:12px; color:#15803D; margin-top:2px;">
                Agreed Stay: <strong>${resDetail.nights} night(s)</strong> @ <strong>${formatCurrency(resDetail.nightly_rate)}</strong>/night = <strong>${formatCurrency(resDetail.nightly_rate * resDetail.nights)}</strong> (+ GST/taxes).
                Room night charges will post automatically to this folio upon check-in.
              </div>
            </div>
          </div>
          <button class="btn btn-sm btn-primary" id="collect-advance-deposit-btn" style="background:#16A34A; border-color:#16A34A; display:flex; align-items:center; gap:6px;">
            <span>💳 Collect Advance Deposit</span>
          </button>
        </div>
      ` : ''}

      <!-- Multi-Folio Split Tabs -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
        <div class="segmented-control" id="folio-tabs-bar" style="overflow-x:auto;">
          ${folioTabsHtml}
        </div>
        <button class="btn btn-secondary btn-sm" id="add-split-folio-btn">
          <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" /></svg>
          <span>Add Split Folio</span>
        </button>
      </div>

      <!-- Bulk Action Bar (Hidden until items selected) -->
      <div id="folio-bulk-actions-bar" style="display:none; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:6px; padding:8px 16px; margin-bottom:12px; justify-content:space-between; align-items:center;">
        <div style="font-size:12px; font-weight:600; color:#1E40AF;" id="bulk-selection-count">0 items selected</div>
        <div style="display:flex; gap:8px; align-items:center;">
          <select id="bulk-move-target-folio" class="form-select font-mono" style="height:30px; font-size:11px;">
            ${this.folios.filter(f => f.id !== currentFolio.id).map(f => `<option value="${f.id}">Move to ${f.name}</option>`).join('')}
          </select>
          <button class="btn btn-primary btn-sm" id="bulk-move-btn" style="height:30px; font-size:11px;">Move Items</button>
        </div>
      </div>

      <!-- 2-Column Ledger & Settlement Layout -->
      <div class="folio-layout-grid" style="display:grid; grid-template-columns: 2fr 1fr; gap:20px;">
        <!-- Left: Itemized Charges & Payments in Active Folio -->
        <div style="display:flex; flex-direction:column; gap:16px;">
          <!-- Charges Table -->
          <div class="card" style="padding:20px; border:1px solid #E5E7EB;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h3 style="font-size:14px; font-weight:700; color:#111827; margin:0;">Charges in Folio: ${currentFolio.name}</h3>
              <div style="display:flex; gap:8px;">
                <button class="btn btn-secondary btn-sm" id="transfer-all-folio-btn" title="Transfer all line items to another folio">
                  Transfer All...
                </button>
                <button class="btn btn-primary btn-sm" id="add-charge-btn">
                  + Add Charge
                </button>
              </div>
            </div>

            <div class="table-responsive">
              <table class="data-table" style="font-size:12px;">
                <thead>
                  <tr>
                    <th style="width:24px;"><input type="checkbox" id="select-all-charges"></th>
                    <th>DATE</th>
                    <th>DESCRIPTION</th>
                    <th>CATEGORY</th>
                    <th class="text-right">AMOUNT</th>
                  </tr>
                </thead>
                <tbody>
                  ${currentFolio.items.length === 0 ? `
                    <tr><td colspan="5" style="text-align:center; padding:24px; color:#6B7280;">No charges in this folio.</td></tr>
                  ` : currentFolio.items.map(item => `
                    <tr>
                      <td><input type="checkbox" class="charge-item-checkbox" value="${item.id}"></td>
                      <td>${formatDate(item.date)}</td>
                      <td style="font-weight:600; color:#111827;">${item.description}</td>
                      <td><span class="badge badge-neutral" style="font-size:10px;">${item.category.toUpperCase()}</span></td>
                      <td class="text-right font-mono font-bold" style="${parseFloat(item.amount) < 0 ? 'color:#059669;' : ''}">
                        ${formatCurrency(item.amount)}
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Payments Table -->
          <div class="card" style="padding:20px; border:1px solid #E5E7EB;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h3 style="font-size:14px; font-weight:700; color:#111827; margin:0;">Payments & Credits</h3>
              <div style="display:flex; gap:8px;">
                <button class="btn btn-primary btn-sm" id="collect-card-btn" style="background:#2563EB;">
                  💳 Collect Card (Stripe)
                </button>
                <button class="btn btn-secondary btn-sm" id="record-manual-pmt-btn">
                  + Manual Payment
                </button>
              </div>
            </div>

            <div class="table-responsive">
              <table class="data-table" style="font-size:12px;">
                <thead>
                  <tr>
                    <th>DATE</th>
                    <th>METHOD</th>
                    <th>REFERENCE</th>
                    <th class="text-right">AMOUNT</th>
                    <th style="text-align:right;">ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  ${!currentFolio.payments || currentFolio.payments.length === 0 ? `
                    <tr><td colspan="5" style="text-align:center; padding:24px; color:#6B7280;">No payments allocated to this folio.</td></tr>
                  ` : currentFolio.payments.map(p => `
                    <tr>
                      <td>${formatDate(p.date)}</td>
                      <td><span class="badge badge-success" style="font-size:10px;">${p.method.toUpperCase()}</span></td>
                      <td class="font-mono" style="font-size:11px; color:#6B7280;">${p.reference || '—'}</td>
                      <td class="text-right font-mono font-bold" style="color:${parseFloat(p.amount) < 0 ? '#DC2626' : '#059669'};">
                        ${formatCurrency(p.amount)}
                      </td>
                      <td style="text-align:right;">
                        ${parseFloat(p.amount) > 0 && !p.is_refund ? `
                          <button class="btn btn-ghost btn-sm refund-payment-btn" data-id="${p.id}" data-amt="${p.amount}" style="color:#DC2626; font-size:11px; padding:2px 6px;">
                            Refund
                          </button>
                        ` : ''}
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Right: Folio Financial Breakdown & Actions -->
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div class="card" style="padding:20px; border:1px solid #E5E7EB;">
            <h4 style="font-size:13px; font-weight:700; color:#111827; margin:0 0 16px 0; text-transform:uppercase;">
              Folio Summary · ${currentFolio.name}
            </h4>

            <div style="display:flex; flex-direction:column; gap:10px; font-size:13px; border-bottom:1px solid #E5E7EB; padding-bottom:14px; margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between;">
                <span style="color:#6B7280;">Folio Charges Total:</span>
                <span class="font-mono font-bold">${formatCurrency(currentFolio.total_amount)}</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span style="color:#6B7280;">Folio Payments & Credits:</span>
                <span class="font-mono font-bold" style="color:#059669;">-${formatCurrency(currentFolio.total_paid)}</span>
              </div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <span style="font-size:14px; font-weight:700; color:#111827;">Balance Due:</span>
              <span class="font-mono font-bold" style="font-size:18px; color:${parseFloat(currentFolio.balance_due) > 0 ? '#DC2626' : '#059669'};">
                ${formatCurrency(currentFolio.balance_due)}
              </span>
            </div>

            <!-- Quick Folio Actions -->
            <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:14px;">
              <button class="btn btn-primary btn-md" id="right-col-record-pmt-btn" style="width:100%; justify-content:center; font-weight:600; padding:10px 14px;">
                💳 Record / Settle Payment
              </button>
              <button class="btn btn-secondary btn-md" id="right-col-add-charge-btn" style="width:100%; justify-content:center; padding:9px 14px;">
                + Add Folio Charge
              </button>
            </div>

            ${!currentFolio.is_master ? `
              <div style="display:flex; gap:8px; border-top:1px solid #E5E7EB; padding-top:14px;">
                <button class="btn btn-secondary btn-sm" id="rename-folio-btn" style="flex:1;">Rename Folio</button>
                <button class="btn btn-ghost btn-sm" id="delete-folio-btn" style="color:#DC2626;">Delete</button>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;

    this.bindFolioEvents(resDetail, currentFolio);
  },

  bindFolioEvents(resDetail, currentFolio) {
    // Tab switching
    document.querySelectorAll('.folio-tab-btn').forEach(btn => {
      btn.onclick = () => {
        this.activeFolioId = parseInt(btn.getAttribute('data-folio-id'));
        this.selectReservation(this.selectedReservationId);
      };
    });

    // Add split folio
    const addBtn = document.getElementById('add-split-folio-btn');
    if (addBtn) addBtn.onclick = () => this.openAddFolioModal();

    // Add charge
    const addChgBtn = document.getElementById('add-charge-btn');
    if (addChgBtn) addChgBtn.onclick = () => this.openAddChargeModal(currentFolio);

    const rightChgBtn = document.getElementById('right-col-add-charge-btn');
    if (rightChgBtn) rightChgBtn.onclick = () => this.openAddChargeModal(currentFolio);

    // Record manual payment
    const manualPmtBtn = document.getElementById('record-manual-pmt-btn');
    if (manualPmtBtn) manualPmtBtn.onclick = () => this.openRecordPaymentModal(currentFolio, resDetail);

    const rightPmtBtn = document.getElementById('right-col-record-pmt-btn');
    if (rightPmtBtn) rightPmtBtn.onclick = () => this.openRecordPaymentModal(currentFolio, resDetail);

    const advanceBtn = document.getElementById('collect-advance-deposit-btn');
    if (advanceBtn) advanceBtn.onclick = () => this.openRecordPaymentModal(currentFolio, resDetail);

    // Stripe Collect Card
    const stripeBtn = document.getElementById('collect-card-btn');
    if (stripeBtn) stripeBtn.onclick = () => this.openStripePaymentModal(resDetail, currentFolio);

    // Refund button
    document.querySelectorAll('.refund-payment-btn').forEach(btn => {
      btn.onclick = () => {
        const pid = parseInt(btn.getAttribute('data-id'));
        const amt = btn.getAttribute('data-amt');
        this.openRefundModal(pid, amt);
      };
    });

    // Checkbox selections for bulk move
    const checkboxes = document.querySelectorAll('.charge-item-checkbox');
    const selectAll = document.getElementById('select-all-charges');
    const bulkBar = document.getElementById('folio-bulk-actions-bar');
    const countEl = document.getElementById('bulk-selection-count');

    const updateBulkBar = () => {
      const selected = Array.from(checkboxes).filter(c => c.checked).map(c => parseInt(c.value));
      if (selected.length > 0 && this.folios.length > 1) {
        bulkBar.style.display = 'flex';
        countEl.textContent = `${selected.length} item(s) selected`;
      } else {
        bulkBar.style.display = 'none';
      }
    };

    if (selectAll) {
      selectAll.onchange = () => {
        checkboxes.forEach(c => c.checked = selectAll.checked);
        updateBulkBar();
      };
    }

    checkboxes.forEach(c => c.onchange = updateBulkBar);

    // Bulk move action
    const bulkMoveBtn = document.getElementById('bulk-move-btn');
    if (bulkMoveBtn) {
      bulkMoveBtn.onclick = async () => {
        const itemIds = Array.from(checkboxes).filter(c => c.checked).map(c => parseInt(c.value));
        const targetFolioId = parseInt(document.getElementById('bulk-move-target-folio').value);

        if (!itemIds.length || !targetFolioId) return;

        try {
          const res = await API.post('/api/folio-items/bulk-move', {
            item_ids: itemIds,
            folio_id: targetFolioId,
          });
          UI.toast(res.message, 'success');
          this.selectReservation(this.selectedReservationId);
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      };
    }

    // Transfer all
    const transferBtn = document.getElementById('transfer-all-folio-btn');
    if (transferBtn) {
      transferBtn.onclick = () => this.openTransferAllModal(currentFolio);
    }

    // Rename folio
    const renameBtn = document.getElementById('rename-folio-btn');
    if (renameBtn) {
      renameBtn.onclick = () => this.openRenameFolioModal(currentFolio);
    }

    // Delete folio
    const deleteBtn = document.getElementById('delete-folio-btn');
    if (deleteBtn) {
      deleteBtn.onclick = async () => {
        if (!confirm(`Are you sure you want to delete folio '${currentFolio.name}'?`)) return;
        try {
          await API.delete(`/api/folios/${currentFolio.id}`);
          UI.toast('Folio deleted.', 'success');
          this.activeFolioId = null;
          this.selectReservation(this.selectedReservationId);
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      };
    }
  },

  openAddFolioModal() {
    UI.modal({
      title: 'Create Additional Folio Tab',
      contentHtml: `
        <div class="form-group">
          <label class="form-label">Folio Name <span class="required-mark">*</span></label>
          <input type="text" id="new-folio-name" class="form-input" placeholder="e.g. Company Charges, Incidentals, Room 2">
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="create-folio-btn">Create Folio</button>
      `,
    });

    document.getElementById('create-folio-btn').onclick = async () => {
      const name = document.getElementById('new-folio-name').value.trim();
      if (!name) return;

      try {
        const created = await API.post(`/api/reservations/${this.selectedReservationId}/folios`, { name });
        UI.toast(`Folio '${name}' created.`, 'success');
        UI.closeModal();
        this.activeFolioId = created.id;
        this.selectReservation(this.selectedReservationId);
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  openTransferAllModal(currentFolio) {
    const targetOptions = this.folios
      .filter(f => f.id !== currentFolio.id)
      .map(f => `<option value="${f.id}">${f.name} (${f.is_master ? 'Master' : 'Split'})</option>`)
      .join('');

    UI.modal({
      title: `Transfer All Items from ${currentFolio.name}`,
      contentHtml: `
        <div class="form-group">
          <label class="form-label">Destination Folio</label>
          <select id="transfer-target-folio" class="form-select">${targetOptions}</select>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="transfer-confirm-btn">Execute Transfer</button>
      `,
    });

    document.getElementById('transfer-confirm-btn').onclick = async () => {
      const targetId = parseInt(document.getElementById('transfer-target-folio').value);
      try {
        const res = await API.post(`/api/folios/${currentFolio.id}/transfer`, { to_folio_id: targetId });
        UI.toast(res.message, 'success');
        UI.closeModal();
        this.selectReservation(this.selectedReservationId);
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  openRenameFolioModal(currentFolio) {
    UI.modal({
      title: `Rename Folio · ${currentFolio.name}`,
      contentHtml: `
        <div class="form-group">
          <label class="form-label">New Folio Name</label>
          <input type="text" id="rename-val" class="form-input" value="${currentFolio.name}">
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="rename-save-btn">Save</button>
      `,
    });

    document.getElementById('rename-save-btn').onclick = async () => {
      const name = document.getElementById('rename-val').value.trim();
      if (!name) return;
      try {
        await API.patch(`/api/folios/${currentFolio.id}`, { name });
        UI.toast('Folio renamed.', 'success');
        UI.closeModal();
        this.selectReservation(this.selectedReservationId);
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  openAddChargeModal(currentFolio) {
    const today = window.currentBusinessDate || new Date().toISOString().slice(0, 10);
    UI.modal({
      title: `Add Charge to ${currentFolio.name}`,
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:12px;">
          <div class="form-group">
            <label class="form-label">Charge Date</label>
            <input type="date" id="charge-date" class="form-input" value="${today}" required>
          </div>
          <div class="form-group">
            <label class="form-label">Category</label>
            <select id="charge-cat" class="form-select">
              <option value="minibar">Minibar / Snacks</option>
              <option value="restaurant">Restaurant & Dining</option>
              <option value="service">Laundry & Butler Service</option>
              <option value="room">Room Charge</option>
              <option value="adjustment">Courtesy Adjustment</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Description</label>
            <input type="text" id="charge-desc" class="form-input" placeholder="e.g. San Pellegrino, Royal Dinner Buffet" required>
          </div>
          <div class="form-group">
            <label class="form-label">Amount (${getCurrencySymbol()}${getActiveCurrency()})</label>
            <input type="number" step="0.5" id="charge-amt" class="form-input font-mono" placeholder="500.00" required>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="post-charge-btn">Post Charge</button>
      `,
    });

    document.getElementById('post-charge-btn').onclick = async () => {
      const dt = document.getElementById('charge-date').value;
      const cat = document.getElementById('charge-cat').value;
      const desc = document.getElementById('charge-desc').value.trim();
      const amt = parseFloat(document.getElementById('charge-amt').value);

      if (!desc || isNaN(amt)) {
        UI.toast('Please enter description and amount.', 'error');
        return;
      }

      try {
        await API.post(`/api/billing/reservations/${this.selectedReservationId}/charges`, {
          folio_id: currentFolio.id,
          date: dt,
          description: desc,
          category: cat,
          amount: amt,
        });
        UI.toast('Charge posted to folio.', 'success');
        UI.closeModal();
        this.selectReservation(this.selectedReservationId);
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  openRecordPaymentModal(currentFolio, resDetail = null) {
    const today = window.currentBusinessDate || new Date().toISOString().slice(0, 10);
    let bal = Math.max(0, parseFloat(currentFolio.balance_due));
    if (bal === 0 && resDetail && resDetail.status === 'booked') {
      bal = (parseFloat(resDetail.nightly_rate || 0) * parseInt(resDetail.nights || 1));
    }

    UI.modal({
      title: `Record / Settle Payment · ${currentFolio.name}`,
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:12px;">
          <div class="form-group">
            <label class="form-label">Payment Date</label>
            <input type="date" id="pmt-date" class="form-input" value="${today}" required>
          </div>
          <div class="form-group">
            <label class="form-label">Payment Method</label>
            <select id="pmt-method" class="form-select">
              <option value="bank_transfer" selected>UPI / QR Code / NetBanking</option>
              <option value="cash">Cash Settlement</option>
              <option value="credit_card">Credit / Debit Card (POS Terminal)</option>
              <option value="other">Company Direct Bill</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Payment Amount (${getCurrencySymbol()}${getActiveCurrency()})</label>
            <input type="number" step="0.5" id="pmt-amt" class="form-input font-mono" value="${bal.toFixed(2)}" placeholder="0.00" required>
            ${resDetail && resDetail.status === 'booked' ? `
              <span style="font-size:11px; color:#166534; margin-top:2px; display:block;">Suggested stay total: ${formatCurrency(bal)} (Advance deposit)</span>
            ` : ''}
          </div>
          <div class="form-group">
            <label class="form-label">Authorization / UPI / Reference #</label>
            <input type="text" id="pmt-ref" class="form-input font-mono" placeholder="e.g. UPI-987654321, CASH-RC-101">
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="record-pmt-btn">Record Payment</button>
      `,
    });

    document.getElementById('record-pmt-btn').onclick = async () => {
      const dt = document.getElementById('pmt-date').value;
      const meth = document.getElementById('pmt-method').value;
      const amt = parseFloat(document.getElementById('pmt-amt').value);
      const ref = document.getElementById('pmt-ref').value.trim();

      if (isNaN(amt) || amt <= 0) {
        UI.toast('Please enter a positive payment amount.', 'error');
        return;
      }

      try {
        await API.post(`/api/billing/reservations/${this.selectedReservationId}/payments`, {
          folio_id: currentFolio.id,
          date: dt,
          method: meth,
          amount: amt,
          reference: ref || null,
        });
        UI.toast('Payment recorded successfully.', 'success');
        UI.closeModal();
        if (window.refreshAllDashboardStats) {
          window.refreshAllDashboardStats();
        }
        this.selectReservation(this.selectedReservationId);
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  openStripePaymentModal(resDetail, currentFolio) {
    const bal = Math.max(0, parseFloat(currentFolio.balance_due));

    UI.modal({
      title: 'Stripe Payment Gateway',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="padding:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; font-size:12px;">
            <div>Guest: <strong>${resDetail.guest ? resDetail.guest.full_name : 'Guest'}</strong></div>
            <div>Reservation: <strong class="font-mono">#${resDetail.confirmation_number}</strong></div>
            <div>Target Folio: <strong>${currentFolio.name}</strong></div>
          </div>

          <div class="form-group">
            <label class="form-label">Charge Amount (${getCurrencySymbol()}${getActiveCurrency()})</label>
            <input type="number" step="0.5" id="stripe-amt" class="form-input font-mono" value="${bal.toFixed(2)}" required>
          </div>

          <div id="stripe-intent-info" style="display:none; padding:12px; border-radius:6px; font-size:12px;"></div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="stripe-process-btn">Create Payment Intent</button>
      `,
    });

    document.getElementById('stripe-process-btn').onclick = async () => {
      const amt = parseFloat(document.getElementById('stripe-amt').value);
      if (isNaN(amt) || amt <= 0) {
        UI.toast('Please enter a valid amount.', 'error');
        return;
      }

      try {
        const res = await API.post('/api/payments/create-intent', {
          reservation_id: this.selectedReservationId,
          folio_id: currentFolio.id,
          amount: amt,
        });

        const infoBox = document.getElementById('stripe-intent-info');
        infoBox.style.display = 'block';

        if (res.manual_mode) {
          infoBox.style.background = '#FFFBEB';
          infoBox.style.border = '1px solid #FDE68A';
          infoBox.style.color = '#92400E';
          infoBox.innerHTML = `
            <strong>Stripe Test / Manual Mode</strong><br>
            Stripe keys are not configured or simulated. Intent ID: <span class="font-mono">${res.payment_intent_id}</span>.
            <div style="margin-top:8px;">
              <button class="btn btn-primary btn-sm" id="stripe-confirm-mock-btn">Simulate Successful Card Authorization</button>
            </div>
          `;

          document.getElementById('stripe-confirm-mock-btn').onclick = async () => {
            await API.post(`/api/billing/reservations/${this.selectedReservationId}/payments`, {
              folio_id: currentFolio.id,
              date: window.currentBusinessDate || new Date().toISOString().slice(0, 10),
              method: 'stripe',
              amount: amt,
              reference: `Stripe ${res.payment_intent_id}`,
            });
            UI.toast(`Card payment of ${formatCurrency(amt)} captured.`, 'success');
            UI.closeModal();
            this.selectReservation(this.selectedReservationId);
          };
        } else {
          infoBox.style.background = '#ECFDF5';
          infoBox.style.border = '1px solid #A7F3D0';
          infoBox.style.color = '#065F46';
          infoBox.innerHTML = `
            <strong>Stripe Live Intent Initialized</strong><br>
            Client Secret: <span class="font-mono">${res.client_secret.slice(0, 20)}...</span><br>
            Ready for Stripe.js Card Element mount.
          `;
        }
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  openRefundModal(paymentId, originalAmount) {
    UI.modal({
      title: `Issue Payment Refund · Payment #${paymentId}`,
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:12px;">
          <div style="font-size:12px; color:#6B7280;">
            Original Payment Amount: <strong class="font-mono">${formatCurrency(originalAmount)}</strong>
          </div>
          <div class="form-group">
            <label class="form-label">Refund Amount (${getCurrencySymbol()}${getActiveCurrency()})</label>
            <input type="number" step="0.5" id="refund-amt" class="form-input font-mono" value="${parseFloat(originalAmount).toFixed(2)}" max="${originalAmount}">
          </div>
          <div class="form-group">
            <label class="form-label">Reason for Refund</label>
            <input type="text" id="refund-reason" class="form-input" placeholder="e.g. Guest checkout adjustment, cancellation refund">
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="confirm-refund-btn" style="background:#DC2626; border-color:#DC2626;">Process Refund</button>
      `,
    });

    document.getElementById('confirm-refund-btn').onclick = async () => {
      const amt = parseFloat(document.getElementById('refund-amt').value);
      const reason = document.getElementById('refund-reason').value.trim();

      if (isNaN(amt) || amt <= 0 || amt > parseFloat(originalAmount)) {
        UI.toast('Please enter a valid refund amount.', 'error');
        return;
      }

      try {
        await API.post(`/api/payments/${paymentId}/refund`, {
          amount: amt,
          reason: reason || null,
        });
        UI.toast(`Refund of ${formatCurrency(amt)} recorded.`, 'success');
        UI.closeModal();
        this.selectReservation(this.selectedReservationId);
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },
};
