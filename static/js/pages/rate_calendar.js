/**
 * CheckinOS - Rate Calendar Page
 * 30-Day Dynamic Pricing, Rate Override Management, and Occupancy Matrix.
 */

window.Pages = window.Pages || {};

window.Pages.RateCalendar = {
  startDate: null,
  daysCount: 30,
  calendarData: null,

  async render(container) {
    if (!this.startDate) {
      const today = window.currentBusinessDate ? new Date(window.currentBusinessDate) : new Date();
      this.startDate = today.toISOString().slice(0, 10);
    }

    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:20px;">
        <!-- Top Toolbar -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <div style="display:inline-flex; align-items:center; gap:6px; flex-shrink:0;">
              <button class="btn btn-secondary date-nav-btn" id="cal-prev-btn" title="Previous 30 Days">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
                <span>Prev 30 Days</span>
              </button>
              <button class="btn btn-secondary date-nav-btn" id="cal-today-btn" title="Jump to Today">Today</button>
              <button class="btn btn-secondary date-nav-btn" id="cal-next-btn" title="Next 30 Days">
                <span>Next 30 Days</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
              </button>
            </div>
            <span id="cal-range-label" style="font-size:13px; font-weight:600; color:#374151; margin-left:4px; white-space:nowrap;"></span>
          </div>

          <div style="display:flex; align-items:center; gap:8px;">
            <div style="display:flex; align-items:center; gap:12px; font-size:11px; margin-right:12px;">
              <span style="display:inline-flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:2px; background:#ECFDF5; border:1px solid #A7F3D0;"></span> &lt;50% Occ</span>
              <span style="display:inline-flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:2px; background:#FFFBEB; border:1px solid #FDE68A;"></span> 50-85% Occ</span>
              <span style="display:inline-flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; border-radius:2px; background:#FEF2F2; border:1px solid #FECACA;"></span> &gt;85% Occ</span>
            </div>

            <button class="btn btn-primary btn-sm" id="cal-bulk-btn">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.5 6h9.75M10.5 12h9.75M10.5 18h9.75M3.75 6.75h.007v.008H3.75V6.75Zm0 5.25h.007v.008H3.75V12Zm0 5.25h.007v.008H3.75V17.25Z" /></svg>
              <span>Bulk Override</span>
            </button>
          </div>
        </div>

        <!-- Matrix Container -->
        <div class="card" style="padding:0; overflow:hidden; border:1px solid #E5E7EB;">
          <div id="rate-calendar-grid" style="overflow-x:auto; max-height:calc(100vh - 240px);">
            <div style="padding:48px; text-align:center; color:#6B7280;">Loading rate matrix...</div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  },

  bindEvents() {
    document.getElementById('cal-prev-btn').onclick = () => {
      const d = new Date(this.startDate);
      d.setDate(d.getDate() - 30);
      this.startDate = d.toISOString().slice(0, 10);
      this.loadData();
    };

    document.getElementById('cal-today-btn').onclick = () => {
      const d = window.currentBusinessDate ? new Date(window.currentBusinessDate) : new Date();
      this.startDate = d.toISOString().slice(0, 10);
      this.loadData();
    };

    document.getElementById('cal-next-btn').onclick = () => {
      const d = new Date(this.startDate);
      d.setDate(d.getDate() + 30);
      this.startDate = d.toISOString().slice(0, 10);
      this.loadData();
    };

    document.getElementById('cal-bulk-btn').onclick = () => this.openBulkModal();
  },

  async loadData() {
    const grid = document.getElementById('rate-calendar-grid');
    if (!grid) return;

    try {
      const res = await API.get('/api/rate-calendar', {
        start_date: this.startDate,
        days: this.daysCount,
      });
      this.calendarData = res;
      this.renderGrid(res);
    } catch (e) {
      grid.innerHTML = `<div style="padding:32px; color:#DC2626; text-align:center;">Failed to load rate calendar: ${e.message}</div>`;
    }
  },

  renderGrid(data) {
    const grid = document.getElementById('rate-calendar-grid');
    if (!grid) return;

    if (!data.room_types || data.room_types.length === 0) {
      grid.innerHTML = '<div style="padding:48px; text-align:center; color:#6B7280;">No room types found.</div>';
      return;
    }

    const sampleDays = data.room_types[0].days;
    const startStr = formatDate(sampleDays[0].date);
    const endStr = formatDate(sampleDays[sampleDays.length - 1].date);
    const rangeLabel = document.getElementById('cal-range-label');
    if (rangeLabel) rangeLabel.textContent = `${startStr} – ${endStr} (30 Days)`;

    let html = `
      <table style="width:100%; border-collapse:separate; border-spacing:0; font-size:12px; text-align:center;">
        <thead>
          <tr style="background:#F9FAFB; position:sticky; top:0; z-index:10;">
            <th style="position:sticky; left:0; z-index:12; background:#F9FAFB; min-width:180px; max-width:180px; padding:12px 16px; text-align:left; font-size:11px; font-weight:700; color:#374151; border-bottom:1px solid #E5E7EB; border-right:1px solid #E5E7EB;">
              ROOM CATEGORY
            </th>
    `;

    sampleDays.forEach((d) => {
      const dateObj = new Date(d.date + 'T00:00:00');
      const dayName = new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(dateObj);
      const dayNum = dateObj.getDate();
      const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;

      html += `
        <th style="min-width:96px; padding:8px 4px; border-bottom:1px solid #E5E7EB; border-right:1px solid #F3F4F6; background:${isWeekend ? '#F3F4F6' : '#F9FAFB'};">
          <div style="font-size:10px; font-weight:600; color:${isWeekend ? '#DC2626' : '#6B7280'}; text-transform:uppercase;">${dayName}</div>
          <div style="font-size:14px; font-weight:700; color:#111827;" class="font-mono">${dayNum}</div>
        </th>
      `;
    });

    html += `</tr></thead><tbody>`;

    data.room_types.forEach((rt) => {
      html += `
        <tr style="border-bottom:1px solid #E5E7EB;">
          <!-- Category Label (Sticky Column) -->
          <td style="position:sticky; left:0; z-index:5; background:#FFFFFF; padding:12px 16px; text-align:left; border-bottom:1px solid #E5E7EB; border-right:1px solid #E5E7EB; box-shadow: 2px 0 4px -2px rgba(0,0,0,0.05);">
            <div style="font-weight:600; color:#111827; font-size:13px;">${rt.name}</div>
            <div style="display:flex; gap:8px; align-items:center; margin-top:2px;">
              <span class="badge badge-neutral" style="font-size:9px; height:16px; padding:0 4px;">${rt.code}</span>
              <span style="font-size:11px; color:#6B7280;">${rt.room_count} rooms</span>
            </div>
            <div style="font-size:11px; color:#6B7280; margin-top:2px;">
              Base: <span class="font-mono font-bold" style="color:#111827;">${formatCurrency(rt.base_rate)}</span>
            </div>
          </td>
      `;

      rt.days.forEach((day) => {
        // Color tint by occupancy
        let tintBg = '#ECFDF5';
        let tintBorder = '#A7F3D0';
        let tintText = '#065F46';

        if (day.occupancy_pct >= 85) {
          tintBg = '#FEF2F2';
          tintBorder = '#FECACA';
          tintText = '#991B1B';
        } else if (day.occupancy_pct >= 50) {
          tintBg = '#FFFBEB';
          tintBorder = '#FDE68A';
          tintText = '#92400E';
        }

        const isOverride = day.override_id !== null;

        html += `
          <td class="rate-cal-cell" 
              data-rt-id="${rt.id}" 
              data-rt-name="${rt.name}"
              data-date="${day.date}" 
              data-rate="${day.rate}" 
              data-override-id="${day.override_id || ''}"
              data-closed="${day.closed}"
              data-min-stay="${day.min_stay || ''}"
              style="padding:6px 4px; border-bottom:1px solid #E5E7EB; border-right:1px solid #F3F4F6; cursor:pointer; vertical-align:top; transition:background 0.15s ease;"
              title="Click to edit rate for ${rt.name} on ${day.date}">
            <div style="display:flex; flex-direction:column; gap:4px; align-items:center;">
              <!-- Price Display -->
              <div style="display:flex; align-items:center; gap:2px;">
                <span class="font-mono" style="font-size:12px; font-weight:700; color:${isOverride ? '#2563EB' : '#111827'};">
                  ${formatCurrency(day.rate)}
                </span>
                ${isOverride ? '<span style="font-size:9px; color:#2563EB; font-weight:bold;">*</span>' : ''}
              </div>

              <!-- Occupancy Pill -->
              <div style="background:${tintBg}; border:1px solid ${tintBorder}; color:${tintText}; border-radius:4px; padding:2px 4px; font-size:10px; width:100%; max-width:84px; display:flex; justify-content:space-between; align-items:center;">
                <span class="font-mono font-bold">${day.available_count}L</span>
                <span class="font-mono" style="font-size:9px;">${Math.round(day.occupancy_pct)}%</span>
              </div>

              <!-- Indicators: Closed, Min Stay -->
              <div style="display:flex; gap:2px; flex-wrap:wrap; justify-content:center;">
                ${day.closed ? '<span style="background:#EF4444; color:#FFF; font-size:8px; padding:1px 3px; border-radius:2px; font-weight:700;">STOP</span>' : ''}
                ${day.min_stay ? `<span style="background:#E0E7FF; color:#3730A3; font-size:8px; padding:1px 3px; border-radius:2px; font-weight:600;">${day.min_stay}n</span>` : ''}
              </div>
            </div>
          </td>
        `;
      });

      html += `</tr>`;
    });

    html += `</tbody></table>`;
    grid.innerHTML = html;

    // Attach click events on cells
    grid.querySelectorAll('.rate-cal-cell').forEach((td) => {
      td.addEventListener('click', () => {
        const rtId = parseInt(td.getAttribute('data-rt-id'));
        const rtName = td.getAttribute('data-rt-name');
        const dt = td.getAttribute('data-date');
        const rate = td.getAttribute('data-rate');
        const overrideId = td.getAttribute('data-override-id');
        const closed = td.getAttribute('data-closed') === 'true';
        const minStay = td.getAttribute('data-min-stay');

        this.openEditModal({ rtId, rtName, dt, rate, overrideId, closed, minStay });
      });
    });
  },

  openEditModal({ rtId, rtName, dt, rate, overrideId, closed, minStay }) {
    const formattedD = formatDate(dt, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

    UI.modal({
      title: `Update Rate · ${rtName}`,
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="font-size:12px; color:#6B7280; border-bottom:1px solid #E5E7EB; padding-bottom:8px;">
            Target Date: <strong>${formattedD}</strong>
          </div>

          <div class="form-group">
            <label class="form-label">Nightly Rate (${getCurrencySymbol()}${getActiveCurrency()})</label>
            <input type="number" step="100" id="override-modal-rate" class="form-input font-mono" value="${rate}" required>
          </div>

          <div class="form-group">
            <label class="form-label">Minimum Stay Requirement (Nights)</label>
            <input type="number" min="1" max="30" id="override-modal-min-stay" class="form-input font-mono" value="${minStay || ''}" placeholder="No minimum stay">
          </div>

          <div style="display:flex; gap:16px; align-items:center; margin-top:4px;">
            <label style="display:flex; align-items:center; gap:8px; font-size:13px; font-weight:500; cursor:pointer;">
              <input type="checkbox" id="override-modal-closed" ${closed ? 'checked' : ''} style="width:16px; height:16px;">
              <span>Stop Sell / Close Room Type</span>
            </label>
          </div>
        </div>
      `,
      footerHtml: `
        <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
          <div>
            ${overrideId ? `<button class="btn btn-ghost btn-sm" id="override-modal-delete-btn" style="color:#DC2626;">Reset to Base</button>` : ''}
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
            <button class="btn btn-primary btn-md" id="override-modal-save-btn">Save Override</button>
          </div>
        </div>
      `,
    });

    document.getElementById('override-modal-save-btn').onclick = async () => {
      const newRate = parseFloat(document.getElementById('override-modal-rate').value);
      const newMinStayVal = document.getElementById('override-modal-min-stay').value;
      const newMinStay = newMinStayVal ? parseInt(newMinStayVal) : null;
      const isClosed = document.getElementById('override-modal-closed').checked;

      if (isNaN(newRate) || newRate <= 0) {
        UI.toast('Please enter a valid positive rate.', 'error');
        return;
      }

      try {
        await API.put('/api/rate-overrides', {
          room_type_id: rtId,
          date: dt,
          rate: newRate,
          min_stay: newMinStay,
          closed: isClosed,
          closed_to_arrival: false,
          closed_to_departure: false,
        });

        UI.toast(`Updated rate for ${rtName} on ${formatDate(dt)}`, 'success');
        UI.closeModal();
        this.loadData();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };

    const delBtn = document.getElementById('override-modal-delete-btn');
    if (delBtn) {
      delBtn.onclick = async () => {
        try {
          await API.delete(`/api/rate-overrides/${overrideId}`);
          UI.toast('Override removed. Reverted to category base rate.', 'success');
          UI.closeModal();
          this.loadData();
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      };
    }
  },

  openBulkModal() {
    if (!this.calendarData || !this.calendarData.room_types) return;

    const rtCheckboxes = this.calendarData.room_types.map((rt) => `
      <label style="display:flex; align-items:center; gap:8px; font-size:13px; font-weight:500; cursor:pointer;">
        <input type="checkbox" name="bulk-rt-id" value="${rt.id}" checked style="width:16px; height:16px;">
        <span>${rt.name} (Base: ${formatCurrency(rt.base_rate)})</span>
      </label>
    `).join('');

    const todayStr = this.startDate;
    const endStr = new Date(new Date(this.startDate).getTime() + 14 * 86400000).toISOString().slice(0, 10);

    UI.modal({
      title: 'Bulk Override Rates & Inventory',
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div>
            <label class="form-label" style="margin-bottom:6px;">Select Room Categories</label>
            <div style="display:flex; flex-direction:column; gap:8px; padding:12px; background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px;">
              ${rtCheckboxes}
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">From Date</label>
              <input type="date" id="bulk-start-date" class="form-input" value="${todayStr}" required>
            </div>
            <div class="form-group">
              <label class="form-label">To Date</label>
              <input type="date" id="bulk-end-date" class="form-input" value="${endStr}" required>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">New Nightly Rate (${getCurrencySymbol()}${getActiveCurrency()})</label>
              <input type="number" step="100" id="bulk-rate" class="form-input font-mono" placeholder="Leave empty to keep current">
            </div>
            <div class="form-group">
              <label class="form-label">Minimum Stay (Nights)</label>
              <input type="number" min="1" max="30" id="bulk-min-stay" class="form-input font-mono" placeholder="No restriction">
            </div>
          </div>

          <div style="display:flex; gap:16px;">
            <label style="display:flex; align-items:center; gap:8px; font-size:13px; font-weight:500; cursor:pointer;">
              <input type="checkbox" id="bulk-closed" style="width:16px; height:16px;">
              <span>Stop Sell / Close Room Types in Date Range</span>
            </label>
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
        <button class="btn btn-primary btn-md" id="bulk-apply-btn">Apply Bulk Overrides</button>
      `,
    });

    document.getElementById('bulk-apply-btn').onclick = async () => {
      const selectedRt = Array.from(document.querySelectorAll('input[name="bulk-rt-id"]:checked')).map(el => parseInt(el.value));
      const fromD = document.getElementById('bulk-start-date').value;
      const toD = document.getElementById('bulk-end-date').value;
      const rateVal = document.getElementById('bulk-rate').value;
      const minStayVal = document.getElementById('bulk-min-stay').value;
      const isClosed = document.getElementById('bulk-closed').checked;

      if (!selectedRt.length) {
        UI.toast('Select at least one room category.', 'error');
        return;
      }
      if (!fromD || !toD || toD < fromD) {
        UI.toast('Please select a valid date range.', 'error');
        return;
      }

      // Generate date array
      const dates = [];
      let cur = new Date(fromD + 'T00:00:00');
      const end = new Date(toD + 'T00:00:00');
      while (cur <= end) {
        dates.push(cur.toISOString().slice(0, 10));
        cur.setDate(cur.getDate() + 1);
      }

      try {
        const payload = {
          room_type_ids: selectedRt,
          dates: dates,
          rate: rateVal ? parseFloat(rateVal) : null,
          min_stay: minStayVal ? parseInt(minStayVal) : null,
          closed: isClosed ? true : null,
        };

        const res = await API.post('/api/rate-overrides/bulk', payload);
        UI.toast(res.message || 'Bulk overrides applied successfully!', 'success');
        UI.closeModal();
        this.loadData();
      } catch (err) {
        UI.toast(err.message, 'error');
      }
    };
  },
};
