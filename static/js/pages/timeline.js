/**
 * CheckinOS - Availability Timeline / Gantt Page
 * 30-Day Room Schedule, Interactive Reservation Blocks, Move & Reallocation Workflows.
 */

window.Pages = window.Pages || {};

window.Pages.Timeline = {
  startDate: null,
  daysCount: 30,
  floorFilter: 'all',
  timelineData: null,

  async render(container) {
    if (!this.startDate) {
      const today = window.currentBusinessDate ? new Date(window.currentBusinessDate) : new Date();
      this.startDate = today.toISOString().slice(0, 10);
    }

    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <!-- Top Toolbar -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <div style="display:inline-flex; align-items:center; gap:6px; flex-shrink:0; max-width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch; padding:2px 0;">
              <button class="btn btn-secondary date-nav-btn" id="tl-prev-btn" title="Previous 30 Days">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
                <span>Prev 30 Days</span>
              </button>
              <button class="btn btn-secondary date-nav-btn" id="tl-today-btn" title="Jump to Today">Today</button>
              <button class="btn btn-secondary date-nav-btn" id="tl-next-btn" title="Next 30 Days">
                <span>Next 30 Days</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
              </button>
            </div>
            <span id="tl-range-label" style="font-size:13px; font-weight:600; color:#374151; margin-left:4px; white-space:nowrap;"></span>
          </div>

          <div style="display:flex; align-items:center; gap:12px;">
            <!-- Floor Filter -->
            <select id="tl-floor-select" class="form-select font-mono" style="font-size:12px; height:32px; width:130px;">
              <option value="all">All Floors</option>
              <option value="1">Floor 1 (101-110)</option>
              <option value="2">Floor 2 (201-207)</option>
              <option value="3">Floor 3 (301-303)</option>
            </select>

            <!-- Legend -->
            <div style="display:flex; align-items:center; gap:10px; font-size:11px;">
              <span style="display:inline-flex; align-items:center; gap:4px;">
                <span style="width:12px; height:8px; border-radius:2px; background:#2563EB;"></span> Booked
              </span>
              <span style="display:inline-flex; align-items:center; gap:4px;">
                <span style="width:12px; height:8px; border-radius:2px; background:#059669;"></span> In-House (Checked In)
              </span>
            </div>
          </div>
        </div>

        <!-- Gantt Board Frame -->
        <div class="card" style="padding:0; overflow:hidden; border:1px solid #E5E7EB;">
          <div id="timeline-gantt-board" style="overflow-x:auto; max-height:calc(100vh - 230px); position:relative;">
            <div style="padding:48px; text-align:center; color:#6B7280;">Loading availability timeline...</div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  },

  bindEvents() {
    document.getElementById('tl-prev-btn').onclick = () => {
      const d = new Date(this.startDate);
      d.setDate(d.getDate() - 30);
      this.startDate = d.toISOString().slice(0, 10);
      this.loadData();
    };

    document.getElementById('tl-today-btn').onclick = () => {
      const d = window.currentBusinessDate ? new Date(window.currentBusinessDate) : new Date();
      this.startDate = d.toISOString().slice(0, 10);
      this.loadData();
    };

    document.getElementById('tl-next-btn').onclick = () => {
      const d = new Date(this.startDate);
      d.setDate(d.getDate() + 30);
      this.startDate = d.toISOString().slice(0, 10);
      this.loadData();
    };

    document.getElementById('tl-floor-select').onchange = (e) => {
      this.floorFilter = e.target.value;
      this.renderBoard();
    };
  },

  async loadData() {
    const board = document.getElementById('timeline-gantt-board');
    if (!board) return;

    try {
      const res = await API.get('/api/timeline', {
        start_date: this.startDate,
        days: this.daysCount,
      });
      this.timelineData = res;
      this.renderBoard();
    } catch (e) {
      board.innerHTML = `<div style="padding:32px; color:#DC2626; text-align:center;">Failed to load timeline: ${e.message}</div>`;
    }
  },

  renderBoard() {
    const board = document.getElementById('timeline-gantt-board');
    if (!board || !this.timelineData) return;

    const data = this.timelineData;
    let rooms = data.rooms;
    if (this.floorFilter !== 'all') {
      const floorNum = parseInt(this.floorFilter);
      rooms = rooms.filter(r => r.floor === floorNum);
    }

    const startD = new Date(this.startDate + 'T00:00:00');
    const dayCols = [];
    for (let i = 0; i < this.daysCount; i++) {
      const d = new Date(startD);
      d.setDate(d.getDate() + i);
      dayCols.push({
        dateStr: d.toISOString().slice(0, 10),
        dayName: new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(d),
        dayNum: d.getDate(),
        isWeekend: d.getDay() === 0 || d.getDay() === 6,
        index: i,
      });
    }

    const rangeLabel = document.getElementById('tl-range-label');
    if (rangeLabel && dayCols.length > 0) {
      rangeLabel.textContent = `${formatDate(dayCols[0].dateStr)} – ${formatDate(dayCols[dayCols.length - 1].dateStr)} (${this.daysCount} Days)`;
    }

    const colWidth = 52; // pixels per day
    const totalTrackWidth = colWidth * this.daysCount;
    const roomColWidth = 190; // room sticky column

    let html = `
      <div style="min-width:${roomColWidth + totalTrackWidth}px; position:relative;">
        <!-- Header Row -->
        <div style="display:flex; position:sticky; top:0; z-index:20; background:#F9FAFB; border-bottom:1px solid #E5E7EB;">
          <div style="position:sticky; left:0; z-index:25; width:${roomColWidth}px; min-width:${roomColWidth}px; background:#F9FAFB; border-right:1px solid #E5E7EB; padding:10px 14px; font-size:11px; font-weight:700; color:#374151; display:flex; align-items:center;">
            ROOM / CATEGORY
          </div>
          <div style="display:flex; width:${totalTrackWidth}px;">
    `;

    dayCols.forEach((col) => {
      html += `
        <div style="width:${colWidth}px; min-width:${colWidth}px; text-align:center; padding:6px 0; border-right:1px solid #F3F4F6; background:${col.isWeekend ? '#F3F4F6' : '#F9FAFB'};">
          <div style="font-size:10px; font-weight:600; color:${col.isWeekend ? '#DC2626' : '#6B7280'}; text-transform:uppercase;">${col.dayName}</div>
          <div style="font-size:13px; font-weight:700; color:#111827;" class="font-mono">${col.dayNum}</div>
        </div>
      `;
    });

    html += `</div></div><!-- End Header -->`;

    // Room Rows
    rooms.forEach((room) => {
      let statusColor = '#059669';
      if (room.status === 'occupied') statusColor = '#2563EB';
      else if (room.status === 'dirty') statusColor = '#D97706';
      else if (room.status === 'maintenance') statusColor = '#DC2626';

      html += `
        <div style="display:flex; height:46px; border-bottom:1px solid #E5E7EB; position:relative;">
          <!-- Room Sticky Header -->
          <div style="position:sticky; left:0; z-index:15; width:${roomColWidth}px; min-width:${roomColWidth}px; background:#FFFFFF; border-right:1px solid #E5E7EB; padding:6px 14px; display:flex; align-items:center; justify-content:space-between; box-shadow: 2px 0 4px -2px rgba(0,0,0,0.05);">
            <div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="font-mono font-bold" style="font-size:13px; color:#111827;">${room.number}</span>
                <span style="font-size:10px; color:#6B7280;">F${room.floor}</span>
              </div>
              <div style="font-size:11px; color:#4B5563; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:110px;">${room.room_type_name}</div>
            </div>
            <span style="width:8px; height:8px; border-radius:50%; background:${statusColor};" title="Status: ${room.status}"></span>
          </div>

          <!-- Day Columns Background Grid -->
          <div style="display:flex; width:${totalTrackWidth}px; position:relative; background:#FFFFFF;">
      `;

      dayCols.forEach((col) => {
        html += `
          <div style="width:${colWidth}px; min-width:${colWidth}px; height:100%; border-right:1px solid #F3F4F6; background:${col.isWeekend ? '#FAFAFA' : '#FFFFFF'};"></div>
        `;
      });

      // Render Booking Bars for this room
      const windowStart = new Date(this.startDate + 'T00:00:00').getTime();
      const msPerDay = 86400000;

      room.reservations.forEach((res) => {
        const cin = new Date(res.check_in_date + 'T00:00:00').getTime();
        const cout = new Date(res.check_out_date + 'T00:00:00').getTime();

        // Skip if outside window
        const windowEnd = windowStart + this.daysCount * msPerDay;
        if (cout <= windowStart || cin >= windowEnd) return;

        // Clamp visible stay within current 30-day window bounds
        const visibleCin = Math.max(cin, windowStart);
        const visibleCout = Math.min(cout, windowEnd);
        const offsetDays = (visibleCin - windowStart) / msPerDay;
        const visibleDays = Math.max(1, (visibleCout - visibleCin) / msPerDay);

        const leftPx = offsetDays * colWidth + 2;
        const widthPx = Math.max(28, visibleDays * colWidth - 4);

        const isCheckedIn = res.status === 'checked_in';
        const barBg = isCheckedIn ? '#059669' : '#2563EB';
        const barHover = isCheckedIn ? '#047857' : '#1D4ED8';

        html += `
          <div class="timeline-res-bar"
               data-res-id="${res.id}"
               data-conf="${res.confirmation_number}"
               data-guest="${res.guest_name}"
               data-cin="${res.check_in_date}"
               data-cout="${res.check_out_date}"
               data-room-num="${room.number}"
               data-room-id="${room.id}"
               data-status="${res.status}"
               data-rate="${res.nightly_rate}"
               data-balance="${res.balance}"
               style="position:absolute; left:${leftPx}px; width:${widthPx}px; top:6px; height:32px; border-radius:6px; background:${barBg}; color:#FFFFFF; padding:0 8px; display:flex; align-items:center; justify-content:space-between; font-size:11px; font-weight:600; cursor:pointer; z-index:10; box-shadow:0 1px 2px rgba(0,0,0,0.1); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; user-select:none; transition:transform 0.1s ease, filter 0.1s ease;"
               title="${res.guest_name} (#${res.confirmation_number}) · ${res.check_in_date} to ${res.check_out_date}">
            <div style="display:flex; align-items:center; gap:6px; overflow:hidden;">
              <span class="font-mono font-bold" style="font-size:10px; background:rgba(255,255,255,0.25); padding:1px 4px; border-radius:3px;">${res.guest_initials}</span>
              <span style="overflow:hidden; text-overflow:ellipsis;">${res.guest_name}</span>
            </div>
            <span class="font-mono" style="font-size:10px; opacity:0.85; margin-left:4px;">${res.nights}n</span>
          </div>
        `;
      });

      html += `</div></div>`;
    });

    html += `</div>`;
    board.innerHTML = html;

    // Attach click events to reservation bars
    board.querySelectorAll('.timeline-res-bar').forEach((bar) => {
      bar.addEventListener('click', (e) => {
        e.stopPropagation();
        this.openReservationDrawer({
          id: parseInt(bar.getAttribute('data-res-id')),
          conf: bar.getAttribute('data-conf'),
          guest: bar.getAttribute('data-guest'),
          cin: bar.getAttribute('data-cin'),
          cout: bar.getAttribute('data-cout'),
          roomNum: bar.getAttribute('data-room-num'),
          roomId: parseInt(bar.getAttribute('data-room-id')),
          status: bar.getAttribute('data-status'),
          rate: bar.getAttribute('data-rate'),
          balance: bar.getAttribute('data-balance'),
        });
      });
    });
  },

  openReservationDrawer(res) {
    const roomsOptions = (this.timelineData?.rooms || []).map(r => `
      <option value="${r.id}" ${r.id === res.roomId ? 'selected' : ''}>
        Room ${r.number} (${r.room_type_name})
      </option>
    `).join('');

    UI.modal({
      title: `Reservation #${res.conf}`,
      contentHtml: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; padding:12px; background:#F9FAFB; border:1px solid #E5E7EB; border-radius:8px;">
            <div>
              <div style="font-size:15px; font-weight:700; color:#111827;">${res.guest}</div>
              <div style="font-size:12px; color:#6B7280; margin-top:2px;">Assigned to Room <strong>${res.roomNum}</strong></div>
            </div>
            <span class="badge ${res.status === 'checked_in' ? 'badge-success' : 'badge-info'}" style="text-transform:uppercase;">
              ${res.status}
            </span>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Check-In</div>
              <div style="font-size:13px; font-weight:600; color:#111827;">${formatDate(res.cin)}</div>
            </div>
            <div>
              <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Check-Out</div>
              <div style="font-size:13px; font-weight:600; color:#111827;">${formatDate(res.cout)}</div>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Nightly Rate</div>
              <div class="font-mono" style="font-size:13px; font-weight:600; color:#111827;">${formatCurrency(res.rate)}</div>
            </div>
            <div>
              <div style="font-size:11px; color:#6B7280; text-transform:uppercase;">Folio Balance Due</div>
              <div class="font-mono font-bold" style="font-size:13px; color:${parseFloat(res.balance) > 0 ? '#DC2626' : '#059669'};">
                ${formatCurrency(res.balance)}
              </div>
            </div>
          </div>

          <!-- Move / Change Allocation Section -->
          <div style="border-top:1px solid #E5E7EB; padding-top:16px;">
            <div style="font-size:13px; font-weight:700; color:#111827; margin-bottom:10px;">
              Move Stay or Change Room Assignment
            </div>

            <div class="form-group" style="margin-bottom:12px;">
              <label class="form-label">Destination Room</label>
              <select id="move-dest-room" class="form-select font-mono">${roomsOptions}</select>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
              <div class="form-group">
                <label class="form-label">Check-In Date</label>
                <input type="date" id="move-cin" class="form-input" value="${res.cin}">
              </div>
              <div class="form-group">
                <label class="form-label">Check-Out Date</label>
                <input type="date" id="move-cout" class="form-input" value="${res.cout}">
              </div>
            </div>
          </div>
        </div>
      `,
      footerHtml: `
        <div style="display:flex; justify-content:space-between; width:100%; align-items:center;">
          <button class="btn btn-secondary btn-md" onclick="UI.closeModal(); if (window.openReservationDrawer) window.openReservationDrawer(${res.id});">
            Open Folio Details &rarr;
          </button>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
            <button class="btn btn-primary btn-md" id="move-confirm-btn">Execute Move</button>
          </div>
        </div>
      `,
    });

    document.getElementById('move-confirm-btn').onclick = async () => {
      const targetRoomId = parseInt(document.getElementById('move-dest-room').value);
      const targetCin = document.getElementById('move-cin').value;
      const targetCout = document.getElementById('move-cout').value;

      if (!targetCin || !targetCout || targetCout <= targetCin) {
        UI.toast('Check-out date must be strictly after check-in date.', 'error');
        return;
      }

      try {
        await API.patch(`/api/reservations/${res.id}/move`, {
          room_id: targetRoomId,
          check_in_date: targetCin,
          check_out_date: targetCout,
        });

        UI.toast(`Successfully moved booking #${res.conf}`, 'success');
        UI.closeModal();
        this.loadData();
      } catch (err) {
        // 409 Conflict handling with clear feedback
        UI.toast(err.message, 'error');
      }
    };
  },
};
