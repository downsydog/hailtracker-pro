"""
Security Hardening for Flask

Applies:
  1. Rate limiting (if flask-limiter installed)
  2. CORS (if flask-cors installed)
  3. Secure cookie/session config
  4. Security headers via after_request

All behind env-driven config with safe defaults.

Environment:
    RATE_LIMIT_DEFAULT  - Default rate limit (e.g. '60/minute'). Empty = disabled.
    CORS_ORIGINS        - Allowed origins (comma-separated or '*'). Empty = disabled.
    DEV_MODE            - 'true' relaxes some settings for local dev.
    SECRET_KEY          - Required for secure sessions.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def apply_security(app):
    """
    Apply security hardening to a Flask app.

    Safe to call even if optional dependencies are not installed —
    each feature degrades gracefully.
    """
    dev_mode = os.environ.get('DEV_MODE', 'false').lower() in ('true', '1', 'yes')

    _apply_rate_limiting(app, dev_mode)
    _apply_cors(app, dev_mode)
    _apply_secure_cookies(app, dev_mode)
    _apply_security_headers(app, dev_mode)

    logger.info(
        "Security hardening applied (dev_mode=%s)", dev_mode
    )


def _apply_rate_limiting(app, dev_mode: bool):
    """Apply Flask-Limiter rate limiting."""
    limit = os.environ.get('RATE_LIMIT_DEFAULT', '')
    if not limit:
        logger.info("Rate limiting disabled (RATE_LIMIT_DEFAULT not set)")
        return

    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        limiter = Limiter(
            get_remote_address,
            app=app,
            default_limits=[limit],
            storage_uri='memory://',
        )
        app.extensions['limiter'] = limiter
        logger.info("Rate limiting enabled: %s", limit)
    except ImportError:
        logger.info(
            "flask-limiter not installed, rate limiting disabled. "
            "Install with: pip install Flask-Limiter"
        )


def _apply_cors(app, dev_mode: bool):
    """Apply Flask-CORS."""
    origins = os.environ.get('CORS_ORIGINS', '')
    if not origins:
        logger.info("CORS disabled (CORS_ORIGINS not set)")
        return

    try:
        from flask_cors import CORS

        origin_list = [o.strip() for o in origins.split(',')]
        CORS(app, origins=origin_list)
        logger.info("CORS enabled: origins=%s", origin_list)
    except ImportError:
        logger.info(
            "flask-cors not installed, CORS disabled. "
            "Install with: pip install Flask-CORS"
        )


def _apply_secure_cookies(app, dev_mode: bool):
    """Configure secure session/cookie settings."""
    if dev_mode:
        # Relaxed for local dev (HTTP, no domain restrictions)
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        logger.info("Cookies: dev mode (secure=False)")
    else:
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config.setdefault('PERMANENT_SESSION_LIFETIME', 3600)
        logger.info("Cookies: production mode (secure=True, httponly, samesite=Lax)")


def _apply_security_headers(app, dev_mode: bool):
    """Add security headers via after_request."""

    @app.after_request
    def add_security_headers(response):
        # Prevent MIME sniffing
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        # Clickjacking protection
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        # XSS protection (legacy, but harmless)
        response.headers.setdefault('X-XSS-Protection', '1; mode=block')
        # Referrer policy
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')

        if not dev_mode:
            # HSTS in production (1 year)
            response.headers.setdefault(
                'Strict-Transport-Security',
                'max-age=31536000; includeSubDomains'
            )

        return response

    logger.info("Security headers registered (HSTS=%s)", not dev_mode)
