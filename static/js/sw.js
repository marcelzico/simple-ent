// static/js/sw.js
const CACHE_NAME = 'medzone-chat-v1';
const urlsToCache = [
    '/',
    '/static/css/',
    '/static/js/',
    '/static/images/',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                return response || fetch(event.request);
            }
        )
    );
});

self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Sync offline messages when online
    if ('indexedDB' in window) {
        const offlineStorage = await import('./offline-storage.js');
        await offlineStorage.syncPendingMessages();
    }
}