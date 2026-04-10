"""FastAPI entry point for VFX SOTA Monitor."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import categories, items, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup hook (scheduler setup goes here later)
    yield
    # Shutdown hook


app = FastAPI(
    title="VFX SOTA Monitor API",
    version="0.1.0",
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


@app.get("/")
async def root():
    return {"name": "VFX SOTA Monitor", "version": "0.1.0", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
