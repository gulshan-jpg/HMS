/**
 * CheckinOS - Policies View
 * Dedicated management for Guest Cancellation Policies, No-Show Penalties, and Guarantee Terms.
 */

window.Pages = window.Pages || {};

window.Pages.Policies = {
  async render(container) {
    container.innerHTML = `
      <div class="page-header" style="margin-bottom:20px;">
        <div>
          <h1 class="page-title">Cancellation Policies & Terms</h1>
          <div class="page-header-desc">Define free cancellation windows, late cancellation penalty rules, no-show fees, and automated refund terms.</div>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:20px; max-width:1100px;">
        <!-- Information Banner -->
        <div class="card" style="padding:16px 20px; border-left:4px solid #111827; background:#FFFFFF; display:flex; justify-content:space-between; align-items:center;">
          <div style="font-size:13px; color:#374151;">
            <strong>Automated Folio Penalties:</strong> When a reservation is cancelled outside its free cancellation window, CheckinOS automatically computes the policy penalty, posts a <code>cancellation_fee</code> folio line, and nets out deposit refunds.
          </div>
          <button class="btn btn-primary btn-sm" id="page-new-policy-btn" style="white-space:nowrap;">
            <svg style="width:14px; height:14px; margin-right:4px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            <span>Create Policy</span>
          </button>
        </div>

        <!-- Policies Table Card -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB; background:#FFFFFF;">
          <div id="policies-table-content">
            <div style="padding:24px; text-align:center; color:#6B7280;">Loading cancellation policies...</div>
          </div>
        </div>
      </div>
    `;

    document.getElementById('page-new-policy-btn').onclick = () => this.openPolicyModal();
    await this.loadPolicies();
  },

  async loadPolicies() {
    const tableWrap = document.getElementById('policies-table-content');
    if (!tableWrap) return;

    try {
      const policies = await API.get('/api/cancellation-policies');
      if (!policies || policies.length === 0) {
        tableWrap.innerHTML = '<div style="padding:32px; text-align:center; color:#6B7280;">No cancellation policies configured yet. Click "Create Policy" above.</div>';
        return;
      }

      let html = `
        <div class="data-table-container">
          <table class="data-table" style="width:100%; font-size:13px;">
            <thead>
              <tr>
                <th>POLICY NAME</th>
                <th>DESCRIPTION</th>
                <th>FREE CANCEL WINDOW</th>
                <th>PENALTY TYPE</th>
                <th>PENALTY VALUE</th>
                <th>STATUS</th>
                <th style="text-align:right;">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
      `;

      policies.forEach(p => {
        let penStr = p.penalty_type.replace('_', ' ');
        if (p.penalty_type === 'percent') penStr = `${p.penalty_value}% of stay`;
        else if (p.penalty_type === 'fixed') penStr = `${formatCurrency(p.penalty_value)}`;
        else if (p.penalty_type === 'first_night') penStr = '1st Night Room Rate';
        else if (p.penalty_type === 'none') penStr = 'Free (No Penalty)';

        html += `
          <tr>
            <td style="font-weight:700; color:#111827;">${p.name}</td>
            <td style="font-size:12px; color:#6B7280; max-width:320px;">${p.description || '—'}</td>
            <td class="font-mono font-bold">${p.free_cancel_days === 0 ? 'Non-refundable' : `Up to ${p.free_cancel_days}d before arrival`}</td>
            <td style="text-transform:capitalize;">${p.penalty_type.replace('_', ' ')}</td>
            <td class="font-mono font-bold" style="color:${p.penalty_type === 'none' ? '#059669' : '#DC2626'};">${penStr}</td>
            <td>
              <span class="badge ${p.active ? 'badge-success' : 'badge-neutral'}" style="font-size:10px;">
                ${p.active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </td>
            <td style="text-align:right;">
              <button class="btn btn-secondary btn-sm edit-pol-action" data-id="${p.id}" style="padding:3px 10px; font-size:11px;">Edit</button>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table></div>`;
      tableWrap.innerHTML = html;

      tableWrap.querySelectorAll('.edit-pol-action').forEach(btn => {
        btn.onclick = () => {
          const pid = parseInt(btn.getAttribute('data-id'));
          const target = policies.find(x => x.id === pid);
          if (target) this.openPolicyModal(target);
        };
      });
    } catch (e) {
      tableWrap.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load policies: ${e.message}</div>`;
    }
  },

  openPolicyModal(policy = null) {
    const isEdit = !!policy;

    UI.modal({
      title: isEdit ? `Edit Policy · ${policy.name}` : 'Create Cancellation Policy',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div class="form-group">
            <label class="form-label">Policy Name <span class="required-mark">*</span></label>
            <input type="text" id="policy-modal-name" class="form-input" value="${policy ? policy.name : ''}" placeholder="e.g. Flexible 24h, Strict Non-Refundable" required>
          </div>

          <div class="form-group">
            <label class="form-label">Description</label>
            <input type="text" id="policy-modal-desc" class="form-input" value="${policy ? (policy.description || '') : ''}" placeholder="Clear explanation displayed to staff and guest during cancellation">
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Free Cancellation Window (Days)</label>
              <input type="number" min="0" id="policy-modal-free-days" class="form-input font-mono" value="${policy ? policy.free_cancel_days : '1'}" placeholder="0 = non-refundable">
              <span class="form-hint-msg" style="font-size:11px; color:#6B7280;">Days prior to arrival when cancellation is 100% free.</span>
            </div>
            <div class="form-group">
              <label class="form-label">Late Cancellation Penalty</label>
              <select id="policy-modal-pen-type" class="form-select">
                <option value="first_night" ${policy && policy.penalty_type === 'first_night' ? 'selected' : ''}>1 Night Room Rate</option>
                <option value="percent" ${policy && policy.penalty_type === 'percent' ? 'selected' : ''}>Percentage of Stay (%)</option>
                <option value="fixed" ${policy && policy.penalty_type === 'fixed' ? 'selected' : ''}>Fixed Amount (${getCurrencySymbol()})</option>
                <option value="none" ${policy && policy.penalty_type === 'none' ? 'selected' : ''}>No Penalty (Free Cancellation)</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Penalty Value (% or ${getCurrencySymbol()})</label>
            <input type="number" step="0.5" id="policy-modal-pen-val" class="form-input font-mono" value="${policy ? policy.penalty_value : '100'}">
          </div>

          <div>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" id="policy-modal-active" ${!policy || policy.active ? 'checked' : ''} style="width:16px; height:16px;">
              <span style="font-weight:500;">Active Policy (Available on Rate Plans and Reservations)</span>
            </label>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="save-policy-modal-btn">${isEdit ? 'Update Policy' : 'Save Policy'}</button>
      `,
    });

    document.getElementById('save-policy-modal-btn').onclick = async () => {
      const name = document.getElementById('policy-modal-name').value.trim();
      const desc = document.getElementById('policy-modal-desc').value.trim();
      const freeDays = parseInt(document.getElementById('policy-modal-free-days').value) || 0;
      const penType = document.getElementById('policy-modal-pen-type').value;
      const penVal = parseFloat(document.getElementById('policy-modal-pen-val').value) || 0;
      const active = document.getElementById('policy-modal-active').checked;

      if (!name) {
        UI.toast('Policy Name is required.', 'error');
        return;
      }

      const payload = {
        name,
        description: desc,
        free_cancel_days: freeDays,
        penalty_type: penType,
        penalty_value: penVal,
        no_show_penalty: penType,
        active,
      };

      try {
        if (isEdit) {
          await API.put(`/api/cancellation-policies/${policy.id}`, payload);
          UI.toast(`Policy '${name}' updated successfully.`, 'success');
        } else {
          await API.post('/api/cancellation-policies', payload);
          UI.toast(`Policy '${name}' created successfully.`, 'success');
        }
        UI.closeModal();
        this.loadPolicies();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  }
};
