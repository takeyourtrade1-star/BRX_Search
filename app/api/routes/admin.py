from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies import require_admin_api_key
from app.infrastructure.search.indexer import run_indexer

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post(
    "/reindex",
    dependencies=[Depends(require_admin_api_key)],
    summary="Trigger full reindex",
    description="Indexes all card prints (MTG, OP, PK) from MySQL into Meilisearch. Protected by X-Admin-Key.",
)
async def reindex() -> JSONResponse:
    result = run_indexer()
    if result.get("error"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "message": result["error"],
                "counts": {
                    "mtg": result.get("mtg", 0),
                    "op": result.get("op", 0),
                    "pk": result.get("pk", 0),
                    "total": result.get("total", 0),
                },
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "message": "Reindex completed",
            "counts": {
                "mtg": result["mtg"],
                "op": result["op"],
                "pk": result["pk"],
                "total": result["total"],
            },
        },
    )
