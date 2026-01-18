"""
Mobile app routes for Elite Sales
Serves mobile Progressive Web App views
"""

from flask import Blueprint, render_template, jsonify, request, send_from_directory
from flask_login import login_required, current_user
import json

mobile_bp = Blueprint('mobile', __name__, url_prefix='/mobile')


@mobile_bp.route('/')
@mobile_bp.route('/app')
@login_required
def elite_sales_app():
    """
    Main Elite Sales mobile app
    Single page application for field sales team
    """
    import sqlite3
    from pathlib import Path

    # Get salesperson ID from user profile or query
    salesperson_id = getattr(current_user, 'salesperson_id', None)

    # If no salesperson_id, try to look it up by email
    if not salesperson_id:
        try:
            db_path = Path(__file__).parent.parent.parent.parent / 'data' / 'hailtracker_crm.db'
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM salespeople WHERE email = ?",
                (current_user.email,)
            )
            row = cursor.fetchone()
            if row:
                salesperson_id = row['id']
            conn.close()
        except Exception:
            pass

    # Default to 1 if not found
    if not salesperson_id:
        salesperson_id = 1

    app_data = {
        'salesperson_id': salesperson_id,
        'user_name': getattr(current_user, 'full_name', None) or getattr(current_user, 'name', None) or current_user.email,
        'user_email': current_user.email
    }

    return render_template(
        'mobile/elite_sales_app.html',
        app_data=json.dumps(app_data)
    )


@mobile_bp.route('/dashboard')
@login_required
def dashboard():
    """Mobile dashboard redirect to main app"""
    return render_template('mobile/elite_sales_app.html', initial_view='dashboard')


@mobile_bp.route('/leads')
@login_required
def leads():
    """Mobile leads view"""
    return render_template('mobile/elite_sales_app.html', initial_view='leads')


@mobile_bp.route('/route')
@login_required
def route():
    """Mobile route view"""
    return render_template('mobile/elite_sales_app.html', initial_view='route')


@mobile_bp.route('/estimate')
@login_required
def estimate():
    """Mobile estimate view"""
    return render_template('mobile/elite_sales_app.html', initial_view='estimate')


@mobile_bp.route('/scripts')
@login_required
def scripts():
    """Mobile scripts view"""
    return render_template('mobile/elite_sales_app.html', initial_view='scripts')


@mobile_bp.route('/leaderboard')
@login_required
def leaderboard():
    """Mobile leaderboard view"""
    return render_template('mobile/elite_sales_app.html', initial_view='leaderboard')


@mobile_bp.route('/competitors')
@login_required
def competitors():
    """Mobile competitors view"""
    return render_template('mobile/elite_sales_app.html', initial_view='competitors')


@mobile_bp.route('/settings')
@login_required
def settings():
    """Mobile settings view"""
    return render_template('mobile/elite_sales_app.html', initial_view='settings')


# PWA Support Routes
@mobile_bp.route('/manifest.json')
def manifest():
    """
    PWA manifest file
    """
    manifest_data = {
        "name": "Elite Sales - HailTracker Pro",
        "short_name": "Elite Sales",
        "description": "Mobile sales intelligence app for PDR field teams",
        "start_url": "/mobile/app",
        "display": "standalone",
        "background_color": "#1a1a2e",
        "theme_color": "#00d4ff",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/mobile/icons/icon-72.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-96.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-128.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-144.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-152.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-192-maskable.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/mobile/icons/icon-384.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/mobile/icons/icon-512-maskable.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable"
            }
        ],
        "categories": ["business", "productivity"],
        "shortcuts": [
            {
                "name": "Quick Lead",
                "short_name": "Lead",
                "description": "Capture a new lead quickly",
                "url": "/mobile/leads?action=new",
                "icons": [{"src": "/static/mobile/icons/shortcut-lead.png", "sizes": "96x96"}]
            },
            {
                "name": "My Route",
                "short_name": "Route",
                "description": "View today's route",
                "url": "/mobile/route",
                "icons": [{"src": "/static/mobile/icons/shortcut-route.png", "sizes": "96x96"}]
            }
        ]
    }

    return jsonify(manifest_data)


@mobile_bp.route('/sw.js')
def service_worker():
    """
    Service worker for offline support
    """
    sw_code = '''
// Elite Sales Service Worker
const CACHE_NAME = 'elite-sales-v1';
const OFFLINE_URL = '/mobile/offline';

const PRECACHE_URLS = [
    '/mobile/app',
    '/static/mobile/css/elite_sales.css',
    '/static/mobile/js/elite_sales_app.js',
    '/static/mobile/icons/icon-192.png'
];

// Install event - cache essential files
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(name => name !== CACHE_NAME)
                        .map(name => caches.delete(name))
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip API requests (let them fail if offline)
    if (event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Clone and cache successful responses
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(event.request, responseClone));
                }
                return response;
            })
            .catch(() => {
                // Fallback to cache
                return caches.match(event.request)
                    .then(response => response || caches.match(OFFLINE_URL));
            })
    );
});

// Background sync for offline data
self.addEventListener('sync', event => {
    if (event.tag === 'sync-leads') {
        event.waitUntil(syncLeads());
    }
});

async function syncLeads() {
    // Get pending leads from IndexedDB and sync
    console.log('Syncing offline leads...');
}

// Push notifications
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};

    const options = {
        body: data.body || 'New notification',
        icon: '/static/mobile/icons/icon-192.png',
        badge: '/static/mobile/icons/badge-72.png',
        vibrate: [100, 50, 100],
        data: data.url || '/mobile/app',
        actions: data.actions || []
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Elite Sales', options)
    );
});

// Notification click
self.addEventListener('notificationclick', event => {
    event.notification.close();

    event.waitUntil(
        clients.matchAll({ type: 'window' })
            .then(clientList => {
                // Focus existing window or open new
                for (const client of clientList) {
                    if (client.url === event.notification.data && 'focus' in client) {
                        return client.focus();
                    }
                }
                return clients.openWindow(event.notification.data);
            })
    );
});
'''

    from flask import Response
    return Response(sw_code, mimetype='application/javascript')


@mobile_bp.route('/offline')
def offline():
    """
    Offline fallback page
    """
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - Elite Sales</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 20px;
                text-align: center;
            }
            .offline-icon {
                font-size: 64px;
                margin-bottom: 20px;
            }
            h1 {
                font-size: 24px;
                margin-bottom: 10px;
            }
            p {
                color: rgba(255,255,255,0.7);
                margin-bottom: 30px;
            }
            .btn {
                background: linear-gradient(135deg, #00d4ff, #0099cc);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="offline-icon">📡</div>
        <h1>You're Offline</h1>
        <p>Check your internet connection and try again.</p>
        <button class="btn" onclick="location.reload()">Try Again</button>
    </body>
    </html>
    '''
