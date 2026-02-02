from fastapi import APIRouter, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse

from app.api.dependencies import require_admin_api_key
from app.infrastructure.search.indexer import run_indexer
import logging

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


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
    dependencies=[Depends(require_admin_api_key)],
    summary="Trigger full reindex (Async)",
    status_code=status.HTTP_202_ACCEPTED
)
async def reindex(background_tasks: BackgroundTasks) -> JSONResponse:
    # Lancia il processo in background e risponde SUBITO
    background_tasks.add_task(background_reindex)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "message": "Reindexing started in background. Check logs for progress."
        },
    )
