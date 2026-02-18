import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, health
from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Search microservice: Meilisearch indexer for Trading Card Marketplace",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

def _cors_origins() -> list[str]:
    if settings.CORS_ORIGINS.strip() == "*":
        return ["*"]
    if settings.CORS_ORIGINS.strip():
        return [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if settings.DEBUG:
        return ["*"]
    return []


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }
