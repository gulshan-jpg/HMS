/**
 * CheckinOS - Night Audit & End-of-Day Management Page
 * Reconciles revenue, auto-posts room charges & taxes, marks no-shows, advances business date.
 */

window.Pages = window.Pages || {};

window.Pages.NightAudit = {
  previewData: null,
  historyData: [],

  async render(container) {
    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:24px;">
        <!-- Close Day Action Card -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px;">
                <h2 style="font-size:18px; font-weight:700; color:#111827; margin:0;">End-of-Day Night Audit Roll</h2>
                <span class="badge badge-success" style="font-size:11px;">SYSTEM OPEN</span>
              </div>
              <p style="font-size:13px; color:#6B7280; margin-top:4px; max-width:640px;">
                Executing the night audit finalizes daily room revenues, assesses no-show penalties, generates financial snapshots, and rolls the hotel business calendar forward by 24 hours.
              </p>
            </div>

            <div style="display:flex; gap:12px; align-items:center;">
              <button class="btn btn-secondary btn-md" id="audit-refresh-preview-btn">
                <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
                <span>Refresh Checks</span>
              </button>
              <button class="btn btn-primary btn-md" id="audit-run-btn" style="background:#111827;">
                <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" /></svg>
                <span>Run Night Audit</span>
              </button>
            </div>
          </div>

          <!-- Audit Checklist / Stats Grid -->
          <div id="audit-preview-container" style="margin-top:20px; border-top:1px solid #F3F4F6; padding-top:20px;">
            <div style="text-align:center; padding:24px; color:#6B7280;">Loading audit dry run...</div>
          </div>
        </div>

        <!-- Historical Snapshots Table -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <div>
              <h3 style="font-size:16px; font-weight:700; color:#111827; margin:0;">Historical Daily Audit Snapshots</h3>
              <p style="font-size:12px; color:#6B7280; margin-top:2px;">Audited performance and tax records for previous business dates.</p>
            </div>
          </div>

          <div id="audit-history-container" style="overflow-x:auto;">
            <div style="text-align:center; padding:24px; color:#6B7280;">Loading snapshot history...</div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadPreview();
    await this.loadHistory();
  },

  bindEvents() {
    document.getElementById('audit-refresh-preview-btn').onclick = () => this.loadPreview();
    document.getElementById('audit-run-btn').onclick = () => this.openRunConfirmationModal();
  },

  async loadPreview() {
    const container = document.getElementById('audit-preview-container');
    if (!container) return;

    try {
      const data = await API.get('/api/night-audit/preview');
      this.previewData = data;

      const formattedCur = formatDate(data.business_date, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
      const formattedNext = formatDate(data.next_business_date, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

      let warningHtml = '';
      if (data.warning_message) {
        warningHtml = `
          <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; padding:12px 16px; display:flex; align-items:flex-start; gap:12px; margin-bottom:16px;">
            <svg style="width:20px; height:20px; color:#D97706; flex-shrink:0; margin-top:1px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
            <div>
              <div style="font-size:13px; font-weight:700; color:#92400E;">Departure Resolution Required</div>
              <div style="font-size:12px; color:#B45309; margin-top:2px;">${data.warning_message}</div>
            </div>
          </div>
        `;
      }

      container.innerHTML = `
        ${warningHtml}

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:16px;">
          <!-- Card 1: Current vs Next -->
          <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:8px; padding:14px;">
            <div style="font-size:11px; font-weight:600; color:#6B7280; text-transform:uppercase;">Business Date Transition</div>
            <div style="font-size:14px; font-weight:700; color:#111827; margin-top:6px;" class="font-mono">${data.business_date}</div>
            <div style="font-size:11px; color:#059669; font-weight:600; margin-top:4px;">Rolls to → ${data.next_business_date}</div>
          </div>

          <!-- Card 2: Room Charges -->
          <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:8px; padding:14px;">
            <div style="font-size:11px; font-weight:600; color:#6B7280; text-transform:uppercase;">Room Charges to Post</div>
            <div style="font-size:18px; font-weight:700; color:#111827; margin-top:4px;" class="font-mono">
              ${formatCurrency(data.room_charges_estimated_total)}
            </div>
            <div style="font-size:11px; color:#6B7280; margin-top:4px;">${data.room_charges_to_post_count} in-house reservation(s)</div>
          </div>

          <!-- Card 3: No-Shows -->
          <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:8px; padding:14px;">
            <div style="font-size:11px; font-weight:600; color:#6B7280; text-transform:uppercase;">Pending No-Shows</div>
            <div style="font-size:18px; font-weight:700; color:${data.no_shows_count > 0 ? '#D97706' : '#111827'}; margin-top:4px;" class="font-mono">
              ${data.no_shows_count}
            </div>
            <div style="font-size:11px; color:#6B7280; margin-top:4px;">Penalties: ${formatCurrency(data.no_show_estimated_penalties)}</div>
          </div>

          <!-- Card 4: Unresolved Departures -->
          <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:8px; padding:14px;">
            <div style="font-size:11px; font-weight:600; color:#6B7280; text-transform:uppercase;">Unresolved Departures</div>
            <div style="font-size:18px; font-weight:700; color:${data.unresolved_departures_count > 0 ? '#DC2626' : '#059669'}; margin-top:4px;" class="font-mono">
              ${data.unresolved_departures_count}
            </div>
            <div style="font-size:11px; color:${data.can_run_without_force ? '#059669' : '#DC2626'}; font-weight:600; margin-top:4px;">
              ${data.can_run_without_force ? 'All Departures Clear' : 'Requires Checkout / Force'}
            </div>
          </div>
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load audit preview: ${e.message}</div>`;
    }
  },

  async loadHistory() {
    const container = document.getElementById('audit-history-container');
    if (!container) return;

    try {
      const records = await API.get('/api/night-audit/history?limit=30');
      this.historyData = records;

      if (!records || records.length === 0) {
        container.innerHTML = '<div style="padding:24px; text-align:center; color:#6B7280;">No historical snapshots found yet.</div>';
        return;
      }

      let html = `
        <table class="data-table" style="width:100%; font-size:12px;">
          <thead>
            <tr>
              <th>BUSINESS DATE</th>
              <th>OCCUPANCY</th>
              <th>ADR</th>
              <th>REVPAR</th>
              <th>ROOM REVENUE</th>
              <th>TOTAL REVENUE</th>
              <th>TAXES COLLECTED</th>
              <th>ARRIVALS</th>
              <th>DEPARTURES</th>
            </tr>
          </thead>
          <tbody>
      `;

      records.forEach((s) => {
        html += `
          <tr>
            <td class="font-mono font-bold">${s.business_date}</td>
            <td class="font-mono">${parseFloat(s.occupancy_rate).toFixed(1)}%</td>
            <td class="font-mono">${formatCurrency(s.adr)}</td>
            <td class="font-mono">${formatCurrency(s.revpar)}</td>
            <td class="font-mono font-bold">${formatCurrency(s.room_revenue)}</td>
            <td class="font-mono font-bold">${formatCurrency(s.total_revenue)}</td>
            <td class="font-mono">${formatCurrency(s.tax_collected)}</td>
            <td class="font-mono">${s.arrivals}</td>
            <td class="font-mono">${s.departures}</td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
    } catch (e) {
      container.innerHTML = `<div style="color:#DC2626; padding:16px;">Failed to load snapshot history: ${e.message}</div>`;
    }
  },

  openRunConfirmationModal() {
    if (!this.previewData) return;

    const data = this.previewData;
    const hasWarnings = data.unresolved_departures_count > 0;

    UI.modal({
      title: 'Confirm Night Audit Execution',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <p style="font-size:13px; color:#374151; margin:0;">
            You are about to close hotel business date <strong>${data.business_date}</strong> and roll to <strong>${data.next_business_date}</strong>.
          </p>

          <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; padding:12px; font-size:12px; display:flex; flex-direction:column; gap:6px;">
            <div>• Post <strong>${data.room_charges_to_post_count}</strong> room night charges & applicable taxes totaling <strong>${formatCurrency(data.room_charges_estimated_total)}</strong>.</div>
            <div>• Mark <strong>${data.no_shows_count}</strong> unarrived reservation(s) as No-Show with penalty charges.</div>
            <div>• Generate immutable daily financial snapshot for historical reporting.</div>
          </div>

          ${hasWarnings ? `
            <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:12px; font-size:12px; color:#991B1B;">
              <strong>Warning:</strong> There are ${data.unresolved_departures_count} overdue departure(s). You must check the confirmation below to force roll.
              <label style="display:flex; align-items:center; gap:8px; margin-top:8px; cursor:pointer; font-weight:600;">
                <input type="checkbox" id="audit-force-checkbox" style="width:16px; height:16px;">
                <span>Force Close Day despite unresolved departures</span>
              </label>
            </div>
          ` : ''}
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="audit-execute-btn" style="background:#DC2626; border-color:#DC2626;">
          Execute Audit & Roll Date
        </button>
      `,
    });

    document.getElementById('audit-execute-btn').onclick = async () => {
      const forceCheckbox = document.getElementById('audit-force-checkbox');
      const forceVal = forceCheckbox ? forceCheckbox.checked : false;

      if (hasWarnings && !forceVal) {
        UI.toast('Please check "Force Close Day" to proceed with unresolved departures.', 'error');
        return;
      }

      try {
        const res = await API.post('/api/night-audit/run', { force: forceVal });
        UI.closeModal();
        UI.toast(`Night audit completed! Business date rolled to ${res.new_business_date}`, 'success');

        // Refresh topbar business date
        if (window.refreshBusinessDate) {
          window.refreshBusinessDate();
        }

        await this.loadPreview();
        await this.loadHistory();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },
};
