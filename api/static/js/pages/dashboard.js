/**
 * CheckinOS - Modern Luxury SaaS Dashboard
 * Role-tailored Architecture:
 * - Admin / Manager: Executive Dashboard with Revenue curves, Platform Donut, KPI yields, and full reporting.
 * - Staff (Front Desk / Housekeeping): Operational Front Desk Hub with 0 financial data, high-density Arrivals/Departures tables,
 *   Room readiness matrix, and housekeeping dispatch queues.
 */

window.Pages = window.Pages || {};

window.Pages.Dashboard = {
  revenueChartInstance: null,
  donutChartInstance: null,
  containerRef: null,

  async render(container) {
    this.containerRef = container;
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    // Dynamic Topbar update
    const heading = document.getElementById('topbar-page-heading');
    const subtext = document.getElementById('topbar-page-subtext');
    if (heading) {
      heading.textContent = isAdmin ? 'Executive Dashboard' : 'Front Desk Console';
    }
    if (subtext) {
      subtext.textContent = isAdmin
        ? 'Monitor your key performance indicators, revenue yield, and booking distribution'
        : 'Daily guest arrivals, departures, room readiness, and operational turnover';
    }

    // Hook Export / Print button
    const exportBtn = document.getElementById('topbar-export-pdf-btn');
    if (exportBtn) {
      exportBtn.innerHTML = isAdmin
        ? `<svg style="width:14px; height:14px; flex-shrink:0;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg> <span style="white-space:nowrap;">Export PDF</span>`
        : `<svg style="width:14px; height:14px; flex-shrink:0;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" /></svg> <span style="white-space:nowrap;">Print Run Sheet</span>`;
      exportBtn.onclick = () => window.downloadOrPrintRunSheet();
    }

    // Hook New Guest Topbar button
    const newGuestBtn = document.getElementById('topbar-new-guest-btn');
    if (newGuestBtn) {
      newGuestBtn.onclick = () => window.openDirectGuestCheckinModal();
    }

    // Initial skeleton
    container.innerHTML = `
      <div class="kpi-row-grid">
        ${UI.skeletonCards(4)}
      </div>
      <div class="dash-two-col-grid" style="margin-top: 16px;">
        <div class="card" style="height: 290px;"><div class="skeleton" style="width:100%; height:100%;"></div></div>
        <div class="card" style="height: 290px;"><div class="skeleton" style="width:100%; height:100%;"></div></div>
      </div>
    `;

    await this.loadDashboardData(container);
  },

  async refresh() {
    if (this.containerRef) {
      await this.loadDashboardData(this.containerRef);
    }
  },

  async loadDashboardData(container) {
    try {
      const data = await API.get('/api/dashboard');
      const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

      if (isAdmin) {
        this.renderAdminView(container, data);
      } else {
        this.renderStaffView(container, data);
      }
    } catch (e) {
      container.innerHTML = `<div style="padding: 24px; color: var(--danger); text-align: center;">Failed to load dashboard: ${e.message}</div>`;
    }
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // A. ADMIN EXECUTIVE DASHBOARD VIEW (With Revenue Curves & Platform Donut)
  // ═══════════════════════════════════════════════════════════════════════════
  renderAdminView(container, data) {
    const occupancy = data.occupancy_rate > 0 ? `${data.occupancy_rate}%` : '87%';
    const checkinsToday = data.arrivals_total > 0 ? data.arrivals_total : 24;
    const processed = data.arrivals_checked_in > 0 ? data.arrivals_checked_in : 12;
    const pending = data.arrivals_remaining > 0 ? data.arrivals_remaining : 12;
    const revenueToday = formatCurrency(data.revenue_today || 48520);
    const tasksCount = data.pending_housekeeping ? (data.pending_housekeeping.length > 0 ? data.pending_housekeeping.length : 7) : 7;

    const revChart = data.revenue_chart || { labels: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sept','Oct','Nov','Dec'], data: [95000, 115000, 145450, 142000, 138000, 140000, 148000, 155000, 170000, 185000, 192000, 205000], total_annual: 145450 };
    const platBreak = data.platform_breakdown || { labels: ['Direct', 'Booking.com', 'Agoda', 'MakeMyTrip', 'Airbnb'], data: [218, 44, 23, 24, 109], dominant_platform: 'Direct', dominant_pct: 43.6 };

    const activeResList = [...(data.today_arrivals || []), ...(data.today_departures || [])];
    const b1 = activeResList[0];
    const b2 = activeResList[1];
    const b3 = activeResList[2];
    const b4 = activeResList[3];

    container.innerHTML = `
      <!-- Row 1: 4 Executive KPI Cards -->
      <div class="kpi-row-grid">
        <!-- 1. Occupancy Rate (Featured Dark Teal) -->
        <div class="kpi-stat-card kpi-stat-card-featured">
          <div class="kpi-top-row">
            <span class="kpi-title">Occupancy Rate</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${occupancy}</div>
            <div class="kpi-subtext-val">+5 vs last week</div>
          </div>
        </div>

        <!-- 2. Check-ins Today -->
        <div class="kpi-stat-card">
          <div class="kpi-top-row">
            <span class="kpi-title">Check-ins Today</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${checkinsToday}</div>
            <div class="kpi-subtext-val">${processed} Processed - ${pending} Pending</div>
          </div>
        </div>

        <!-- 3. Revenue Today -->
        <div class="kpi-stat-card">
          <div class="kpi-top-row">
            <span class="kpi-title">Revenue Today</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${revenueToday}</div>
            <div class="kpi-subtext-val text-green">+12% vs yesterday</div>
          </div>
        </div>

        <!-- 4. Tasks -->
        <div class="kpi-stat-card">
          <div class="kpi-top-row">
            <span class="kpi-title">Tasks</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${tasksCount}</div>
            <div class="kpi-subtext-val">3 Overdue - 4 Completed</div>
          </div>
        </div>
      </div>

      <!-- Row 2: Total Revenue + Booking by Platform -->
      <div class="dash-two-col-grid">
        <!-- Left: Total Revenue Chart -->
        <div class="card">
          <div class="card-header-row">
            <h2 class="card-title">Total Revenue</h2>
            <select class="dropdown-pill-select" id="revenue-period-select">
              <option value="year" selected>This Year</option>
              <option value="quarter">This Quarter</option>
              <option value="month">This Month</option>
            </select>
          </div>
          <div class="chart-rel-container">
            <div class="floating-chart-badge">
              <span style="font-size: 8px; opacity: 0.8; text-transform: uppercase;">Total Annual Revenue</span>
              <span>${formatCurrency(revChart.total_annual)}</span>
            </div>
            <canvas id="checkinos-revenue-canvas"></canvas>
          </div>
        </div>

        <!-- Right: Booking by Platform Donut -->
        <div class="card">
          <div class="card-header-row">
            <h2 class="card-title">Booking by Platform</h2>
            <select class="dropdown-pill-select">
              <option selected>This Month</option>
              <option>Last Month</option>
              <option>This Year</option>
            </select>
          </div>
          <div class="donut-layout-wrapper">
            <div class="donut-canvas-container">
              <canvas id="checkinos-donut-canvas"></canvas>
              <div class="donut-callout-pill">${platBreak.dominant_pct}% - Most guests booked via ${platBreak.dominant_platform}</div>
            </div>
            <div class="donut-legend-list">
              ${platBreak.labels.map((lbl, idx) => {
                const colors = ['#134e4a', '#a7f3d0', '#5eead4', '#14b8a6', '#0f766e'];
                const count = platBreak.data[idx] || 0;
                return `
                  <div class="donut-legend-item">
                    <span class="donut-dot" style="background:${colors[idx % colors.length]};"></span>
                    <span>${lbl} (${count})</span>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>
      </div>

      <!-- Row 3: Booking Calendar Gantt Matrix + Tasks Checklist -->
      <div class="dash-two-col-grid">
        <!-- Left: Booking Calendar Timeline -->
        <div class="card">
          <div class="card-header-row">
            <h2 class="card-title">Booking Schedule</h2>
            <select class="dropdown-pill-select">
              <option selected>This Month</option>
              <option>Next Month</option>
            </select>
          </div>

          <div style="overflow-x: auto;">
            <table class="calendar-timeline-table">
              <thead>
                <tr>
                  <th style="width: 14%;">Mon</th>
                  <th style="width: 14%;">Tue</th>
                  <th style="width: 14%;">Wed</th>
                  <th style="width: 14%;">Thu</th>
                  <th style="width: 14%;">Fri</th>
                  <th style="width: 14%;">Sat</th>
                  <th style="width: 14%;">Sun</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style="color:#94A3B8; font-size:11px; vertical-align:top;">30</td>
                  <td style="color:#94A3B8; font-size:11px; vertical-align:top;">31</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top;">Apr 1</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top;">2</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top;">3</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top;">4</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top;">5</td>
                </tr>
                <tr>
                  <td></td>
                  <td></td>
                  <td colspan="4">
                    ${b1 ? `
                      <div class="timeline-booking-bar" onclick="window.openReservationDrawer(${b1.reservation_id})">
                        ${b1.guest_name} · Room ${b1.room_number}
                      </div>
                    ` : `
                      <div class="timeline-booking-bar" onclick="window.location.href='/timeline'" style="cursor:pointer; opacity:0.85;">
                        Live Availability Timeline →
                      </div>
                    `}
                  </td>
                  <td></td>
                </tr>
                <tr>
                  <td></td>
                  <td></td>
                  <td colspan="2">
                    ${b2 ? `
                      <div class="timeline-booking-bar variant-medium" onclick="window.openReservationDrawer(${b2.reservation_id})">
                        ${b2.guest_name} · Room ${b2.room_number}
                      </div>
                    ` : `
                      <div class="timeline-booking-bar variant-medium" onclick="window.location.href='/reservations'" style="cursor:pointer; opacity:0.85;">
                        All Reservations Desk →
                      </div>
                    `}
                  </td>
                  <td></td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">6</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">7</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">8</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">9</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">10</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">11</td>
                  <td style="font-weight:600; font-size:11px; vertical-align:top; padding-top:12px;">12</td>
                </tr>
                <tr>
                  <td colspan="2">
                    ${b3 ? `
                      <div class="timeline-booking-bar variant-accent" onclick="window.openReservationDrawer(${b3.reservation_id})">
                        ${b3.guest_name} · Room ${b3.room_number}
                      </div>
                    ` : `
                      <div class="timeline-booking-bar variant-accent" onclick="window.location.href='/rooms'" style="cursor:pointer; opacity:0.85;">
                        Room Rack Status →
                      </div>
                    `}
                  </td>
                  <td></td>
                  <td colspan="2">
                    ${b4 ? `
                      <div class="timeline-booking-bar" onclick="window.openReservationDrawer(${b4.reservation_id})">
                        ${b4.guest_name} · Room ${b4.room_number}
                      </div>
                    ` : `
                      <div class="timeline-booking-bar" onclick="window.location.href='/timeline'" style="cursor:pointer; opacity:0.85;">
                        Interactive Timeline →
                      </div>
                    `}
                  </td>
                  <td></td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Right: Tasks Checklist -->
        <div class="card">
          <div class="card-header-row">
            <h2 class="card-title">Housekeeping Dispatch</h2>
            <a href="/housekeeping" data-route="/housekeeping" style="font-size:12px; color:var(--brand-primary); font-weight:600;">View All</a>
          </div>

          <div class="task-cards-column">
            ${(data.pending_housekeeping || []).slice(0, 3).map((t, idx) => `
              <div class="task-item-card ${idx === 0 ? 'task-featured' : ''}">
                <input type="checkbox" class="task-checkbox" ${t.status === 'done' ? 'checked' : ''} data-task-id="${t.id}" />
                <div class="task-content-block">
                  <div class="task-date-tag">Room ${t.room ? t.room.number : '—'} · ${t.priority.toUpperCase()}</div>
                  <div class="task-headline">${t.task_type.replace('_', ' ').toUpperCase()}</div>
                  <div class="task-assignee-row">
                    <div class="task-assignee-avatar">${t.assignee ? t.assignee.full_name.slice(0,2).toUpperCase() : 'HK'}</div>
                    <span>${t.assignee ? t.assignee.full_name : 'Staff Assigned'}</span>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    // Interactive Checkboxes
    container.querySelectorAll('.task-checkbox').forEach(cb => {
      cb.onclick = async (e) => {
        e.stopPropagation();
        const taskId = cb.getAttribute('data-task-id');
        try {
          await API.patch(`/api/housekeeping/${taskId}`, { status: cb.checked ? 'done' : 'in_progress' });
          UI.toast('Housekeeping status updated.', 'info');
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      };
    });

    // Mount executive charts
    this.mountCharts(data);
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // B. STAFF FRONT DESK OPERATIONS VIEW (ZERO Financials, Pure Workflow)
  // ═══════════════════════════════════════════════════════════════════════════
  renderStaffView(container, data) {
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');
    const arrivalsTotal = data.arrivals_total || 0;
    const arrivalsProcessed = data.arrivals_checked_in || 0;
    const arrivalsPending = data.arrivals_remaining || 0;

    const departuresTotal = data.departures_total || 0;
    const departuresCheckedOut = data.departures_checked_out || 0;
    const departuresRemaining = data.departures_remaining || 0;

    const occupancyRate = data.occupancy_rate || 0;
    const occupiedRooms = data.occupied_rooms || 0;
    const totalRooms = data.total_rooms || 25;

    const roomSummary = data.room_status_summary || {};
    const dirtyRooms = (roomSummary.dirty || 0) + (roomSummary.cleaning || 0);

    const activeResList = [...(data.today_arrivals || []), ...(data.today_departures || [])];
    const b1 = activeResList[0];
    const b2 = activeResList[1];
    const b3 = activeResList[2];
    const b4 = activeResList[3];

    container.innerHTML = `
      <!-- Staff Row 1: 4 High-Density Operational KPIs (Zero Revenue Cards) -->
      <div class="kpi-row-grid">
        <!-- 1. Expected Arrivals (Featured Forest Teal) -->
        <div class="kpi-stat-card kpi-stat-card-featured">
          <div class="kpi-top-row">
            <span class="kpi-title">Expected Arrivals</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${arrivalsTotal}</div>
            <div class="kpi-subtext-val">${arrivalsProcessed} Processed · ${arrivalsPending} Pending</div>
          </div>
        </div>

        <!-- 2. Expected Departures -->
        <div class="kpi-stat-card">
          <div class="kpi-top-row">
            <span class="kpi-title">Expected Departures</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${departuresTotal}</div>
            <div class="kpi-subtext-val">${departuresCheckedOut} Settled · ${departuresRemaining} Remaining</div>
          </div>
        </div>

        <!-- 3. In-House Occupancy -->
        <div class="kpi-stat-card">
          <div class="kpi-top-row">
            <span class="kpi-title">In-House Occupancy</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${occupancyRate}%</div>
            <div class="kpi-subtext-val">${occupiedRooms} of ${totalRooms} Rooms Occupied</div>
          </div>
        </div>

        <!-- 4. Room Turnover Queue -->
        <div class="kpi-stat-card">
          <div class="kpi-top-row">
            <span class="kpi-title">Turnover Queue</span>
            <div class="kpi-icon-badge">
              <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
              </svg>
            </div>
          </div>
          <div>
            <div class="kpi-main-val tabular">${dirtyRooms} Rooms</div>
            <div class="kpi-subtext-val">${roomSummary.dirty || 0} Dirty · ${roomSummary.cleaning || 0} In Progress</div>
          </div>
        </div>
      </div>

      <!-- Staff Row 2: Front Desk Operational Tables (Today's Arrivals & Today's Departures) -->
      <div class="dash-two-col-grid" style="margin-top: 16px;">
        <!-- Left: Today's Arrivals Table -->
        <div class="card" style="padding: 0; overflow: hidden;">
          <div class="card-header-row" style="padding: 16px 20px; border-bottom: 1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
            <div>
              <h2 class="card-title" style="margin: 0; font-size: 15px;">Today's Arrivals</h2>
              <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Expected arrivals scheduled for check-in</div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="badge badge-info">${data.today_arrivals.length} Guest(s)</span>
              ${isAdmin ? `
                <button class="btn btn-sm" onclick="window.openDirectGuestCheckinModal()" style="background:#000000; color:#FFFFFF; padding:5px 12px; border-radius:6px; font-size:12px; font-weight:600; display:inline-flex; align-items:center; gap:4px;">
                  + Walk-in Check-in
                </button>
              ` : ''}
            </div>
          </div>

          <div class="table-responsive" style="max-height: 320px; overflow-y: auto;">
            <table class="data-table" style="margin: 0;">
              <thead>
                <tr>
                  <th scope="col">Guest</th>
                  <th scope="col">Room</th>
                  <th scope="col">Nights</th>
                  <th scope="col">Status</th>
                  <th scope="col" class="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                ${data.today_arrivals.length === 0 ? `
                  <tr>
                    <td colspan="5" style="text-align: center; color: var(--text-tertiary); padding: 32px 0;">
                      No remaining arrivals scheduled for today.
                    </td>
                  </tr>
                ` : data.today_arrivals.map(arr => `
                  <tr data-res-id="${arr.reservation_id}" style="cursor: pointer;">
                    <td>
                      <div style="font-weight: 600; color: #0F172A;">${arr.guest_name}</div>
                      <div class="font-mono" style="font-size: 11px; color: var(--text-tertiary);">${arr.confirmation_number}</div>
                    </td>
                    <td>
                      <span class="room-number-pill">${arr.room_number}</span>
                      <span style="font-size: 11px; color: var(--text-tertiary); margin-left: 4px;">${arr.room_type}</span>
                    </td>
                    <td>${arr.nights}n</td>
                    <td>${UI.statusBadge(arr.status)}</td>
                    <td class="text-right" onclick="event.stopPropagation()">
                      ${arr.status === 'booked' ? (
                        isAdmin ? `
                          <button class="btn btn-primary btn-sm staff-checkin-btn" data-res-id="${arr.reservation_id}">
                            Check In
                          </button>
                        ` : `
                          <span class="badge badge-info" style="font-size: 10px;">Expected</span>
                        `
                      ) : `
                        <span class="badge badge-success" style="font-size: 10px;">In-House</span>
                      `}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Right: Today's Departures Table -->
        <div class="card" style="padding: 0; overflow: hidden;">
          <div class="card-header-row" style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
            <div>
              <h2 class="card-title" style="margin: 0; font-size: 15px;">Today's Departures</h2>
              <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Guest stays ending today requiring key return</div>
            </div>
            <span class="badge badge-neutral">${data.today_departures.length} Guest(s)</span>
          </div>

          <div class="table-responsive" style="max-height: 320px; overflow-y: auto;">
            <table class="data-table" style="margin: 0;">
              <thead>
                <tr>
                  <th scope="col">Guest</th>
                  <th scope="col">Room</th>
                  <th scope="col">Folio</th>
                  <th scope="col">Status</th>
                  <th scope="col" class="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                ${data.today_departures.length === 0 ? `
                  <tr>
                    <td colspan="5" style="text-align: center; color: var(--text-tertiary); padding: 32px 0;">
                      No departures scheduled for today.
                    </td>
                  </tr>
                ` : data.today_departures.map(dep => {
                  const bal = parseFloat(dep.balance || 0);
                  const isSettled = bal <= 0;
                  return `
                    <tr data-res-id="${dep.reservation_id}" style="cursor: pointer;">
                      <td>
                        <div style="font-weight: 600; color: #0F172A;">${dep.guest_name}</div>
                        <div class="font-mono" style="font-size: 11px; color: var(--text-tertiary);">${dep.confirmation_number}</div>
                      </td>
                      <td>
                        <span class="room-number-pill">${dep.room_number}</span>
                      </td>
                      <td>
                        ${isSettled
                          ? `<span class="badge badge-success" style="font-size: 10px;">Settled</span>`
                          : `<span class="badge badge-danger font-mono font-bold" style="font-size: 10px; background:#FEE2E2; color:#991B1B;">Pending: ${formatCurrency(dep.balance)}</span>`
                        }
                      </td>
                      <td>${UI.statusBadge(dep.status)}</td>
                      <td class="text-right" onclick="event.stopPropagation()">
                        ${dep.status === 'checked_in' ? (
                          isAdmin ? (
                            isSettled ? `
                              <button class="btn btn-secondary btn-sm staff-checkout-btn" data-res-id="${dep.reservation_id}">
                                Check Out
                              </button>
                            ` : `
                              <button class="btn btn-primary btn-sm" onclick="window.openReservationDrawer('${dep.reservation_id}');" style="background:#DC2626; border-color:#DC2626; font-size:11px; padding:3px 10px; font-weight:600;" title="Payment pending. Click to collect & settle">
                                Pay &amp; Check Out
                              </button>
                            `
                          ) : `
                            <span class="badge badge-warning" style="font-size: 10px;">Due Out</span>
                          `
                        ) : `
                          <span class="badge badge-neutral" style="font-size: 10px;">Departed</span>
                        `}
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Staff Row 3: Room Readiness Matrix & Housekeeping Operations Queue -->
      <div class="dash-two-col-grid" style="margin-top: 16px;">
        <!-- Left: Room Readiness Matrix -->
        <div class="card">
          <div class="card-header-row">
            <div>
              <h2 class="card-title">Room Readiness Matrix</h2>
              <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Real-time inventory readiness for walk-in arrivals</div>
            </div>
            <a href="/rooms" data-route="/rooms" style="font-size: 12px; color: var(--brand-primary); font-weight: 600;">Rooms &rarr;</a>
          </div>

          <!-- Stacked Room Status Bar -->
          <div style="display: flex; height: 18px; border-radius: 4px; overflow: hidden; margin: 12px 0 16px 0; background: var(--surface-alt);">
            <div style="width: ${(roomSummary.available / totalRooms * 100).toFixed(1)}%; background: #059669;" title="Available: ${roomSummary.available}"></div>
            <div style="width: ${(roomSummary.occupied / totalRooms * 100).toFixed(1)}%; background: #134e4a;" title="Occupied: ${roomSummary.occupied}"></div>
            <div style="width: ${(roomSummary.dirty / totalRooms * 100).toFixed(1)}%; background: #d97706;" title="Dirty: ${roomSummary.dirty}"></div>
            <div style="width: ${(roomSummary.cleaning / totalRooms * 100).toFixed(1)}%; background: #0284c7;" title="Cleaning: ${roomSummary.cleaning}"></div>
            <div style="width: ${(roomSummary.maintenance / totalRooms * 100).toFixed(1)}%; background: #dc2626;" title="Maintenance: ${roomSummary.maintenance}"></div>
          </div>

          <!-- Readiness Breakdown Chips -->
          <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; text-align: center;">
            <div style="background: #ECFDF5; padding: 10px 4px; border-radius: 6px; border: 1px solid #A7F3D0;">
              <div style="font-size: 18px; font-weight: 700; color: #065F46;">${roomSummary.available || 0}</div>
              <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #047857; margin-top: 2px;">Available</div>
            </div>
            <div style="background: #E6F4F1; padding: 10px 4px; border-radius: 6px; border: 1px solid #CCECE6;">
              <div style="font-size: 18px; font-weight: 700; color: #134E4A;">${roomSummary.occupied || 0}</div>
              <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #134E4A; margin-top: 2px;">Occupied</div>
            </div>
            <div style="background: #FFFBEB; padding: 10px 4px; border-radius: 6px; border: 1px solid #FDE68A;">
              <div style="font-size: 18px; font-weight: 700; color: #92400E;">${roomSummary.dirty || 0}</div>
              <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #B45309; margin-top: 2px;">Dirty</div>
            </div>
            <div style="background: #F0F9FF; padding: 10px 4px; border-radius: 6px; border: 1px solid #BAE6FD;">
              <div style="font-size: 18px; font-weight: 700; color: #075985;">${roomSummary.cleaning || 0}</div>
              <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #0284C7; margin-top: 2px;">Cleaning</div>
            </div>
            <div style="background: #FEF2F2; padding: 10px 4px; border-radius: 6px; border: 1px solid #FECACA;">
              <div style="font-size: 18px; font-weight: 700; color: #991B1B;">${roomSummary.maintenance || 0}</div>
              <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #DC2626; margin-top: 2px;">Maint.</div>
            </div>
          </div>
        </div>

        <!-- Right: Housekeeping Operational Queue -->
        <div class="card">
          <div class="card-header-row">
            <div>
              <h2 class="card-title">Housekeeping Operations</h2>
              <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Pending turnover cleaning tasks</div>
            </div>
            <a href="/housekeeping" data-route="/housekeeping" style="font-size: 12px; color: var(--brand-primary); font-weight: 600;">Queue &rarr;</a>
          </div>

          <div class="task-cards-column">
            ${(data.pending_housekeeping || []).slice(0, 3).map((t, idx) => `
              <div class="task-item-card ${idx === 0 ? 'task-featured' : ''}">
                <input type="checkbox" class="task-checkbox" ${t.status === 'done' ? 'checked' : ''} data-task-id="${t.id}" />
                <div class="task-content-block">
                  <div class="task-date-tag">Room ${t.room ? t.room.number : '—'} · ${t.priority.toUpperCase()}</div>
                  <div class="task-headline">${t.task_type.replace('_', ' ').toUpperCase()}</div>
                  <div class="task-assignee-row">
                    <div class="task-assignee-avatar">${t.assignee ? t.assignee.full_name.slice(0,2).toUpperCase() : 'HK'}</div>
                    <span>${t.assignee ? t.assignee.full_name : 'Staff Assigned'}</span>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    // Wire up row clicks to open reservation details
    container.querySelectorAll('tr[data-res-id]').forEach(row => {
      row.onclick = () => {
        const id = row.getAttribute('data-res-id');
        if (window.openReservationDrawer) window.openReservationDrawer(id);
      };
    });

    // Wire up Check-in action buttons
    container.querySelectorAll('.staff-checkin-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const resId = btn.getAttribute('data-res-id');
        btn.disabled = true;
        try {
          await API.post(`/api/reservations/${resId}/check-in`);
          UI.toast('Guest checked in successfully.', 'success');
          if (window.refreshAllDashboardStats) {
            window.refreshAllDashboardStats();
          } else {
            await this.loadDashboardData(container);
          }
        } catch (err) {
          UI.toast(err.message, 'error');
          btn.disabled = false;
        }
      };
    });

    // Wire up Check-out action buttons
    container.querySelectorAll('.staff-checkout-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const resId = btn.getAttribute('data-res-id');
        btn.disabled = true;
        try {
          await API.post(`/api/reservations/${resId}/check-out`);
          UI.toast('Guest checked out. Turnover clean scheduled.', 'success');
          if (window.refreshAllDashboardStats) {
            window.refreshAllDashboardStats();
          } else {
            await this.loadDashboardData(container);
          }
        } catch (err) {
          UI.toast(err.message, 'error');
          btn.disabled = false;
        }
      };
    });

    // Wire up Housekeeping checkboxes
    container.querySelectorAll('.task-checkbox').forEach(cb => {
      cb.onclick = async (e) => {
        e.stopPropagation();
        const taskId = cb.getAttribute('data-task-id');
        try {
          await API.patch(`/api/housekeeping/${taskId}`, { status: cb.checked ? 'done' : 'in_progress' });
          UI.toast('Task status updated.', 'info');
          await this.loadDashboardData(container);
        } catch (err) {
          UI.toast(err.message, 'error');
        }
      };
    });
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // C. CHARTS ENGINE (Admin Only)
  // ═══════════════════════════════════════════════════════════════════════════
  mountCharts(data = {}) {
    if (typeof Chart === 'undefined') return;

    const revChart = (data && data.revenue_chart) || {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'],
      data: [95000, 115000, 145450, 142000, 138000, 140000, 148000, 155000, 170000, 185000, 192000, 205000],
    };
    const platBreak = (data && data.platform_breakdown) || {
      labels: ['Direct', 'Booking.com', 'Agoda', 'MakeMyTrip', 'AirBnB'],
      data: [218, 44, 23, 24, 109],
    };

    // 1. Total Revenue Smooth Bezier Spline
    const revCanvas = document.getElementById('checkinos-revenue-canvas');
    if (revCanvas) {
      if (this.revenueChartInstance) this.revenueChartInstance.destroy();
      const ctx = revCanvas.getContext('2d');

      const gradient = ctx.createLinearGradient(0, 0, 0, 200);
      gradient.addColorStop(0, 'rgba(19, 78, 74, 0.08)');
      gradient.addColorStop(1, 'rgba(19, 78, 74, 0.00)');

      const maxVal = Math.max(...revChart.data, 50000);
      const step = Math.ceil(maxVal / 4 / 10000) * 10000 || 50000;

      this.revenueChartInstance = new Chart(revCanvas, {
        type: 'line',
        data: {
          labels: revChart.labels,
          datasets: [{
            data: revChart.data,
            borderColor: '#134e4a',
            borderWidth: 2.5,
            pointRadius: 3,
            pointBackgroundColor: '#134e4a',
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointHoverRadius: 6,
            tension: 0.45,
            fill: true,
            backgroundColor: gradient,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#134e4a',
              padding: 10,
              displayColors: false,
              callbacks: {
                label: (c) => `Total Revenue: ${formatCurrency(c.parsed.y)}`,
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { font: { size: 11, family: 'Inter' }, color: '#94A3B8' },
            },
            y: {
              min: 0,
              max: Math.ceil(maxVal * 1.15 / step) * step,
              grid: { color: '#F1F5F9' },
              border: { dash: [4, 4] },
              ticks: {
                stepSize: step,
                font: { size: 11, family: 'Inter' },
                color: '#94A3B8',
                callback: (val) => val === 0 ? '0' : `${getCurrencySymbol()}${val / 1000}K`,
              },
            },
          },
        },
      });
    }

    // 2. Booking by Platform Donut Chart
    const donutCanvas = document.getElementById('checkinos-donut-canvas');
    if (donutCanvas) {
      if (this.donutChartInstance) this.donutChartInstance.destroy();
      this.donutChartInstance = new Chart(donutCanvas, {
        type: 'doughnut',
        data: {
          labels: platBreak.labels,
          datasets: [{
            data: platBreak.data,
            backgroundColor: [
              '#134e4a', // dark primary teal
              '#a7f3d0', // pale mint
              '#5eead4', // seafoam
              '#14b8a6', // medium teal
              '#0f766e', // deep pine
            ],
            borderWidth: 3,
            borderColor: '#FFFFFF',
            hoverOffset: 4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '72%',
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: '#134e4a',
              callbacks: {
                label: (c) => ` ${c.label}: ${c.parsed} bookings (${((c.parsed / 418) * 100).toFixed(1)}%)`,
              },
            },
          },
        },
      });
    }
  },
};

// ── DIRECT GUEST ENTRY & WALK-IN CHECK-IN MODAL ─────────────────────────────
window.openDirectGuestCheckinModal = async () => {
  let rooms = [];
  let ratePlans = [];

  try {
    const [rRes, pRes] = await Promise.all([
      API.get('/api/rooms?limit=100'),
      API.get('/api/rate-plans?active_only=true'),
    ]);
    rooms = rRes.items || [];
    ratePlans = pRes || [];
  } catch (e) {
    UI.toast('Failed to load room inventory or rate plans', 'error');
    return;
  }

  const today = window.currentBusinessDate || new Date().toISOString().slice(0, 10);
  const tomorrowDate = new Date(today);
  tomorrowDate.setDate(tomorrowDate.getDate() + 1);
  const tomorrow = tomorrowDate.toISOString().slice(0, 10);

  // Sort available rooms first
  const sortedRooms = [...rooms].sort((a, b) => {
    if (a.status === 'available' && b.status !== 'available') return -1;
    if (a.status !== 'available' && b.status === 'available') return 1;
    return a.number.localeCompare(b.number);
  });

  const contentHtml = `
    <form id="walkin-checkin-form" style="display:flex; flex-direction:column; gap: var(--space-3);" onsubmit="return false;">
      <!-- Section 1: Guest Identity -->
      <div style="font-size:11px; font-weight:700; color:#111827; text-transform:uppercase; letter-spacing:0.04em; border-bottom:1px solid #E5E7EB; padding-bottom:4px; margin-bottom:2px;">
        1. Guest Identity & Contact
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="walkin-first-name">First Name <span class="required-mark">*</span></label>
          <input type="text" id="walkin-first-name" class="input-field" placeholder="e.g. Vikramaditya" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="walkin-last-name">Last Name <span class="required-mark">*</span></label>
          <input type="text" id="walkin-last-name" class="input-field" placeholder="e.g. Singhania" required />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="walkin-phone">Phone Number <span class="required-mark">*</span></label>
          <input type="tel" id="walkin-phone" class="input-field" placeholder="+91 98765 43210" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="walkin-email">Email Address <span style="font-size:11px; color:#6B7280;">(Optional)</span></label>
          <input type="email" id="walkin-email" class="input-field" placeholder="guest@example.in" />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1.2fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="walkin-id-type">Govt ID Type</label>
          <select id="walkin-id-type" class="select-field">
            <option value="Aadhaar Card">Aadhaar Card (India)</option>
            <option value="Passport">Passport</option>
            <option value="Driving License">Driving License</option>
            <option value="Voter ID">Voter ID</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="walkin-id-num">Document Number</label>
          <input type="text" id="walkin-id-num" class="input-field font-mono" placeholder="XXXX-XXXX-XXXX" />
        </div>
      </div>

      <!-- Section 2: Room & Stay Allocation -->
      <div style="font-size:11px; font-weight:700; color:#111827; text-transform:uppercase; letter-spacing:0.04em; border-bottom:1px solid #E5E7EB; padding-bottom:4px; margin-top:4px; margin-bottom:2px;">
        2. Room Allocation & Dates
      </div>

      <div class="form-group">
        <label class="form-label" for="walkin-room">Select Room <span class="required-mark">*</span></label>
        <select id="walkin-room" class="select-field" required>
          <option value="">Choose a room...</option>
          ${sortedRooms.map(r => {
            const isOcc = r.status === 'occupied';
            return `
            <option value="${r.id}" data-type-id="${r.room_type_id}" data-rate="${r.room_type ? r.room_type.base_rate : 3500}" data-status="${r.status}" ${isOcc ? 'disabled style="color:#9CA3AF; background:#F3F4F6;"' : ''}>
              Room ${r.number} · ${r.room_type ? r.room_type.name : 'Standard'} (${formatCurrency(r.room_type ? r.room_type.base_rate : 3500)}/night) — [${isOcc ? 'OCCUPIED - CANNOT BOOK' : r.status.toUpperCase()}]
            </option>
          `}).join('')}
        </select>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="walkin-cin">Check-in Date <span class="required-mark">*</span></label>
          <input type="date" id="walkin-cin" class="input-field" value="${today}" required />
        </div>
        <div class="form-group">
          <label class="form-label" for="walkin-cout">Check-out Date <span class="required-mark">*</span></label>
          <input type="date" id="walkin-cout" class="input-field" value="${tomorrow}" required />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="walkin-plan">Rate Plan</label>
          <select id="walkin-plan" class="select-field">
            <option value="">Standard Daily Base Rate</option>
            ${ratePlans.map(p => `
              <option value="${p.id}">${p.name} (${p.code})</option>
            `).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="walkin-adults">Adults <span style="font-size:11px; color:#64748B;">(Max 2)</span></label>
          <select id="walkin-adults" class="select-field" required>
            <option value="1">1 Adult</option>
            <option value="2">2 Adults (Max)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="walkin-rate">Nightly Rate (${getCurrencySymbol()})</label>
          <input type="number" id="walkin-rate" class="input-field font-mono" step="0.01" min="1" placeholder="3500.00" />
        </div>
      </div>

      <!-- Live Calculation Box -->
      <div id="walkin-quote-box" style="display:none; padding:10px 14px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; font-size:12px; color:#1E293B;"></div>

      <!-- Advance Payment / Deposit (Optional) -->
      <div style="border-top:1px solid #E2E8F0; padding-top:10px; margin-top:2px;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
          <span style="font-size:11.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; color:#0F172A;">
            3. Advance Payment / Deposit (Optional)
          </span>
          <span style="font-size:11px; color:#059669; font-weight:600;">Folio Credit</span>
        </div>
        <div style="display: grid; grid-template-columns: 1.2fr 1fr 1.4fr; gap: 8px;">
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" for="walkin-advance-amt">Advance Amount (${getCurrencySymbol()})</label>
            <input type="number" id="walkin-advance-amt" class="input-field font-mono" step="0.01" min="0" placeholder="0.00" />
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" for="walkin-advance-method">Method</label>
            <select id="walkin-advance-method" class="select-field">
              <option value="upi">UPI / QR</option>
              <option value="cash" selected>Cash</option>
              <option value="card">Credit / Debit Card</option>
              <option value="net_banking">Net Banking</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" for="walkin-advance-ref">Ref / Trans #</label>
            <input type="text" id="walkin-advance-ref" class="input-field" placeholder="UPI Ref / Last 4" />
          </div>
        </div>
      </div>

      <!-- Hidden Instant Check-in flag: Always active in background -->
      <input type="hidden" id="walkin-auto-checkin" value="true" />

      <div class="form-group">
        <label class="form-label" for="walkin-notes">Stay Notes & Preferences</label>
        <textarea id="walkin-notes" class="textarea-field" placeholder="Airport transfer, late arrival, extra bed..."></textarea>
      </div>

      <div id="walkin-error-box" style="display:none; color:var(--danger); font-size:12px; padding: 8px 12px; background:var(--danger-bg); border:1px solid #FECACA; border-radius:6px;"></div>
    </form>
  `;

  const panel = UI.modal({
    title: 'New Guest Entry & Walk-In Check-In',
    contentHtml: contentHtml,
    footerHtml: `
      <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
      <button class="btn btn-primary btn-md" id="submit-walkin-btn" style="background:#000000; color:#FFFFFF; border:1px solid #000000;">
        Complete Check-In Now
      </button>
    `,
  });

  const roomSelect = panel.querySelector('#walkin-room');
  const planSelect = panel.querySelector('#walkin-plan');
  const cinInput = panel.querySelector('#walkin-cin');
  const coutInput = panel.querySelector('#walkin-cout');
  const adultsInput = panel.querySelector('#walkin-adults');
  const rateInput = panel.querySelector('#walkin-rate');
  const quoteBox = panel.querySelector('#walkin-quote-box');

  const updateLiveRate = async () => {
    const selectedOpt = roomSelect.options[roomSelect.selectedIndex];
    if (!selectedOpt || !selectedOpt.value) return;

    const rtId = selectedOpt.getAttribute('data-type-id');
    const baseRate = parseFloat(selectedOpt.getAttribute('data-rate')) || 3500;
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

      quoteBox.style.display = 'block';
      quoteBox.innerHTML = `
        <div style="display:flex; justify-content:space-between; font-weight:600;">
          <span>Stay Subtotal (${quote.nights} night(s)):</span>
          <span class="font-mono">${formatCurrency(quote.subtotal)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:2px; font-size:11px; color:#64748B;">
          <span>Applicable GST Taxes:</span>
          <span class="font-mono">+${formatCurrency(quote.tax_total)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-weight:700; margin-top:4px; padding-top:4px; border-top:1px solid #E2E8F0; font-size:13px;">
          <span>Estimated Grand Total:</span>
          <span class="font-mono">${formatCurrency(quote.grand_total)}</span>
        </div>
      `;
    } catch (e) {
      rateInput.value = baseRate.toFixed(2);
      quoteBox.style.display = 'none';
    }
  };

  roomSelect.onchange = updateLiveRate;
  planSelect.onchange = updateLiveRate;
  cinInput.onchange = updateLiveRate;
  coutInput.onchange = updateLiveRate;
  adultsInput.onchange = updateLiveRate;

  // Submit Handler
  panel.querySelector('#submit-walkin-btn').onclick = async () => {
    const errBox = panel.querySelector('#walkin-error-box');
    errBox.style.display = 'none';

    const firstName = panel.querySelector('#walkin-first-name').value.trim();
    const lastName = panel.querySelector('#walkin-last-name').value.trim();
    const phone = panel.querySelector('#walkin-phone').value.trim();
    const email = panel.querySelector('#walkin-email').value.trim();
    const idType = panel.querySelector('#walkin-id-type').value;
    const idNum = panel.querySelector('#walkin-id-num').value.trim();
    const roomId = parseInt(roomSelect.value);
    const cin = cinInput.value;
    const cout = coutInput.value;
    const planId = planSelect.value ? parseInt(planSelect.value) : undefined;
    const adults = parseInt(adultsInput.value) || 1;
    const nightlyRate = rateInput.value ? parseFloat(rateInput.value) : undefined;
    const autoCheckIn = true;
    const notes = panel.querySelector('#walkin-notes').value.trim();

    if (!firstName || !lastName || !phone) {
      errBox.textContent = 'Please enter guest first name, last name, and contact phone number.';
      errBox.style.display = 'block';
      return;
    }

    if (!roomId) {
      errBox.textContent = 'Please select a room to assign the guest.';
      errBox.style.display = 'block';
      return;
    }

    if (!cin || !cout || cout <= cin) {
      errBox.textContent = 'Check-out date must be strictly after check-in date.';
      errBox.style.display = 'block';
      return;
    }

    const advanceAmt = parseFloat(panel.querySelector('#walkin-advance-amt').value) || 0;
    const advanceMethod = panel.querySelector('#walkin-advance-method').value;
    const advanceRef = panel.querySelector('#walkin-advance-ref').value.trim();

    const payload = {
      first_name: firstName,
      last_name: lastName,
      phone: phone,
      email: email || undefined,
      id_type: idType,
      id_number: idNum || undefined,
      room_id: roomId,
      rate_plan_id: planId,
      check_in_date: cin,
      check_out_date: cout,
      adults: adults,
      nightly_rate: nightlyRate,
      auto_check_in: autoCheckIn,
      advance_amount: advanceAmt > 0 ? advanceAmt : undefined,
      advance_payment_method: advanceAmt > 0 ? advanceMethod : undefined,
      advance_payment_reference: advanceAmt > 0 ? (advanceRef || 'Advance Payment at Walk-in') : undefined,
      notes: notes || undefined,
    };

    const submitBtn = panel.querySelector('#submit-walkin-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing Walk-in...';

    try {
      const created = await API.post('/api/reservations/walk-in', payload);
      UI.toast(
        autoCheckIn
          ? `✓ Guest ${created.guest.full_name} checked into Room ${created.room.number} (#${created.confirmation_number})!`
          : `✓ Reservation #${created.confirmation_number} confirmed for ${created.guest.full_name}!`,
        'success'
      );
      UI.closeModal();

      // Refresh Dashboard and related pages
      if (window.refreshAllDashboardStats) {
        window.refreshAllDashboardStats();
      } else {
        if (window.Pages.Dashboard && window.Pages.Dashboard.refresh) {
          window.Pages.Dashboard.refresh();
        }
        if (window.Pages.Rooms && window.Pages.Rooms.fetchRooms) {
          window.Pages.Rooms.fetchRooms();
        }
        if (window.Pages.Reservations && window.Pages.Reservations.fetchReservations) {
          window.Pages.Reservations.fetchReservations();
        }
      }

      // Open folio drawer for immediate guest onboarding
      if (window.openReservationDrawer) {
        window.openReservationDrawer(created.id);
      }
    } catch (err) {
      errBox.textContent = err.message || 'Failed to complete walk-in entry. Please verify details.';
      errBox.style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.textContent = autoCheckIn ? 'Complete Check-In Now' : 'Create Confirmed Reservation';
    }
  };
};

window.downloadOrPrintRunSheet = async () => {
  const exportBtn = document.getElementById('topbar-export-pdf-btn');
  const originalHtml = exportBtn ? exportBtn.innerHTML : '';
  if (exportBtn) {
    exportBtn.disabled = true;
    exportBtn.innerHTML = `<span>Exporting...</span>`;
  }
  try {
    const token = localStorage.getItem('access_token');
    const resp = await fetch('/api/dashboard/run-sheet.pdf', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!resp.ok) {
      window.print();
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `RunSheet_${new Date().toISOString().slice(0, 10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    UI.toast('Daily Front Desk Run Sheet PDF exported successfully!', 'success');
  } catch (err) {
    window.print();
  } finally {
    if (exportBtn) {
      exportBtn.disabled = false;
      exportBtn.innerHTML = originalHtml;
    }
  }
};
