/* Service worker: caches the dashboard shell so the app opens instantly and
   shows a friendly state when the Pi can't be reached. Live data (API,
   socket.io, uploads) always goes to the network. */
const VERSION = 'ledmatrix-v2.0.4';
const SHELL = [
  '/',
  '/static/css/styles.css?v=2.0.4',
  '/static/js/app.js?v=2.0.4',
  '/static/vendor/socket.io.min.js',
  '/static/fonts/doto-latin-900-normal.woff2',
  '/static/fonts/doto-latin-700-normal.woff2',
  '/static/icons/icon-192.png',
  '/manifest.webmanifest',
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/socket.io')) return;

  if (req.mode === 'navigate') {
    // Network first for the page so state is fresh; cached copy when offline
    event.respondWith(
      fetch(req).then(res => {
        const copy = res.clone();
        caches.open(VERSION).then(c => c.put('/', copy));
        return res;
      }).catch(() => caches.match('/'))
    );
    return;
  }

  // Static files: cache first, refresh in the background
  event.respondWith(
    caches.match(req).then(cached => {
      const network = fetch(req).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
        return res;
      }).catch(() => cached);
      return cached || network;
    })
  );
});
