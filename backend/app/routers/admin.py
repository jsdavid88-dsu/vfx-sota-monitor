"""Admin endpoints — protected by X-Admin-Token header.

Used by:
- AI Cluster Worker (Phase 3) — pending-scoring / score-update
- Manual ops — crawl trigger, run history
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models import CrawlRun, Item, ItemCategory
from app.schemas.admin import CrawlResult, PendingItem, ScoreUpdate, ScoreUpdateResult
from app.tasks.crawler import SOURCE_LABELS, crawl_all, crawl_source

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/pending-scoring", response_model=list[PendingItem])
async def pending_scoring(
    limit: int = Query(50, le=200),
    _: None = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Items with llm_score=0 waiting for LLM scoring (AI Cluster Worker consumes this)."""
    stmt = (
        select(Item)
        .options(selectinload(Item.categories).selectinload(ItemCategory.category))
        .where(Item.llm_score == 0)
        .order_by(Item.discovered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().unique().all()
    return [
        PendingItem(
            id=i.id,
            source=i.source,
            title=i.title,
            abstract=i.abstract,
            url=i.url,
            category_slugs=[ic.category.slug for ic in i.categories if ic.category],
        )
        for i in items
    ]


@router.post("/score-update", response_model=ScoreUpdateResult)
async def score_update(
    updates: list[ScoreUpdate],
    _: None = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Apply LLM scoring results from AI Cluster Worker."""
    count = 0
    for u in updates:
        item = await db.get(Item, u.id)
        if not item:
            continue
        item.llm_score = u.llm_score
        if u.llm_reason:
            item.llm_reason = u.llm_reason[:4000]
        if u.priority:
            item.priority = u.priority
        count += 1
    await db.commit()
    return ScoreUpdateResult(updated=count)


@router.post("/crawl/{source}", response_model=CrawlResult)
async def trigger_crawl_source(
    source: str,
    background: BackgroundTasks,
    wait: bool = Query(False, description="wait=true means run synchronously"),
    _: None = Depends(verify_admin_token),
):
    """Trigger a single-source crawl. Default: fire-and-forget."""
    if source not in SOURCE_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    if wait:
        result = await crawl_source(source)
        return CrawlResult(**result)
    else:
        background.add_task(crawl_source, source)
        return CrawlResult(source=source)


@router.post("/crawl")
async def trigger_crawl_all(
    background: BackgroundTasks,
    _: None = Depends(verify_admin_token),
):
    """Trigger all sources (fire-and-forget)."""
    background.add_task(crawl_all)
    return {"status": "started", "sources": SOURCE_LABELS}


@router.get("/runs")
async def list_runs(
    limit: int = Query(20, le=100),
    _: None = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "source": r.source,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "items_found": r.items_found,
            "items_new": r.items_new,
            "error": r.error,
        }
        for r in rows
    ]
