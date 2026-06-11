const CACHE_NAME = 'verte-v1';
const ASSETS = [
  '/auth.html',
  // Add your other frontend file paths here (e.g., '/style.css', '/app.js')
];

// Install the Service Worker and cache core files
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

// Serve cached assets when offline, otherwise fetch over network
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      return cachedResponse || fetch(e.request);
    })
  );
});