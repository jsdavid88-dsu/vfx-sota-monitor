"""FastAPI entry point for VFX SOTA Monitor."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, categories, items, stats
from app.tasks import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start daily scheduler (skip if running under alembic or test)
    if os.getenv("DISABLE_SCHEDULER") != "1":
        try:
            start_scheduler()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Scheduler start failed: {e}")

    yield

    try:
        shutdown_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="VFX SOTA Monitor API",
    version="0.2.0",
    description="Red Cat Gang VFX Team SOTA tracking system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router, prefix=settings.api_prefix)
app.include_router(items.router, prefix=settings.api_prefix)
app.include_router(stats.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {
        "name": "VFX SOTA Monitor",
        "version": "0.2.0",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
