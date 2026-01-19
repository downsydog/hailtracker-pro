/**
 * HailTracker Pro - Service Worker
 * Handles offline caching, background sync, and push notifications
 */

const CACHE_VERSION = 'hailtracker-v1.0.0';
const CACHE_STATIC = `${CACHE_VERSION}-static`;
const CACHE_DYNAMIC = `${CACHE_VERSION}-dynamic`;
const CACHE_API = `${CACHE_VERSION}-api`;

// Files to cache immediately on install
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/css/mobile.css',
  '/static/css/pwa.css',
  '/static/js/app.js',
  '/static/js/offline.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/offline'
];

// API endpoints to cache for offline use
const API_CACHE_ROUTES = [
  '/api/radars',
  '/api/stats',
  '/api/events'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');

  event.waitUntil(
    caches.open(CACHE_STATIC)
      .then(cache => {
        console.log('[Service Worker] Caching static assets');
        // Cache what we can, don't fail if some assets are missing
        return Promise.allSettled(
          STATIC_ASSETS.map(url =>
            cache.add(url).catch(err => {
              console.log(`[Service Worker] Could not cache: ${url}`, err);
            })
          )
        );
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');

  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames
            .filter(name => name.startsWith('hailtracker-') &&
                          name !== CACHE_STATIC &&
                          name !== CACHE_DYNAMIC &&
                          name !== CACHE_API)
            .map(name => {
              console.log('[Service Worker] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Handle API requests differently
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Handle static assets and pages
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          // Return cached version
          return cachedResponse;
        }

        // Fetch from network and cache
        return fetch(request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200) {
              return response;
            }

            // Don't cache responses from external domains
            if (!url.origin.includes(self.location.origin)) {
              return response;
            }

            // Clone response (can only read once)
            const responseToCache = response.clone();

            caches.open(CACHE_DYNAMIC)
              .then(cache => {
                cache.put(request, responseToCache);
              });

            return response;
          })
          .catch(() => {
            // Offline fallback
            if (request.destination === 'document') {
              return caches.match('/offline');
            }
            // Return empty response for other resources
            return new Response('', { status: 503, statusText: 'Offline' });
          });
      })
  );
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
  try {
    // Try network first
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_API);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Network failed, try cache
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      console.log('[Service Worker] Serving API from cache:', request.url);
      // Add header to indicate cached response
      const headers = new Headers(cachedResponse.headers);
      headers.set('X-From-Cache', 'true');
      return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers: headers
      });
    }

    // Return error response
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'Data not available in cache. Please try again when online.',
        offline: true
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Background sync for queued actions
self.addEventListener('sync', event => {
  console.log('[Service Worker] Background sync:', event.tag);

  if (event.tag === 'sync-data') {
    event.waitUntil(syncOfflineData());
  }

  if (event.tag === 'sync-reports') {
    event.waitUntil(syncOfflineReports());
  }
});

// Sync offline data when connection restored
async function syncOfflineData() {
  try {
    const db = await openIndexedDB();
    const tx = db.transaction('pendingActions', 'readwrite');
    const store = tx.objectStore('pendingActions');
    const actions = await getAllFromStore(store);

    for (const action of actions) {
      try {
        await fetch(action.url, {
          method: action.method,
          headers: action.headers,
          body: action.body
        });

        // Remove from queue on success
        store.delete(action.id);
        console.log('[Service Worker] Synced action:', action.id);
      } catch (error) {
        console.error('[Service Worker] Sync failed for action:', action.id, error);
      }
    }

    await tx.complete;
  } catch (error) {
    console.error('[Service Worker] Sync failed:', error);
  }
}

// Sync offline reports
async function syncOfflineReports() {
  try {
    const db = await openIndexedDB();
    const tx = db.transaction('offlineReports', 'readwrite');
    const store = tx.objectStore('offlineReports');
    const reports = await getAllFromStore(store);

    for (const report of reports) {
      try {
        const response = await fetch('/api/reports', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(report.data)
        });

        if (response.ok) {
          store.delete(report.id);
          console.log('[Service Worker] Synced report:', report.id);

          // Notify user
          self.registration.showNotification('Report Synced', {
            body: 'Your offline hail report has been uploaded.',
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/badge-72.png'
          });
        }
      } catch (error) {
        console.error('[Service Worker] Report sync failed:', report.id, error);
      }
    }

    await tx.complete;
  } catch (error) {
    console.error('[Service Worker] Report sync failed:', error);
  }
}

// Push notification handler
self.addEventListener('push', event => {
  console.log('[Service Worker] Push notification received');

  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { body: event.data ? event.data.text() : 'New notification' };
  }

  const title = data.title || 'HailTracker Alert';

  // Determine icon based on notification type
  let icon = '/static/icons/icon-192x192.png';
  let badge = '/static/icons/badge-72x72.png';

  // Use priority to determine notification behavior
  const isHighPriority = data.priority === 'HIGH' || data.priority === 'high';

  const options = {
    body: data.body || 'New notification',
    icon: data.icon || icon,
    badge: data.badge || badge,
    vibrate: isHighPriority ? [200, 100, 200, 100, 200] : [200, 100, 200],
    tag: data.tag || 'pdr-notification',
    renotify: true,
    requireInteraction: isHighPriority,
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/static/icons/view-icon.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/static/icons/dismiss-icon.png'
      }
    ],
    data: {
      url: (data.data && data.data.url) || data.url || '/portal/',
      jobId: data.jobId || (data.data && data.data.jobId),
      notificationId: data.notificationId,
      timestamp: Date.now()
    }
  };

  // Add image if provided (for rich notifications)
  if (data.image) {
    options.image = data.image;
  }

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  // Open the app or focus existing window
  const url = event.notification.data.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // Check if there's already a window open
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// Notification close handler
self.addEventListener('notificationclose', event => {
  console.log('[Service Worker] Notification closed');
});

// Helper: Open IndexedDB
function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('HailTrackerDB', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = event => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains('pendingActions')) {
        db.createObjectStore('pendingActions', { keyPath: 'id', autoIncrement: true });
      }

      if (!db.objectStoreNames.contains('cachedEvents')) {
        const eventsStore = db.createObjectStore('cachedEvents', { keyPath: 'id' });
        eventsStore.createIndex('date', 'event_date', { unique: false });
      }

      if (!db.objectStoreNames.contains('offlineReports')) {
        db.createObjectStore('offlineReports', { keyPath: 'id', autoIncrement: true });
      }

      if (!db.objectStoreNames.contains('settings')) {
        db.createObjectStore('settings', { keyPath: 'key' });
      }
    };
  });
}

// Helper: Get all items from store
function getAllFromStore(store) {
  return new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'update-events') {
    event.waitUntil(updateCachedEvents());
  }
});

// Update cached events periodically
async function updateCachedEvents() {
  try {
    const response = await fetch('/api/events?days=7&limit=100');
    if (response.ok) {
      const cache = await caches.open(CACHE_API);
      cache.put('/api/events?days=7&limit=100', response.clone());
      console.log('[Service Worker] Updated cached events');
    }
  } catch (error) {
    console.log('[Service Worker] Could not update cached events:', error);
  }
}

console.log('[Service Worker] Loaded successfully');
