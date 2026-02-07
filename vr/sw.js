/**
 * VR Hub Service Worker
 * Basic offline support
 */

const CACHE_NAME = 'vr-hub-v1';
const urlsToCache = [
  '/vr/',
  '/vr/index.html',
  '/vr/controller-support.js',
  '/vr/quick-wins.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) return response;
        return fetch(event.request);
      })
  );
});
