"""
Security Module

Provides:
  - Rate limiting (Flask-Limiter, optional)
  - CORS (Flask-CORS, optional)
  - Secure cookie / session configuration
  - apply_security(app) — single call to harden a Flask app
"""

from .hardening import apply_security

__all__ = ['apply_security']
