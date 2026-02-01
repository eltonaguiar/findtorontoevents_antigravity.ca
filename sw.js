// Service Worker to strip query parameters from JS/CSS requests
self.addEventListener('fetch', function(event) {
  const url = new URL(event.request.url);
  
  // Strip query parameters from _next static assets
  if (url.pathname.includes('/_next/static/') || url.pathname.includes('/next/_next/static/')) {
    if (url.search) {
      url.search = '';
      event.respondWith(fetch(url.toString()));
      return;
    }
  }
  
  event.respondWith(fetch(event.request));
});

self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(self.clients.claim());
});
