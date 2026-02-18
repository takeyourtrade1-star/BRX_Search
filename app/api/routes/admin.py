from fastapi import APIRouter, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse

from app.api.dependencies import validate_admin_key
from app.infrastructure.search.indexer import run_indexer
import logging

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get("", summary="Verifica endpoint admin")
async def admin_info() -> dict:
    """Permette di verificare che il servizio sia il Search Engine: GET /api/admin."""
    return {
        "service": "BRX Search (admin)",
        "reindex": "POST /api/admin/reindex con header X-Admin-API-Key",
    }


def background_reindex():
    """Wrapper per gestire eccezioni nel background task"""
    try:
        logger.info("Starting background reindex...")
        result = run_indexer()
        if result.get("error"):
            logger.error(f"Reindex failed: {result['error']}")
        else:
            logger.info(f"Reindex success: {result}")
    except Exception as e:
        logger.exception("Critical error during reindex")


@router.post(
    "/reindex",
    summary="Avvia reindex totale (async)",
    description="Avvia il reindex totale. Richiede l'header X-Admin-API-Key.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex(
    background_tasks: BackgroundTasks,
    _: None = Depends(validate_admin_key),
) -> JSONResponse:
    # Lancia il processo in background e risponde SUBITO
    background_tasks.add_task(background_reindex)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "message": "Reindexing started in background. Check logs for progress."
        },
    )
