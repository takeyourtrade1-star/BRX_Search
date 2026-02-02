from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_admin_api_key(
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> None:
    """
    Protect admin routes (e.g. reindex) with an API key.
    If SEARCH_ADMIN_API_KEY is not set, the route is unprotected (dev only).
    """
    settings = get_settings()
    if not settings.SEARCH_ADMIN_API_KEY:
        return
    if not x_admin_key or x_admin_key != settings.SEARCH_ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )
