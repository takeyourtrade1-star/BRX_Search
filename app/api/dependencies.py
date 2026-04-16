"""
Sicurezza admin: validazione API Key via header X-Admin-API-Key.
Nessun JWT: le operazioni admin (es. reindex) richiedono solo la chiave configurata.
"""
from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def validate_admin_key(
    x_admin_api_key: str | None = Header(None, alias="X-Admin-API-Key"),
) -> None:
    """
    Valida l'header X-Admin-API-Key contro SEARCH_ADMIN_API_KEY.
    Se la chiave è errata o manca, solleva 403 Forbidden.
    """
    settings = get_settings()
    expected = settings.SEARCH_ADMIN_API_KEY.get_secret_value()
    received = (x_admin_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SEARCH_ADMIN_API_KEY non configurata. Imposta la variabile d'ambiente e riavvia il servizio.",
        )
    if received != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chiave Admin non valida",
        )
