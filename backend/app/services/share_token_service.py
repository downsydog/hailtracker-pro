"""
Share Token Service

Generates and verifies cryptographically signed tokens for sharing estimates
with external parties (adjusters, customers) without requiring authentication.

Security:
- Uses JWT with HS256 signing
- Tokens are scoped to tenant_id + estimate_id
- Tokens have configurable expiration (default 14 days)
- Permissions are embedded in the token payload
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


# Secret key for signing tokens - should be set via environment variable
# Falls back to a default for development only
SHARE_TOKEN_SECRET = os.environ.get('SHARE_TOKEN_SECRET', 'dev-share-secret-key-change-in-production')

# Token configuration
DEFAULT_EXPIRY_DAYS = 14
MAX_EXPIRY_DAYS = 90


@dataclass
class ShareTokenPayload:
    """Decoded share token payload."""
    tenant_id: int
    estimate_id: int
    allow_estimate_pdf: bool
    allow_photosheet: bool
    allow_dispute_pack: bool
    allow_supplements: bool
    allow_signing: bool  # New: allow customer signature
    expires_at: datetime
    created_at: datetime
    created_by: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tenant_id': self.tenant_id,
            'estimate_id': self.estimate_id,
            'allow_estimate_pdf': self.allow_estimate_pdf,
            'allow_photosheet': self.allow_photosheet,
            'allow_dispute_pack': self.allow_dispute_pack,
            'allow_supplements': self.allow_supplements,
            'allow_signing': self.allow_signing,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }


@dataclass
class ShareTokenResult:
    """Result of token creation."""
    token: str
    expires_at: datetime
    url: str
    payload: ShareTokenPayload


class ShareTokenError(Exception):
    """Base exception for share token errors."""
    pass


class TokenExpiredError(ShareTokenError):
    """Token has expired."""
    pass


class TokenInvalidError(ShareTokenError):
    """Token is invalid or malformed."""
    pass


class TokenPermissionError(ShareTokenError):
    """Token does not have required permission."""
    pass


def create_estimate_share_token(
    tenant_id: int,
    estimate_id: int,
    expires_in_days: int = DEFAULT_EXPIRY_DAYS,
    allow_estimate_pdf: bool = True,
    allow_photosheet: bool = True,
    allow_dispute_pack: bool = True,
    allow_supplements: bool = True,
    allow_signing: bool = False,
    created_by: Optional[int] = None,
    base_url: Optional[str] = None
) -> ShareTokenResult:
    """
    Create a share token for an estimate.

    Args:
        tenant_id: Tenant ID (for multi-tenant isolation)
        estimate_id: Estimate ID to share
        expires_in_days: Token expiration in days (default 14, max 90)
        allow_estimate_pdf: Allow downloading estimate PDF
        allow_photosheet: Allow downloading photo sheet PDF
        allow_dispute_pack: Allow downloading dispute pack ZIP
        allow_supplements: Allow viewing/downloading supplements
        allow_signing: Allow customer signature on estimate
        created_by: User ID who created the token
        base_url: Base URL for constructing share link (e.g., "https://app.example.com")

    Returns:
        ShareTokenResult with token, expiration, and URL
    """
    # Validate expiry
    if expires_in_days < 1:
        expires_in_days = 1
    if expires_in_days > MAX_EXPIRY_DAYS:
        expires_in_days = MAX_EXPIRY_DAYS

    now = datetime.utcnow()
    expires_at = now + timedelta(days=expires_in_days)

    # Build payload
    payload = {
        'type': 'estimate_share',
        'tid': tenant_id,  # Short keys to keep token smaller
        'eid': estimate_id,
        'pdf': allow_estimate_pdf,
        'ps': allow_photosheet,
        'dp': allow_dispute_pack,
        'sup': allow_supplements,
        'sig': allow_signing,  # New: signing permission
        'exp': int(expires_at.timestamp()),
        'iat': int(now.timestamp()),
        'cby': created_by
    }

    # Sign token
    token = jwt.encode(payload, SHARE_TOKEN_SECRET, algorithm='HS256')

    # Build URL
    if base_url is None:
        base_url = os.environ.get('APP_BASE_URL', 'http://localhost:5173')
    url = f"{base_url.rstrip('/')}/share/estimate/{token}"

    # Create payload object for logging
    token_payload = ShareTokenPayload(
        tenant_id=tenant_id,
        estimate_id=estimate_id,
        allow_estimate_pdf=allow_estimate_pdf,
        allow_photosheet=allow_photosheet,
        allow_dispute_pack=allow_dispute_pack,
        allow_supplements=allow_supplements,
        allow_signing=allow_signing,
        expires_at=expires_at,
        created_at=now,
        created_by=created_by
    )

    return ShareTokenResult(
        token=token,
        expires_at=expires_at,
        url=url,
        payload=token_payload
    )


def verify_estimate_share_token(token: str) -> ShareTokenPayload:
    """
    Verify and decode a share token.

    Args:
        token: The JWT token string

    Returns:
        ShareTokenPayload with decoded data

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid or malformed
    """
    try:
        # Decode and verify
        payload = jwt.decode(token, SHARE_TOKEN_SECRET, algorithms=['HS256'])

        # Validate token type
        if payload.get('type') != 'estimate_share':
            raise TokenInvalidError("Invalid token type")

        # Check expiration (JWT library should handle this, but double-check)
        exp_timestamp = payload.get('exp', 0)
        if datetime.utcnow().timestamp() > exp_timestamp:
            raise TokenExpiredError("Share link has expired")

        # Build payload object
        return ShareTokenPayload(
            tenant_id=payload['tid'],
            estimate_id=payload['eid'],
            allow_estimate_pdf=payload.get('pdf', True),
            allow_photosheet=payload.get('ps', True),
            allow_dispute_pack=payload.get('dp', True),
            allow_supplements=payload.get('sup', True),
            allow_signing=payload.get('sig', False),
            expires_at=datetime.fromtimestamp(exp_timestamp),
            created_at=datetime.fromtimestamp(payload.get('iat', 0)),
            created_by=payload.get('cby')
        )

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Share link has expired")
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid share token: {str(e)}")
    except KeyError as e:
        raise TokenInvalidError(f"Malformed share token: missing {e}")


def check_token_permission(payload: ShareTokenPayload, permission: str) -> bool:
    """
    Check if a token has a specific permission.

    Args:
        payload: Decoded token payload
        permission: Permission to check ('estimate_pdf', 'photosheet', 'dispute_pack', 'supplements', 'signing')

    Returns:
        True if permission is granted
    """
    permission_map = {
        'estimate_pdf': payload.allow_estimate_pdf,
        'photosheet': payload.allow_photosheet,
        'dispute_pack': payload.allow_dispute_pack,
        'supplements': payload.allow_supplements,
        'signing': payload.allow_signing
    }
    return permission_map.get(permission, False)


def require_token_permission(payload: ShareTokenPayload, permission: str) -> None:
    """
    Require a specific permission or raise error.

    Args:
        payload: Decoded token payload
        permission: Required permission

    Raises:
        TokenPermissionError: If permission not granted
    """
    if not check_token_permission(payload, permission):
        raise TokenPermissionError(f"This share link does not include access to {permission}")
