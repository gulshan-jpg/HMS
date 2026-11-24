/**
 * CheckinOS - Main Frontend Application Entrypoint
 * Bootstraps the Single Page Application, registers routes, and configures distinct Admin vs Staff interfaces.
 */

window.refreshAllDashboardStats = function() {
  if (window.Pages && window.Pages.Dashboard && typeof window.Pages.Dashboard.refresh === 'function') {
    window.Pages.Dashboard.refresh();
  }
  if (window.Pages && window.Pages.Rooms) {
    if (typeof window.Pages.Rooms.loadInitialData === 'function') {
      window.Pages.Rooms.loadInitialData();
    } else if (typeof window.Pages.Rooms.fetchRooms === 'function') {
      window.Pages.Rooms.fetchRooms();
    }
  }
  if (window.Pages && window.Pages.Reservations && typeof window.Pages.Reservations.fetchReservations === 'function') {
    window.Pages.Reservations.fetchReservations();
  }
  if (window.Pages && window.Pages.Billing && typeof window.Pages.Billing.fetchFolios === 'function') {
    window.Pages.Billing.fetchFolios();
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  // Check if on login page
  if (window.location.pathname.includes('/login')) {
    return;
  }

  // Check auth session
  const token = API.getToken();
  if (!token) {
    window.location.href = '/login';
    return;
  }

  // Instant profile restore from localStorage for 0ms cold-start rendering
  let user = API.getUser();
  if (user) {
    window.currentUser = user;
    setupRoleInterface(user);
    // Verify session asynchronously in background without blocking UI
    API.me().then(freshUser => {
      window.currentUser = freshUser;
    }).catch(e => {
      API.setToken(null);
      window.location.href = '/login';
    });
  } else {
    try {
      user = await API.me();
      window.currentUser = user;
      setupRoleInterface(user);
    } catch (e) {
      API.setToken(null);
      window.location.href = '/login';
      return;
    }
  }

  // Register SPA routes
  Router.register('/', (container) => window.Pages.Dashboard.render(container));
  Router.register('/app', (container) => window.Pages.Dashboard.render(container));
  Router.register('/bookings', (container) => window.Pages.Reservations.render(container));
  Router.register('/reservations', (container) => window.Pages.Reservations.render(container));
  Router.register('/rooms', (container) => window.Pages.Rooms.render(container));
  Router.register('/rate-calendar', (container) => window.Pages.RateCalendar.render(container));
  Router.register('/timeline', (container) => window.Pages.Timeline.render(container));
  Router.register('/housekeeping', (container) => window.Pages.Housekeeping.render(container));
  Router.register('/night-audit', (container) => window.Pages.NightAudit.render(container));
  Router.register('/billing', (container) => window.Pages.Billing.render(container));
  Router.register('/channels', (container) => window.Pages.Channels.render(container));
  Router.register('/property', (container) => window.Pages.Property.render(container));
  Router.register('/policies', (container) => window.Pages.Policies.render(container));
  Router.register('/guests', (container) => window.Pages.Guests.render(container));
  Router.register('/settings', (container) => window.Pages.Settings.render(container));
  Router.register('/import', () => {
    window.location.href = '/settings';
  });

  // Initialize router
  Router.init();

  // Load and display current Business Date in topbar
  loadBusinessDate();

  // Initialize SaaS Org context, Trial Banner & Help Widget
  setupSaaSContext(user);

  // Topbar search click trigger
  const searchTrigger = document.getElementById('topbar-search-trigger');
  if (searchTrigger) {
    searchTrigger.onclick = () => window.openGlobalSearchModal();
  }

  // Topbar New Guest action button
  const newGuestBtn = document.getElementById('topbar-new-guest-btn');
  if (newGuestBtn) {
    newGuestBtn.onclick = () => {
      if (window.openDirectGuestCheckinModal) {
        window.openDirectGuestCheckinModal();
      } else if (window.openNewReservationModal) {
        window.openNewReservationModal();
      }
    };
  }

  // Topbar Export PDF button
  const exportBtn = document.getElementById('topbar-export-pdf-btn');
  if (exportBtn) {
    exportBtn.onclick = () => {
      if (window.downloadOrPrintRunSheet) {
        window.downloadOrPrintRunSheet();
      } else {
        window.print();
      }
    };
  }

  // Topbar sign out button
  const logoutBtn = document.getElementById('topbar-logout-btn');
  if (logoutBtn) {
    logoutBtn.onclick = () => API.logout();
  }

  // Mobile Drawer Sidebar Navigation Toggle
  const sidebarToggle = document.getElementById('mobile-sidebar-toggle');
  const sidebar = document.getElementById('app-sidebar') || document.querySelector('.sidebar');
  const backdrop = document.getElementById('mobile-sidebar-backdrop');

  function openMobileSidebar() {
    if (sidebar) sidebar.classList.add('is-open');
    if (backdrop) backdrop.classList.add('is-open');
    document.body.classList.add('sidebar-open');
  }

  function closeMobileSidebar() {
    if (sidebar) sidebar.classList.remove('is-open');
    if (backdrop) backdrop.classList.remove('is-open');
    document.body.classList.remove('sidebar-open');
  }

  if (sidebarToggle) {
    sidebarToggle.onclick = () => {
      if (sidebar && sidebar.classList.contains('is-open')) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
    };
  }
  if (backdrop) {
    backdrop.onclick = closeMobileSidebar;
  }
  // Auto-close drawer on mobile when clicking any navigation link
  document.querySelectorAll('.sidebar-nav-list a, .sidebar-footer-nav a').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 820) {
        closeMobileSidebar();
      }
    });
  });
});

function setupRoleInterface(user) {
  const isElevated = ['owner', 'admin', 'manager'].includes(user.role);

  // 1. Sidebar menu filtering: Staff sees ONLY operational routes
  ['/rate-calendar', '/billing', '/night-audit', '/channels', '/property', '/policies'].forEach(route => {
    const el = document.querySelector(`a[data-route="${route}"]`);
    if (el && el.closest('li')) {
      el.closest('li').style.display = isElevated ? 'block' : 'none';
    }
  });

  const settingsLink = document.querySelector('a[data-route="/settings"]');
  if (settingsLink) {
    settingsLink.style.display = 'flex';
  }

  // Adjust first nav link label for staff
  const dashLinkText = document.querySelector('a[data-route="/"] span');
  if (dashLinkText) {
    dashLinkText.textContent = isElevated ? 'Dashboard' : 'Front Desk';
  }

  // 2. Topbar user profile badge with preset role
  const profileSlot = document.getElementById('topbar-user-profile');
  if (profileSlot) {
    const roleLabels = {
      owner: 'HOTEL OWNER',
      admin: 'ADMINISTRATOR',
      manager: 'GENERAL MANAGER',
      front_desk: 'FRONT DESK',
      housekeeping: 'HOUSEKEEPING',
      accountant: 'ACCOUNTANT'
    };
    const rolePills = {
      owner: 'badge-info',
      admin: 'badge-info',
      manager: 'badge-info',
      front_desk: 'badge-neutral',
      housekeeping: 'badge-warning',
      accountant: 'badge-neutral'
    };

    profileSlot.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: flex-end; line-height: 1.2; white-space: nowrap; flex-shrink: 0;">
        <span style="font-weight: 600; font-size: 13px; color: #0F172A; white-space: nowrap;">${user.full_name}</span>
        <span class="badge ${rolePills[user.role] || 'badge-neutral'}" style="font-size: 10px; height: 18px; padding: 0 6px; margin-top: 2px; white-space: nowrap;">
          ${roleLabels[user.role] || user.role.toUpperCase()}
        </span>
      </div>
    `;
  }
}

async function setupSaaSContext(user) {
  try {
    const [org, billing] = await Promise.all([
      API.get('/api/org').catch(() => null),
      API.get('/api/billing/status').catch(() => null),
    ]);

    // Update Brand Hotel Name
    if (org && org.name) {
      const brandText = document.querySelector('.sidebar-brand-text');
      if (brandText) {
        brandText.innerHTML = `${org.name} <span style="font-size: 10px; font-weight: normal; color: #9CA3AF; display: block; font-family: monospace;">${org.plan.toUpperCase()}</span>`;
      }
    }

    // Demo Mode Pill in Topbar
    const actionsBlock = document.querySelector('.topbar-actions-block');
    if (actionsBlock && !document.getElementById('demo-mode-pill')) {
      const demoPill = document.createElement('div');
      demoPill.id = 'demo-mode-pill';
      demoPill.style.cssText = 'display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; padding: 4px 10px; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 999px; color: #D97706; cursor: pointer;';
      demoPill.innerHTML = `
        <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#D97706;"></span>
        <span>DEMO MODE</span>
      `;
      demoPill.onclick = () => openPurgeDemoModal();
      actionsBlock.insertBefore(demoPill, actionsBlock.firstChild);
    }

    // Trial Banner below Topbar if trialing
    if (billing && billing.trialing) {
      const mainCanvas = document.querySelector('.main-canvas');
      if (mainCanvas && !document.getElementById('trial-banner')) {
        const banner = document.createElement('div');
        banner.id = 'trial-banner';
        banner.style.cssText = 'background: #111827; color: #FFFFFF; padding: 8px 24px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; z-index: 30;';
        banner.innerHTML = `
          <div>
            <strong>14-Day Free Trial:</strong> You have <strong>${billing.days_left || 14} days</strong> remaining in your ${billing.plan.toUpperCase()} trial. All features are fully active.
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn btn-primary btn-sm" style="background: #FFFFFF; color: #111827; font-weight: 600; padding: 4px 12px; height: 28px;" onclick="window.Pages.Settings.openUpgradeModal()">
              Pick a Plan
            </button>
            <button style="background: none; border: none; color: #9CA3AF; cursor: pointer; font-size: 14px;" onclick="document.getElementById('trial-banner').remove()">✕</button>
          </div>
        `;
        mainCanvas.insertBefore(banner, document.getElementById('main-content'));
      }
    }

    // Floating Help & Tour Widget
    setupFloatingHelpWidget();

    // Trigger Guided Tour if not yet completed
    if (user.tour_completed === false) {
      setTimeout(() => startGuidedTour(), 1000);
    }
  } catch (err) {
    console.warn('SaaS context initialization error:', err);
  }
}

function openPurgeDemoModal() {
  UI.modal({
    title: 'Purge Sample Demonstration Data',
    contentHtml: `
      <div style="font-size: 13px; color: #374151; line-height: 1.5;">
        <p style="margin-bottom: 12px;">Your hotel was provisioned with realistic sample reservations, guests, and rate plans to let you explore the system immediately.</p>
        <p style="margin-bottom: 12px;">Ready to start taking real hotel bookings? Purging will soft-delete all sample demo records while keeping your hotel configuration, room types, and custom settings intact.</p>
        <div style="background: #FEF2F2; border: 1px solid #FECACA; padding: 12px; border-radius: 6px; color: #DC2626; font-size: 12px;">
          <strong>Notice:</strong> This action permanently removes demo reservations from your active room rack.
        </div>
      </div>
    `,
    footerHtml: `
      <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Keep Demo Data</button>
      <button class="btn btn-primary btn-md" style="background: #DC2626; border-color: #DC2626;" onclick="executePurgeDemoData()">Purge Demo Data Now</button>
    `
  });
}

async function executePurgeDemoData() {
  try {
    UI.toast('Purging sample demonstration records...', 'info');
    const res = await API.delete('/api/demo-data');
    UI.toast(res.message || 'Demo records purged successfully', 'success');
    UI.closeModal();
    const pill = document.getElementById('demo-mode-pill');
    if (pill) pill.remove();
    Router.navigate(window.location.pathname);
  } catch (e) {
    UI.toast(e.message || 'Failed to purge demo data', 'danger');
  }
}

function setupFloatingHelpWidget() {
  if (document.getElementById('floating-help-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'floating-help-btn';
  btn.className = 'no-print';
  btn.style.cssText = 'position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px; border-radius: 50%; background: #111827; color: #FFFFFF; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15); cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 80;';
  btn.title = 'Need Help? Tour & Guides';
  btn.innerHTML = `<svg style="width:20px; height:20px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z" /></svg>`;

  btn.onclick = () => {
    UI.modal({
      title: 'Help, Tour & Keyboard Shortcuts',
      contentHtml: `
        <div style="display: flex; flex-direction: column; gap: 14px; font-size: 13px;">
          <div style="border: 1px solid #E5E7EB; border-radius: 6px; padding: 14px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong>Guided Product Tour</strong>
              <div style="color: #6B7280; font-size: 12px;">Step-by-step 6-point interactive walkthrough of CheckinOS.</div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="UI.closeModal(); startGuidedTour();">Start Tour</button>
          </div>

          <div style="border: 1px solid #E5E7EB; border-radius: 6px; padding: 14px;">
            <strong style="margin-bottom: 8px; display: block;">Keyboard Shortcuts</strong>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
              <div><kbd style="background: #F3F4F6; padding: 2px 6px; border: 1px solid #D1D5DB; border-radius: 4px;">⌘K</kbd> Global Search</div>
              <div><kbd style="background: #F3F4F6; padding: 2px 6px; border: 1px solid #D1D5DB; border-radius: 4px;">ESC</kbd> Close Overlay</div>
              <div><kbd style="background: #F3F4F6; padding: 2px 6px; border: 1px solid #D1D5DB; border-radius: 4px;">P</kbd> Print Folio / Invoice</div>
              <div><kbd style="background: #F3F4F6; padding: 2px 6px; border: 1px solid #D1D5DB; border-radius: 4px;">?</kbd> Open Help Menu</div>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 8px; font-size: 12px; color: #6B7280;">
            <a href="/status" target="_blank" style="text-decoration: underline;">System Status (99.98%)</a>
            <a href="mailto:support@checkinos.io" style="text-decoration: underline;">Contact Engineering Support</a>
          </div>
        </div>
      `,
      footerHtml: '<button class="btn btn-primary btn-md" onclick="UI.closeModal()">Close</button>'
    });
  };

  document.body.appendChild(btn);
}

function startGuidedTour() {
  const steps = [
    {
      title: '1. Operations Dashboard',
      text: 'Monitor live occupancy, pending arrivals, today\'s revenue in INR (₹), and turnover cleaning orders at a glance.',
      route: '/'
    },
    {
      title: '2. Room Availability Timeline (Gantt)',
      text: 'Visual calendar of all room occupancies. Drag-and-drop bookings between rooms with automatic conflict prevention.',
      route: '/timeline'
    },
    {
      title: '3. 45-Second Check-In & Folios',
      text: 'Click any booked reservation to check in the guest. Room charges, taxes, and advance deposits are automatically posted.',
      route: '/reservations'
    },
    {
      title: '4. Mobile Housekeeping (No Passwords)',
      text: 'Generate secure 24-hour links for cleaning staff. Housekeepers open the link on mobile and mark rooms clean with one tap.',
      route: '/housekeeping'
    },
    {
      title: '5. Automated Night Audit',
      text: 'End-of-day rollover posts nightly room charges, balances taxes, and records manager audit snapshots.',
      route: '/night-audit'
    },
    {
      title: '6. Settings, Data Safety & Backups',
      text: 'Configure dynamic rate plans, GST slabs, manage daily backups, and restore deleted records from Trash.',
      route: '/settings'
    }
  ];

  let stepIdx = 0;

  function showStep(idx) {
    const s = steps[idx];
    Router.navigate(s.route);

    UI.modal({
      title: `Guided Tour (${idx + 1}/6): ${s.title}`,
      contentHtml: `
        <div style="font-size: 14px; line-height: 1.6; color: #374151;">
          <p>${s.text}</p>
          <div style="display: flex; gap: 4px; margin-top: 18px;">
            ${steps.map((_, i) => `<div style="flex: 1; height: 4px; border-radius: 2px; background: ${i <= idx ? '#111827' : '#E5E7EB'};"></div>`).join('')}
          </div>
        </div>
      `,
      footerHtml: `
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal(); completeTourAPI();">Skip Tour</button>
        ${idx > 0 ? `<button class="btn btn-secondary btn-md" onclick="showTourStep(${idx - 1})">&larr; Previous</button>` : ''}
        ${idx < steps.length - 1 
          ? `<button class="btn btn-primary btn-md" onclick="showTourStep(${idx + 1})">Next Step &rarr;</button>`
          : `<button class="btn btn-primary btn-md" onclick="UI.closeModal(); completeTourAPI();">Finish Tour & Start Working</button>`}
      `
    });
  }

  window.showTourStep = showStep;
  showStep(0);
}

async function completeTourAPI() {
  try {
    await API.post('/api/user/complete-tour');
    if (window.currentUser) window.currentUser.tour_completed = true;
  } catch (e) {
    // Ignore
  }
}

async function loadBusinessDate() {
  const el = document.getElementById('topbar-business-date-val');
  if (!el) return;
  try {
    const data = await API.get('/api/night-audit/business-date');
    if (data && data.date) {
      window.currentBusinessDate = data.date;
      el.textContent = formatDate(data.date, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
    }
  } catch (e) {
    el.textContent = formatDate(new Date().toISOString().slice(0, 10));
  }
}
window.refreshBusinessDate = loadBusinessDate;
