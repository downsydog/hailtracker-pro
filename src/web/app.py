"""
HailTracker Pro - Flask Web Application

Continental-scale hail tracking platform with:
- Interactive map
- REST API
- Real-time updates
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path FIRST before any src imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, jsonify, request, send_file
from flask_login import LoginManager, login_required, current_user
import sqlite3

# Auth imports
from src.auth.auth_manager import AuthManager
from src.auth.user_model import User

from src.radar.coverage import (
    find_covering_radars, find_nearest_radar,
    get_radar_by_code, get_all_radars, haversine_distance
)
from src.pdr.opportunity import PDROpportunityScorer, HailEvent
from src.pdr.market import PDRMarketAnalyzer

# ML Model imports
try:
    from src.ml.models.radar_hail_classifier import RadarHailClassifier
    from src.ml.models.storm_forecaster import StormSeverityForecaster
    from src.ml.models.seasonal_risk import SeasonalRiskModel
    from src.ml.models.hail_size_estimator import HailSizeEstimator
    from src.ml.models.vehicle_damage_detector import VehicleDamageDetector
    from src.ml.models.photo_validator import PhotoAuthenticityValidator
    from src.ml.models.pdr_business_models import (
        MLOpportunityScorer, ClaimRatePredictor,
        DamagePredictionModel, ParkingLotVehicleCounter
    )
    from src.ml.models.advanced_models import (
        RouteOptimizer, ConversionPredictor,
        DealershipInventoryEstimator, SentimentAnalyzer,
        RepairTimeEstimator
    )
    # Import REAL pre-trained sentiment model
    from src.ml.models.real_sentiment import RealSentimentAnalyzer
    REAL_SENTIMENT_AVAILABLE = True
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    REAL_SENTIMENT_AVAILABLE = False
    print(f"ML models not available: {e}")

import numpy as np

logger = logging.getLogger('HailTrackerWeb')


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / 'templates'),
        static_folder=str(PROJECT_ROOT / 'static')
    )

    # Default config
    app.config.update(
        DATABASE_PATH=str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db'),
        SECRET_KEY=os.environ.get('SECRET_KEY', 'hailtracker-dev-key'),
        DEBUG=os.environ.get('DEBUG', 'false').lower() == 'true',
        TEMPLATES_AUTO_RELOAD=True  # Always reload templates on change
    )

    if config:
        app.config.update(config)

    # Ensure templates and static directories exist
    (PROJECT_ROOT / 'templates').mkdir(exist_ok=True)
    (PROJECT_ROOT / 'static').mkdir(exist_ok=True)

    # ====================
    # Initialize Flask-Login
    # ====================
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Initialize auth manager
    auth_manager = AuthManager()

    @login_manager.user_loader
    def load_user(user_id):
        """Load user for Flask-Login"""
        user_dict = auth_manager.get_user_by_id(int(user_id))
        if user_dict:
            return User(user_dict)
        return None

    # Make auth_manager available to routes
    app.auth_manager = auth_manager

    logger.info("Flask-Login initialized")

    # ====================
    # Bridge Flask-Login to g.current_user
    # ====================
    # The custom decorators in src/core/auth/decorators.py check g.current_user
    # but Flask-Login sets current_user. This bridges the two systems.

    @app.before_request
    def bridge_flask_login_to_g():
        """Bridge Flask-Login's current_user to g.current_user for custom decorators"""
        from flask import g
        from flask_login import current_user

        # Initialize context variables
        g.current_user = None
        g.organization_id = 1  # Default org for demo
        g.account_id = 1

        if current_user.is_authenticated:
            # Convert User object to dict format expected by decorators
            g.current_user = {
                'id': current_user.id,
                'email': current_user.email,
                'username': current_user.username,
                'full_name': current_user.full_name,
                'role': current_user.role,
                'company_id': current_user.company_id,
                'organization_id': 1,  # Default for demo
                'permissions': auth_manager.get_user_permissions(current_user.id)
            }
            g.organization_id = 1  # Default org for demo

    # Initialize components
    pdr_scorer = PDROpportunityScorer(app.config['DATABASE_PATH'])
    market_analyzer = PDRMarketAnalyzer(app.config['DATABASE_PATH'])

    # Initialize ML models
    ml_models = {}
    if ML_AVAILABLE:
        try:
            # TIER 1: Meteorology
            ml_models['radar_classifier'] = RadarHailClassifier()
            ml_models['radar_classifier'].load()

            ml_models['storm_forecaster'] = StormSeverityForecaster()
            ml_models['storm_forecaster'].load()

            ml_models['seasonal_risk'] = SeasonalRiskModel()
            ml_models['seasonal_risk'].load()

            # TIER 2: Photo Analysis
            ml_models['size_estimator'] = HailSizeEstimator()
            ml_models['size_estimator'].load()

            ml_models['damage_detector'] = VehicleDamageDetector()
            ml_models['damage_detector'].load()

            ml_models['photo_validator'] = PhotoAuthenticityValidator()
            ml_models['photo_validator'].load()

            # TIER 3: PDR Business
            ml_models['ml_opportunity_scorer'] = MLOpportunityScorer()
            ml_models['ml_opportunity_scorer'].load()

            ml_models['claim_predictor'] = ClaimRatePredictor()
            ml_models['claim_predictor'].load()

            ml_models['damage_predictor'] = DamagePredictionModel()
            ml_models['damage_predictor'].load()

            ml_models['vehicle_counter'] = ParkingLotVehicleCounter()
            ml_models['vehicle_counter'].load()

            # TIER 4: Advanced
            ml_models['route_optimizer'] = RouteOptimizer()
            ml_models['route_optimizer'].load()

            ml_models['conversion_predictor'] = ConversionPredictor()
            ml_models['conversion_predictor'].load()

            ml_models['inventory_estimator'] = DealershipInventoryEstimator()
            ml_models['inventory_estimator'].load()

            # Use REAL pre-trained sentiment model if available
            if REAL_SENTIMENT_AVAILABLE:
                ml_models['sentiment_analyzer'] = RealSentimentAnalyzer()
                ml_models['sentiment_analyzer'].load()
                logger.info("Loaded REAL pre-trained sentiment model (66M params)")
            else:
                ml_models['sentiment_analyzer'] = SentimentAnalyzer()
                ml_models['sentiment_analyzer'].load()

            ml_models['repair_estimator'] = RepairTimeEstimator()
            ml_models['repair_estimator'].load()

            logger.info(f"Loaded {len(ml_models)} ML models")
        except Exception as e:
            logger.warning(f"Error loading ML models: {e}")

    def get_db():
        """Get database connection."""
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        conn.row_factory = sqlite3.Row
        return conn

    # ====================
    # Web Routes
    # ====================

    @app.route('/')
    def index():
        """Main dashboard page."""
        return render_template('index.html')

    @app.route('/map')
    def map_view():
        """Full-screen map view."""
        return render_template('map.html')

    @app.route('/events')
    def events_view():
        """Events list view."""
        return render_template('events.html')

    @app.route('/opportunities')
    def opportunities_view():
        """PDR opportunities view."""
        return render_template('opportunities.html')

    @app.route('/markets')
    def markets_view():
        """Market analysis view."""
        return render_template('markets.html')

    # ====================
    # API Routes - Events
    # ====================

    @app.route('/api/events')
    def api_events():
        """Get hail events with optional filters."""
        # Parse query parameters
        days = request.args.get('days', 30, type=int)
        min_size = request.args.get('min_size', 0, type=float)
        state = request.args.get('state')
        country = request.args.get('country')
        limit = request.args.get('limit', 100, type=int)

        conn = get_db()
        cursor = conn.cursor()

        # Build query
        query = """
            SELECT id, event_date, latitude, longitude,
                   max_hail_size_inches, state_province, city, country,
                   primary_radar, pdr_opportunity_score
            FROM hail_events
            WHERE event_date >= date('now', ?)
        """
        params = [f'-{days} days']

        if min_size > 0:
            query += " AND max_hail_size_inches >= ?"
            params.append(min_size)

        if state:
            query += " AND state_province = ?"
            params.append(state)

        if country:
            query += " AND country = ?"
            params.append(country)

        query += " ORDER BY event_date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append({
                'id': row['id'],
                'event_date': row['event_date'],
                'lat': row['latitude'],
                'lon': row['longitude'],
                'max_hail_size_inches': row['max_hail_size_inches'],
                'state_province': row['state_province'],
                'city': row['city'],
                'country': row['country'],
                'primary_radar': row['primary_radar'],
                'pdr_score': row['pdr_opportunity_score']
            })

        return jsonify({
            'events': events,
            'count': len(events),
            'filters': {
                'days': days,
                'min_size': min_size,
                'state': state,
                'country': country
            }
        })

    @app.route('/api/events/<int:event_id>')
    def api_event_detail(event_id):
        """Get detailed event information."""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM hail_events WHERE id = ?
        """, (event_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Event not found'}), 404

        event = dict(row)

        # Add radar info
        if event.get('primary_radar'):
            radar = get_radar_by_code(event['primary_radar'])
            if radar:
                event['radar_info'] = {
                    'site_code': radar.site_code,
                    'name': radar.name,
                    'lat': radar.latitude,
                    'lon': radar.longitude
                }

        return jsonify(event)

    @app.route('/api/events/search')
    def api_event_search():
        """Search events by location."""
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius_km = request.args.get('radius_km', 50, type=float)
        days = request.args.get('days', 365, type=int)

        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon required'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Bounding box search
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * 0.85)

        cursor.execute("""
            SELECT id, event_date, latitude, longitude,
                   max_hail_size_inches, state_province, city
            FROM hail_events
            WHERE event_date >= date('now', ?)
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            ORDER BY event_date DESC
            LIMIT 100
        """, (
            f'-{days} days',
            lat - lat_delta, lat + lat_delta,
            lon - lon_delta, lon + lon_delta
        ))

        rows = cursor.fetchall()
        conn.close()

        # Filter by actual distance and calculate
        events = []
        for row in rows:
            dist = haversine_distance(lat, lon, row['latitude'], row['longitude'])
            if dist <= radius_km:
                events.append({
                    'id': row['id'],
                    'event_date': row['event_date'],
                    'lat': row['latitude'],
                    'lon': row['longitude'],
                    'max_hail_size_inches': row['max_hail_size_inches'],
                    'state_province': row['state_province'],
                    'city': row['city'],
                    'distance_km': round(dist, 1)
                })

        events.sort(key=lambda x: x['distance_km'])

        return jsonify({
            'events': events,
            'count': len(events),
            'search': {
                'lat': lat,
                'lon': lon,
                'radius_km': radius_km,
                'days': days
            }
        })

    # ====================
    # API Routes - Radars
    # ====================

    @app.route('/api/radars')
    def api_radars():
        """Get all radar sites."""
        radars = get_all_radars()

        return jsonify({
            'radars': [
                {
                    'site_code': r.site_code,
                    'name': r.name,
                    'country': r.country,
                    'state_province': r.state_province,
                    'lat': r.latitude,
                    'lon': r.longitude,
                    'elevation_m': r.elevation_m,
                    'data_source': r.data_source
                }
                for r in radars
            ],
            'count': len(radars)
        })

    @app.route('/api/radars/<site_code>')
    def api_radar_detail(site_code):
        """Get radar site details."""
        radar = get_radar_by_code(site_code)

        if not radar:
            return jsonify({'error': 'Radar not found'}), 404

        return jsonify({
            'site_code': radar.site_code,
            'name': radar.name,
            'country': radar.country,
            'state_province': radar.state_province,
            'lat': radar.latitude,
            'lon': radar.longitude,
            'elevation_m': radar.elevation_m,
            'coverage_radius_km': radar.coverage_radius_km,
            'timezone': radar.timezone,
            'data_source': radar.data_source,
            'data_url': radar.data_url
        })

    @app.route('/api/radars/coverage')
    def api_radar_coverage():
        """Find radars covering a location."""
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        max_radars = request.args.get('max', 5, type=int)

        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon required'}), 400

        coverages = find_covering_radars(lat, lon, max_radars=max_radars)

        return jsonify({
            'location': {'lat': lat, 'lon': lon},
            'coverage': [
                {
                    'site_code': c.radar.site_code,
                    'name': c.radar.name,
                    'country': c.radar.country,
                    'distance_km': round(c.distance_km, 1),
                    'bearing_deg': round(c.bearing_deg, 1),
                    'quality': c.coverage_quality,
                    'is_primary': c.is_primary
                }
                for c in coverages
            ]
        })

    # ====================
    # API Routes - PDR
    # ====================

    @app.route('/api/pdr/opportunities')
    def api_pdr_opportunities():
        """Get PDR opportunities."""
        days = request.args.get('days', 30, type=int)
        min_score = request.args.get('min_score', 50, type=float)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.*, e.event_date, e.latitude, e.longitude,
                   e.state_province, e.city, e.max_hail_size_inches
            FROM pdr_opportunities o
            JOIN hail_events e ON o.event_id = e.id
            WHERE o.is_active = 1
              AND o.opportunity_score >= ?
              AND e.event_date >= date('now', ?)
            ORDER BY o.opportunity_score DESC
            LIMIT 50
        """, (min_score, f'-{days} days'))

        rows = cursor.fetchall()
        conn.close()

        opportunities = []
        for row in rows:
            opportunities.append({
                'event_id': row['event_id'],
                'event_date': row['event_date'],
                'location': f"{row['city']}, {row['state_province']}" if row['city'] else row['state_province'],
                'lat': row['latitude'],
                'lon': row['longitude'],
                'hail_size': row['max_hail_size_inches'],
                'score': row['opportunity_score'],
                'priority': row['priority'],
                'estimated_vehicles': row['estimated_vehicles'],
                'unclaimed_estimate': row['unclaimed_vehicles_estimate'],
                'revenue_potential': row['estimated_revenue_potential'],
                'window_remaining': row['opportunity_window_days']
            })

        return jsonify({
            'opportunities': opportunities,
            'count': len(opportunities)
        })

    @app.route('/api/pdr/markets')
    def api_pdr_markets():
        """Get PDR market analysis."""
        analyses = market_analyzer.analyze_all_markets()

        markets = []
        for analysis in analyses:
            markets.append({
                'id': analysis.market.market_id,
                'name': analysis.market.name,
                'priority': analysis.market.priority,
                'in_season': analysis.current_season_active,
                'ytd_events': analysis.ytd_events,
                'ytd_vs_avg': analysis.ytd_vs_average,
                'recent_opportunities': analysis.recent_opportunities,
                'market_value_ytd': analysis.total_market_value_ytd,
                'competition': analysis.competition_level,
                'states': analysis.market.states_provinces,
                'actions': analysis.recommended_actions[:3]
            })

        return jsonify({
            'markets': markets,
            'summary': market_analyzer.get_market_summary()
        })

    @app.route('/api/pdr/score', methods=['POST'])
    def api_pdr_score():
        """Score a hail event for PDR opportunity."""
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        required = ['lat', 'lon', 'hail_size_inches', 'event_date']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} required'}), 400

        event = HailEvent(
            event_id=data.get('event_id', 0),
            event_date=datetime.strptime(data['event_date'], '%Y-%m-%d'),
            lat=data['lat'],
            lon=data['lon'],
            max_hail_size_inches=data['hail_size_inches'],
            affected_area_km2=data.get('affected_area_km2', 100),
            state_province=data.get('state_province', ''),
            city=data.get('city', '')
        )

        opportunity = pdr_scorer.score_event(event)

        return jsonify({
            'score': opportunity.opportunity_score,
            'priority': opportunity.priority,
            'estimated_vehicles_damaged': opportunity.estimated_vehicles_damaged,
            'unclaimed_estimate': opportunity.unclaimed_estimate,
            'damage_severity': opportunity.damage_severity,
            'total_market_value': opportunity.total_market_value,
            'window_remaining_days': opportunity.window_remaining_days,
            'recommended_actions': opportunity.recommended_actions
        })

    # ====================
    # API Routes - Stats
    # ====================

    @app.route('/api/stats')
    def api_stats():
        """Get system statistics."""
        conn = get_db()
        cursor = conn.cursor()

        # Total events
        cursor.execute("SELECT COUNT(*) FROM hail_events")
        total_events = cursor.fetchone()[0]

        # Events by country
        cursor.execute("""
            SELECT country, COUNT(*) as count
            FROM hail_events
            GROUP BY country
        """)
        by_country = {row['country']: row['count'] for row in cursor.fetchall()}

        # Recent events (7 days)
        cursor.execute("""
            SELECT COUNT(*) FROM hail_events
            WHERE event_date >= date('now', '-7 days')
        """)
        recent_7d = cursor.fetchone()[0]

        # Radar count
        cursor.execute("SELECT COUNT(*) FROM radar_sites WHERE is_active = 1")
        radar_count = cursor.fetchone()[0]

        # Social posts
        cursor.execute("SELECT COUNT(*) FROM social_media_posts")
        social_posts = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'total_events': total_events,
            'events_by_country': by_country,
            'events_last_7_days': recent_7d,
            'active_radars': radar_count,
            'social_posts': social_posts,
            'timestamp': datetime.utcnow().isoformat()
        })

    @app.route('/api/health')
    def api_health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'version': '2.0.0',
            'ml_models_loaded': len(ml_models),
            'timestamp': datetime.utcnow().isoformat()
        })

    # ====================
    # PWA Routes
    # ====================

    @app.route('/offline')
    def offline():
        """Serve offline page."""
        return render_template('offline.html')

    @app.route('/static/sw.js')
    def service_worker():
        """Serve service worker with correct headers."""
        from flask import send_from_directory, make_response
        response = make_response(
            send_from_directory(app.static_folder, 'sw.js')
        )
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    @app.route('/static/manifest.json')
    def manifest():
        """Serve manifest with correct headers."""
        from flask import send_from_directory
        return send_from_directory(
            app.static_folder, 'manifest.json',
            mimetype='application/json'
        )

    # Push notification VAPID keys
    # Load from .env file if environment not set
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')

    if not VAPID_PUBLIC_KEY:
        env_file = PROJECT_ROOT / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('VAPID_PUBLIC_KEY='):
                        VAPID_PUBLIC_KEY = line.split('=', 1)[1]
                    elif line.startswith('VAPID_PRIVATE_KEY='):
                        VAPID_PRIVATE_KEY = line.split('=', 1)[1]

    # Store subscriptions in memory (in production, use database)
    push_subscriptions = []

    @app.route('/api/v1/push/public-key')
    def get_push_public_key():
        """Return VAPID public key for push subscriptions."""
        if not VAPID_PUBLIC_KEY:
            return jsonify({
                'error': 'Push notifications not configured',
                'publicKey': None
            }), 200

        return jsonify({
            'publicKey': VAPID_PUBLIC_KEY
        })

    @app.route('/api/v1/push/subscribe', methods=['POST'])
    def subscribe_to_push():
        """Save push subscription."""
        subscription = request.get_json()

        if not subscription:
            return jsonify({'error': 'Subscription data required'}), 400

        # In production, save to database
        push_subscriptions.append(subscription)

        return jsonify({
            'success': True,
            'message': 'Subscription saved'
        })

    @app.route('/api/v1/push/unsubscribe', methods=['POST'])
    def unsubscribe_from_push():
        """Remove push subscription."""
        subscription = request.get_json()

        if not subscription:
            return jsonify({'error': 'Subscription data required'}), 400

        # In production, remove from database
        endpoint = subscription.get('endpoint')
        global push_subscriptions
        push_subscriptions = [s for s in push_subscriptions if s.get('endpoint') != endpoint]

        return jsonify({
            'success': True,
            'message': 'Subscription removed'
        })

    @app.route('/api/v1/push/test', methods=['POST'])
    def test_push_notification():
        """Send test push notification (for development)."""
        if not VAPID_PRIVATE_KEY:
            return jsonify({'error': 'Push notifications not configured'}), 503

        try:
            from pywebpush import webpush, WebPushException

            notification = {
                'title': 'HailTracker Test',
                'body': 'Push notifications are working!',
                'icon': '/static/icons/icon-192.png',
                'badge': '/static/icons/badge-72.png',
                'url': '/'
            }

            sent_count = 0
            for subscription in push_subscriptions:
                try:
                    webpush(
                        subscription_info=subscription,
                        data=jsonify(notification).get_data(as_text=True),
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims={'sub': 'mailto:admin@hailtracker.pro'}
                    )
                    sent_count += 1
                except WebPushException as e:
                    logger.error(f"Push failed: {e}")

            return jsonify({
                'success': True,
                'sent': sent_count,
                'total_subscriptions': len(push_subscriptions)
            })

        except ImportError:
            return jsonify({
                'error': 'pywebpush not installed',
                'hint': 'pip install pywebpush'
            }), 503

    @app.route('/api/v1/push/send', methods=['POST'])
    def send_push_notification():
        """Send push notification to all subscribers."""
        if not VAPID_PRIVATE_KEY:
            return jsonify({'error': 'Push notifications not configured'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Notification data required'}), 400

        try:
            from pywebpush import webpush, WebPushException
            import json

            notification = {
                'title': data.get('title', 'HailTracker Alert'),
                'body': data.get('body', 'New hail event detected'),
                'icon': data.get('icon', '/static/icons/icon-192.png'),
                'badge': '/static/icons/badge-72.png',
                'url': data.get('url', '/'),
                'tag': data.get('tag', 'hail-alert'),
                'priority': data.get('priority', 'normal')
            }

            sent_count = 0
            failed_count = 0

            for subscription in push_subscriptions:
                try:
                    webpush(
                        subscription_info=subscription,
                        data=json.dumps(notification),
                        vapid_private_key=VAPID_PRIVATE_KEY,
                        vapid_claims={'sub': 'mailto:admin@hailtracker.pro'}
                    )
                    sent_count += 1
                except WebPushException as e:
                    logger.error(f"Push failed: {e}")
                    failed_count += 1

            return jsonify({
                'success': True,
                'sent': sent_count,
                'failed': failed_count,
                'total': len(push_subscriptions)
            })

        except ImportError:
            return jsonify({
                'error': 'pywebpush not installed'
            }), 503

    # ====================
    # API Routes - ML Models
    # ====================

    @app.route('/api/ml/status')
    def api_ml_status():
        """Get ML models status."""
        return jsonify({
            'ml_available': ML_AVAILABLE,
            'models_loaded': len(ml_models),
            'models': list(ml_models.keys()),
            'tiers': {
                'tier1_meteorology': ['radar_classifier', 'storm_forecaster', 'seasonal_risk'],
                'tier2_photo_analysis': ['size_estimator', 'damage_detector', 'photo_validator'],
                'tier3_pdr_business': ['ml_opportunity_scorer', 'claim_predictor', 'damage_predictor', 'vehicle_counter'],
                'tier4_advanced': ['route_optimizer', 'conversion_predictor', 'inventory_estimator', 'sentiment_analyzer', 'repair_estimator']
            }
        })

    # --- TIER 1: Meteorology ---

    @app.route('/api/ml/radar/analyze', methods=['POST'])
    def api_ml_radar_analyze():
        """Analyze radar data for hail detection."""
        if 'radar_classifier' not in ml_models:
            return jsonify({'error': 'Radar classifier not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Simulate radar data from parameters
        radar_data = {
            'reflectivity': np.random.uniform(
                data.get('min_reflectivity', 40),
                data.get('max_reflectivity', 65),
                (20, 100, 100)
            ),
            'zdr': np.random.uniform(-1, 3, (20, 100, 100)) if data.get('include_dual_pol', False) else None,
            'cc': np.random.uniform(0.9, 1.0, (20, 100, 100)) if data.get('include_dual_pol', False) else None,
        }

        result = ml_models['radar_classifier'].classify(radar_data)
        return jsonify(result)

    @app.route('/api/ml/storm/forecast', methods=['POST'])
    def api_ml_storm_forecast():
        """Forecast storm severity at multiple time horizons."""
        if 'storm_forecaster' not in ml_models:
            return jsonify({'error': 'Storm forecaster not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        radar_trend = data.get('radar_trend', [
            {'max_reflectivity': 55, 'vil': 35, 'storm_speed': 35, 'storm_direction': 260}
        ])

        environment = data.get('environment', {
            'cape': 2000,
            'shear_0_6km': 40,
            'freezing_level': 3500,
            'hour': 18,
            'month': 6
        })

        result = ml_models['storm_forecaster'].forecast(radar_trend, environment)
        return jsonify(result)

    @app.route('/api/ml/risk/seasonal')
    def api_ml_seasonal_risk():
        """Get seasonal hail risk for a location."""
        if 'seasonal_risk' not in ml_models:
            return jsonify({'error': 'Seasonal risk model not loaded'}), 503

        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        month = request.args.get('month', type=int)

        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon required'}), 400

        result = ml_models['seasonal_risk'].predict_risk(lat, lon, month)
        return jsonify(result)

    # --- TIER 2: Photo Analysis ---

    @app.route('/api/ml/photo/estimate-size', methods=['POST'])
    def api_ml_estimate_size():
        """Estimate hail size from photo features."""
        if 'size_estimator' not in ml_models:
            return jsonify({'error': 'Size estimator not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Accept image features or simulate from description
        if 'features' in data:
            image_data = np.array(data['features'])
        else:
            # Simulate image based on described characteristics
            brightness = data.get('brightness', 180)
            contrast = data.get('contrast', 50)
            image_data = np.random.randint(
                max(0, brightness - contrast),
                min(255, brightness + contrast),
                (100, 100, 3)
            )

        result = ml_models['size_estimator'].estimate_size(image_data)
        return jsonify(result)

    @app.route('/api/ml/photo/detect-damage', methods=['POST'])
    def api_ml_detect_damage():
        """Detect vehicle damage from photo features."""
        if 'damage_detector' not in ml_models:
            return jsonify({'error': 'Damage detector not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        if 'features' in data:
            image_data = np.array(data['features'])
        else:
            brightness = data.get('brightness', 140)
            image_data = np.random.randint(
                max(0, brightness - 30),
                min(255, brightness + 30),
                (200, 300, 3)
            )

        result = ml_models['damage_detector'].detect_damage(image_data)
        return jsonify(result)

    @app.route('/api/ml/photo/validate', methods=['POST'])
    def api_ml_validate_photo():
        """Validate photo authenticity."""
        if 'photo_validator' not in ml_models:
            return jsonify({'error': 'Photo validator not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        if 'features' in data:
            image_data = np.array(data['features'])
        else:
            image_data = np.random.randint(80, 200, (200, 300, 3))

        metadata = data.get('metadata', {})

        result = ml_models['photo_validator'].validate(image_data, metadata)
        return jsonify(result)

    # --- TIER 3: PDR Business Intelligence ---

    @app.route('/api/ml/opportunity/score', methods=['POST'])
    def api_ml_score_opportunity():
        """ML-based opportunity scoring."""
        if 'ml_opportunity_scorer' not in ml_models:
            return jsonify({'error': 'ML opportunity scorer not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        event = {
            'max_hail_size_inches': data.get('hail_size', 1.5),
            'duration_minutes': data.get('duration', 30),
            'affected_area_km2': data.get('area_km2', 100),
            'event_age_days': data.get('event_age_days', 7),
            'population_density': data.get('population_density', 500),
            'vehicle_density': data.get('vehicle_density', 200),
            'median_income': data.get('median_income', 55000),
            'num_dealerships': data.get('num_dealerships', 5),
            'competition_score': data.get('competition_score', 0.5),
            'radar_confidence': data.get('radar_confidence', 0.85),
            'state_province': data.get('state_province', ''),
            'month': data.get('month', 6)
        }

        result = ml_models['ml_opportunity_scorer'].score_event(event)
        return jsonify(result)

    @app.route('/api/ml/claim-rate/predict', methods=['POST'])
    def api_ml_predict_claim_rate():
        """Predict insurance claim rate."""
        if 'claim_predictor' not in ml_models:
            return jsonify({'error': 'Claim rate predictor not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        event = {
            'max_hail_size_inches': data.get('hail_size', 1.5),
            'median_income': data.get('median_income', 55000),
            'insurance_penetration': data.get('insurance_penetration', 0.85),
            'population_density': data.get('population_density', 500),
            'event_age_days': data.get('event_age_days', 7),
            'country': data.get('country', 'US'),
            'prior_claims_in_area': data.get('prior_claims', 50),
            'deductible_avg': data.get('deductible_avg', 500)
        }

        result = ml_models['claim_predictor'].predict_claim_rate(event)
        return jsonify(result)

    @app.route('/api/ml/damage/predict', methods=['POST'])
    def api_ml_predict_damage():
        """Predict damage from storm parameters."""
        if 'damage_predictor' not in ml_models:
            return jsonify({'error': 'Damage predictor not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        storm = {
            'max_hail_size_inches': data.get('max_hail_size', 1.5),
            'min_hail_size_inches': data.get('min_hail_size', 0.75),
            'duration_minutes': data.get('duration', 20),
            'storm_speed_mph': data.get('storm_speed', 30),
            'wind_speed_mph': data.get('wind_speed', 20),
            'coverage_percentage': data.get('coverage', 50),
            'intensity_score': data.get('intensity', 0.6)
        }

        result = ml_models['damage_predictor'].predict_damage(storm)
        return jsonify(result)

    @app.route('/api/ml/vehicles/estimate', methods=['POST'])
    def api_ml_estimate_vehicles():
        """Estimate vehicles in affected area."""
        if 'vehicle_counter' not in ml_models:
            return jsonify({'error': 'Vehicle counter not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        area = {
            'area_km2': data.get('area_km2', 50),
            'population_density': data.get('population_density', 500),
            'business_count': data.get('business_count', 50),
            'parking_lot_count': data.get('parking_lot_count', 10),
            'dealership_count': data.get('dealership_count', 2),
            'land_use': data.get('land_use', 'mixed'),
            'hour_of_day': data.get('hour', 14),
            'is_weekend': data.get('is_weekend', False)
        }

        result = ml_models['vehicle_counter'].estimate_vehicles(area)
        return jsonify(result)

    # --- TIER 4: Advanced Intelligence ---

    @app.route('/api/ml/route/optimize', methods=['POST'])
    def api_ml_optimize_route():
        """Optimize route through multiple locations."""
        if 'route_optimizer' not in ml_models:
            return jsonify({'error': 'Route optimizer not loaded'}), 503

        data = request.get_json()
        if not data or 'locations' not in data:
            return jsonify({'error': 'locations array required'}), 400

        locations = data['locations']
        if len(locations) < 2:
            return jsonify({'error': 'At least 2 locations required'}), 400

        result = ml_models['route_optimizer'].optimize_route(locations)
        return jsonify(result)

    @app.route('/api/ml/conversion/predict', methods=['POST'])
    def api_ml_predict_conversion():
        """Predict lead conversion probability."""
        if 'conversion_predictor' not in ml_models:
            return jsonify({'error': 'Conversion predictor not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        lead = {
            'damage_severity': data.get('damage_severity', 2),
            'response_time_hours': data.get('response_time_hours', 24),
            'quote_amount': data.get('quote_amount', 1000),
            'competitor_quotes': data.get('competitor_quotes', 1),
            'income_bracket': data.get('income_bracket', 3),
            'insurance_claim': data.get('insurance_claim', 1),
            'event_age_days': data.get('event_age_days', 7),
            'source': data.get('source', 'online')
        }

        result = ml_models['conversion_predictor'].predict_conversion(lead)
        return jsonify(result)

    @app.route('/api/ml/inventory/estimate', methods=['POST'])
    def api_ml_estimate_inventory():
        """Estimate dealership inventory."""
        if 'inventory_estimator' not in ml_models:
            return jsonify({'error': 'Inventory estimator not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        dealership = {
            'lot_size_sqft': data.get('lot_size_sqft', 50000),
            'num_employees': data.get('num_employees', 20),
            'annual_sales': data.get('annual_sales', 500),
            'years_in_business': data.get('years_in_business', 10),
            'type': data.get('type', 'new_franchise'),
            'is_luxury': data.get('is_luxury', False),
            'num_brands': data.get('num_brands', 1)
        }

        result = ml_models['inventory_estimator'].estimate_inventory(dealership)
        return jsonify(result)

    @app.route('/api/ml/sentiment/analyze', methods=['POST'])
    def api_ml_analyze_sentiment():
        """Analyze text sentiment."""
        if 'sentiment_analyzer' not in ml_models:
            return jsonify({'error': 'Sentiment analyzer not loaded'}), 503

        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'text field required'}), 400

        result = ml_models['sentiment_analyzer'].analyze(data['text'])
        return jsonify(result)

    @app.route('/api/ml/repair-time/estimate', methods=['POST'])
    def api_ml_estimate_repair_time():
        """Estimate repair time for a job."""
        if 'repair_estimator' not in ml_models:
            return jsonify({'error': 'Repair time estimator not loaded'}), 503

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        job = {
            'dent_count': data.get('dent_count', 50),
            'num_panels': data.get('num_panels', 4),
            'severity_score': data.get('severity_score', 2),
            'avg_dent_size_mm': data.get('avg_dent_size_mm', 15),
            'has_body_lines': data.get('has_body_lines', True),
            'aluminum_panels': data.get('aluminum_panels', False),
            'vehicle_age_years': data.get('vehicle_age_years', 5),
            'vehicle_type': data.get('vehicle_type', 'sedan')
        }

        result = ml_models['repair_estimator'].estimate_time(job)
        return jsonify(result)

    # ====================
    # Fleet Location Intelligence API
    # ====================

    from src.business.fleet_locations import FleetLocationManager
    from src.business.priority_scorer import PriorityScorer
    from src.business.route_optimizer import RouteOptimizer as FleetRouteOptimizer

    # Use dedicated fleet locations database
    fleet_db_path = os.path.join(os.path.dirname(app.config['DATABASE_PATH']), 'fleet_locations.db')
    fleet_manager = FleetLocationManager(fleet_db_path)
    priority_scorer = PriorityScorer()
    fleet_route_optimizer = FleetRouteOptimizer()

    @app.route('/fleet')
    def fleet_map_view():
        """Fleet location intelligence map."""
        return render_template('fleet_map.html')

    @app.route('/api/fleet/locations')
    def api_fleet_locations():
        """Get fleet locations with filtering."""
        # Bounding box
        south = request.args.get('south', type=float)
        north = request.args.get('north', type=float)
        west = request.args.get('west', type=float)
        east = request.args.get('east', type=float)

        # Filters
        categories = request.args.getlist('category')
        min_vehicles = request.args.get('min_vehicles', 0, type=int)
        limit = request.args.get('limit', 500, type=int)
        city = request.args.get('city')
        state = request.args.get('state')

        conn = fleet_manager._get_conn()

        if south and north and west and east:
            # Bounding box query
            query = """
                SELECT fl.*, fc.icon, fc.color, fc.tier, fc.display_name as category_name
                FROM fleet_locations fl
                LEFT JOIN fleet_categories fc ON fl.category = fc.category
                WHERE fl.lat BETWEEN ? AND ?
                  AND fl.lon BETWEEN ? AND ?
                  AND fl.estimated_vehicles >= ?
            """
            params = [south, north, west, east, min_vehicles]
        else:
            # All locations
            query = """
                SELECT fl.*, fc.icon, fc.color, fc.tier, fc.display_name as category_name
                FROM fleet_locations fl
                LEFT JOIN fleet_categories fc ON fl.category = fc.category
                WHERE fl.estimated_vehicles >= ?
            """
            params = [min_vehicles]

        if categories:
            placeholders = ','.join('?' * len(categories))
            query += f" AND fl.category IN ({placeholders})"
            params.extend(categories)

        # City filter
        if city:
            query += " AND fl.city = ?"
            params.append(city)

        # State filter
        if state:
            query += " AND fl.state = ?"
            params.append(state)

        query += " ORDER BY fc.tier, fl.estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add estimated revenue
        for loc in locations:
            loc['estimated_revenue'] = loc['estimated_vehicles'] * loc.get('avg_revenue_per_vehicle', 1500)

        return jsonify({
            'locations': locations,
            'count': len(locations)
        })

    @app.route('/api/fleet/cities')
    def api_fleet_cities():
        """Get list of cities with location counts."""
        conn = fleet_manager._get_conn()
        rows = conn.execute("""
            SELECT city, state, COUNT(*) as location_count,
                   SUM(estimated_vehicles) as total_vehicles,
                   AVG(lat) as center_lat, AVG(lon) as center_lon
            FROM fleet_locations
            WHERE city IS NOT NULL AND city != ''
            GROUP BY city, state
            HAVING location_count >= 10
            ORDER BY total_vehicles DESC
        """).fetchall()
        conn.close()

        cities = [dict(row) for row in rows]
        return jsonify({
            'cities': cities,
            'count': len(cities)
        })

    @app.route('/api/fleet/locations/<int:location_id>')
    def api_fleet_location_detail(location_id):
        """Get detailed location information."""
        conn = fleet_manager._get_conn()
        row = conn.execute("""
            SELECT fl.*, fc.icon, fc.color, fc.tier, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE fl.id = ?
        """, (location_id,)).fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Location not found'}), 404

        location = dict(row)
        location['estimated_revenue'] = location['estimated_vehicles'] * location.get('avg_revenue_per_vehicle', 1500)

        return jsonify(location)

    @app.route('/api/fleet/search')
    def api_fleet_search():
        """Search fleet locations."""
        query = request.args.get('q', '')
        limit = request.args.get('limit', 50, type=int)

        if not query:
            return jsonify({'error': 'Search query required'}), 400

        locations = fleet_manager.search_locations(query, limit)
        return jsonify({
            'locations': locations,
            'count': len(locations),
            'query': query
        })

    @app.route('/api/fleet/near')
    def api_fleet_near():
        """Get locations near a point."""
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius_km = request.args.get('radius', 50, type=float)
        categories = request.args.getlist('category')
        min_vehicles = request.args.get('min_vehicles', 0, type=int)

        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon required'}), 400

        locations = fleet_manager.get_locations_near_point(
            lat, lon, radius_km, categories, min_vehicles
        )

        return jsonify({
            'locations': locations,
            'count': len(locations),
            'center': {'lat': lat, 'lon': lon},
            'radius_km': radius_km
        })

    @app.route('/api/fleet/categories')
    def api_fleet_categories():
        """Get category summary."""
        summary = fleet_manager.get_category_summary()
        return jsonify({
            'categories': summary,
            'total_locations': fleet_manager.get_location_count()
        })

    @app.route('/api/fleet/score', methods=['POST'])
    def api_fleet_score():
        """Score a location for priority."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        location = data.get('location', {})
        hail_event = data.get('hail_event')

        result = priority_scorer.score_location(location, hail_event)

        return jsonify({
            'score': result.score,
            'grade': result.grade,
            'factors': result.factors,
            'estimated_revenue': result.estimated_revenue,
            'recommendation': result.recommendation
        })

    @app.route('/api/fleet/score-event', methods=['POST'])
    def api_fleet_score_event():
        """Score multiple locations for a hail event."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        location_ids = data.get('location_ids', [])
        hail_event = data.get('hail_event', {})

        if not location_ids:
            return jsonify({'error': 'location_ids required'}), 400

        # Fetch locations
        conn = fleet_manager._get_conn()
        placeholders = ','.join('?' * len(location_ids))
        rows = conn.execute(f"""
            SELECT fl.*, fc.icon, fc.color, fc.tier
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE fl.id IN ({placeholders})
        """, location_ids).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Score them
        scored = priority_scorer.score_locations_for_event(locations, hail_event)

        return jsonify({
            'locations': scored,
            'count': len(scored),
            'hail_event': hail_event
        })

    @app.route('/api/fleet/route/optimize', methods=['POST'])
    def api_fleet_optimize_route():
        """Optimize route through locations."""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        locations = data.get('locations', [])
        start_location = data.get('start_location')

        if len(locations) < 2:
            return jsonify({'error': 'At least 2 locations required'}), 400

        route = fleet_route_optimizer.optimize_route(locations, start_location)

        return jsonify({
            'locations': route.locations,
            'summary': route.summary,
            'google_maps_url': route.google_maps_url
        })

    @app.route('/api/fleet/route/export/<format>')
    def api_fleet_export_route(format):
        """Export route in various formats."""
        # This would normally get route from session/database
        # For now, return sample
        return jsonify({'error': 'Route export requires route data'}), 400

    @app.route('/api/fleet/watchlist')
    def api_fleet_watchlist():
        """Get user's watch list."""
        conn = fleet_manager._get_conn()
        rows = conn.execute("""
            SELECT wl.*, fl.name, fl.category, fl.lat, fl.lon,
                   fl.estimated_vehicles, fl.phone, fl.manager_name,
                   fc.icon, fc.color
            FROM watch_list wl
            JOIN fleet_locations fl ON wl.location_id = fl.id
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE wl.user_id = 1
            ORDER BY fl.estimated_vehicles DESC
        """).fetchall()
        conn.close()

        return jsonify({
            'watchlist': [dict(row) for row in rows],
            'count': len(rows)
        })

    @app.route('/api/fleet/watchlist', methods=['POST'])
    def api_fleet_add_to_watchlist():
        """Add location to watch list."""
        data = request.get_json()
        if not data or 'location_id' not in data:
            return jsonify({'error': 'location_id required'}), 400

        conn = fleet_manager._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO watch_list (user_id, location_id, notes, alert_on_hail)
                VALUES (1, ?, ?, ?)
            """, (data['location_id'], data.get('notes', ''), data.get('alert_on_hail', True)))
            conn.commit()
            return jsonify({'success': True, 'message': 'Added to watch list'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/fleet/watchlist/<int:location_id>', methods=['DELETE'])
    def api_fleet_remove_from_watchlist(location_id):
        """Remove location from watch list."""
        conn = fleet_manager._get_conn()
        conn.execute("DELETE FROM watch_list WHERE user_id = 1 AND location_id = ?", (location_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Removed from watch list'})

    # ==================== Photo Verification API ====================

    @app.route('/api/fleet/verify-damage', methods=['POST'])
    def api_fleet_verify_damage():
        """
        Verify hail damage from text description.

        POST JSON:
        {
            "description": "Quarter sized hail hit the lot",
            "location_id": 123,  // optional
            "lat": 35.4676,      // optional
            "lon": -97.5164,     // optional
            "date": "2026-01-15" // optional
        }
        """
        from src.business.photo_verification import PhotoVerifier
        from datetime import datetime

        data = request.get_json()
        if not data or 'description' not in data:
            return jsonify({'error': 'description required'}), 400

        description = data['description']

        # Get location
        claimed_location = None
        if data.get('lat') and data.get('lon'):
            claimed_location = (data['lat'], data['lon'])
        elif data.get('location_id'):
            # Look up location from database
            conn = fleet_manager._get_conn()
            row = conn.execute(
                "SELECT lat, lon FROM fleet_locations WHERE id = ?",
                (data['location_id'],)
            ).fetchone()
            conn.close()
            if row:
                claimed_location = (row['lat'], row['lon'])

        # Get date
        claimed_date = None
        if data.get('date'):
            try:
                claimed_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
            except ValueError:
                claimed_date = None
        else:
            claimed_date = datetime.now()  # Assume today if not specified

        # Verify
        verifier = PhotoVerifier()
        result = verifier.verify(
            description=description,
            claimed_location=claimed_location,
            claimed_date=claimed_date
        )

        return jsonify({
            'valid': result.is_valid,
            'confidence': result.confidence,
            'extracted_size': {
                'inches': result.extracted_size,
                'text': result.extracted_size_text
            },
            'severity': result.severity,
            'timestamp_valid': result.timestamp_valid,
            'location_valid': result.location_valid,
            'warnings': result.warnings,
            'notes': result.notes
        })

    @app.route('/api/fleet/hail-sizes', methods=['GET'])
    def api_fleet_hail_sizes():
        """Get hail size reference chart."""
        from src.business.photo_verification import HAIL_SIZE_REFERENCE, DAMAGE_SEVERITY

        sizes = []
        for name, inches in sorted(HAIL_SIZE_REFERENCE.items(), key=lambda x: x[1]):
            # Find severity
            severity = 'UNKNOWN'
            for (min_s, max_s), sev in DAMAGE_SEVERITY.items():
                if min_s <= inches < max_s:
                    severity = sev['level']
                    break

            sizes.append({
                'name': name,
                'inches': inches,
                'cm': round(inches * 2.54, 1),
                'severity': severity
            })

        return jsonify({
            'reference_sizes': sizes,
            'severity_levels': [
                {'level': 'MINIMAL', 'range': '< 0.75"', 'description': 'Minor cosmetic damage possible'},
                {'level': 'LIGHT', 'range': '0.75" - 1.0"', 'description': 'Light dents on soft panels'},
                {'level': 'MODERATE', 'range': '1.0" - 1.5"', 'description': 'Visible dents, paintwork may crack'},
                {'level': 'SIGNIFICANT', 'range': '1.5" - 2.0"', 'description': 'Significant body damage'},
                {'level': 'SEVERE', 'range': '2.0" - 3.0"', 'description': 'Severe damage, possible glass breakage'},
                {'level': 'CATASTROPHIC', 'range': '> 3.0"', 'description': 'Total loss possible'}
            ]
        })

    # ====================
    # Export API Endpoints
    # ====================

    from src.business.exports import (
        FleetExcelExporter, MailingLabelsExporter, CallingListExporter,
        DirectMailExporter, EmailCampaignExporter, SMSCampaignExporter, MapsRoutesExporter
    )

    exports_dir = os.path.join(os.path.dirname(app.config['DATABASE_PATH']), '..', 'exports')
    os.makedirs(exports_dir, exist_ok=True)

    @app.route('/api/fleet/export/excel', methods=['POST'])
    def export_fleet_excel():
        """Export fleet locations to Excel workbook"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        category = data.get('category')
        limit = data.get('limit', 500)

        # Get locations from database
        conn = fleet_manager._get_conn()

        query = """
            SELECT fl.*, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE 1=1
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND fl.id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND fl.city = ?"
            params.append(city)
        if state:
            query += " AND fl.state = ?"
            params.append(state)
        if category:
            query += " AND fl.category = ?"
            params.append(category)

        query += " ORDER BY fl.estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add priority scores
        for loc in locations:
            loc['priority_score'] = min(100, (loc.get('estimated_vehicles', 0) / 5) + 30)
            loc['estimated_revenue'] = loc.get('estimated_vehicles', 0) * 1500

        # Create hail event info
        hail_event = {
            'location': f"{city}, {state}" if city else 'Multiple Cities',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'hail_size_inches': 0,
            'affected_area_sqmi': 0
        }

        # Generate Excel
        exporter = FleetExcelExporter(output_dir=exports_dir)
        filename = exporter.export_to_excel(locations, hail_event)

        return send_file(
            filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/labels', methods=['POST'])
    def export_mailing_labels():
        """Export mailing labels (Avery 5160 format)"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        limit = data.get('limit', 300)

        conn = fleet_manager._get_conn()

        query = """
            SELECT * FROM fleet_locations
            WHERE address IS NOT NULL AND address != ''
              AND city IS NOT NULL AND city != ''
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND city = ?"
            params.append(city)
        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        exporter = MailingLabelsExporter(output_dir=exports_dir)
        filename = exporter.export_mailing_labels(locations)

        return send_file(
            filename,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/calling-list', methods=['POST'])
    def export_calling_list():
        """Export cold calling list PDF"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        limit = data.get('limit', 100)

        conn = fleet_manager._get_conn()

        query = """
            SELECT fl.*, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE fl.phone IS NOT NULL AND fl.phone != ''
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND fl.id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND fl.city = ?"
            params.append(city)
        if state:
            query += " AND fl.state = ?"
            params.append(state)

        query += " ORDER BY fl.estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add priority scores
        for loc in locations:
            loc['priority_score'] = min(100, (loc.get('estimated_vehicles', 0) / 5) + 30)
            loc['estimated_revenue'] = loc.get('estimated_vehicles', 0) * 1500

        exporter = CallingListExporter(output_dir=exports_dir)
        filename = exporter.export_calling_list(locations)

        return send_file(
            filename,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/quick-dial', methods=['POST'])
    def export_quick_dial():
        """Export compact quick dial list PDF"""
        data = request.get_json() or {}
        city = data.get('city')
        state = data.get('state')
        limit = data.get('limit', 200)

        conn = fleet_manager._get_conn()

        query = """
            SELECT * FROM fleet_locations
            WHERE phone IS NOT NULL AND phone != ''
        """
        params = []

        if city:
            query += " AND city = ?"
            params.append(city)
        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        for loc in locations:
            loc['priority_score'] = min(100, (loc.get('estimated_vehicles', 0) / 5) + 30)

        exporter = CallingListExporter(output_dir=exports_dir)
        filename = exporter.export_quick_dial_list(locations)

        return send_file(
            filename,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    # ====================
    # Part 2: Marketing Automation Exports
    # ====================

    @app.route('/api/fleet/export/direct-mail', methods=['POST'])
    def export_direct_mail():
        """Export personalized direct mail letters (Word doc)"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        limit = data.get('limit', 50)

        # Company info from request or defaults
        company_info = data.get('company_info', {
            'name': 'Your PDR Company',
            'phone': '(555) 123-4567',
            'email': 'contact@yourpdr.com',
            'website': 'www.yourpdr.com',
            'address': ''
        })

        # Hail event info
        hail_event = data.get('hail_event', {
            'date': datetime.now().strftime('%B %d, %Y'),
            'location': city or 'your area',
            'hail_size_inches': 0
        })

        conn = fleet_manager._get_conn()

        query = """
            SELECT * FROM fleet_locations
            WHERE address IS NOT NULL AND address != ''
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND city = ?"
            params.append(city)
        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add hail size if event provided
        hail_size = hail_event.get('hail_size_inches', 0)
        for loc in locations:
            loc['hail_size_inches'] = hail_size
            loc['estimated_revenue'] = loc.get('estimated_vehicles', 0) * 1500

        exporter = DirectMailExporter(output_dir=exports_dir)
        filename = exporter.export_direct_mail(locations, company_info, hail_event)

        return send_file(
            filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/email-campaign', methods=['POST'])
    def export_email_campaign():
        """Export email campaign CSV (MailChimp, Constant Contact, or generic)"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        platform = data.get('platform', 'mailchimp')
        limit = data.get('limit', 500)

        conn = fleet_manager._get_conn()

        query = """
            SELECT fl.*, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE fl.email IS NOT NULL AND fl.email != ''
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND fl.id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND fl.city = ?"
            params.append(city)
        if state:
            query += " AND fl.state = ?"
            params.append(state)

        query += " ORDER BY fl.estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add computed fields
        hail_size = data.get('hail_size_inches', 0)
        for loc in locations:
            loc['hail_size_inches'] = hail_size
            loc['priority_score'] = min(100, (loc.get('estimated_vehicles', 0) / 5) + 30)
            loc['estimated_revenue'] = loc.get('estimated_vehicles', 0) * 1500

        exporter = EmailCampaignExporter(output_dir=exports_dir)
        filename = exporter.export_email_campaign(locations, platform=platform)

        return send_file(
            filename,
            mimetype='text/csv',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/sms-campaign', methods=['POST'])
    def export_sms_campaign():
        """Export SMS campaign CSV (Twilio, EZTexting, SimpleTexting, or generic)"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        platform = data.get('platform', 'twilio')
        message_template = data.get('message_template')
        limit = data.get('limit', 500)

        conn = fleet_manager._get_conn()

        query = """
            SELECT fl.*, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE fl.phone IS NOT NULL AND fl.phone != ''
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND fl.id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND fl.city = ?"
            params.append(city)
        if state:
            query += " AND fl.state = ?"
            params.append(state)

        query += " ORDER BY fl.estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add computed fields
        hail_size = data.get('hail_size_inches', 0)
        for loc in locations:
            loc['hail_size_inches'] = hail_size
            loc['priority_score'] = min(100, (loc.get('estimated_vehicles', 0) / 5) + 30)
            loc['estimated_revenue'] = loc.get('estimated_vehicles', 0) * 1500

        exporter = SMSCampaignExporter(output_dir=exports_dir)
        filename = exporter.export_sms_campaign(locations, platform=platform, message_template=message_template)

        return send_file(
            filename,
            mimetype='text/csv',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/maps-routes', methods=['POST'])
    def export_maps_routes():
        """Export Google Maps route links"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        city = data.get('city')
        state = data.get('state')
        routes_per_day = data.get('routes_per_day', 10)
        optimize = data.get('optimize', True)
        limit = data.get('limit', 100)

        conn = fleet_manager._get_conn()

        query = """
            SELECT fl.*, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE fl.address IS NOT NULL AND fl.address != ''
        """
        params = []

        if location_ids:
            placeholders = ','.join('?' * len(location_ids))
            query += f" AND fl.id IN ({placeholders})"
            params.extend(location_ids)
        if city:
            query += " AND fl.city = ?"
            params.append(city)
        if state:
            query += " AND fl.state = ?"
            params.append(state)

        query += " ORDER BY fl.estimated_vehicles DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        # Add computed fields
        for loc in locations:
            loc['priority_score'] = min(100, (loc.get('estimated_vehicles', 0) / 5) + 30)
            loc['estimated_revenue'] = loc.get('estimated_vehicles', 0) * 1500

        exporter = MapsRoutesExporter(output_dir=exports_dir)
        filename = exporter.export_routes(locations, routes_per_day=routes_per_day, optimize=optimize)

        return send_file(
            filename,
            mimetype='text/csv',
            as_attachment=True,
            download_name=os.path.basename(filename)
        )

    @app.route('/api/fleet/export/single-route', methods=['POST'])
    def export_single_route():
        """Generate a single Google Maps route URL"""
        data = request.get_json() or {}
        location_ids = data.get('location_ids', [])
        optimize = data.get('optimize', True)

        if not location_ids:
            return jsonify({'error': 'location_ids required'}), 400

        if len(location_ids) > 25:
            return jsonify({'error': 'Maximum 25 locations per route'}), 400

        conn = fleet_manager._get_conn()
        placeholders = ','.join('?' * len(location_ids))
        rows = conn.execute(f"""
            SELECT * FROM fleet_locations
            WHERE id IN ({placeholders})
        """, location_ids).fetchall()
        conn.close()

        locations = [dict(row) for row in rows]

        exporter = MapsRoutesExporter(output_dir=exports_dir)
        route = exporter.export_single_route(locations, optimize=optimize)

        return jsonify(route)

    # ====================
    # CRM Routes
    # ====================

    from src.web.routes.crm import crm_bp
    app.register_blueprint(crm_bp)
    logger.info("CRM routes registered")

    # Debug: print CRM routes
    crm_routes = [r.rule for r in app.url_map.iter_rules() if 'crm' in r.rule]
    logger.info(f"CRM routes count: {len(crm_routes)}")
    for route in crm_routes[:5]:
        logger.info(f"  Route: {route}")

    # ====================
    # Auth Routes
    # ====================

    from src.web.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("Auth routes registered")

    # ====================
    # Home Routes
    # ====================

    from src.web.routes.home import home_bp
    app.register_blueprint(home_bp)
    logger.info("Home routes registered")

    # ====================
    # Admin Routes
    # ====================

    from src.web.routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    logger.info("Admin routes registered")

    # ====================
    # Elite Sales Routes
    # ====================

    from src.web.routes.elite_sales import elite_sales_bp
    app.register_blueprint(elite_sales_bp)
    logger.info("Elite Sales routes registered")

    # ====================
    # Mobile App Routes
    # ====================

    from src.web.routes.mobile import mobile_bp
    app.register_blueprint(mobile_bp)
    logger.info("Mobile app routes registered")

    # ====================
    # Customer Portal Routes
    # ====================

    from src.web.routes.customer_portal import customer_portal_bp
    app.register_blueprint(customer_portal_bp)
    logger.info("Customer Portal routes registered")

    # ====================
    # Customer Intake Routes (Public tablet form)
    # ====================

    from src.web.routes.customer_intake import customer_intake_bp
    app.register_blueprint(customer_intake_bp)
    logger.info("Customer Intake routes registered")

    # ====================
    # Kiosk Routes (Tablet walk-in intake)
    # ====================

    from src.web.routes.kiosk import kiosk_bp
    app.register_blueprint(kiosk_bp)
    logger.info("Kiosk routes registered")

    # ====================
    # Scheduling API Routes
    # ====================

    from src.web.routes.scheduling import scheduling_bp
    app.register_blueprint(scheduling_bp)
    logger.info("Scheduling API routes registered")

    # ====================
    # Self-Scheduling Routes (Public)
    # ====================

    from src.web.routes.self_schedule import self_schedule_bp
    app.register_blueprint(self_schedule_bp)
    logger.info("Self-scheduling routes registered")

    # ====================
    # Tech App API Routes
    # ====================

    from src.web.routes.tech_api import tech_api_bp
    app.register_blueprint(tech_api_bp)
    logger.info("Tech API routes registered at /api/tech")

    # ====================
    # Leads API Routes
    # ====================

    from src.web.routes.leads_api import leads_api_bp
    app.register_blueprint(leads_api_bp)
    logger.info("Leads API routes registered at /api/leads")

    # ====================
    # Jobs API Routes
    # ====================

    from src.web.routes.jobs_api import jobs_api_bp
    app.register_blueprint(jobs_api_bp)
    logger.info("Jobs API routes registered at /api/jobs")

    # ====================
    # Customers API Routes
    # ====================

    from src.web.routes.customers_api import customers_api_bp
    app.register_blueprint(customers_api_bp)
    logger.info("Customers API routes registered at /api/customers")

    # ====================
    # Vehicles API Routes
    # ====================

    from src.web.routes.vehicles_api import vehicles_api_bp
    app.register_blueprint(vehicles_api_bp)
    logger.info("Vehicles API routes registered at /api/vehicles")

    # ====================
    # Estimates API Routes
    # ====================

    from src.web.routes.estimates_api import estimates_api_bp
    app.register_blueprint(estimates_api_bp)
    logger.info("Estimates API routes registered at /api/estimates")

    # ====================
    # Admin API Routes
    # ====================

    from src.web.routes.admin_api import admin_api_bp
    app.register_blueprint(admin_api_bp)
    logger.info("Admin API routes registered at /api/admin")

    # ====================
    # Reports API Routes
    # ====================

    from src.web.routes.reports_api import reports_api_bp
    app.register_blueprint(reports_api_bp)
    logger.info("Reports API routes registered at /api/reports")

    # ====================
    # Notifications API Routes
    # ====================

    from src.web.routes.notifications_api import notifications_api_bp
    app.register_blueprint(notifications_api_bp)
    logger.info("Notifications API routes registered at /api/notifications")

    # ====================
    # Search API Routes
    # ====================

    from src.web.routes.search_api import search_api_bp
    app.register_blueprint(search_api_bp)
    logger.info("Search API routes registered at /api/search")

    # ====================
    # Hail Events API Routes
    # ====================

    from src.web.routes.hail_events_api import hail_events_api_bp
    app.register_blueprint(hail_events_api_bp)
    logger.info("Hail Events API routes registered at /api/hail-events")

    # ====================
    # Invoices API Routes
    # ====================

    from src.web.routes.invoices_api import invoices_api_bp
    app.register_blueprint(invoices_api_bp)
    logger.info("Invoices API routes registered at /api/invoices")

    # ====================
    # Claims API Routes
    # ====================

    from src.web.routes.claims_api import claims_api_bp
    app.register_blueprint(claims_api_bp)
    logger.info("Claims API routes registered at /api/claims")

    # ====================
    # Parts API Routes
    # ====================

    from src.web.routes.parts_api import parts_api_bp
    app.register_blueprint(parts_api_bp)
    logger.info("Parts API routes registered at /api/parts")

    # ====================
    # R&I API Routes
    # ====================

    from src.web.routes.ri_api import ri_api_bp
    app.register_blueprint(ri_api_bp)
    logger.info("R&I API routes registered at /api/ri")

    # Storm Cell Tracking API Routes
    from src.web.routes.storm_tracking_api import storm_tracking_api_bp
    app.register_blueprint(storm_tracking_api_bp)
    logger.info("Storm Cell Tracking API routes registered at /api/storm-cells")

    # Storm Monitor API Routes
    from src.web.routes.storm_monitor_api import storm_monitor_api_bp
    app.register_blueprint(storm_monitor_api_bp)
    logger.info("Storm Monitor API routes registered at /api/storm-monitor")

    # ML Models API Routes
    from src.web.routes.ml_api import ml_api_bp
    app.register_blueprint(ml_api_bp)
    logger.info("ML API routes registered at /api/ml")

    # Job-Storm Linking Routes (from hail_events_api)
    from src.web.routes.hail_events_api import jobs_storm_bp
    app.register_blueprint(jobs_storm_bp)
    logger.info("Jobs-Storm linking routes registered at /api/jobs")

    # Fleet Locations API Routes (business prospects)
    from src.web.routes.fleet_locations_api import fleet_locations_api_bp
    app.register_blueprint(fleet_locations_api_bp)
    logger.info("Fleet Locations API routes registered at /api/fleet-locations")

    # ====================
    # Unified App Routes (Main Application)
    # ====================

    from src.web.routes.app_main import app_bp
    from src.core.auth.middleware import TenantMiddleware
    from src.core.auth.auth_manager import AuthManager as TenantAuthManager

    # Setup tenant auth middleware for unified app routes
    tenant_auth_manager = TenantAuthManager()
    TenantMiddleware(app, tenant_auth_manager)

    app.register_blueprint(app_bp)
    logger.info("Unified App routes registered at /app")

    return app


# Run directly
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
