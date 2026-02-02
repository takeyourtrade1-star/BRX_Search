from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "service": "search-engine"},
    )


@router.get("/health/live")
async def liveness_check() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "alive"},
    )
