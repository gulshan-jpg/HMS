/**
 * CheckinOS - Single Page Application Router & Global Hotkeys
 * Manages view routing, topbar headings, sidebar synchronization, and shortcuts.
 */

const Router = {
  routes: {},
  currentPath: '',

  register(path, handler) {
    this.routes[path] = handler;
  },

  init() {
    window.addEventListener('popstate', () => this.handleRoute());
    window.addEventListener('hashchange', () => this.handleRoute());

    // Intercept clicks on internal links
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[data-route]');
      if (link) {
        e.preventDefault();
        const targetRoute = link.getAttribute('href') || link.getAttribute('data-route');
        this.navigate(targetRoute);
      }
    });

    this.initKeyboardShortcuts();
    this.handleRoute();
  },

  navigate(path, params = {}) {
    if (path.startsWith('#')) {
      window.location.hash = path;
      return;
    }
    window.history.pushState(params, '', path);
    this.handleRoute();
  },

  normalizePath() {
    let p = window.location.pathname;
    if (window.location.hash && window.location.hash.length > 1) {
      p = window.location.hash.replace('#', '');
    }
    // Clean trailing slash
    if (p.length > 1 && p.endsWith('/')) {
      p = p.slice(0, -1);
    }
    if (p === '/app') {
      return '/';
    }
    return p || '/';
  },

  handleRoute() {
    const token = API.getToken();
    if (!token && !window.location.pathname.includes('/login')) {
      window.location.href = '/login';
      return;
    }

    const path = this.normalizePath();

    // Role-based access control: Staff cannot access management, rate calendar or audit routes
    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');
    if (window.currentUser && !isAdmin && (path === '/rate-calendar' || path === '/billing' || path === '/night-audit' || path === '/channels' || path === '/property' || path === '/policies')) {
      UI.toast('Access Restricted: Rate calendar & management consoles are restricted to Administrators.', 'warning');
      this.navigate('/');
      return;
    }

    this.currentPath = path;

    // Update active nav link
    document.querySelectorAll('.nav-link').forEach((item) => {
      const itemRoute = item.getAttribute('data-route');
      if (itemRoute === path || (itemRoute === '/bookings' && path === '/reservations') || (itemRoute === '/reservations' && path === '/bookings')) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Update topbar title and subtext
    this.updateTopbarHeader(path);

    // Route execution
    const handler = this.routes[path] || this.routes['/'];
    if (handler) {
      const contentEl = document.getElementById('main-content');
      if (contentEl) {
        handler(contentEl);
      }
    }
  },

  updateTopbarHeader(path) {
    const heading = document.getElementById('topbar-page-heading');
    const subtext = document.getElementById('topbar-page-subtext');
    if (!heading || !subtext) return;

    const isAdmin = window.currentUser && (window.currentUser.role === 'owner' || window.currentUser.role === 'admin' || window.currentUser.role === 'manager');

    const routeMeta = isAdmin ? {
      '/': { title: 'Dashboard', subtext: 'Executive performance, occupancy analytics, and revenue metrics' },
      '/bookings': { title: 'All Bookings', subtext: 'Comprehensive directory of all reservations, stays, invoices & payments' },
      '/reservations': { title: 'All Bookings', subtext: 'Comprehensive directory of all reservations, stays, invoices & payments' },
      '/rooms': { title: 'Rooms & Inventory', subtext: 'Property inventory management, rates, and assignment states' },
      '/rate-calendar': { title: 'Rate Calendar', subtext: '30-day dynamic pricing matrix, rate overrides, and occupancy yields' },
      '/timeline': { title: 'Availability Timeline', subtext: 'Interactive 30-day Gantt timeline, drag-and-drop bookings, and room allocations' },
      '/housekeeping': { title: 'Housekeeping & Tasks', subtext: 'Turnover cleaning, room inspections, and maintenance work orders' },
      '/night-audit': { title: 'Night Audit & EOD Roll', subtext: 'Close daily business, post nightly room charges, mark no-shows, and reconcile revenue' },
      '/guests': { title: 'Guest Directory', subtext: 'Guest contact repository, lifetime spend, and stay histories' },
      '/billing': { title: 'Analytics & Billing', subtext: 'Ledger accounting, incidental postings, payments, and checkout settlement' },
      '/channels': { title: 'OTA & Channel Sync', subtext: 'Real-time booking ingestion from OYO, Airbnb, Booking.com, and Agoda' },
      '/property': { title: 'Property Management', subtext: 'Hotel configuration, commercial rate plans, tax engine, and team' },
      '/policies': { title: 'Cancellation Policies', subtext: 'Commercial booking policies, cancellation fees, and refund terms' },
      '/settings': { title: 'Account Settings', subtext: 'Operator profile, security credentials, preferences, and session controls' },
    } : {
      '/': { title: 'Front Desk Console', subtext: 'Today\'s arrivals, departure processing, and live room readiness' },
      '/bookings': { title: 'All Bookings', subtext: 'Guest check-in, checkout, invoices, and departure turnover' },
      '/reservations': { title: 'All Bookings', subtext: 'Guest check-in, checkout, invoices, and departure turnover' },
      '/rooms': { title: 'Room Inventory', subtext: 'Live housekeeping readiness and room assignment states (Read-Only)' },
      '/rate-calendar': { title: 'Rate Calendar', subtext: '30-day view of published nightly rates and property occupancy' },
      '/timeline': { title: 'Availability Timeline', subtext: 'Interactive 30-day room allocations and in-house stay schedule' },
      '/housekeeping': { title: 'Turnover & Tasks', subtext: 'Active cleaning queue and maintenance work orders' },
      '/guests': { title: 'Guest Directory', subtext: 'Guest contact repository and in-house stay histories' },
      '/settings': { title: 'My Account', subtext: 'Operator profile, security credentials, and session controls' },
    };

    const meta = routeMeta[path] || (isAdmin
      ? { title: 'Dashboard', subtext: 'Monitor key performance indicators' }
      : { title: 'Front Desk Console', subtext: 'Front desk operational workspace' });
    heading.textContent = meta.title;
    subtext.textContent = meta.subtext;
  },

  initKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      const isTyping = activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select';

      // ⌘K / Ctrl+K opens Global Search
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        window.openGlobalSearchModal();
        return;
      }

      // '?' opens shortcuts cheatsheet when not in input
      if (e.key === '?' && !isTyping && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        window.openShortcutsModal();
        return;
      }

      // 'n' triggers new reservation on reservations page
      if (e.key.toLowerCase() === 'n' && !isTyping && !e.metaKey && !e.ctrlKey) {
        if (this.currentPath === '/reservations') {
          e.preventDefault();
          if (window.openNewReservationModal) {
            window.openNewReservationModal();
          }
        }
      }
    });
  },
};

// Global Search Modal with Live Search
window.openGlobalSearchModal = () => {
  const content = `
    <div style="display:flex; flex-direction:column; gap:16px;">
      <div style="display:flex; align-items:center; gap:10px; border-bottom:1px solid #E2E8F0; padding-bottom:12px;">
        <svg style="width:18px; height:18px; color:var(--text-tertiary);" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input type="text" id="global-search-input" placeholder="Search rooms, guests, or tasks... (e.g. Priya, 201, HTL)" style="flex:1; border:none; outline:none; font-size:15px;" autofocus autocomplete="off" />
      </div>
      <div id="global-search-results" style="max-height:340px; overflow-y:auto;">
        <div style="padding: 24px; text-align: center; color: var(--text-tertiary); font-size: 13px;">
          Type to search reservations and guest records
        </div>
      </div>
    </div>
  `;

  const panel = UI.modal({
    title: 'Search System Records',
    contentHtml: content,
    wide: true,
  });

  const searchInput = panel.querySelector('#global-search-input');
  const resultsContainer = panel.querySelector('#global-search-results');
  let debounceTimeout = null;

  searchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim();
    clearTimeout(debounceTimeout);
    if (!q) {
      resultsContainer.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-tertiary); font-size: 13px;">Type to search reservations and guest records</div>`;
      return;
    }

    debounceTimeout = setTimeout(async () => {
      try {
        const [resList, guestsList] = await Promise.all([
          API.get('/api/reservations', { search: q, limit: 6 }),
          API.get('/api/guests', { search: q, limit: 6 }),
        ]);

        const resItems = Array.isArray(resList?.items) ? resList.items : (Array.isArray(resList) ? resList : []);
        const guestItems = Array.isArray(guestsList?.items) ? guestsList.items : (Array.isArray(guestsList) ? guestsList : []);

        let html = '';

        if (resItems.length === 0 && guestItems.length === 0) {
          html = `<div style="padding: 24px; text-align: center; color: var(--text-tertiary); font-size: 13px;">No matching records found for "${q}"</div>`;
        } else {
          if (resItems.length > 0) {
            html += `<div style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; padding: 6px 10px;">Reservations</div>`;
            resItems.forEach((r) => {
              html += `
                <div class="search-result-row" data-action="res" data-id="${r.id}" style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; border-radius:8px; cursor:pointer; hover:background:#F8FAFC;">
                  <div>
                    <div style="font-weight: 600; font-size: 13px;">${r.guest ? r.guest.full_name : 'Guest'} · Room ${r.room ? r.room.number : '—'}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);"><span class="font-mono">${r.confirmation_number}</span> · ${formatDate(r.check_in_date)} to ${formatDate(r.check_out_date)}</div>
                  </div>
                  <div>${UI.statusBadge(r.status)}</div>
                </div>
              `;
            });
          }

          if (guestItems.length > 0) {
            html += `<div style="font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; padding: 12px 10px 4px;">Guests</div>`;
            guestItems.forEach((g) => {
              html += `
                <div class="search-result-row" data-action="guest" data-id="${g.id}" style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; border-radius:8px; cursor:pointer;">
                  <div>
                    <div style="font-weight: 600; font-size: 13px;">${g.full_name}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">${g.email} · ${g.phone}</div>
                  </div>
                  <div style="font-size: 12px; color: var(--text-secondary);">${g.total_stays} stay(s)</div>
                </div>
              `;
            });
          }
        }

        resultsContainer.innerHTML = html;

        resultsContainer.querySelectorAll('.search-result-row').forEach((item) => {
          item.onclick = () => {
            const action = item.getAttribute('data-action');
            const id = item.getAttribute('data-id');
            UI.closeModal();
            if (action === 'res') {
              Router.navigate('/reservations');
              setTimeout(() => {
                if (window.openReservationDrawer) window.openReservationDrawer(id);
              }, 200);
            } else if (action === 'guest') {
              Router.navigate('/guests');
              setTimeout(() => {
                if (window.openGuestDrawer) window.openGuestDrawer(id);
              }, 200);
            }
          };
        });
      } catch (e) {
        resultsContainer.innerHTML = `<div style="padding: 16px; color: var(--danger); font-size: 12px;">Search query failed</div>`;
      }
    }, 200);
  });
};

// Keyboard Shortcuts Cheatsheet Modal
window.openShortcutsModal = () => {
  const content = `
    <div style="display: flex; flex-direction: column; gap: 12px; font-size: 13px;">
      <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--border);">
        <span>Quick Search</span>
        <span class="font-mono" style="background:#F1F5F9; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">⌘ K / Ctrl + K</span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--border);">
        <span>New Reservation</span>
        <span class="font-mono" style="background:#F1F5F9; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">N</span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--border);">
        <span>Close Modal / Drawer</span>
        <span class="font-mono" style="background:#F1F5F9; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">ESC</span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid var(--border);">
        <span>Shortcuts Help</span>
        <span class="font-mono" style="background:#F1F5F9; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">?</span>
      </div>
    </div>
  `;

  UI.modal({
    title: 'CheckinOS Hotkeys',
    contentHtml: content,
  });
};

window.Router = Router;
