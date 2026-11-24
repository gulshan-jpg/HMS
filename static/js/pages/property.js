/**
 * CheckinOS - Property Management View
 * Manages Hotel Profile, Rate Plans, Tax Engine, Staff Team, Email Templates, Backups, and Audit.
 */

window.Pages = window.Pages || {};

window.Pages.Property = {
  currentTab: 'hotel',

  async render(container) {
    container.innerHTML = `
      <div class="page-header" style="margin-bottom:16px;">
        <div>
          <h1 class="page-title">Property Configuration</h1>
          <div class="page-header-desc">Manage hotel metadata, commercial rate plans, tax engine, staff accounts, and data safety.</div>
        </div>
      </div>

      <!-- Property Tab Bar -->
      <div class="segmented-control" id="property-tabs-bar" style="margin-bottom: 20px; overflow-x:auto;">
        <button class="segmented-btn active" data-tab="hotel">Hotel Profile</button>
        <button class="segmented-btn" data-tab="rate_plans">Rate Plans</button>
        <button class="segmented-btn" data-tab="taxes">Tax Engine</button>
        <button class="segmented-btn" data-tab="team">Staff & Team</button>
        <button class="segmented-btn" data-tab="emails">Email Templates</button>
        <button class="segmented-btn" data-tab="backups">Data Safety & Backups</button>
        <button class="segmented-btn" data-tab="audit">Audit Log</button>
        <button class="segmented-btn" data-tab="trash">Trash & Restore</button>
      </div>

      <!-- Tab Content Area -->
      <div id="property-tab-content">
        <div class="card" style="padding: 24px;">
          <div class="skeleton" style="height: 180px; width: 100%;"></div>
        </div>
      </div>
    `;

    this.bindEvents(container);
    await this.renderActiveTab();
  },

  bindEvents(container) {
    container.querySelectorAll('#property-tabs-bar .segmented-btn').forEach(btn => {
      btn.onclick = () => {
        container.querySelectorAll('#property-tabs-bar .segmented-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentTab = btn.getAttribute('data-tab');
        this.renderActiveTab();
      };
    });
  },

  async renderActiveTab() {
    const tabEl = document.getElementById('property-tab-content');
    if (!tabEl) return;

    tabEl.innerHTML = '<div class="card" style="padding:24px;"><div class="skeleton" style="height:160px;"></div></div>';

    if (this.currentTab === 'hotel') {
      await window.Pages.Settings.renderHotelTab(tabEl);
    } else if (this.currentTab === 'rate_plans') {
      await window.Pages.Settings.renderRatePlansTab(tabEl);
    } else if (this.currentTab === 'taxes') {
      await window.Pages.Settings.renderTaxesTab(tabEl);
    } else if (this.currentTab === 'team') {
      await window.Pages.Settings.renderTeamTab(tabEl);
    } else if (this.currentTab === 'emails') {
      await window.Pages.Settings.renderEmailsTab(tabEl);
    } else if (this.currentTab === 'backups') {
      await window.Pages.Settings.renderBackupsTab(tabEl);
    } else if (this.currentTab === 'audit') {
      await window.Pages.Settings.renderAuditTab(tabEl);
    } else if (this.currentTab === 'trash') {
      await window.Pages.Settings.renderTrashTab(tabEl);
    }
  }
};
