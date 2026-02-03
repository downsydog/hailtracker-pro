"""
HailTracker Pro Flask Application
=================================
Multi-tenant SaaS for PDR fleet prospecting.
"""

from flask import Flask, jsonify
from .config import config
from .extensions import db, jwt, migrate, cors


def create_app(config_name='default'):
    """
    Application factory.

    Args:
        config_name: Configuration to use (development, production, default)

    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # ==========================================================================
    # JWT Error Handlers
    # ==========================================================================

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired tokens."""
        return jsonify({
            'error': 'Token has expired',
            'code': 'token_expired'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid tokens."""
        return jsonify({
            'error': 'Invalid token',
            'code': 'invalid_token'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handle missing tokens."""
        return jsonify({
            'error': 'Authorization token required',
            'code': 'authorization_required'
        }), 401

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        """Handle requests that need a fresh token."""
        return jsonify({
            'error': 'Fresh token required',
            'code': 'fresh_token_required'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """Handle revoked tokens."""
        return jsonify({
            'error': 'Token has been revoked',
            'code': 'token_revoked'
        }), 401

    # ==========================================================================
    # Error Handlers
    # ==========================================================================

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    # ==========================================================================
    # Health Check
    # ==========================================================================

    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'hailtracker-pro'
        }), 200

    @app.route('/api/health')
    def api_health_check():
        """API health check endpoint."""
        try:
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'

        return jsonify({
            'status': 'healthy',
            'database': db_status,
            'service': 'hailtracker-pro-api'
        }), 200

    # ==========================================================================
    # Register Blueprints
    # ==========================================================================

    from .api.auth import auth_bp
    from .api.admin import admin_bp
    from .api.customer import customer_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(customer_bp, url_prefix='/api')

    # ==========================================================================
    # Create Tables
    # ==========================================================================

    with app.app_context():
        db.create_all()

    return app
