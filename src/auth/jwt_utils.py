"""
JWT Utilities for HailTracker Pro
Handles token generation, verification, and refresh
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'hailtracker-dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# DEV_MODE bypasses authentication when true
DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'


def generate_token(user_id: int, tenant_id: int, email: str, role: str,
                   name: str = None, expires_delta: timedelta = None) -> str:
    """
    Generate a JWT access token.

    Args:
        user_id: User's database ID
        tenant_id: User's tenant ID for multi-tenant scoping
        email: User's email address
        role: User's role (admin, manager, technician, viewer)
        name: User's display name
        expires_delta: Custom expiration time (default: 24 hours)

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = JWT_ACCESS_TOKEN_EXPIRES

    now = datetime.utcnow()
    payload = {
        'sub': str(user_id),  # JWT requires sub to be a string
        'user_id': user_id,   # Keep numeric ID for convenience
        'tenant_id': tenant_id,
        'email': email,
        'role': role,
        'name': name or email,
        'iat': now,
        'exp': now + expires_delta,
        'type': 'access'
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_id: int, tenant_id: int) -> str:
    """
    Generate a JWT refresh token (longer lived, used to get new access tokens).

    Args:
        user_id: User's database ID
        tenant_id: User's tenant ID

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.utcnow()
    payload = {
        'sub': str(user_id),  # JWT requires sub to be a string
        'user_id': user_id,   # Keep numeric ID for convenience
        'tenant_id': tenant_id,
        'iat': now,
        'exp': now + JWT_REFRESH_TOKEN_EXPIRES,
        'type': 'refresh'
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def refresh_token(refresh_token_str: str) -> Optional[Dict[str, str]]:
    """
    Use a refresh token to generate a new access token.

    Args:
        refresh_token_str: Valid refresh token

    Returns:
        Dict with new access_token and refresh_token, or None if invalid
    """
    payload = verify_token(refresh_token_str)

    if not payload:
        return None

    if payload.get('type') != 'refresh':
        return None

    # Need to look up user to get current role/email
    # For now, return minimal tokens - auth_routes will handle full refresh
    user_id = payload.get('sub')
    tenant_id = payload.get('tenant_id')

    if not user_id or not tenant_id:
        return None

    return {
        'user_id': user_id,
        'tenant_id': tenant_id
    }


def get_dev_user() -> Dict[str, Any]:
    """
    Get a development mode user for bypassing auth.
    Used when DEV_MODE=true.

    Returns:
        Dict with dev user info including token
    """
    dev_user = {
        'user_id': 1,
        'tenant_id': 1,
        'email': 'dev@hailtrackerpro.com',
        'role': 'admin',
        'name': 'Dev Admin'
    }

    token = generate_token(
        user_id=dev_user['user_id'],
        tenant_id=dev_user['tenant_id'],
        email=dev_user['email'],
        role=dev_user['role'],
        name=dev_user['name']
    )

    dev_user['token'] = token
    dev_user['refresh_token'] = generate_refresh_token(dev_user['user_id'], dev_user['tenant_id'])

    return dev_user
