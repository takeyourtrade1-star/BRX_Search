from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_admin_api_key(
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> None:
    """
    Protect admin routes (e.g. reindex) with API key from env.
    SEARCH_ADMIN_API_KEY is required; X-Admin-Key header must match.
    """
    settings = get_settings()
    expected = settings.SEARCH_ADMIN_API_KEY.get_secret_value()
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )
