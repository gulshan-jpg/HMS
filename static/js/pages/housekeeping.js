/**
 * Hotel OS - Housekeeping & Maintenance Operations
 * Kanban-Lite Board (Pending, In Progress, Done) with status advancing and turnover task creation.
 */

window.Pages = window.Pages || {};

window.Pages.Housekeeping = {
  priorityFilter: 'all',
  tasks: [],

  async render(container) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Housekeeping & Maintenance</h1>
          <div class="page-header-desc">Turnover cleaning, room inspections, and maintenance work orders.</div>
        </div>
        <div class="toolbar-group">
          <button class="btn btn-secondary btn-md" id="mobile-hk-link-btn">
            <svg style="width:14px; height:14px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.5 1.5H8.25A2.25 2.25 0 0 0 6 3.75v16.5a2.25 2.25 0 0 0 2.25 2.25h7.5A2.25 2.25 0 0 0 18 20.25V3.75a2.25 2.25 0 0 0-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" /></svg>
            <span>Staff Mobile Link</span>
          </button>
          <button class="btn btn-primary btn-md" id="new-task-top-btn">
            ${UI.getIcon('plus', 16)} New Work Order
          </button>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="toolbar-container card" style="padding: var(--space-3) var(--space-4);">
        <div class="toolbar-group">
          <label style="font-size: 12px; font-weight: 500; color: var(--text-secondary);">Priority:</label>
          <select id="task-prio-filter" class="select-field" style="width: 140px; height: 32px;">
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div class="toolbar-group">
          <button class="btn btn-secondary btn-sm" id="refresh-tasks-btn">
            ${UI.getIcon('dashboard', 14)} Refresh Board
          </button>
        </div>
      </div>

      <!-- Kanban 3-Column Board -->
      <div class="kanban-board" id="housekeeping-board">
        <!-- Pending Col -->
        <div class="kanban-col" id="col-pending">
          <div class="kanban-header">
            <span class="kanban-title">${UI.getIcon('housekeeping', 16)} Pending Dispatch</span>
            <span class="badge badge-warning" id="count-pending">0</span>
          </div>
          <div class="kanban-cards-list" id="cards-pending"></div>
        </div>

        <!-- In Progress Col -->
        <div class="kanban-col" id="col-in-progress">
          <div class="kanban-header">
            <span class="kanban-title">${UI.getIcon('bed', 16)} Cleaning in Progress</span>
            <span class="badge badge-info" id="count-in-progress">0</span>
          </div>
          <div class="kanban-cards-list" id="cards-in-progress"></div>
        </div>

        <!-- Done Col -->
        <div class="kanban-col" id="col-done">
          <div class="kanban-header">
            <span class="kanban-title">${UI.getIcon('check', 16)} Completed & Clean</span>
            <span class="badge badge-success" id="count-done">0</span>
          </div>
          <div class="kanban-cards-list" id="cards-done"></div>
        </div>
      </div>
    `;

    this.bindEvents(container);
    await this.fetchTasks();
  },

  bindEvents(container) {
    const hkLinkBtn = container.querySelector('#mobile-hk-link-btn');
    if (hkLinkBtn) {
      hkLinkBtn.onclick = async () => {
        try {
          UI.toast('Generating secure staff link...', 'info');
          const res = await API.post('/api/housekeeping/generate-share-token');
          const fullUrl = window.location.origin + res.share_url;
          UI.modal({
            title: 'Housekeeping Mobile Staff Link',
            contentHtml: `
              <div style="display:flex; flex-direction:column; gap:16px;">
                <p style="font-size:13px; color:#4B5563; line-height:1.5;">
                  Share this temporary link with housekeeping and cleaning staff. It allows them to mark rooms clean/dirty and log maintenance issues from their mobile phones without needing an account password.
                </p>
                <div style="display:flex; gap:8px;">
                  <input type="text" id="share-link-input" class="form-input font-mono" value="${fullUrl}" readonly style="flex:1; font-size:12px;" />
                  <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText('${fullUrl}'); UI.toast('Copied to clipboard!', 'success');">
                    Copy Link
                  </button>
                </div>
                <div style="font-size:11px; color:#6B7280;">
                  Expires in 24 hours. Single-tap status changes and real-time synchronization.
                </div>
              </div>
            `,
            footerHtml: `
              <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Close</button>
              <button class="btn btn-primary btn-md" onclick="window.open('${fullUrl}', '_blank')">Open Mobile View</button>
            `
          });
        } catch (e) {
          UI.toast(e.message, 'error');
        }
      };
    }

    const newBtn = container.querySelector('#new-task-top-btn');
    if (newBtn) newBtn.onclick = () => window.openNewTaskModal();

    const refreshBtn = container.querySelector('#refresh-tasks-btn');
    if (refreshBtn) refreshBtn.onclick = () => this.fetchTasks();

    const prioFilter = container.querySelector('#task-prio-filter');
    if (prioFilter) {
      prioFilter.onchange = () => {
        this.priorityFilter = prioFilter.value;
        this.renderKanbanColumns();
      };
    }
  },

  async fetchTasks() {
    try {
      const res = await API.get('/api/housekeeping', { limit: 100 });
      this.tasks = res.items;
      this.renderKanbanColumns();
    } catch (e) {
      UI.toast(`Failed to load housekeeping tasks: ${e.message}`, 'error');
    }
  },

  renderKanbanColumns() {
    let filtered = this.tasks;
    if (this.priorityFilter !== 'all') {
      filtered = filtered.filter(t => t.priority.toLowerCase() === this.priorityFilter.toLowerCase());
    }

    const pending = filtered.filter(t => t.status === 'pending');
    const inProgress = filtered.filter(t => t.status === 'in_progress');
    const done = filtered.filter(t => t.status === 'done');

    const elPending = document.getElementById('count-pending');
    const elInProgress = document.getElementById('count-in-progress');
    const elDone = document.getElementById('count-done');
    if (elPending) elPending.textContent = pending.length;
    if (elInProgress) elInProgress.textContent = inProgress.length;
    if (elDone) elDone.textContent = done.length;

    const renderCard = (task) => `
      <div class="kanban-card" data-task-id="${task.id}">
        <div class="kanban-card-top">
          <span class="kanban-room-num">Room ${task.room ? task.room.number : '—'}</span>
          ${UI.statusBadge(task.priority)}
        </div>
        <div class="kanban-card-title">${task.task_type.replace(/_/g, ' ').toUpperCase()}</div>
        ${task.notes ? `<div class="kanban-card-notes">${task.notes}</div>` : ''}
        <div class="kanban-card-footer">
          <span class="kanban-assignee">
            ${task.assigned_to ? `Assigned: <strong>${task.assigned_to}</strong>` : '<em>Unassigned</em>'}
          </span>
          <span style="font-size: 11px; color: var(--text-tertiary);">
            ${formatRelativeTime(task.created_at)}
          </span>
        </div>
        <div style="margin-top: 8px; display: flex; justify-content: flex-end; gap: 6px;">
          ${task.status === 'pending' ? `
            <button class="btn btn-secondary btn-sm advance-task-btn" data-id="${task.id}" data-target="in_progress">
              Start Cleaning &rarr;
            </button>
          ` : ''}
          ${task.status === 'in_progress' ? `
            <button class="btn btn-primary btn-sm advance-task-btn" data-id="${task.id}" data-target="done">
              ${UI.getIcon('check', 14)} Mark Complete
            </button>
          ` : ''}
          ${task.status === 'done' ? `
            <span style="font-size: 11px; color: var(--success); font-weight: 500;">Ready for Guest</span>
          ` : ''}
        </div>
      </div>
    `;

    document.getElementById('cards-pending').innerHTML = pending.length === 0
      ? '<div style="font-size: 12px; color: var(--text-tertiary); text-align: center; padding: 24px;">No pending cleanings</div>'
      : pending.map(renderCard).join('');

    document.getElementById('cards-in-progress').innerHTML = inProgress.length === 0
      ? '<div style="font-size: 12px; color: var(--text-tertiary); text-align: center; padding: 24px;">No tasks in progress</div>'
      : inProgress.map(renderCard).join('');

    document.getElementById('cards-done').innerHTML = done.length === 0
      ? '<div style="font-size: 12px; color: var(--text-tertiary); text-align: center; padding: 24px;">No finished tasks today</div>'
      : done.map(renderCard).join('');

    // Wire advance buttons
    document.querySelectorAll('.advance-task-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const taskId = btn.getAttribute('data-id');
        const targetStatus = btn.getAttribute('data-target');

        try {
          btn.disabled = true;
          await API.patch(`/api/housekeeping/${taskId}/status`, { status: targetStatus });
          UI.toast(targetStatus === 'done' ? 'Task marked complete. Room inventory released as available!' : 'Task started.', 'success');
          await this.fetchTasks();
          if (window.Pages.Dashboard.refresh) window.Pages.Dashboard.refresh();
        } catch (err) {
          UI.toast(err.message, 'error');
          btn.disabled = false;
        }
      };
    });
  },
};

// ── New Housekeeping Task Modal ────────────────────────────────────────────
window.openNewTaskModal = async (preSelectedRoomId = null) => {
  let rooms = [];
  try {
    const res = await API.get('/api/rooms', { limit: 100 });
    rooms = res.items;
  } catch (e) {
    UI.toast('Failed to load room inventory', 'error');
    return;
  }

  const contentHtml = `
    <form id="new-task-form">
      <div class="form-group">
        <label class="form-label" for="task-room">Room Number <span class="required-mark">*</span></label>
        <select id="task-room" class="select-field" required>
          <option value="">Select target room...</option>
          ${rooms.map(r => `
            <option value="${r.id}" ${preSelectedRoomId && parseInt(preSelectedRoomId) === r.id ? 'selected' : ''}>
              Room ${r.number} (${r.room_type ? r.room_type.name : 'Standard'}) — [Status: ${r.status}]
            </option>
          `).join('')}
        </select>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);">
        <div class="form-group">
          <label class="form-label" for="task-type">Task Category <span class="required-mark">*</span></label>
          <select id="task-type" class="select-field" required>
            <option value="checkout_clean">Checkout Turnover Clean</option>
            <option value="stayover_clean">Stayover Daily Refresh</option>
            <option value="deep_clean">Deep Clean / Sanitation</option>
            <option value="inspection">Supervisor Inspection</option>
            <option value="maintenance_repair">Maintenance Repair / HVAC</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="task-prio">Priority Level <span class="required-mark">*</span></label>
          <select id="task-prio" class="select-field" required>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label" for="task-assignee">Assigned Housekeeper / Tech</label>
        <input type="text" id="task-assignee" class="input-field" placeholder="e.g. Maria Santos, Jack Miller" />
      </div>

      <div class="form-group">
        <label class="form-label" for="task-notes">Special Instructions</label>
        <textarea id="task-notes" class="textarea-field" placeholder="Balcony windows cleaning, change HVAC air filter..."></textarea>
      </div>
    </form>
  `;

  const footerHtml = `
    <button class="btn btn-secondary btn-md" onclick="UI.closeModal()">Cancel</button>
    <button class="btn btn-primary btn-md" id="submit-new-task-btn">Dispatch Work Order</button>
  `;

  const panel = UI.modal({
    title: 'Schedule Housekeeping / Work Order',
    contentHtml,
    footerHtml,
  });

  panel.querySelector('#submit-new-task-btn').onclick = async () => {
    const form = panel.querySelector('#new-task-form');
    if (!UI.validateForm(form)) return;

    const payload = {
      room_id: parseInt(panel.querySelector('#task-room').value),
      task_type: panel.querySelector('#task-type').value,
      priority: panel.querySelector('#task-prio').value,
      assigned_to: panel.querySelector('#task-assignee').value.trim() || undefined,
      notes: panel.querySelector('#task-notes').value.trim() || undefined,
    };

    try {
      await API.post('/api/housekeeping', payload);
      UI.toast('Work order dispatched successfully.', 'success');
      UI.closeModal();

      if (window.Pages.Housekeeping.fetchTasks) window.Pages.Housekeeping.fetchTasks();
      if (window.Pages.Dashboard.refresh) window.Pages.Dashboard.refresh();
      if (window.Pages.Rooms.loadInitialData) window.Pages.Rooms.loadInitialData();
    } catch (e) {
      UI.toast(e.message, 'error');
    }
  };
};
