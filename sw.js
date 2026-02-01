// Service Worker - pass through all requests (do NOT strip ?v= from _next assets)
// Stripping ?v= caused "Preloaded but not used" and stale chunk loads; see FIX_SUMMARY.md / fix-toronto-events skill.
self.addEventListener('fetch', function(event) {
  event.respondWith(fetch(event.request));
});

self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(self.clients.claim());
});
