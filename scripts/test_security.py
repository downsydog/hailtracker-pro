#!/usr/bin/env python3
"""
Offline test for security hardening (HARDEN-5).

Verifies:
  - Import succeeds
  - apply_security() doesn't crash (even without flask-limiter/flask-cors)
  - Secure cookie config applied
  - Security headers added to responses
  - Dev mode relaxes settings

Usage:
    python scripts/test_security.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("SECURITY OFFLINE TEST (HARDEN-5)")
    print("=" * 60)

    # --- 1) Import ---
    print("\n[1] Import check...")
    from src.security.hardening import apply_security
    print("    OK: apply_security imported")

    # --- 2) Apply to a test Flask app (dev mode) ---
    print("\n[2] Apply security (dev mode)...")
    os.environ['DEV_MODE'] = 'true'
    os.environ.pop('RATE_LIMIT_DEFAULT', None)
    os.environ.pop('CORS_ORIGINS', None)

    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'

    @app.route('/test')
    def test_route():
        return 'ok'

    apply_security(app)

    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SECURE'] is False  # Dev mode
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    print("    OK: dev mode cookies configured")

    # --- 3) Security headers ---
    print("\n[3] Security headers...")
    with app.test_client() as client:
        resp = client.get('/test')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
        assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
        assert resp.headers.get('X-XSS-Protection') == '1; mode=block'
        assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
        # No HSTS in dev mode
        assert resp.headers.get('Strict-Transport-Security') is None
    print("    OK: security headers present, no HSTS in dev")

    # --- 4) Production mode ---
    print("\n[4] Apply security (production mode)...")
    os.environ['DEV_MODE'] = 'false'

    app2 = Flask(__name__)
    app2.config['SECRET_KEY'] = 'prod-secret'

    @app2.route('/test')
    def test_route2():
        return 'ok'

    apply_security(app2)

    assert app2.config['SESSION_COOKIE_SECURE'] is True  # Production
    assert app2.config['SESSION_COOKIE_HTTPONLY'] is True

    with app2.test_client() as client:
        resp = client.get('/test')
        hsts = resp.headers.get('Strict-Transport-Security')
        assert hsts is not None and 'max-age' in hsts
    print(f"    OK: production cookies secure=True, HSTS={hsts}")

    # --- 5) Rate limiting (graceful degradation) ---
    print("\n[5] Rate limiting graceful degradation...")
    os.environ['RATE_LIMIT_DEFAULT'] = '10/minute'
    app3 = Flask(__name__)
    app3.config['SECRET_KEY'] = 'test'
    # This should not crash even if flask-limiter is not installed
    apply_security(app3)
    has_limiter = 'limiter' in app3.extensions
    print(f"    OK: rate limiting {'active' if has_limiter else 'degraded (flask-limiter not installed)'}")

    # --- 6) CORS (graceful degradation) ---
    print("\n[6] CORS graceful degradation...")
    os.environ['CORS_ORIGINS'] = '*'
    app4 = Flask(__name__)
    app4.config['SECRET_KEY'] = 'test'
    apply_security(app4)
    print("    OK: CORS applied (or degraded gracefully)")

    # Clean up env
    os.environ.pop('RATE_LIMIT_DEFAULT', None)
    os.environ.pop('CORS_ORIGINS', None)
    os.environ.pop('DEV_MODE', None)

    print("\n" + "=" * 60)
    print("ALL SECURITY TESTS PASSED (HARDEN-5)")
    print("=" * 60)


if __name__ == '__main__':
    main()
