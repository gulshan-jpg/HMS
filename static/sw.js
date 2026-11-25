/* Service Worker for CheckinOS Offline-Tolerant Front Desk */
const CACHE_NAME = 'checkinos-v4.3.0';
const STATIC_ASSETS = [
  '/',
  '/app',
  '/login',
  '/demo',
  '/static/css/style.css?v=4.3.0',
  '/static/js/api.js?v=4.3.0',
  '/static/js/ui.js?v=4.3.0',
  '/static/js/router.js?v=4.3.0',
  '/static/js/pages/dashboard.js?v=4.3.0',
  '/static/js/pages/reservations.js?v=4.3.0',
  '/static/js/pages/rooms.js?v=4.3.0',
  '/static/js/pages/rate_calendar.js?v=4.3.0',
  '/static/js/pages/timeline.js?v=4.3.0',
  '/static/js/pages/night_audit.js?v=4.3.0',
  '/static/js/pages/guests.js?v=4.3.0',
  '/static/js/pages/housekeeping.js?v=4.3.0',
  '/static/js/pages/billing.js?v=4.3.0',
  '/static/js/pages/channels.js?v=4.3.0',
  '/static/js/pages/property.js?v=4.3.0',
  '/static/js/pages/policies.js?v=4.3.0',
  '/static/js/pages/settings.js?v=4.3.0',
  '/static/js/app.js?v=4.3.0',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => console.warn('Pre-cache partial', err));
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Stale-while-revalidate for static scripts and stylesheets
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => {
        const fetchPromise = fetch(req).then((networkResponse) => {
          if (networkResponse.status === 200) {
            const respClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, respClone));
          }
          return networkResponse;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // Network-first with cache fallback for pages and API endpoints
  event.respondWith(
    fetch(req)
      .then((networkResponse) => {
        if (networkResponse.status === 200) {
          const respClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(req, respClone);
          });
        }
        return networkResponse;
      })
      .catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        if (req.headers.get('accept') && req.headers.get('accept').includes('text/html')) {
          return caches.match('/app');
        }
        return new Response(JSON.stringify({ error: "Offline mode active. Data loaded from device cache." }), {
          headers: { 'Content-Type': 'application/json' }
        });
      })
  );
});
