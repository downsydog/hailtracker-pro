"""
Web Dashboard for HailTracker Pro Alerts

Flask-based web interface for monitoring storm alerts in real-time.
"""

import os
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, render_template, jsonify, request, Response
import queue

from .alert_manager import Alert, AlertLevel, AlertManager


class WebDashboard:
    """
    Web dashboard for real-time alert monitoring.

    Features:
    - Real-time alert display with auto-refresh
    - Interactive map showing alert locations
    - Alert statistics and history
    - Server-Sent Events for live updates
    """

    def __init__(
        self,
        alert_manager: Optional[AlertManager] = None,
        host: str = '127.0.0.1',
        port: int = 5000,
        debug: bool = False
    ):
        """
        Initialize web dashboard.

        Args:
            alert_manager: AlertManager instance to monitor
            host: Host to bind to
            port: Port to listen on
            debug: Enable Flask debug mode
        """
        self.alert_manager = alert_manager or AlertManager()
        self.host = host
        self.port = port
        self.debug = debug

        # Alert queue for SSE
        self.alert_queues: List[queue.Queue] = []
        self.alerts: List[Dict] = []
        self.max_alerts = 100

        # Create Flask app
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static')
        )

        # Register routes
        self._register_routes()

        # Register as notifier
        self.alert_manager.add_notifier(self._handle_alert)

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('dashboard.html')

        @self.app.route('/api/alerts')
        def get_alerts():
            """Get all alerts."""
            return jsonify({
                'alerts': self.alerts,
                'count': len(self.alerts)
            })

        @self.app.route('/api/alerts/recent')
        def get_recent_alerts():
            """Get recent alerts (last hour)."""
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent = [
                a for a in self.alerts
                if datetime.fromisoformat(a['timestamp']) > one_hour_ago
            ]
            return jsonify({
                'alerts': recent,
                'count': len(recent)
            })

        @self.app.route('/api/alerts/active')
        def get_active_alerts():
            """Get active (non-expired) alerts."""
            now = datetime.now()
            active = [
                a for a in self.alerts
                if a.get('expires') and datetime.fromisoformat(a['expires']) > now
            ]
            return jsonify({
                'alerts': active,
                'count': len(active)
            })

        @self.app.route('/api/stats')
        def get_stats():
            """Get alert statistics."""
            stats = {
                'total': len(self.alerts),
                'critical': sum(1 for a in self.alerts if a['level'] == 'CRITICAL'),
                'warning': sum(1 for a in self.alerts if a['level'] == 'WARNING'),
                'watch': sum(1 for a in self.alerts if a['level'] == 'WATCH'),
                'info': sum(1 for a in self.alerts if a['level'] == 'INFO'),
            }

            if self.alerts:
                stats['avg_pdr_score'] = sum(a['pdr_score'] for a in self.alerts) / len(self.alerts)
                stats['max_hail_size'] = max(a['hail']['size_mm'] for a in self.alerts)

                # Recent alerts (last hour)
                one_hour_ago = datetime.now() - timedelta(hours=1)
                stats['recent_count'] = sum(
                    1 for a in self.alerts
                    if datetime.fromisoformat(a['timestamp']) > one_hour_ago
                )
            else:
                stats['avg_pdr_score'] = 0
                stats['max_hail_size'] = 0
                stats['recent_count'] = 0

            return jsonify(stats)

        @self.app.route('/api/stream')
        def stream():
            """Server-Sent Events stream for real-time updates."""
            def generate():
                q = queue.Queue()
                self.alert_queues.append(q)
                try:
                    while True:
                        try:
                            alert = q.get(timeout=30)
                            yield f"data: {json.dumps(alert)}\n\n"
                        except queue.Empty:
                            # Send keepalive
                            yield f": keepalive\n\n"
                except GeneratorExit:
                    self.alert_queues.remove(q)

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                }
            )

        @self.app.route('/api/test-alert', methods=['POST'])
        def test_alert():
            """Generate a test alert."""
            level = request.json.get('level', 'INFO') if request.json else 'INFO'

            from .alert_manager import Alert, AlertLevel

            level_map = {
                'INFO': AlertLevel.INFO,
                'WATCH': AlertLevel.WATCH,
                'WARNING': AlertLevel.WARNING,
                'CRITICAL': AlertLevel.CRITICAL
            }

            alert = Alert(
                id=f"TEST-{datetime.now().strftime('%H%M%S')}",
                timestamp=datetime.now(),
                level=level_map.get(level, AlertLevel.INFO),
                event_name=f"Test {level} Alert",
                location=(32.7767 + (hash(level) % 10) * 0.1, -96.7970 + (hash(level) % 10) * 0.1),
                radar_id='KFWS',
                hail_detected=level in ['WARNING', 'CRITICAL'],
                hail_probability=25 + hash(level) % 75,
                hail_size_mm=10 + hash(level) % 50,
                severity='moderate' if level in ['WARNING', 'CRITICAL'] else 'light',
                pdr_score=30 + hash(level) % 60,
                max_reflectivity=50 + hash(level) % 25,
                mesh_mm=15 + hash(level) % 40,
                posh=40 + hash(level) % 50,
                message=f"This is a test {level} alert",
                recommendations=["Monitor conditions", "This is a test"]
            )

            self._handle_alert(alert)
            return jsonify({'status': 'ok', 'alert_id': alert.id})

    def _handle_alert(self, alert: Alert):
        """Handle incoming alert."""
        alert_dict = alert.to_dict()

        # Add to history
        self.alerts.insert(0, alert_dict)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[:self.max_alerts]

        # Broadcast to SSE clients
        for q in self.alert_queues:
            try:
                q.put_nowait(alert_dict)
            except queue.Full:
                pass

    def add_alert(self, alert: Alert):
        """Manually add an alert."""
        self._handle_alert(alert)

    def run(self, threaded: bool = True):
        """
        Start the web dashboard.

        Args:
            threaded: Run in a background thread
        """
        if threaded:
            thread = threading.Thread(
                target=lambda: self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=self.debug,
                    use_reloader=False,
                    threaded=True
                )
            )
            thread.daemon = True
            thread.start()
            print(f"Dashboard running at http://{self.host}:{self.port}")
            return thread
        else:
            print(f"Starting dashboard at http://{self.host}:{self.port}")
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                threaded=True
            )


def create_app(alert_manager: Optional[AlertManager] = None) -> Flask:
    """Create Flask app for WSGI deployment."""
    dashboard = WebDashboard(alert_manager)
    return dashboard.app
