/**
 * Hotel OS - UI Component Framework
 * Modals, Drawers, Toasts, Skeletons, Status Badges, Form Validation, and SVG Icons.
 */

const UI = {
  // SVG Icon Map (crisp, professional, commercial SaaS icons)
  icons: {
    dashboard: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>',
    calendar: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" /></svg>',
    bed: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" /></svg>',
    guests: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" /></svg>',
    housekeeping: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" /></svg>',
    billing: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z" /></svg>',
    settings: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>',
    search: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>',
    plus: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>',
    check: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>',
    x: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>',
    dots: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" /></svg>',
    bell: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" /></svg>',
    logout: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" /></svg>',
    printer: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0 1 10.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0 .229 2.523a1.125 1.125 0 0 1-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0 0 21 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 0 0-1.913-.247M6.34 18H5.25A2.25 2.25 0 0 1 3 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.041 48.041 0 0 1 1.913-.247m10.5 0a48.536 48.536 0 0 0-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.656h10.5Z" /></svg>',
    filter: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" /></svg>',
    menu: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>',
    alert: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>',
    arrowRight: '<svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>',
  },

  getIcon(name, size = 18) {
    const raw = this.icons[name] || this.icons.bed;
    return raw.replace('<svg ', `<svg style="width:${size}px; height:${size}px;" `);
  },

  // ── Toasts (Bottom-Right, 320px, Max 3) ──────────────────────────────────
  toast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    // Keep max 3 toasts
    while (container.children.length >= 3) {
      container.removeChild(container.firstChild);
    }

    const toastEl = document.createElement('div');
    toastEl.className = `toast toast-${type}`;
    toastEl.innerHTML = `
      <div class="toast-msg">${message}</div>
      <button class="toast-close-btn" aria-label="Close notification">&times;</button>
    `;

    const closeBtn = toastEl.querySelector('.toast-close-btn');
    closeBtn.onclick = () => {
      toastEl.remove();
    };

    container.appendChild(toastEl);

    // Auto dismiss after 4 seconds
    setTimeout(() => {
      if (toastEl.parentNode) {
        toastEl.style.opacity = '0';
        toastEl.style.transform = 'translateX(20px)';
        toastEl.style.transition = 'all 0.2s ease';
        setTimeout(() => toastEl.remove(), 200);
      }
    }, 4000);
  },

  // ── Modal Dialog System ──────────────────────────────────────────────────
  activeModal: null,
  previousActiveElement: null,

  modal({ title, contentHtml, footerHtml = '', wide = false, onClose = null }) {
    this.closeModal();

    this.previousActiveElement = document.activeElement;

    // Lock background scroll on mobile and desktop
    document.body.classList.add('modal-open');

    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.id = 'active-modal-backdrop';

    const panel = document.createElement('div');
    panel.className = `modal-panel ${wide ? 'modal-wide' : ''}`;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');

    panel.innerHTML = `
      <div class="modal-header">
        <h3 class="modal-title">${title}</h3>
        <button class="btn btn-ghost btn-icon close-modal-btn" aria-label="Close modal">
          ${this.getIcon('x', 16)}
        </button>
      </div>
      <div class="modal-body">${contentHtml}</div>
      ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ''}
    `;

    backdrop.appendChild(panel);
    document.body.appendChild(backdrop);

    // Fade in
    requestAnimationFrame(() => {
      backdrop.classList.add('is-open');
    });

    const closeHandler = () => {
      this.closeModal();
      if (onClose) onClose();
    };

    panel.querySelector('.close-modal-btn').onclick = closeHandler;

    // Close when clicking outside on backdrop
    backdrop.onclick = (e) => {
      if (e.target === backdrop) closeHandler();
    };

    this.activeModal = { backdrop, onClose };

    // Trap focus to first input
    const firstInput = panel.querySelector('input, select, textarea, button:not(.close-modal-btn)');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 50);
    }

    return panel;
  },

  closeModal() {
    document.body.classList.remove('modal-open');
    if (this.activeModal) {
      const { backdrop, onClose } = this.activeModal;
      backdrop.classList.remove('is-open');
      setTimeout(() => {
        backdrop.remove();
        if (this.previousActiveElement && typeof this.previousActiveElement.focus === 'function') {
          this.previousActiveElement.focus();
        }
      }, 150);
      this.activeModal = null;
    }
  },

  // ── Detail Drawer (Right side, 480px) ────────────────────────────────────
  activeDrawer: null,

  drawer({ title, subtitle = '', contentHtml, footerHtml = '', onClose = null }) {
    this.closeDrawer();

    // Lock background scroll on mobile and desktop
    document.body.classList.add('drawer-open');

    const backdrop = document.createElement('div');
    backdrop.className = 'drawer-backdrop';
    backdrop.id = 'active-drawer-backdrop';

    const panel = document.createElement('div');
    panel.className = 'drawer-panel';
    panel.id = 'active-drawer-panel';

    panel.innerHTML = `
      <div class="drawer-header">
        <div>
          <h3 class="modal-title">${title}</h3>
          ${subtitle ? `<div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">${subtitle}</div>` : ''}
        </div>
        <button class="btn btn-ghost btn-icon close-drawer-btn" aria-label="Close drawer">
          ${this.getIcon('x', 16)}
        </button>
      </div>
      <div class="drawer-body">${contentHtml}</div>
      ${footerHtml ? `<div class="drawer-footer">${footerHtml}</div>` : ''}
    `;

    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

    requestAnimationFrame(() => {
      backdrop.classList.add('is-open');
      panel.classList.add('is-open');
    });

    const closeHandler = () => {
      this.closeDrawer();
      if (onClose) onClose();
    };

    panel.querySelector('.close-drawer-btn').onclick = closeHandler;
    backdrop.onclick = closeHandler;

    this.activeDrawer = { backdrop, panel, onClose };
    return panel;
  },

  closeDrawer() {
    document.body.classList.remove('drawer-open');
    if (this.activeDrawer) {
      const { backdrop, panel } = this.activeDrawer;
      backdrop.classList.remove('is-open');
      panel.classList.remove('is-open');
      setTimeout(() => {
        backdrop.remove();
        panel.remove();
      }, 200);
      this.activeDrawer = null;
    }
  },

  // ── Confirmation Dialog ──────────────────────────────────────────────────
  confirm({ title, message, confirmText = 'Confirm', cancelText = 'Cancel', isDanger = false }) {
    return new Promise((resolve) => {
      const content = `
        <div style="font-size:13px; color:var(--text); line-height:1.5;">${message}</div>
      `;
      const footer = `
        <button class="btn btn-secondary btn-md" id="confirm-cancel-btn">${cancelText}</button>
        <button class="btn ${isDanger ? 'btn-danger' : 'btn-primary'} btn-md" id="confirm-ok-btn">${confirmText}</button>
      `;

      const panel = this.modal({
        title,
        contentHtml: content,
        footerHtml: footer,
        onClose: () => resolve(false),
      });

      panel.querySelector('#confirm-cancel-btn').onclick = () => {
        this.closeModal();
        resolve(false);
      };
      panel.querySelector('#confirm-ok-btn').onclick = () => {
        this.closeModal();
        resolve(true);
      };
    });
  },

  // ── Status Badges ────────────────────────────────────────────────────────
  statusBadge(status) {
    const s = (status || '').toLowerCase();
    let badgeClass = 'badge-neutral';
    let label = status || 'Unknown';

    switch (s) {
      case 'available':
        badgeClass = 'badge-success';
        label = 'Available';
        break;
      case 'occupied':
        badgeClass = 'badge-info';
        label = 'Occupied';
        break;
      case 'dirty':
        badgeClass = 'badge-warning';
        label = 'Dirty';
        break;
      case 'cleaning':
        badgeClass = 'badge-warning';
        label = 'Cleaning';
        break;
      case 'maintenance':
        badgeClass = 'badge-danger';
        label = 'Maintenance';
        break;
      case 'booked':
        badgeClass = 'badge-info';
        label = 'Booked';
        break;
      case 'checked_in':
        badgeClass = 'badge-success';
        label = 'In-House';
        break;
      case 'checked_out':
        badgeClass = 'badge-neutral';
        label = 'Departed';
        break;
      case 'cancelled':
        badgeClass = 'badge-danger';
        label = 'Cancelled';
        break;
      case 'no_show':
        badgeClass = 'badge-warning';
        label = 'No Show';
        break;
      case 'pending':
        badgeClass = 'badge-warning';
        label = 'Pending';
        break;
      case 'in_progress':
        badgeClass = 'badge-info';
        label = 'In Progress';
        break;
      case 'done':
        badgeClass = 'badge-success';
        label = 'Done';
        break;
      default:
        badgeClass = 'badge-neutral';
        label = status.replace(/_/g, ' ');
    }

    return `<span class="badge ${badgeClass}">${label}</span>`;
  },

  // ── Empty State Component ────────────────────────────────────────────────
  emptyState({ icon = 'bed', text = 'No items found', actionHtml = '' }) {
    return `
      <div class="empty-state">
        <div class="empty-state-icon">${this.getIcon(icon, 36)}</div>
        <div class="empty-state-title">${text}</div>
        ${actionHtml ? `<div class="empty-state-action">${actionHtml}</div>` : ''}
      </div>
    `;
  },

  // ── Loading Skeletons ────────────────────────────────────────────────────
  skeletonTable(rows = 5, cols = 6) {
    let rowsHtml = '';
    for (let i = 0; i < rows; i++) {
      rowsHtml += '<tr>';
      for (let j = 0; j < cols; j++) {
        const width = j === 0 ? '70%' : (j === cols - 1 ? '50%' : '85%');
        rowsHtml += `<td><div class="skeleton skeleton-text" style="width: ${width};"></div></td>`;
      }
      rowsHtml += '</tr>';
    }
    return rowsHtml;
  },

  skeletonCards(count = 4) {
    let html = '';
    for (let i = 0; i < count; i++) {
      html += `
        <div class="kpi-card">
          <div style="width:100%;">
            <div class="skeleton skeleton-text" style="width:40%; height:12px;"></div>
            <div class="skeleton skeleton-text" style="width:65%; height:28px; margin: 8px 0;"></div>
            <div class="skeleton skeleton-text" style="width:50%; height:12px;"></div>
          </div>
        </div>
      `;
    }
    return html;
  },

  // ── Form Validation & Focus ──────────────────────────────────────────────
  validateForm(formEl) {
    let isValid = true;
    let firstInvalid = null;

    // Reset previous errors
    formEl.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    formEl.querySelectorAll('.form-error-msg').forEach(el => el.remove());

    const fields = formEl.querySelectorAll('input[required], select[required], textarea[required]');
    fields.forEach(field => {
      const val = field.value ? field.value.trim() : '';
      let error = null;

      if (!val) {
        error = 'This field is required';
      } else if (field.type === 'email' && !val.includes('@')) {
        error = 'Please enter a valid email address';
      } else if (field.hasAttribute('minlength') && val.length < parseInt(field.getAttribute('minlength'))) {
        error = `Must be at least ${field.getAttribute('minlength')} characters`;
      }

      if (error) {
        isValid = false;
        field.classList.add('is-invalid');
        const errDiv = document.createElement('div');
        errDiv.className = 'form-error-msg';
        errDiv.textContent = error;
        field.parentNode.appendChild(errDiv);

        if (!firstInvalid) firstInvalid = field;
      }
    });

    if (firstInvalid) {
      firstInvalid.focus();
    }

    return isValid;
  },

  // ── Debounce Utility ───────────────────────────────────────────────────────
  debounce(fn, delay = 250) {
    let timer = null;
    return function (...args) {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        fn.apply(this, args);
      }, delay);
    };
  },
};

// Check for flash toast in sessionStorage (e.g. from redirect)
window.addEventListener('DOMContentLoaded', () => {
  const flash = sessionStorage.getItem('flash_toast');
  if (flash) {
    sessionStorage.removeItem('flash_toast');
    try {
      const parsed = JSON.parse(flash);
      setTimeout(() => UI.toast(parsed.message, parsed.type || 'info'), 150);
    } catch (e) {}
  }
});

// Escape key listener closes any open modal or drawer
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    UI.closeModal();
    UI.closeDrawer();
  }
});

// Global Checkout Success Modal with full details and direct invoice download
window.showCheckoutSuccessModal = (res, rmNum) => {
  const roomLabel = rmNum || (res.room ? (res.room.number || res.room) : 'N/A');
  const guestName = (res.guest && (res.guest.full_name || `${res.guest.first_name || ''} ${res.guest.last_name || ''}`.trim())) || 'Guest';
  const confNumber = res.confirmation_number || ('Res #' + res.id);
  const totalPaid = parseFloat(res.total_paid != null ? res.total_paid : (res.total_charges || 0));
  const totalCharges = parseFloat(res.total_charges != null ? res.total_charges : totalPaid);
  const token = (typeof API !== 'undefined' && API.getToken()) || '';

  const contentHtml = `
    <div style="text-align: center; padding: 8px 4px 6px;">
      <!-- Big Success Icon -->
      <div style="width: 64px; height: 64px; border-radius: 50%; background: #ECFDF5; border: 2.5px solid #10B981; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 14px;">
        <svg style="width: 36px; height: 36px; color: #059669;" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h3 style="font-size: 20px; font-weight: 700; color: #111827; margin: 0 0 4px 0;">Check-Out Completed!</h3>
      <p style="font-size: 13px; color: #4B5563; margin: 0 0 16px 0;">
        Room <strong style="color: #111827;">${roomLabel}</strong> is now vacant &amp; marked as <span class="badge badge-warning" style="font-size: 11px; padding: 2px 6px;">DIRTY</span> for housekeeping turnover.
      </p>

      <!-- Stay & Billing Details Card -->
      <div class="card" style="text-align: left; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 16px; margin-bottom: 18px; font-size: 13px;">
        <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #E5E7EB; padding-bottom: 8px; margin-bottom: 8px;">
          <span style="color: #6B7280;">Guest Name:</span>
          <strong style="color: #111827;">${guestName}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #E5E7EB; padding-bottom: 8px; margin-bottom: 8px;">
          <span style="color: #6B7280;">Booking Confirmation:</span>
          <span class="font-mono font-bold" style="color: #111827;">${confNumber}</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #E5E7EB; padding-bottom: 8px; margin-bottom: 8px;">
          <span style="color: #6B7280;">Room Assigned:</span>
          <span class="font-mono font-bold">Room ${roomLabel}</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #E5E7EB; padding-bottom: 8px; margin-bottom: 8px;">
          <span style="color: #6B7280;">Stay Dates:</span>
          <span>${formatDate(res.check_in_date)} &rarr; ${formatDate(res.check_out_date)} (${res.nights || 1} nights)</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-bottom: 1px dashed #E5E7EB; padding-bottom: 8px; margin-bottom: 8px;">
          <span style="color: #6B7280;">Total Charges:</span>
          <span class="font-mono font-bold">${formatCurrency(totalCharges)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding-top: 2px;">
          <span style="color: #6B7280;">Folio Settlement:</span>
          <span style="color: #059669; font-weight: 700;">
            ✓ Paid in Full (${formatCurrency(totalPaid)}) · ₹0.00 Due
          </span>
        </div>
      </div>

      <!-- Action Buttons -->
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <a href="/api/reservations/${res.id}/invoice.pdf?token=${encodeURIComponent(token)}" target="_blank" class="btn btn-primary btn-md" style="justify-content: center; font-weight: 600; font-size: 14px; background: #2563EB; border-color: #2563EB; display: flex; align-items: center; gap: 6px; padding: 10px 16px;">
          📄 Download / Print Tax Invoice (PDF)
        </a>
        <button class="btn btn-secondary btn-md" onclick="UI.closeModal();" style="justify-content: center; font-weight: 500;">
          Done / Close
        </button>
      </div>
    </div>
  `;

  UI.modal({
    title: `Check-Out Summary · Room ${roomLabel}`,
    contentHtml: contentHtml,
    footerHtml: '',
  });
};

window.UI = UI;
