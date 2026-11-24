/**
 * CheckinOS - Channel Sync View
 * Dedicated management for OTA Ingestion (OYO, Airbnb, Booking.com, Agoda), WhatsApp Alerts, and Webhooks.
 */

window.Pages = window.Pages || {};

window.Pages.Channels = {
  async render(container) {
    container.innerHTML = `
      <div class="page-header" style="margin-bottom:20px;">
        <div>
          <h1 class="page-title">OTA & Channel Sync</h1>
          <div class="page-header-desc">Automated reservation ingestion from OYO, Airbnb, Booking.com, Agoda, Gmail vouchers, and WhatsApp alerts.</div>
        </div>
      </div>

      <div style="display:flex; flex-direction:column; gap:24px; max-width:1100px;">
        <!-- Header & Channel Status Cards -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
          <!-- Gmail & OTA Ingestion Card -->
          <div class="card" style="padding:20px; border:1px solid #E5E7EB; background:#FFFFFF;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:36px; height:36px; border-radius:8px; background:#EFF6FF; color:#2563EB; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px;">
                  OTA
                </div>
                <div>
                  <h4 style="font-size:15px; font-weight:700; margin:0;">OTA Email Voucher Sync</h4>
                  <div style="font-size:11px; color:#6B7280;">Booking.com, Airbnb, OYO, Agoda</div>
                </div>
              </div>
              <span class="badge badge-success" style="font-size:11px; padding:2px 8px;">CONNECTED</span>
            </div>
            <div style="font-size:13px; color:#4B5563; line-height:1.5; margin-bottom:12px;">
              Automatically ingests reservation emails forwarded from <strong>Booking.com, Airbnb, OYO, Agoda, MakeMyTrip</strong>. Extracts confirmation code, stay dates, guest profile, and allocates rooms.
            </div>
            <div style="background:#F9FAFB; padding:10px 12px; border-radius:6px; font-size:11px; font-family:var(--font-mono); color:#374151; border:1px solid #E5E7EB;">
              <strong>Auto-Forward Inbox:</strong> bookings@checkinos.io
            </div>
          </div>

          <!-- WhatsApp Direct Inbound Card -->
          <div class="card" style="padding:20px; border:1px solid #E5E7EB; background:#FFFFFF;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
              <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:36px; height:36px; border-radius:8px; background:#ECFDF5; color:#059669; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px;">
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
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.loadTemplate('booking')" style="font-size:11px; background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE;">
                Booking.com
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.loadTemplate('airbnb')" style="font-size:11px; background:#FFF1F2; color:#E11D48; border-color:#FECDD3;">
                Airbnb
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.loadTemplate('oyo')" style="font-size:11px; background:#FEF2F2; color:#DC2626; border-color:#FECACA;">
                OYO Rooms
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.loadTemplate('agoda')" style="font-size:11px; background:#F0F9FF; color:#0284C7; border-color:#BAE6FD;">
                Agoda
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.loadTemplate('makemytrip')" style="font-size:11px; background:#FFF7ED; color:#EA580C; border-color:#FED7AA;">
                MakeMyTrip
              </button>
              <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.loadTemplate('whatsapp')" style="font-size:11px; background:#ECFDF5; color:#059669; border-color:#A7F3D0;">
                WhatsApp
              </button>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:160px 1fr; gap:12px; margin-bottom:14px;">
            <div>
              <label class="form-label" style="font-size:12px;">Channel</label>
              <select id="channel-sync-select" class="form-select" style="height:38px; font-size:13px;">
                <option value="gmail">Email (Gmail)</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
            </div>
            <div>
              <label class="form-label" style="font-size:12px;">Sender (OTA or Phone)</label>
              <input type="text" id="channel-sender-input" class="form-input" value="customer.service@booking.com" placeholder="e.g. customer.service@booking.com or +91 98765 43210" style="height:38px; font-size:13px;">
            </div>
          </div>

          <div style="margin-bottom:16px;">
            <label class="form-label" style="font-size:12px;">Inbound OTA Message / Email Voucher Body</label>
            <textarea id="channel-raw-text" class="form-input font-mono" rows="6" style="width:100%; font-size:12px; line-height:1.4; padding:10px;">Subject: Booking.com New Reservation #389281729

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
            <button id="channel-execute-btn" class="btn btn-primary btn-md" onclick="window.Pages.Channels.processInboundBooking()" style="height:38px; padding:0 20px;">
              Process & Auto-Create Reservation
            </button>
          </div>

          <div id="channel-result-zone" style="display:none; margin-top:20px;"></div>
        </div>

        <!-- Recent Auto-Synced Reservations Feed -->
        <div class="card" style="padding:24px; border:1px solid #E5E7EB;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h3 style="font-size:16px; font-weight:700; margin:0;">Recent Auto-Synced Inbound Reservations</h3>
            <button class="btn btn-secondary btn-sm" onclick="window.Pages.Channels.refreshSyncFeed()" style="font-size:11px;">
              Refresh Feed
            </button>
          </div>
          <div id="channel-feed-container">
            <div style="padding:20px; text-align:center; color:#6B7280;">Loading auto-synced reservations...</div>
          </div>
        </div>
      </div>
    `;

    await this.refreshSyncFeed();
  },

  loadTemplate(type) {
    const channelSelect = document.getElementById('channel-sync-select');
    const senderInput = document.getElementById('channel-sender-input');
    const textArea = document.getElementById('channel-raw-text');

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
    const channel = document.getElementById('channel-sync-select').value;
    const sender = document.getElementById('channel-sender-input').value.trim();
    const raw_text = document.getElementById('channel-raw-text').value.trim();
    const btn = document.getElementById('channel-execute-btn');
    const zone = document.getElementById('channel-result-zone');

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
    const feedContainer = document.getElementById('channel-feed-container');
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
  }
};
