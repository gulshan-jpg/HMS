/**
 * CheckinOS - Settings View
 * Tabs: Profile, Team Management, Rate Plans, Cancellation Policies, Taxes, and Property Metadata.
 */

window.Pages = window.Pages || {};

window.Pages.Settings = {
  currentTab: 'rate_plans', // default to rate_plans for rapid tier-1 access

  async render(container) {
    const user = window.currentUser || await API.me().catch(() => ({}));
    const org = user.organization || { name: 'Hotel Grand', plan: 'pro' };

    const roleLabels = {
      owner: 'HOTEL OWNER',
      admin: 'ADMINISTRATOR',
      manager: 'GENERAL MANAGER',
      front_desk: 'FRONT DESK',
      housekeeping: 'HOUSEKEEPING',
      accountant: 'ACCOUNTANT'
    };
    const roleBadge = roleLabels[user.role] || (user.role ? user.role.toUpperCase() : 'STAFF');

    const initials = (user.full_name || user.username || 'U')
      .split(' ')
      .map(n => n[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();

    const currentCurrency = getActiveCurrency();

    container.innerHTML = `
      <div class="page-header" style="margin-bottom:20px;">
        <div>
          <h1 class="page-title">Settings & Account</h1>
          <div class="page-header-desc">Manage your operator credentials, password, workspace preferences, and active session.</div>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:24px; max-width:850px;">
        <!-- 1. Operator Profile Card -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB; background:#FFFFFF;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; border-bottom:1px solid #F1F5F9; padding-bottom:18px;">
            <div style="display:flex; align-items:center; gap:16px;">
              <div style="width:54px; height:54px; border-radius:50%; background:#111827; color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:700;">
                ${initials}
              </div>
              <div>
                <h3 style="font-size:18px; font-weight:700; color:#111827; margin:0;">${user.full_name || user.username}</h3>
                <div style="font-size:12px; color:#6B7280; margin-top:2px;">${user.email || 'operator@hotel.com'} · ${org.name || 'CheckinOS'}</div>
              </div>
            </div>
            <span class="badge badge-info" style="font-size:11px; padding:4px 10px; font-weight:700;">
              ${roleBadge}
            </span>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
            <div>
              <label class="form-label" style="font-size:12px;">Full Name</label>
              <input type="text" id="settings-profile-fullname" class="form-input" value="${user.full_name || ''}" style="height:38px;">
            </div>
            <div>
              <label class="form-label" style="font-size:12px;">Work Email</label>
              <input type="email" class="form-input" value="${user.email || ''}" disabled style="height:38px; background:#F9FAFB; color:#6B7280;">
            </div>
            <div>
              <label class="form-label" style="font-size:12px;">Username</label>
              <input type="text" class="form-input font-mono" value="${user.username || ''}" disabled style="height:38px; background:#F9FAFB; color:#6B7280;">
            </div>
            <div>
              <label class="form-label" style="font-size:12px;">Assigned Role</label>
              <input type="text" class="form-input" value="${roleBadge}" disabled style="height:38px; background:#F9FAFB; color:#6B7280;">
            </div>
          </div>

          <div style="display:flex; justify-content:flex-end;">
            <button class="btn btn-primary btn-md" id="settings-save-profile-btn" style="height:38px; padding:0 20px;">
              Save Profile
            </button>
          </div>
        </div>

        <!-- 2. Security & Change Password Card -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB; background:#FFFFFF;">
          <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0 0 4px;">Security & Password</h3>
          <p style="font-size:12px; color:#6B7280; margin:0 0 18px;">Update your login password. Must be at least 8 characters with numbers and symbols.</p>

          <form id="settings-change-password-form" onsubmit="window.Pages.Settings.handleChangePassword(event)">
            <div style="display:flex; flex-direction:column; gap:14px; max-width:540px;">
              <div>
                <label class="form-label" style="font-size:12px;">Current Password</label>
                <input type="password" id="settings-curr-pwd" class="form-input" required placeholder="Enter current password" style="height:38px;">
              </div>
              <div>
                <label class="form-label" style="font-size:12px;">New Password</label>
                <input type="password" id="settings-new-pwd" class="form-input" required placeholder="New password (8+ chars)" style="height:38px;">
              </div>
              <div>
                <label class="form-label" style="font-size:12px;">Confirm New Password</label>
                <input type="password" id="settings-conf-pwd" class="form-input" required placeholder="Confirm new password" style="height:38px;">
              </div>

              <div>
                <button type="submit" id="settings-pwd-btn" class="btn btn-secondary btn-md" style="height:38px; padding:0 18px;">
                  Update Password
                </button>
              </div>
            </div>
          </form>
        </div>

        <!-- 3. Preferences & Display Card -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB; background:#FFFFFF;">
          <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0 0 4px;">Preferences & Display</h3>
          <p style="font-size:12px; color:#6B7280; margin:0 0 18px;">Configure personal workspace preferences. Changing currency dynamically updates all rates across the PMS.</p>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
            <div>
              <label class="form-label" style="font-size:12px;">Operating Currency</label>
              <select id="settings-pref-currency" class="form-select" style="height:38px; font-weight:600;">
                <option value="INR" ${currentCurrency === 'INR' ? 'selected' : ''}>INR (₹) — Indian Rupee</option>
                <option value="USD" ${currentCurrency === 'USD' ? 'selected' : ''}>USD ($) — US Dollar</option>
                <option value="EUR" ${currentCurrency === 'EUR' ? 'selected' : ''}>EUR (€) — Euro</option>
                <option value="GBP" ${currentCurrency === 'GBP' ? 'selected' : ''}>GBP (£) — British Pound</option>
                <option value="AED" ${currentCurrency === 'AED' ? 'selected' : ''}>AED (AED) — UAE Dirham</option>
                <option value="AUD" ${currentCurrency === 'AUD' ? 'selected' : ''}>AUD (A$) — Australian Dollar</option>
                <option value="CAD" ${currentCurrency === 'CAD' ? 'selected' : ''}>CAD (C$) — Canadian Dollar</option>
                <option value="SGD" ${currentCurrency === 'SGD' ? 'selected' : ''}>SGD (S$) — Singapore Dollar</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="font-size:12px;">Date Format</label>
              <select id="settings-pref-dateformat" class="form-select" style="height:38px;">
                <option value="DD/MM/YYYY" selected>DD/MM/YYYY (25/11/2026)</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD (2026-11-25)</option>
                <option value="MM/DD/YYYY">MM/DD/YYYY (11/25/2026)</option>
              </select>
            </div>
          </div>

          <div style="display:flex; flex-direction:column; gap:12px; padding-top:8px;">
            <label style="display:flex; align-items:center; gap:10px; cursor:pointer;">
              <input type="checkbox" id="settings-pref-sound" checked style="width:16px; height:16px;">
              <div>
                <strong style="font-size:13px; color:#111827;">Notification Chimes</strong>
                <div style="font-size:11px; color:#6B7280;">Play subtle audio alert on new OTA bookings and guest arrivals.</div>
              </div>
            </label>
            <label style="display:flex; align-items:center; gap:10px; cursor:pointer;">
              <input type="checkbox" id="settings-pref-auto-refresh" checked style="width:16px; height:16px;">
              <div>
                <strong style="font-size:13px; color:#111827;">Auto-refresh Dashboard Timeline</strong>
                <div style="font-size:11px; color:#6B7280;">Automatically poll and refresh rooms and reservations every 60 seconds.</div>
              </div>
            </label>
          </div>

          <div style="display:flex; justify-content:flex-end; margin-top:16px;">
            <button id="settings-save-prefs-btn" class="btn btn-primary btn-sm" style="height:36px; padding:0 20px;">
              Save Preferences
            </button>
          </div>
        </div>

        <!-- 4. Session & Sign Out Card -->
        <div class="card" style="padding:24px; border:1px solid #FECACA; background:#FFF5F5;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <h3 style="font-size:16px; font-weight:700; color:#991B1B; margin:0 0 4px;">Sign Out</h3>
              <p style="font-size:12px; color:#7F1D1D; margin:0;">End your active workstation session on this device. You will need to sign in again to access the PMS.</p>
            </div>
            <button class="btn btn-md" onclick="API.logout()" style="background:#DC2626; color:#FFFFFF; border:none; height:38px; padding:0 22px; font-weight:600; border-radius:6px; cursor:pointer;">
              Sign Out
            </button>
          </div>
        </div>

        <!-- Footer Developer Credit -->
        <div style="text-align:center; padding:12px 0 24px; font-size:12px; color:#9CA3AF;">
          CheckinOS v2.4 (Enterprise Edition) · Developed by <strong style="color:#111827;">Gulshan</strong>
        </div>
      </div>
    `;

    document.getElementById('settings-save-profile-btn').onclick = () => {
      const name = document.getElementById('settings-profile-fullname').value.trim();
      if (name && window.currentUser) {
        window.currentUser.full_name = name;
      }
      UI.toast('Profile details updated successfully.', 'success');
    };

    document.getElementById('settings-save-prefs-btn').onclick = async () => {
      const chosenCurr = document.getElementById('settings-pref-currency').value;
      localStorage.setItem('checkinos_currency', chosenCurr);
      if (window.currentUser && window.currentUser.organization) {
        window.currentUser.organization.currency = chosenCurr;
      }
      try {
        await API.patch('/api/org', { currency: chosenCurr });
      } catch (e) {}
      UI.toast(`Preferences saved: Operating currency set to ${chosenCurr} (${getCurrencySymbol(chosenCurr)})`, 'success');
    };
  },

  async handleChangePassword(e) {
    e.preventDefault();
    const curr = document.getElementById('settings-curr-pwd').value;
    const newP = document.getElementById('settings-new-pwd').value;
    const confP = document.getElementById('settings-conf-pwd').value;
    const btn = document.getElementById('settings-pwd-btn');

    if (!curr || !newP) {
      UI.toast('Please enter both current and new passwords.', 'warning');
      return;
    }
    if (newP !== confP) {
      UI.toast('New password and confirmation do not match.', 'error');
      return;
    }
    if (newP.length < 8) {
      UI.toast('New password must be at least 8 characters.', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Updating...';

    try {
      await API.post('/api/auth/change-password', {
        current_password: curr,
        new_password: newP,
      });
      UI.toast('Password changed successfully!', 'success');
      document.getElementById('settings-change-password-form').reset();
    } catch (err) {
      UI.toast(err.message || 'Failed to update password.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Update Password';
    }
  },

  // ── 1. RATE PLANS TAB ─────────────────────────────────────────────────────

  async renderRatePlansTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0;">Commercial Rate Plans</h3>
            <div style="font-size:12px; color:#6B7280; margin-top:2px;">Configures standard pricing modifiers, meals, minimum stays, and attached cancellation policies.</div>
          </div>
          <button class="btn btn-primary btn-sm" id="new-rate-plan-btn">
            <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            <span>Create Rate Plan</span>
          </button>
        </div>

        <div id="rate-plans-table-wrap">
          <div style="padding:24px; text-align:center; color:#6B7280;">Loading rate plans...</div>
        </div>
      </div>
    `;

    document.getElementById('new-rate-plan-btn').onclick = () => this.openRatePlanModal();

    try {
      const plans = await API.get('/api/rate-plans');
      const tableWrap = document.getElementById('rate-plans-table-wrap');

      if (!plans || plans.length === 0) {
        tableWrap.innerHTML = '<div style="padding:24px; text-align:center; color:#6B7280;">No rate plans configured yet.</div>';
        return;
      }

      let html = `
        <table class="data-table" style="width:100%; font-size:12px;">
          <thead>
            <tr>
              <th>CODE</th>
              <th>NAME & DESCRIPTION</th>
              <th>MODIFIER</th>
              <th>MEAL PLAN</th>
              <th>MIN STAY</th>
              <th>CANCELLATION</th>
              <th>REFUNDABLE</th>
              <th>STATUS</th>
              <th style="text-align:right;">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
      `;

      plans.forEach(p => {
        let modText = 'Base Rate';
        if (p.modifier_type === 'percent') {
          const val = parseFloat(p.modifier_value);
          modText = val === 0 ? 'Base Rate' : `${val > 0 ? '+' : ''}${val}%`;
        } else if (p.modifier_type === 'absolute') {
          modText = `+${formatCurrency(p.modifier_value)}`;
        } else if (p.modifier_type === 'fixed') {
          modText = `Fixed ${formatCurrency(p.modifier_value)}`;
        }

        const polName = p.cancellation_policy ? p.cancellation_policy.name : 'Default Policy';

        html += `
          <tr>
            <td class="font-mono font-bold">${p.code}</td>
            <td>
              <div style="font-weight:600; color:#111827;">${p.name}</div>
              <div style="font-size:11px; color:#6B7280; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.description || '—'}</div>
            </td>
            <td class="font-mono font-bold" style="color:#2563EB;">${modText}</td>
            <td style="text-transform:capitalize;">${(p.meal_plan || 'room_only').replace('_', ' ')}</td>
            <td class="font-mono">${p.min_stay} night(s)</td>
            <td style="font-size:11px; color:#4B5563;">${polName}</td>
            <td>
              <span class="badge ${p.refundable ? 'badge-success' : 'badge-neutral'}" style="font-size:10px;">
                ${p.refundable ? 'REFUNDABLE' : 'NON-REFUNDABLE'}
              </span>
            </td>
            <td>
              <span class="badge ${p.active ? 'badge-success' : 'badge-neutral'}" style="font-size:10px;">
                ${p.active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </td>
            <td style="text-align:right;">
              <button class="btn btn-secondary btn-sm edit-plan-btn" data-id="${p.id}" style="padding:2px 8px; font-size:11px;">Edit</button>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      tableWrap.innerHTML = html;

      tableWrap.querySelectorAll('.edit-plan-btn').forEach(btn => {
        btn.onclick = () => {
          const pid = parseInt(btn.getAttribute('data-id'));
          const targetPlan = plans.find(x => x.id === pid);
          if (targetPlan) this.openRatePlanModal(targetPlan);
        };
      });
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load rate plans: ${e.message}</div>`;
    }
  },

  async openRatePlanModal(plan = null) {
    const isEdit = !!plan;
    let policies = [];
    try {
      policies = await API.get('/api/cancellation-policies');
    } catch (e) {}

    const policyOpts = policies.map(pol => `
      <option value="${pol.id}" ${plan && plan.cancellation_policy_id === pol.id ? 'selected' : ''}>
        ${pol.name} (${pol.free_cancel_days}d free, ${pol.penalty_type})
      </option>
    `).join('');

    UI.modal({
      title: isEdit ? `Edit Rate Plan · ${plan.name}` : 'Create Commercial Rate Plan',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div style="display:grid; grid-template-columns:1fr 2fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Plan Code <span class="required-mark">*</span></label>
              <input type="text" id="plan-code" class="form-input font-mono" value="${plan ? plan.code : ''}" placeholder="e.g. BB, NR" ${isEdit ? 'readonly' : 'required'} style="text-transform:uppercase;">
            </div>
            <div class="form-group">
              <label class="form-label">Plan Name <span class="required-mark">*</span></label>
              <input type="text" id="plan-name" class="form-input" value="${plan ? plan.name : ''}" placeholder="e.g. Bed & Breakfast Package" required>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Public Description</label>
            <input type="text" id="plan-desc" class="form-input" value="${plan ? (plan.description || '') : ''}" placeholder="Summary shown to guests and front desk agents">
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Pricing Modifier Type</label>
              <select id="plan-mod-type" class="form-select">
                <option value="percent" ${plan && plan.modifier_type === 'percent' ? 'selected' : ''}>Percent (+/- %)</option>
                <option value="absolute" ${plan && plan.modifier_type === 'absolute' ? 'selected' : ''}>Absolute (+/- ${getCurrencySymbol()} per night)</option>
                <option value="fixed" ${plan && plan.modifier_type === 'fixed' ? 'selected' : ''}>Fixed Rate (${getCurrencySymbol()})</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Modifier Value</label>
              <input type="number" step="0.5" id="plan-mod-val" class="form-input font-mono" value="${plan ? plan.modifier_value : '0'}" required>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Meal Plan</label>
              <select id="plan-meal" class="form-select">
                <option value="room_only" ${plan && plan.meal_plan === 'room_only' ? 'selected' : ''}>Room Only</option>
                <option value="breakfast" ${plan && plan.meal_plan === 'breakfast' ? 'selected' : ''}>Bed & Breakfast</option>
                <option value="half_board" ${plan && plan.meal_plan === 'half_board' ? 'selected' : ''}>Half Board (Breakfast + Dinner)</option>
                <option value="full_board" ${plan && plan.meal_plan === 'full_board' ? 'selected' : ''}>Full Board (All Meals)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Minimum Stay (Nights)</label>
              <input type="number" min="1" id="plan-min-stay" class="form-input font-mono" value="${plan ? plan.min_stay : '1'}" required>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Cancellation Policy</label>
            <select id="plan-policy-id" class="form-select">
              <option value="">Standard Policy (Fallback)</option>
              ${policyOpts}
            </select>
          </div>

          <div style="display:flex; gap:24px; padding-top:6px;">
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" id="plan-refundable" ${!plan || plan.refundable ? 'checked' : ''} style="width:16px; height:16px;">
              <span>Refundable Rate</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" id="plan-deposit" ${plan && plan.requires_deposit ? 'checked' : ''} style="width:16px; height:16px;">
              <span>Requires Advance Deposit</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" id="plan-active" ${!plan || plan.active ? 'checked' : ''} style="width:16px; height:16px;">
              <span>Active</span>
            </label>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="save-rate-plan-btn">${isEdit ? 'Update Plan' : 'Save Rate Plan'}</button>
      `,
    });

    document.getElementById('save-rate-plan-btn').onclick = async () => {
      const code = document.getElementById('plan-code').value.trim().toUpperCase();
      const name = document.getElementById('plan-name').value.trim();
      const desc = document.getElementById('plan-desc').value.trim();
      const modType = document.getElementById('plan-mod-type').value;
      const modVal = parseFloat(document.getElementById('plan-mod-val').value) || 0;
      const meal = document.getElementById('plan-meal').value;
      const minStay = parseInt(document.getElementById('plan-min-stay').value) || 1;
      const polVal = document.getElementById('plan-policy-id').value;
      const polId = polVal ? parseInt(polVal) : null;
      const refundable = document.getElementById('plan-refundable').checked;
      const requiresDeposit = document.getElementById('plan-deposit').checked;
      const active = document.getElementById('plan-active').checked;

      if (!code || !name) {
        UI.toast('Code and Name are required.', 'error');
        return;
      }

      const payload = {
        code,
        name,
        description: desc,
        modifier_type: modType,
        modifier_value: modVal,
        meal_plan: meal,
        min_stay: minStay,
        cancellation_policy_id: polId,
        refundable,
        requires_deposit: requiresDeposit,
        active,
      };

      try {
        if (isEdit) {
          await API.put(`/api/rate-plans/${plan.id}`, payload);
          UI.toast(`Rate plan '${name}' updated.`, 'success');
        } else {
          await API.post('/api/rate-plans', payload);
          UI.toast(`Rate plan '${name}' created.`, 'success');
        }
        UI.closeModal();
        this.renderActiveTab();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  // ── 2. CANCELLATION POLICIES TAB ──────────────────────────────────────────

  async renderCancellationTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0;">Cancellation Policies</h3>
            <div style="font-size:12px; color:#6B7280; margin-top:2px;">Governs free cancellation windows, late cancellation penalty calculations, and deposit forfeits.</div>
          </div>
          <button class="btn btn-primary btn-sm" id="new-policy-btn">
            <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            <span>Create Policy</span>
          </button>
        </div>

        <div id="policies-table-wrap">
          <div style="padding:24px; text-align:center; color:#6B7280;">Loading cancellation policies...</div>
        </div>
      </div>
    `;

    document.getElementById('new-policy-btn').onclick = () => this.openCancellationModal();

    try {
      const policies = await API.get('/api/cancellation-policies');
      const tableWrap = document.getElementById('policies-table-wrap');

      if (!policies || policies.length === 0) {
        tableWrap.innerHTML = '<div style="padding:24px; text-align:center; color:#6B7280;">No policies configured yet.</div>';
        return;
      }

      let html = `
        <table class="data-table" style="width:100%; font-size:12px;">
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
        else if (p.penalty_type === 'first_night') penStr = 'First Night Rate';

        html += `
          <tr>
            <td style="font-weight:700; color:#111827;">${p.name}</td>
            <td style="font-size:11px; color:#6B7280; max-width:320px;">${p.description || '—'}</td>
            <td class="font-mono font-bold">${p.free_cancel_days === 0 ? 'No free window' : `Up to ${p.free_cancel_days}d before arrival`}</td>
            <td style="text-transform:capitalize;">${p.penalty_type.replace('_', ' ')}</td>
            <td class="font-mono font-bold" style="color:#DC2626;">${penStr}</td>
            <td>
              <span class="badge ${p.active ? 'badge-success' : 'badge-neutral'}" style="font-size:10px;">
                ${p.active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </td>
            <td style="text-align:right;">
              <button class="btn btn-secondary btn-sm edit-pol-btn" data-id="${p.id}" style="padding:2px 8px; font-size:11px;">Edit</button>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      tableWrap.innerHTML = html;

      tableWrap.querySelectorAll('.edit-pol-btn').forEach(btn => {
        btn.onclick = () => {
          const pid = parseInt(btn.getAttribute('data-id'));
          const target = policies.find(x => x.id === pid);
          if (target) this.openCancellationModal(target);
        };
      });
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load policies: ${e.message}</div>`;
    }
  },

  openCancellationModal(policy = null) {
    const isEdit = !!policy;

    UI.modal({
      title: isEdit ? `Edit Policy · ${policy.name}` : 'Create Cancellation Policy',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div class="form-group">
            <label class="form-label">Policy Name <span class="required-mark">*</span></label>
            <input type="text" id="pol-name" class="form-input" value="${policy ? policy.name : ''}" placeholder="e.g. Flexible 24h, Non-Refundable" required>
          </div>

          <div class="form-group">
            <label class="form-label">Description</label>
            <input type="text" id="pol-desc" class="form-input" value="${policy ? (policy.description || '') : ''}" placeholder="Detailed explanation shown during cancellation">
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Free Cancellation Window (Days)</label>
              <input type="number" min="0" id="pol-free-days" class="form-input font-mono" value="${policy ? policy.free_cancel_days : '1'}" placeholder="0 = non-refundable">
              <span class="form-hint-msg">Days before check-in date when cancellation is free.</span>
            </div>
            <div class="form-group">
              <label class="form-label">Late Cancellation Penalty</label>
              <select id="pol-pen-type" class="form-select">
                <option value="first_night" ${policy && policy.penalty_type === 'first_night' ? 'selected' : ''}>1 Night Room Rate</option>
                <option value="percent" ${policy && policy.penalty_type === 'percent' ? 'selected' : ''}>Percentage of Stay (%)</option>
                <option value="fixed" ${policy && policy.penalty_type === 'fixed' ? 'selected' : ''}>Fixed Amount (${getCurrencySymbol()})</option>
                <option value="none" ${policy && policy.penalty_type === 'none' ? 'selected' : ''}>No Penalty (Free)</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Penalty Value (% or ${getCurrencySymbol()})</label>
            <input type="number" step="0.5" id="pol-pen-val" class="form-input font-mono" value="${policy ? policy.penalty_value : '100'}">
          </div>

          <div>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" id="pol-active" ${!policy || policy.active ? 'checked' : ''} style="width:16px; height:16px;">
              <span>Active Policy</span>
            </label>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="save-pol-btn">${isEdit ? 'Update Policy' : 'Save Policy'}</button>
      `,
    });

    document.getElementById('save-pol-btn').onclick = async () => {
      const name = document.getElementById('pol-name').value.trim();
      const desc = document.getElementById('pol-desc').value.trim();
      const freeDays = parseInt(document.getElementById('pol-free-days').value) || 0;
      const penType = document.getElementById('pol-pen-type').value;
      const penVal = parseFloat(document.getElementById('pol-pen-val').value) || 0;
      const active = document.getElementById('pol-active').checked;

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
          UI.toast(`Policy '${name}' updated.`, 'success');
        } else {
          await API.post('/api/cancellation-policies', payload);
          UI.toast(`Policy '${name}' created.`, 'success');
        }
        UI.closeModal();
        this.renderActiveTab();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  // ── 3. TAXES TAB ──────────────────────────────────────────────────────────

  async renderTaxesTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0;">Dynamic Tax Engine</h3>
            <div style="font-size:12px; color:#6B7280; margin-top:2px;">Configures City Taxes, Tourism Levies, and GST calculation rules (inclusive/exclusive).</div>
          </div>
          <button class="btn btn-primary btn-sm" id="new-tax-btn">
            <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            <span>Create Tax Rate</span>
          </button>
        </div>

        <div id="taxes-table-wrap">
          <div style="padding:24px; text-align:center; color:#6B7280;">Loading taxes...</div>
        </div>
      </div>
    `;

    document.getElementById('new-tax-btn').onclick = () => this.openTaxModal();

    try {
      const taxes = await API.get('/api/taxes');
      const tableWrap = document.getElementById('taxes-table-wrap');

      if (!taxes || taxes.length === 0) {
        tableWrap.innerHTML = '<div style="padding:24px; text-align:center; color:#6B7280;">No custom taxes configured. Default GST applies.</div>';
        return;
      }

      let html = `
        <table class="data-table" style="width:100%; font-size:12px;">
          <thead>
            <tr>
              <th>TAX NAME</th>
              <th>RATE / FIXED</th>
              <th>TYPE</th>
              <th>APPLIES TO</th>
              <th>FREQUENCY</th>
              <th>STATUS</th>
              <th style="text-align:right;">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
      `;

      taxes.forEach(t => {
        let rateStr = '';
        if (parseFloat(t.rate) > 0) rateStr = `${t.rate}%`;
        if (parseFloat(t.fixed_amount) > 0) rateStr = `${formatCurrency(t.fixed_amount)} (Fixed)`;

        html += `
          <tr>
            <td style="font-weight:700; color:#111827;">${t.name}</td>
            <td class="font-mono font-bold" style="color:#2563EB;">${rateStr}</td>
            <td>
              <span class="badge ${t.type === 'inclusive' ? 'badge-info' : 'badge-neutral'}" style="font-size:10px; text-transform:uppercase;">
                ${t.type}
              </span>
            </td>
            <td style="text-transform:capitalize;">${t.applies_to}</td>
            <td style="text-transform:capitalize;">Per ${(t.per || 'night').replace('_', ' ')}</td>
            <td>
              <span class="badge ${t.active ? 'badge-success' : 'badge-neutral'}" style="font-size:10px;">
                ${t.active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </td>
            <td style="text-align:right;">
              <button class="btn btn-secondary btn-sm edit-tax-btn" data-id="${t.id}" style="padding:2px 8px; font-size:11px;">Edit</button>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      tableWrap.innerHTML = html;

      tableWrap.querySelectorAll('.edit-tax-btn').forEach(btn => {
        btn.onclick = () => {
          const tid = parseInt(btn.getAttribute('data-id'));
          const target = taxes.find(x => x.id === tid);
          if (target) this.openTaxModal(target);
        };
      });
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load taxes: ${e.message}</div>`;
    }
  },

  openTaxModal(tax = null) {
    const isEdit = !!tax;

    UI.modal({
      title: isEdit ? `Edit Tax Rate · ${tax.name}` : 'Create Tax Rate',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div class="form-group">
            <label class="form-label">Tax Name <span class="required-mark">*</span></label>
            <input type="text" id="tax-name" class="form-input" value="${tax ? tax.name : ''}" placeholder="e.g. City Municipal Tax, Tourism Levy" required>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Percentage Rate (%)</label>
              <input type="number" step="0.1" id="tax-rate" class="form-input font-mono" value="${tax ? tax.rate : '0'}" placeholder="e.g. 3.00, 12.00">
            </div>
            <div class="form-group">
              <label class="form-label">Fixed Amount (${getCurrencySymbol()}${getActiveCurrency()})</label>
              <input type="number" step="10" id="tax-fixed" class="form-input font-mono" value="${tax ? tax.fixed_amount : '0'}" placeholder="e.g. 150.00">
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Tax Type</label>
              <select id="tax-type" class="form-select">
                <option value="exclusive" ${tax && tax.type === 'exclusive' ? 'selected' : ''}>Exclusive (Added on top)</option>
                <option value="inclusive" ${tax && tax.type === 'inclusive' ? 'selected' : ''}>Inclusive (Extracted from base)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Applies To</label>
              <select id="tax-applies" class="form-select">
                <option value="rooms" ${tax && tax.applies_to === 'rooms' ? 'selected' : ''}>Rooms Only</option>
                <option value="extras" ${tax && tax.applies_to === 'extras' ? 'selected' : ''}>Extras Only (F&B, Minibar)</option>
                <option value="all" ${tax && tax.applies_to === 'all' ? 'selected' : ''}>All Charges</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Calculation Frequency</label>
            <select id="tax-per" class="form-select">
              <option value="night" ${tax && tax.per === 'night' ? 'selected' : ''}>Per Night</option>
              <option value="stay" ${tax && tax.per === 'stay' ? 'selected' : ''}>Per Stay (One-Time)</option>
              <option value="person_per_night" ${tax && tax.per === 'person_per_night' ? 'selected' : ''}>Per Person Per Night</option>
            </select>
          </div>

          <div>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" id="tax-active" ${!tax || tax.active ? 'checked' : ''} style="width:16px; height:16px;">
              <span>Active Tax Rate</span>
            </label>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="save-tax-btn">${isEdit ? 'Update Tax' : 'Save Tax'}</button>
      `,
    });

    document.getElementById('save-tax-btn').onclick = async () => {
      const name = document.getElementById('tax-name').value.trim();
      const rate = parseFloat(document.getElementById('tax-rate').value) || 0;
      const fixed = parseFloat(document.getElementById('tax-fixed').value) || 0;
      const type = document.getElementById('tax-type').value;
      const applies = document.getElementById('tax-applies').value;
      const per = document.getElementById('tax-per').value;
      const active = document.getElementById('tax-active').checked;

      if (!name) {
        UI.toast('Tax Name is required.', 'error');
        return;
      }

      const payload = {
        name,
        rate,
        fixed_amount: fixed,
        type,
        applies_to: applies,
        per,
        active,
      };

      try {
        if (isEdit) {
          await API.put(`/api/taxes/${tax.id}`, payload);
          UI.toast(`Tax '${name}' updated.`, 'success');
        } else {
          await API.post('/api/taxes', payload);
          UI.toast(`Tax '${name}' created.`, 'success');
        }
        UI.closeModal();
        this.renderActiveTab();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  // ── 4. TEAM TAB ───────────────────────────────────────────────────────────

  async renderTeamTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0;">Staff Credentials & RBAC</h3>
            <div style="font-size:12px; color:#6B7280; margin-top:2px;">Front desk, housekeeping, and management access roles.</div>
          </div>
          <button class="btn btn-primary btn-sm" id="new-user-btn">
            <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" /></svg>
            <span>Add Staff Member</span>
          </button>
        </div>

        <div id="users-table-wrap">
          <div style="padding:24px; text-align:center; color:#6B7280;">Loading staff accounts...</div>
        </div>
      </div>
    `;

    document.getElementById('new-user-btn').onclick = () => this.openCreateUserModal();

    try {
      const users = await API.get('/api/users');
      const tableWrap = document.getElementById('users-table-wrap');

      let html = `
        <table class="data-table" style="width:100%; font-size:12px;">
          <thead>
            <tr>
              <th>OPERATOR NAME</th>
              <th>USERNAME</th>
              <th>EMAIL</th>
              <th>ROLE</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
      `;

      users.forEach(u => {
        html += `
          <tr>
            <td style="font-weight:700; color:#111827;">${u.full_name}</td>
            <td class="font-mono">${u.username}</td>
            <td>${u.email}</td>
            <td><span class="badge ${u.role === 'admin' ? 'badge-info' : 'badge-neutral'}" style="text-transform:uppercase;">${u.role}</span></td>
            <td><span class="badge ${u.is_active ? 'badge-success' : 'badge-neutral'}">${u.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      tableWrap.innerHTML = html;
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load staff accounts: ${e.message}</div>`;
    }
  },

  openCreateUserModal() {
    UI.modal({
      title: 'Add New Staff Account',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Full Name <span class="required-mark">*</span></label>
              <input type="text" id="new-user-fn" class="form-input" placeholder="e.g. Rohan Sharma" required>
            </div>
            <div class="form-group">
              <label class="form-label">Username <span class="required-mark">*</span></label>
              <input type="text" id="new-user-un" class="form-input font-mono" placeholder="rsharma" required>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Email Address <span class="required-mark">*</span></label>
            <input type="email" id="new-user-em" class="form-input" placeholder="rohan@grandpavilion.in" required>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Role <span class="required-mark">*</span></label>
              <select id="new-user-role" class="form-select">
                <option value="front_desk">Front Desk Staff</option>
                <option value="housekeeping">Housekeeping Operations</option>
                <option value="manager">Hotel Manager</option>
                <option value="admin">System Administrator</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Password <span class="required-mark">*</span></label>
              <input type="password" id="new-user-pw" class="form-input font-mono" placeholder="Min 10 characters" required minlength="10">
            </div>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="submit-user-btn">Create User</button>
      `,
    });

    document.getElementById('submit-user-btn').onclick = async () => {
      const fn = document.getElementById('new-user-fn').value.trim();
      const un = document.getElementById('new-user-un').value.trim();
      const em = document.getElementById('new-user-em').value.trim();
      const role = document.getElementById('new-user-role').value;
      const pw = document.getElementById('new-user-pw').value;

      if (!fn || !un || !em || !pw) {
        UI.toast('All fields are required.', 'error');
        return;
      }

      try {
        await API.post('/api/users', { full_name: fn, username: un, email: em, role, password: pw });
        UI.toast('Staff account created.', 'success');
        UI.closeModal();
        this.renderActiveTab();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },

  // ── 5. OPERATOR PROFILE TAB ───────────────────────────────────────────────

  async renderProfileTab(container) {
    const user = API.getUser() || { full_name: 'Aditi Rao', username: 'admin', email: 'admin@grandpavilion.in', role: 'admin' };
    container.innerHTML = `
      <div class="card" style="max-width: 680px; padding: 24px; border:1px solid #E5E7EB;">
        <h3 style="font-size:16px; font-weight:700; color:#111827; margin-bottom:16px;">Operator Account Profile</h3>
        <div style="display:flex; gap:20px; align-items:center; margin-bottom:24px; padding-bottom:20px; border-bottom:1px solid #E5E7EB;">
          <div style="width:56px; height:56px; border-radius:50%; background:#111827; color:#FFF; display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:700;">
            ${user.full_name ? user.full_name[0] : 'A'}
          </div>
          <div>
            <div style="font-size:18px; font-weight:700; color:#111827;">${user.full_name}</div>
            <div style="font-size:12px; color:#6B7280; margin-top:2px;">
              Username: <span class="font-mono">${user.username}</span> · Role: <span class="badge badge-info">${user.role.toUpperCase()}</span>
            </div>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px;">
          <div style="display:flex; justify-content:space-between; padding-bottom:8px; border-bottom:1px solid #F3F4F6;">
            <span style="color:#6B7280;">Email Address:</span>
            <strong>${user.email}</strong>
          </div>
          <div style="display:flex; justify-content:space-between; padding-bottom:8px; border-bottom:1px solid #F3F4F6;">
            <span style="color:#6B7280;">Security Session:</span>
            <span>JWT Session (Active)</span>
          </div>
        </div>

        <div style="margin-top:24px;">
          <button class="btn btn-secondary btn-md" onclick="API.logout()">
            Sign Out of Session
          </button>
        </div>
      </div>
    `;
  },

  // ── 6. HOTEL METADATA TAB ─────────────────────────────────────────────────

  async renderHotelTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px;">
        <div class="skeleton" style="height: 180px; width: 100%;"></div>
      </div>
    `;

    try {
      const org = await API.get('/api/org');
      const activeCurr = org.currency || getActiveCurrency();

      container.innerHTML = `
        <div class="card" style="max-width: 760px; padding: 24px; border:1px solid #E5E7EB; background:#FFFFFF;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; border-bottom:1px solid #F1F5F9; padding-bottom:14px;">
            <div>
              <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0;">${org.name || 'Property Profile'}</h3>
              <div style="font-size:12px; color:#6B7280; margin-top:2px;">Organization ID: ${org.id} · Plan: ${(org.plan || 'pro').toUpperCase()}</div>
            </div>
            <span class="badge badge-success" style="font-size:11px;">ACTIVE HOTEL</span>
          </div>

          <form id="hotel-profile-form" onsubmit="window.Pages.Settings.handleSaveHotelProfile(event)">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
              <div>
                <label class="form-label" style="font-size:12px;">Hotel / Property Name <span class="required-mark">*</span></label>
                <input type="text" id="hotel-prop-name" class="form-input" value="${org.name || ''}" required style="height:38px;">
              </div>
              <div>
                <label class="form-label" style="font-size:12px;">Operating Currency <span class="required-mark">*</span></label>
                <select id="hotel-prop-currency" class="form-select" style="height:38px; font-weight:600;">
                  <option value="INR" ${activeCurr === 'INR' ? 'selected' : ''}>INR (₹) — Indian Rupee</option>
                  <option value="USD" ${activeCurr === 'USD' ? 'selected' : ''}>USD ($) — US Dollar</option>
                  <option value="EUR" ${activeCurr === 'EUR' ? 'selected' : ''}>EUR (€) — Euro</option>
                  <option value="GBP" ${activeCurr === 'GBP' ? 'selected' : ''}>GBP (£) — British Pound</option>
                  <option value="AED" ${activeCurr === 'AED' ? 'selected' : ''}>AED (AED) — UAE Dirham</option>
                  <option value="AUD" ${activeCurr === 'AUD' ? 'selected' : ''}>AUD (A$) — Australian Dollar</option>
                  <option value="CAD" ${activeCurr === 'CAD' ? 'selected' : ''}>CAD (C$) — Canadian Dollar</option>
                  <option value="SGD" ${activeCurr === 'SGD' ? 'selected' : ''}>SGD (S$) — Singapore Dollar</option>
                </select>
              </div>
              <div>
                <label class="form-label" style="font-size:12px;">Timezone</label>
                <input type="text" id="hotel-prop-timezone" class="form-input" value="${org.timezone || 'Asia/Kolkata'}" style="height:38px;">
              </div>
              <div>
                <label class="form-label" style="font-size:12px;">Tax ID / GSTIN Number</label>
                <input type="text" id="hotel-prop-taxid" class="form-input font-mono" value="${org.tax_id || ''}" placeholder="29AAAAA0000A1Z5" style="height:38px;">
              </div>
            </div>

            <div style="margin-bottom:20px;">
              <label class="form-label" style="font-size:12px;">Property Street Address</label>
              <textarea id="hotel-prop-address" class="form-input" rows="2" style="width:100%; font-size:13px; padding:10px;">${org.address || ''}</textarea>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div style="font-size:12px; color:#6B7280;">
                ✨ Updating currency automatically adapts all room rates, folios, and invoices.
              </div>
              <button type="submit" id="hotel-prop-save-btn" class="btn btn-primary btn-md" style="height:38px; padding:0 22px;">
                Save Property Profile
              </button>
            </div>
          </form>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load hotel profile: ${e.message}</div>`;
    }
  },

  async handleSaveHotelProfile(e) {
    e.preventDefault();
    const btn = document.getElementById('hotel-prop-save-btn');
    const name = document.getElementById('hotel-prop-name').value.trim();
    const currency = document.getElementById('hotel-prop-currency').value;
    const timezone = document.getElementById('hotel-prop-timezone').value.trim();
    const tax_id = document.getElementById('hotel-prop-taxid').value.trim();
    const address = document.getElementById('hotel-prop-address').value.trim();

    if (!name) {
      UI.toast('Hotel Name is required.', 'warning');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
      const updated = await API.patch('/api/org', {
        name,
        currency,
        timezone,
        tax_id,
        address,
      });

      // Synchronize client currency
      localStorage.setItem('checkinos_currency', currency);
      if (window.currentUser && window.currentUser.organization) {
        window.currentUser.organization.currency = currency;
        window.currentUser.organization.name = name;
      }
      window.currentOrg = updated;

      UI.toast(`Property settings saved! Operating currency set to ${currency} (${getCurrencySymbol(currency)}).`, 'success');
      this.renderHotelTab(document.getElementById('property-tab-content') || document.getElementById('settings-tab-content'));
    } catch (err) {
      UI.toast(err.message || 'Failed to update property settings.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Save Property Profile';
    }
  },

  // ── 7. SUBSCRIPTION & BILLING TAB ──────────────────────────────────────────

  async renderBillingTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px;">
        <div class="skeleton" style="height: 240px; width: 100%;"></div>
      </div>
    `;

    try {
      const [billing, usage] = await Promise.all([
        API.get('/api/billing/status'),
        API.get('/api/org/usage'),
      ]);

      const planName = (billing.plan || 'pro').toUpperCase();
      const statusPill = billing.trialing
        ? `<span class="badge badge-warning">TRIAL (${billing.days_left || 14} DAYS REMAINING)</span>`
        : `<span class="badge badge-success">ACTIVE SUBSCRIPTION</span>`;

      const roomPct = Math.min(100, Math.round((usage.rooms.used / (usage.rooms.limit || 50)) * 100));
      const userPct = Math.min(100, Math.round((usage.users.used / (usage.users.limit || 10)) * 100));

      container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 24px; max-width: 820px;">
          <!-- Plan Banner -->
          <div class="card" style="padding: 24px; border: 1px solid #E5E7EB; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <h3 style="font-size: 20px; font-weight: 700; margin: 0;">${planName} PLAN</h3>
                ${statusPill}
              </div>
              <div style="font-size: 13px; color: #6B7280;">Billed monthly via Stripe with automatic GST invoice receipts.</div>
            </div>
            <div style="display: flex; gap: 10px;">
              <button class="btn btn-secondary btn-md" onclick="window.Pages.Settings.openStripePortal()">
                Stripe Customer Portal
              </button>
              <button class="btn btn-primary btn-md" onclick="window.Pages.Settings.openUpgradeModal()">
                Change Plan
              </button>
            </div>
          </div>

          <!-- Usage Meters -->
          <div class="card" style="padding: 24px; border: 1px solid #E5E7EB;">
            <h4 style="font-size: 15px; font-weight: 600; margin-bottom: 18px;">Plan Capacity & Resource Utilization</h4>
            <div style="display: flex; flex-direction: column; gap: 18px;">
              <!-- Rooms Meter -->
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 500; margin-bottom: 6px;">
                  <span>Physical Rooms Provisioned</span>
                  <span class="font-mono">${usage.rooms.used} / ${usage.rooms.limit === 999999 ? 'Unlimited' : usage.rooms.limit} rooms (${roomPct}%)</span>
                </div>
                <div style="height: 8px; background: #F3F4F6; border-radius: 4px; overflow: hidden;">
                  <div style="height: 100%; width: ${roomPct}%; background: ${roomPct > 90 ? '#DC2626' : '#111827'}; border-radius: 4px;"></div>
                </div>
              </div>

              <!-- Staff Users Meter -->
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 500; margin-bottom: 6px;">
                  <span>Staff & Operator Accounts</span>
                  <span class="font-mono">${usage.users.used} / ${usage.users.limit === 999999 ? 'Unlimited' : usage.users.limit} staff (${userPct}%)</span>
                </div>
                <div style="height: 8px; background: #F3F4F6; border-radius: 4px; overflow: hidden;">
                  <div style="height: 100%; width: ${userPct}%; background: ${userPct > 90 ? '#DC2626' : '#111827'}; border-radius: 4px;"></div>
                </div>
              </div>

              <!-- Bookings this month -->
              <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 12px; border-top: 1px solid #F3F4F6; font-size: 13px;">
                <span style="color: #6B7280;">Reservations Processed This Month:</span>
                <strong class="font-mono" style="font-size: 15px;">${usage.reservations_this_month} bookings</strong>
              </div>
            </div>
          </div>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="card" style="padding: 24px; color: #DC2626;">Error loading billing information: ${e.message}</div>`;
    }
  },

  async openStripePortal() {
    try {
      const data = await API.post('/api/billing/portal');
      if (data.portal_url) {
        window.location.href = data.portal_url;
      } else {
        UI.toast(data.message || 'Customer portal URL generated.', 'info');
      }
    } catch (e) {
      UI.toast(e.message || 'Stripe portal unavailable', 'danger');
    }
  },

  openUpgradeModal() {
    UI.modal({
      title: 'Upgrade Subscription Plan',
      contentHtml: `
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; font-size: 13px;">
          <div style="border: 1px solid #E5E7EB; border-radius: 6px; padding: 16px; text-align: center;">
            <strong>Starter</strong>
            <div style="font-size: 18px; font-weight: bold; margin: 8px 0;">₹2,499/mo</div>
            <div style="color: #6B7280; font-size: 12px; margin-bottom: 12px;">Up to 15 rooms</div>
            <button class="btn btn-secondary btn-sm" style="width: 100%;" onclick="window.Pages.Settings.checkoutPlan('starter')">Select Starter</button>
          </div>
          <div style="border: 2px solid #111827; border-radius: 6px; padding: 16px; text-align: center;">
            <strong>Pro</strong>
            <div style="font-size: 18px; font-weight: bold; margin: 8px 0;">₹6,999/mo</div>
            <div style="color: #6B7280; font-size: 12px; margin-bottom: 12px;">Up to 50 rooms</div>
            <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="window.Pages.Settings.checkoutPlan('pro')">Select Pro</button>
          </div>
          <div style="border: 1px solid #E5E7EB; border-radius: 6px; padding: 16px; text-align: center;">
            <strong>Enterprise</strong>
            <div style="font-size: 18px; font-weight: bold; margin: 8px 0;">₹14,999/mo</div>
            <div style="color: #6B7280; font-size: 12px; margin-bottom: 12px;">Unlimited</div>
            <button class="btn btn-secondary btn-sm" style="width: 100%;" onclick="window.Pages.Settings.checkoutPlan('enterprise')">Select Enterprise</button>
          </div>
        </div>
      `,
      footerHtml: '<button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Close</button>'
    });
  },

  async checkoutPlan(plan) {
    try {
      const data = await API.post('/api/billing/checkout', {
        plan: plan,
        billing_interval: 'month',
        success_url: window.location.origin + '/app?upgraded=true',
        cancel_url: window.location.origin + '/settings',
      });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        UI.toast(data.message || 'Subscription updated', 'success');
        UI.closeModal();
        this.renderActiveTab();
      }
    } catch (e) {
      UI.toast(e.message || 'Checkout failed', 'danger');
    }
  },

  // ── 8. EMAIL NOTIFICATION TEMPLATES TAB ────────────────────────────────────

  async renderEmailsTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px;">
        <div class="skeleton" style="height: 200px; width: 100%;"></div>
      </div>
    `;

    try {
      const templates = await API.get('/api/settings/emails');
      container.innerHTML = `
        <div class="card" style="padding: 20px; border: 1px solid #E5E7EB;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
              <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px 0;">Automated Transactional Emails</h3>
              <div style="font-size: 13px; color: #6B7280;">Sent via SendGrid with fallback console logging. Dynamic variables like {{guest_name}} are supported.</div>
            </div>
          </div>
          <table class="table-compact" style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
              <tr style="text-align: left; border-bottom: 1px solid #E5E7EB; background: #F9FAFB;">
                <th style="padding: 10px 12px;">Trigger / Event</th>
                <th style="padding: 10px 12px;">Subject Line</th>
                <th style="padding: 10px 12px;">Status</th>
                <th style="padding: 10px 12px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${templates.map(t => `
                <tr style="border-bottom: 1px solid #F3F4F6;">
                  <td style="padding: 10px 12px; font-weight: 600;">${t.name}</td>
                  <td style="padding: 10px 12px; color: #4B5563;">${t.subject}</td>
                  <td style="padding: 10px 12px;">
                    <span class="badge ${t.is_active ? 'badge-success' : 'badge-neutral'}">${t.is_active ? 'Active' : 'Disabled'}</span>
                  </td>
                  <td style="padding: 10px 12px; text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.openEditEmailModal(${t.id})">Edit</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="card" style="padding: 20px; color: #DC2626;">Error loading email templates: ${e.message}</div>`;
    }
  },

  async openEditEmailModal(id) {
    try {
      const templates = await API.get('/api/settings/emails');
      const t = templates.find(item => item.id === id);
      if (!t) return;

      UI.modal({
        title: `Edit Email: ${t.name}`,
        contentHtml: `
          <div style="display: flex; flex-direction: column; gap: 14px; font-size: 13px;">
            <div>
              <label style="font-weight: 600; display: block; margin-bottom: 4px;">Subject Line</label>
              <input type="text" id="edit-email-subject" value="${t.subject.replace(/"/g, '&quot;')}" style="width: 100%; padding: 8px 12px; border: 1px solid #D1D5DB; border-radius: 6px;">
            </div>
            <div>
              <label style="font-weight: 600; display: block; margin-bottom: 4px;">HTML Template Body</label>
              <textarea id="edit-email-body" rows="8" style="width: 100%; padding: 8px 12px; border: 1px solid #D1D5DB; border-radius: 6px; font-family: monospace; font-size: 12px;">${t.body_html.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <span class="badge badge-neutral">{{guest_name}}</span>
              <span class="badge badge-neutral">{{hotel_name}}</span>
              <span class="badge badge-neutral">{{confirmation_number}}</span>
              <span class="badge badge-neutral">{{room_number}}</span>
              <span class="badge badge-neutral">{{check_in}}</span>
              <span class="badge badge-neutral">{{check_out}}</span>
            </div>
          </div>
        `,
        footerHtml: `
          <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
          <button class="btn btn-primary btn-md" onclick="window.Pages.Settings.saveEmailTemplate(${t.id})">Save Changes</button>
        `
      });
    } catch (e) {
      UI.toast(e.message, 'danger');
    }
  },

  async saveEmailTemplate(id) {
    const subject = document.getElementById('edit-email-subject').value.trim();
    const body_html = document.getElementById('edit-email-body').value;
    try {
      await API.put(`/api/settings/emails/${id}`, { subject, body_html, is_active: true });
      UI.toast('Email template saved successfully', 'success');
      UI.closeModal();
      this.renderActiveTab();
    } catch (e) {
      UI.toast(e.message || 'Failed to save template', 'danger');
    }
  },

  // ── 9. DATA SAFETY & BACKUPS TAB ──────────────────────────────────────────

  async renderBackupsTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px;">
        <div class="skeleton" style="height: 200px; width: 100%;"></div>
      </div>
    `;

    try {
      const backups = await API.get('/api/admin/backups');
      container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 20px;">
          <div class="card" style="padding: 20px; border: 1px solid #E5E7EB; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px 0;">Automated Snapshots & One-Click Portability</h3>
              <div style="font-size: 13px; color: #6B7280;">Daily snapshots retained for 30 days. Export all hotel data in raw CSV format at any time.</div>
            </div>
            <div style="display: flex; gap: 10px;">
              <button class="btn btn-secondary btn-md" onclick="window.Pages.Settings.triggerExportZip()">
                Download Full ZIP Export
              </button>
              <button class="btn btn-primary btn-md" onclick="window.Pages.Settings.triggerManualBackup()">
                Run Manual Backup Now
              </button>
            </div>
          </div>

          <div class="card" style="padding: 20px; border: 1px solid #E5E7EB;">
            <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Recent Backup Snapshots</h4>
            <table class="table-compact" style="width: 100%; border-collapse: collapse; font-size: 13px;">
              <thead>
                <tr style="text-align: left; border-bottom: 1px solid #E5E7EB; background: #F9FAFB;">
                  <th style="padding: 8px 12px;">Snapshot Filename</th>
                  <th style="padding: 8px 12px;">Type</th>
                  <th style="padding: 8px 12px;">Size</th>
                  <th style="padding: 8px 12px;">Status</th>
                  <th style="padding: 8px 12px;">Timestamp</th>
                  <th style="padding: 8px 12px; text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${backups.length ? backups.map(b => `
                  <tr style="border-bottom: 1px solid #F3F4F6;">
                    <td style="padding: 8px 12px; font-family: monospace;">${b.filename}</td>
                    <td style="padding: 8px 12px; text-transform: capitalize;">${b.trigger_type}</td>
                    <td style="padding: 8px 12px; font-family: monospace;">${(b.size_bytes / 1024).toFixed(1)} KB</td>
                    <td style="padding: 8px 12px;"><span class="badge badge-success">Completed</span></td>
                    <td style="padding: 8px 12px; color: #6B7280;">${new Date(b.created_at).toLocaleString()}</td>
                    <td style="padding: 8px 12px; text-align: right;">
                      <a href="/api/admin/backups/${b.id}/download" class="btn btn-secondary btn-sm" download>Download</a>
                    </td>
                  </tr>
                `).join('') : `
                  <tr><td colspan="6" style="padding: 20px; text-align: center; color: #6B7280;">No backup snapshots recorded yet.</td></tr>
                `}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="card" style="padding: 20px; color: #DC2626;">Error loading backup records: ${e.message}</div>`;
    }
  },

  async triggerManualBackup() {
    try {
      UI.toast('Initiating database snapshot...', 'info');
      const res = await API.post('/api/admin/backups/manual');
      UI.toast(res.message || 'Backup completed successfully', 'success');
      this.renderActiveTab();
    } catch (e) {
      UI.toast(e.message || 'Backup failed', 'danger');
    }
  },

  async triggerExportZip() {
    try {
      UI.toast('Preparing CSV archive...', 'info');
      const token = API.getToken();
      const resp = await fetch('/api/admin/export', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!resp.ok) throw new Error('Export generation failed');
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CheckinOS_DataExport_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      UI.toast('Data export downloaded', 'success');
    } catch (e) {
      UI.toast(e.message || 'Export error', 'danger');
    }
  },

  // ── 10. TRASH & RESTORE TAB ───────────────────────────────────────────────

  async renderTrashTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px;">
        <div class="skeleton" style="height: 180px; width: 100%;"></div>
      </div>
    `;

    try {
      const trash = await API.get('/api/trash');
      const totalDeleted = (trash.reservations?.length || 0) + (trash.rooms?.length || 0) + (trash.guests?.length || 0);

      container.innerHTML = `
        <div class="card" style="padding: 20px; border: 1px solid #E5E7EB;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
              <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px 0;">Soft-Deleted Records (Trash Bin)</h3>
              <div style="font-size: 13px; color: #6B7280;">Items in trash remain safely recoverable for 30 days before permanent deletion.</div>
            </div>
            <span class="badge ${totalDeleted ? 'badge-warning' : 'badge-neutral'} font-mono">${totalDeleted} Deleted Items</span>
          </div>

          <table class="table-compact" style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
              <tr style="text-align: left; border-bottom: 1px solid #E5E7EB; background: #F9FAFB;">
                <th style="padding: 8px 12px;">Entity Type</th>
                <th style="padding: 8px 12px;">Details</th>
                <th style="padding: 8px 12px;">Deleted At</th>
                <th style="padding: 8px 12px; text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${(trash.reservations || []).map(r => `
                <tr style="border-bottom: 1px solid #F3F4F6;">
                  <td style="padding: 8px 12px;"><span class="badge badge-info">Reservation</span></td>
                  <td style="padding: 8px 12px; font-weight: 500;">Conf #${r.confirmation_number} • Room ${r.room ? r.room.number : '—'}</td>
                  <td style="padding: 8px 12px; color: #6B7280;">${new Date(r.deleted_at).toLocaleString()}</td>
                  <td style="padding: 8px 12px; text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.restoreRecord('reservations', ${r.id})">Restore</button>
                  </td>
                </tr>
              `).join('')}
              ${(trash.rooms || []).map(rm => `
                <tr style="border-bottom: 1px solid #F3F4F6;">
                  <td style="padding: 8px 12px;"><span class="badge badge-warning">Room</span></td>
                  <td style="padding: 8px 12px; font-weight: 500;">Room ${rm.number} (Floor ${rm.floor})</td>
                  <td style="padding: 8px 12px; color: #6B7280;">${new Date(rm.deleted_at).toLocaleString()}</td>
                  <td style="padding: 8px 12px; text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.restoreRecord('rooms', ${rm.id})">Restore</button>
                  </td>
                </tr>
              `).join('')}
              ${(trash.guests || []).map(g => `
                <tr style="border-bottom: 1px solid #F3F4F6;">
                  <td style="padding: 8px 12px;"><span class="badge badge-neutral">Guest</span></td>
                  <td style="padding: 8px 12px; font-weight: 500;">${g.first_name} ${g.last_name} (${g.email || 'No email'})</td>
                  <td style="padding: 8px 12px; color: #6B7280;">${new Date(g.deleted_at).toLocaleString()}</td>
                  <td style="padding: 8px 12px; text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.restoreRecord('guests', ${g.id})">Restore</button>
                  </td>
                </tr>
              `).join('')}
              ${!totalDeleted ? `
                <tr><td colspan="4" style="padding: 24px; text-align: center; color: #6B7280;">Trash is empty. No deleted records.</td></tr>
              ` : ''}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="card" style="padding: 20px; color: #DC2626;">Error loading trash: ${e.message}</div>`;
    }
  },

  async restoreRecord(entity, id) {
    try {
      const res = await API.post(`/api/${entity}/${id}/restore`);
      UI.toast(res.message || 'Record restored successfully', 'success');
      this.renderActiveTab();
    } catch (e) {
      UI.toast(e.message || 'Restore failed', 'danger');
    }
  },

  // ── 11. AUDIT TRAIL LOG TAB ───────────────────────────────────────────────

  async renderAuditTab(container) {
    container.innerHTML = `
      <div class="card" style="padding: 24px;">
        <div class="skeleton" style="height: 200px; width: 100%;"></div>
      </div>
    `;

    try {
      const logs = await API.get('/api/audit-log', { limit: 50 });
      container.innerHTML = `
        <div class="card" style="padding: 20px; border: 1px solid #E5E7EB;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
              <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px 0;">Operational Audit Trail</h3>
              <div style="font-size: 13px; color: #6B7280;">Tamper-evident logs of all reservation modifications, room status changes, and staff operations.</div>
            </div>
          </div>

          <table class="table-compact" style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
              <tr style="text-align: left; border-bottom: 1px solid #E5E7EB; background: #F9FAFB;">
                <th style="padding: 8px 12px;">Timestamp</th>
                <th style="padding: 8px 12px;">Action</th>
                <th style="padding: 8px 12px;">Entity</th>
                <th style="padding: 8px 12px;">Actor</th>
                <th style="padding: 8px 12px; text-align: right;">State Diff</th>
              </tr>
            </thead>
            <tbody>
              ${logs.length ? logs.map(l => `
                <tr style="border-bottom: 1px solid #F3F4F6;">
                  <td style="padding: 8px 12px; color: #6B7280; font-family: monospace;">${new Date(l.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                  <td style="padding: 8px 12px; font-weight: 600;">${l.action.replace(/_/g, ' ')}</td>
                  <td style="padding: 8px 12px;"><span class="badge badge-neutral">${l.entity_type} #${l.entity_id}</span></td>
                  <td style="padding: 8px 12px;">${l.user ? l.user.full_name : 'Staff / System'}</td>
                  <td style="padding: 8px 12px; text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick='window.Pages.Settings.viewAuditDiff(${JSON.stringify(l).replace(/'/g, "&apos;")})'>View Diff</button>
                  </td>
                </tr>
              `).join('') : `
                <tr><td colspan="5" style="padding: 20px; text-align: center; color: #6B7280;">No audit records available.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="card" style="padding: 20px; color: #DC2626;">Error loading audit log: ${e.message}</div>`;
    }
  },

  viewAuditDiff(log) {
    const beforeObj = log.before_state ? (typeof log.before_state === 'string' ? JSON.parse(log.before_state) : log.before_state) : null;
    const afterObj = log.after_state ? (typeof log.after_state === 'string' ? JSON.parse(log.after_state) : log.after_state) : null;

    UI.modal({
      title: `Audit Diff: ${log.action} on ${log.entity_type} #${log.entity_id}`,
      contentHtml: `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 12px; font-family: monospace;">
          <div>
            <strong style="display: block; margin-bottom: 6px; color: #DC2626;">BEFORE STATE:</strong>
            <pre style="background: #FEF2F2; border: 1px solid #FECACA; padding: 10px; border-radius: 6px; overflow-x: auto; max-height: 260px;">${beforeObj ? JSON.stringify(beforeObj, null, 2) : 'None (Creation)'}</pre>
          </div>
          <div>
            <strong style="display: block; margin-bottom: 6px; color: #059669;">AFTER STATE:</strong>
            <pre style="background: #ECFDF5; border: 1px solid #A7F3D0; padding: 10px; border-radius: 6px; overflow-x: auto; max-height: 260px;">${afterObj ? JSON.stringify(afterObj, null, 2) : 'None (Deletion)'}</pre>
          </div>
        </div>
      `,
      footerHtml: '<button class="btn btn-primary btn-md" onclick="UI.closeModal()">Close</button>'
    });
  },

  // ── 12. OTA & INBOUND CHANNEL SYNC & AUTO-RESERVATIONS ─────────────────────

  async renderIntegrationsTab(container) {
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:24px; max-width:960px;">
        <!-- Header & Channel Status Cards -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
          <!-- Gmail & OTA Ingestion Card -->
          <div class="card" style="padding:20px; border:1px solid #E5E7EB; background:#FFFFFF;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:36px; height:36px; border-radius:8px; background:#EFF6FF; color:#2563EB; display:flex; align-items:center; justify-content:center; font-weight:700;">
                  OTA
                </div>
                <div>
                  <h4 style="font-size:15px; font-weight:700; margin:0;">OTA Email Voucher Sync</h4>
                  <div style="font-size:11px; color:#6B7280;">OYO, Airbnb, Booking.com, Agoda</div>
                </div>
              </div>
              <span class="badge badge-success" style="font-size:11px; padding:2px 8px;">CONNECTED</span>
            </div>
            <div style="font-size:13px; color:#4B5563; line-height:1.5; margin-bottom:12px;">
              Automatically ingests reservation emails forwarded from <strong>Booking.com, Airbnb, OYO, Agoda, MakeMyTrip</strong>. Extracts confirmation code, dates, guest name, and allocates rooms.
            </div>
            <div style="background:#F9FAFB; padding:10px 12px; border-radius:6px; font-size:11px; font-family:var(--font-mono); color:#374151; border:1px solid #E5E7EB;">
              <strong>Auto-Forward Inbox:</strong> bookings@checkinos.io
            </div>
          </div>

          <!-- WhatsApp Direct Inbound Card -->
          <div class="card" style="padding:20px; border:1px solid #E5E7EB; background:#FFFFFF;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:36px; height:36px; border-radius:8px; background:#ECFDF5; color:#059669; display:flex; align-items:center; justify-content:center; font-weight:700;">
                  WA
                </div>
                <div>
                  <h4 style="font-size:15px; font-weight:700; margin:0;">WhatsApp Booking Alerts</h4>
                  <div style="font-size:11px; color:#6B7280;">OTA WhatsApp & Direct Bot</div>
                </div>
              </div>
              <span class="badge badge-success" style="font-size:11px; padding:2px 8px;">CONNECTED</span>
            </div>
            <div style="font-size:13px; color:#4B5563; line-height:1.5; margin-bottom:12px;">
              Receives incoming OTA WhatsApp alerts (e.g. OYO instant booking alerts) or direct guest WhatsApp messages. Parsed in under 1 second without human intervention.
            </div>
            <div style="background:#F9FAFB; padding:10px 12px; border-radius:6px; font-size:11px; font-family:var(--font-mono); color:#374151; border:1px solid #E5E7EB;">
              <strong>Active Webhook:</strong> /api/integrations/whatsapp/webhook
            </div>
          </div>
        </div>

        <!-- Interactive Inbound Message Simulator & Auto-Booker -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px; flex-wrap:wrap; gap:10px;">
            <div>
              <h3 style="font-size:16px; font-weight:700; margin:0;">Test Live OTA Inbound Sync & Room Allocation</h3>
              <p style="font-size:13px; color:#6B7280; margin:4px 0 0;">Click any OTA below to load an authentic booking notification and watch CheckinOS automatically parse and book it.</p>
            </div>
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.loadTemplate('booking')" style="font-size:11px; background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE;">
                Booking.com
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.loadTemplate('airbnb')" style="font-size:11px; background:#FFF1F2; color:#E11D48; border-color:#FECDD3;">
                Airbnb
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.loadTemplate('oyo')" style="font-size:11px; background:#FEF2F2; color:#DC2626; border-color:#FECACA;">
                OYO Rooms
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.loadTemplate('agoda')" style="font-size:11px; background:#F0F9FF; color:#0284C7; border-color:#BAE6FD;">
                Agoda
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.loadTemplate('makemytrip')" style="font-size:11px; background:#FFF7ED; color:#EA580C; border-color:#FED7AA;">
                MakeMyTrip
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.loadTemplate('whatsapp')" style="font-size:11px; background:#ECFDF5; color:#059669; border-color:#A7F3D0;">
                WhatsApp
              </button>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:140px 1fr; gap:12px; margin-bottom:14px;">
            <div>
              <label class="form-label" style="font-size:12px;">Channel</label>
              <select id="sync-channel-select" class="form-select" style="height:38px; font-size:13px;">
                <option value="gmail">Email (Gmail)</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="font-size:12px;">Sender (OTA or Phone)</label>
              <input type="text" id="sync-sender-input" class="form-input" value="customer.service@booking.com" placeholder="e.g. customer.service@booking.com or +91 98765 43210" style="height:38px; font-size:13px;">
            </div>
          </div>

          <div style="margin-bottom:16px;">
            <label class="form-label" style="font-size:12px;">Inbound OTA Message / Email Voucher Body</label>
            <textarea id="sync-raw-text" class="form-input font-mono" rows="6" style="width:100%; font-size:12px; line-height:1.4; padding:10px;">Subject: Booking.com New Reservation #389281729

New booking confirmed!
Booking.com Confirmation Number: 389281729
Guest Name: Vikram Malhotra
Phone: +91 98765 43210
Email: vikram.389281@guest.booking.com
Booked Room: Deluxe King (1 room, 2 adults)
Check-in: 2026-11-25
Check-out: 2026-11-28 (3 nights)
Total Price: INR 22,500.00
Payment: Paid online via Booking.com</textarea>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:12px; color:#6B7280;">
              ✨ Automatic OTA detection, entity extraction, room collision checking, folio creation & GST posting
            </div>
            <button id="sync-execute-btn" class="btn btn-primary btn-md" onclick="window.Pages.Settings.processInboundBooking()" style="height:38px; padding:0 20px;">
              Process & Auto-Create Reservation
            </button>
          </div>

          <div id="sync-result-zone" style="display:none; margin-top:20px;"></div>
        </div>

        <!-- Recent Auto-Synced Reservations Feed -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h3 style="font-size:16px; font-weight:700; margin:0;">Recent Auto-Synced Inbound Reservations</h3>
            <button class="btn btn-secondary btn-sm" onclick="window.Pages.Settings.refreshSyncFeed()" style="font-size:11px;">
              Refresh Feed
            </button>
          </div>
          <div id="sync-feed-container">
            <div style="padding:20px; text-align:center; color:#6B7280;">Loading auto-synced reservations...</div>
          </div>
        </div>
      </div>
    `;

    await this.refreshSyncFeed();
  },

  loadTemplate(type) {
    const channelSelect = document.getElementById('sync-channel-select');
    const senderInput = document.getElementById('sync-sender-input');
    const textArea = document.getElementById('sync-raw-text');

    if (type === 'booking') {
      channelSelect.value = 'gmail';
      senderInput.value = 'customer.service@booking.com';
      textArea.value = 'Subject: Booking.com New Reservation #389281729\n\nNew booking confirmed!\nBooking.com Confirmation Number: 389281729\nGuest Name: Vikram Malhotra\nPhone: +91 98765 43210\nEmail: vikram.389281@guest.booking.com\nBooked Room: Deluxe King (1 room, 2 adults)\nCheck-in: 2026-11-25\nCheck-out: 2026-11-28 (3 nights)\nTotal Price: INR 22,500.00\nPayment: Paid online via Booking.com';
    } else if (type === 'airbnb') {
      channelSelect.value = 'gmail';
      senderInput.value = 'automated@airbnb.com';
      textArea.value = 'Subject: Reservation confirmed - Sarah Jenkins arrives 26 Nov\n\nAirbnb Confirmation Code: HM489X2P\nGuest: Sarah Jenkins\nGuests: 2 adults\nDates: Nov 26 - Nov 29, 2026 (3 nights)\nListing: Executive Heritage Suite\nTotal Host Payout: INR 49,500\nGuest Contact: +1 415 555 2671';
    } else if (type === 'oyo') {
      channelSelect.value = 'whatsapp';
      senderInput.value = '+91 80100 00099';
      textArea.value = 'OYO Booking Alert! Booking ID: OYO-94821. New booking received for Rohan Mehta (2 guests). Check-in: 25 Nov 2026, Check-out: 27 Nov 2026. Room: Deluxe King. Total Amount: INR 15,000. Phone: +91 91234 56789. Please ensure room is ready!';
    } else if (type === 'agoda') {
      channelSelect.value = 'gmail';
      senderInput.value = 'express-booking@agoda.com';
      textArea.value = 'Agoda Booking Voucher - ID: 7892143\n\nGuest Name: Hiroshi Tanaka\nStay Dates: 2026-11-27 to 2026-11-30 (3 nights)\nBooked Room Type: Standard Suite\nNumber of Guests: 1 adult\nAmount Collected by Agoda: INR 18,000\nGuest Email: h.tanaka@agoda-guest.com\nGuest Phone: +81 90 1234 5678';
    } else if (type === 'makemytrip') {
      channelSelect.value = 'whatsapp';
      senderInput.value = '+91 98200 11223';
      textArea.value = 'MakeMyTrip Instant Booking Notification! Booking ID: MMT-83921. Guest: Ananya Sharma. Check-in: 26 Nov 2026, Check-out: 28 Nov 2026 (2 nights). Room Type: Deluxe King. Total Payable: INR 16,800. Phone: +91 99887 76655.';
    } else {
      channelSelect.value = 'whatsapp';
      senderInput.value = '+91 98112 34567';
      textArea.value = 'Hi Hotel Grand! I want to book a Deluxe room from 2026-11-26 to 2026-11-29 for Rohan Verma, 2 adults. Phone: +91 98112 34567. Please confirm room availability!';
    }
  },

  async processInboundBooking() {
    const channel = document.getElementById('sync-channel-select').value;
    const sender = document.getElementById('sync-sender-input').value.trim();
    const raw_text = document.getElementById('sync-raw-text').value.trim();
    const btn = document.getElementById('sync-execute-btn');
    const zone = document.getElementById('sync-result-zone');

    if (!raw_text) {
      UI.toast('Please provide message text to parse.', 'warning');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Parsing & Booking...';
    zone.style.display = 'none';

    try {
      const resp = await API.post('/api/integrations/inbox-sync', {
        channel,
        sender: sender || (channel === 'whatsapp' ? '+919999999999' : 'guest@example.com'),
        raw_text,
      });

      zone.style.display = 'block';
      const otaBadge = resp.ota_provider && resp.ota_provider !== 'Direct Channel'
        ? `<span class="badge" style="background:#111827; color:#FFFFFF; font-size:11px; padding:2px 8px; margin-right:8px;">${resp.ota_provider}</span>`
        : '';

      zone.innerHTML = `
        <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:18px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="display:flex; align-items:center;">
              ${otaBadge}
              <strong style="color:#065F46; font-size:15px;">✓ Reservation Auto-Created & Room Allocated!</strong>
            </div>
            <span class="badge ${resp.channel === 'whatsapp' ? 'badge-success' : 'badge-info'}" style="text-transform:uppercase;">
              ${resp.channel} AUTO-SYNC
            </span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; font-size:13px; color:#1F2937; margin-bottom:12px;">
            <div><span style="color:#6B7280; font-size:11px; display:block;">CONFIRMATION #</span><strong class="font-mono">${resp.confirmation_number}</strong></div>
            <div><span style="color:#6B7280; font-size:11px; display:block;">GUEST</span><strong>${resp.guest_name}</strong></div>
            <div><span style="color:#6B7280; font-size:11px; display:block;">ROOM NUMBER</span><strong>Room ${resp.room_number} (${resp.room_type})</strong></div>
            <div><span style="color:#6B7280; font-size:11px; display:block;">DATES</span><strong>${resp.check_in_date} → ${resp.check_out_date}</strong></div>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button class="btn btn-secondary btn-sm" onclick="window.openReservationDrawer(${resp.reservation_id})">
              Open Reservation Folio Drawer
            </button>
            <button class="btn btn-primary btn-sm" onclick="window.location.href='/reservations'">
              View on Reservations Desk →
            </button>
          </div>
        </div>
      `;

      UI.toast(`Auto-booked Room ${resp.room_number} for ${resp.guest_name} (${resp.ota_provider || 'OTA'})!`, 'success');
      await this.refreshSyncFeed();
    } catch (err) {
      zone.style.display = 'block';
      zone.innerHTML = `
        <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:8px; padding:16px; color:#DC2626; font-size:13px;">
          <strong>Ingestion Error:</strong> ${err.message || 'Failed to parse message.'}
        </div>
      `;
      UI.toast(err.message, 'danger');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Process & Auto-Create Reservation';
    }
  },

  async refreshSyncFeed() {
    const feedContainer = document.getElementById('sync-feed-container');
    if (!feedContainer) return;

    try {
      const feed = await API.get('/api/integrations/feed');
      if (!feed || feed.length === 0) {
        feedContainer.innerHTML = `
          <div style="text-align:center; padding:32px; color:#6B7280; font-size:13px;">
            No auto-synced reservations yet. Run a test simulation above to create your first auto-booking.
          </div>
        `;
        return;
      }

      const getOtaBadgeStyle = (ota) => {
        if (ota === 'Booking.com') return 'background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;';
        if (ota === 'Airbnb') return 'background:#FFF1F2; color:#E11D48; border:1px solid #FECDD3;';
        if (ota === 'OYO') return 'background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;';
        if (ota === 'Agoda') return 'background:#F0F9FF; color:#0284C7; border:1px solid #BAE6FD;';
        if (ota === 'MakeMyTrip') return 'background:#FFF7ED; color:#EA580C; border:1px solid #FED7AA;';
        return 'background:#ECFDF5; color:#059669; border:1px solid #A7F3D0;';
      };

      feedContainer.innerHTML = `
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Channel / OTA</th>
                <th>Confirmation</th>
                <th>Guest</th>
                <th>Room</th>
                <th>Stay Dates</th>
                <th>Status</th>
                <th style="text-align:right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${feed.map(item => `
                <tr>
                  <td>
                    <div style="display:flex; align-items:center; gap:6px;">
                      <span class="badge" style="font-size:10px; font-weight:700; ${getOtaBadgeStyle(item.ota_provider)}">
                        ${item.ota_provider || 'OTA'}
                      </span>
                      <span style="font-size:11px; color:#6B7280;">(${item.channel})</span>
                    </div>
                  </td>
                  <td class="font-mono" style="font-weight:600; font-size:12px;">${item.confirmation_number}</td>
                  <td>
                    <div style="font-weight:600; font-size:13px;">${item.guest_name}</div>
                    <div style="font-size:11px; color:#6B7280;">${item.phone}</div>
                  </td>
                  <td><strong>Room ${item.room_number}</strong></td>
                  <td style="font-size:12px;">${item.check_in_date} → ${item.check_out_date}</td>
                  <td>
                    <span class="badge ${item.status === 'checked_in' ? 'badge-success' : 'badge-neutral'}">
                      ${item.status.toUpperCase()}
                    </span>
                  </td>
                  <td style="text-align:right;">
                    <button class="btn btn-secondary btn-sm" onclick="window.openReservationDrawer(${item.id})" style="font-size:11px; padding:3px 8px;">
                      Manage
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      feedContainer.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load sync feed: ${err.message}</div>`;
    }
  },
};


