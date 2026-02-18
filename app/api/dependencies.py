"""
JWT-based auth: Resource Server validates tokens from Auth Service using RS256.
No API key, no DB access — only cryptographic signature verification (Zero Trust).
"""
import logging

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=True)


def _normalize_pem_public_key(key_str: str) -> str:
    """
    Ensure PEM format for RSA public key.
    If key comes from AWS SSM as a single line (no -----BEGIN/END-----), add delimiters
    and wrap body to 64 chars per line so PyJWT/crypto can parse it.
    """
    key_str = (key_str or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if not key_str:
        raise ValueError("JWT_PUBLIC_KEY is empty")

    if "-----BEGIN" in key_str and "-----END" in key_str:
        return key_str

    # Single line from env/SSM: assume raw base64 body
    body = key_str.replace(" ", "").replace("\n", "")
    if not body:
        raise ValueError("JWT_PUBLIC_KEY has no key body")
    lines = [body[i : i + 64] for i in range(0, len(body), 64)]
    return "-----BEGIN PUBLIC KEY-----\n" + "\n".join(lines) + "\n-----END PUBLIC KEY-----"


def _get_public_key_for_verify() -> str:
    """Return normalized PEM public key for jwt.decode."""
    settings = get_settings()
    raw = settings.JWT_PUBLIC_KEY.get_secret_value()
    return _normalize_pem_public_key(raw)


def _is_admin(payload: dict) -> bool:
    """Check if JWT payload has admin/superuser permission."""
    if payload.get("is_superuser") is True:
        return True
    roles = payload.get("roles")
    if isinstance(roles, list) and "admin" in roles:
        return True
    if isinstance(roles, str) and roles == "admin":
        return True
    return False


async def get_current_superuser(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate JWT from Authorization: Bearer <token>.
    - Verifies signature with Auth Service public key (RS256).
    - Validates exp (and optional nbf, iat via PyJWT).
    - Ensures user has admin/superuser permission.
    Returns the token payload; raises 401/403 otherwise.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    try:
        public_key = _get_public_key_for_verify()
        settings = get_settings()
        algorithm = settings.JWT_ALGORITHM or "RS256"
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "require": ["exp"],
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        logger.debug("Invalid JWT: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except ValueError as e:
        logger.warning("JWT key config error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth configuration error",
        )

    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or superuser role required",
        )

    return payload


async def validate_admin_key(
    x_admin_api_key: str | None = Header(None, alias="X-Admin-API-Key"),
) -> None:
    """
    Valida l'API Key per le operazioni admin (es. reindex).
    Richiede l'header X-Admin-API-Key con valore uguale a SEARCH_ADMIN_API_KEY.
    Se manca o non corrisponde, solleva 403 Forbidden.
    """
    settings = get_settings()
    expected = settings.SEARCH_ADMIN_API_KEY.get_secret_value()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key not configured",
        )
    if not x_admin_api_key or x_admin_api_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-API-Key",
        )
