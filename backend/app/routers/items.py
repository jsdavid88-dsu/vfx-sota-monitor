"""Item endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Category, Item, ItemCategory
from app.schemas.item import ItemRead

router = APIRouter(prefix="/items", tags=["items"])

SORT_MAP = {
    "discovered": Item.discovered_at.desc(),
    "discovered_asc": Item.discovered_at.asc(),
    "published": Item.published_at.desc(),
    "score": Item.llm_score.desc(),
    "keyword_score": Item.keyword_score.desc(),
    "priority": Item.priority.asc(),
}


def _serialize(item: Item) -> ItemRead:
    cat_slugs = [ic.category.slug for ic in item.categories if ic.category]
    return ItemRead(
        id=item.id,
        source=item.source,
        external_id=item.external_id,
        url=item.url,
        title=item.title,
        abstract=item.abstract,
        authors=item.authors,
        published_at=item.published_at,
        discovered_at=item.discovered_at,
        metadata=item.item_metadata or {},
        keyword_score=item.keyword_score,
        llm_score=item.llm_score,
        llm_reason=item.llm_reason,
        priority=item.priority,
        status=item.status,
        category_slugs=cat_slugs,
    )


@router.get("", response_model=list[ItemRead])
async def list_items(
    source: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    since: datetime | None = None,
    min_score: int | None = Query(None, ge=0, le=10),
    sort: str = Query("discovered", pattern="^(discovered|discovered_asc|published|score|keyword_score|priority)$"),
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Item).options(
        selectinload(Item.categories).selectinload(ItemCategory.category)
    )
    if source:
        stmt = stmt.where(Item.source == source)
    if priority:
        stmt = stmt.where(Item.priority == priority)
    if since:
        stmt = stmt.where(Item.discovered_at >= since)
    if min_score is not None:
        stmt = stmt.where(Item.llm_score >= min_score)
    if category:
        stmt = stmt.join(ItemCategory).join(Category).where(Category.slug == category)

    order_by = SORT_MAP.get(sort, Item.discovered_at.desc())
    stmt = stmt.order_by(order_by).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().unique().all()
    return [_serialize(i) for i in items]


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Item)
        .options(selectinload(Item.categories).selectinload(ItemCategory.category))
        .where(Item.id == item_id)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _serialize(item)
