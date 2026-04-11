"""Search endpoint — full-text across items."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Item, ItemCategory
from app.schemas.item import ItemRead

router = APIRouter(prefix="/search", tags=["search"])


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
async def search_items(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Simple case-insensitive LIKE across title, abstract, authors, external_id."""
    like = f"%{q}%"
    stmt = (
        select(Item)
        .options(selectinload(Item.categories).selectinload(ItemCategory.category))
        .where(
            or_(
                Item.title.ilike(like),
                Item.abstract.ilike(like),
                Item.authors.ilike(like),
                Item.external_id.ilike(like),
                Item.llm_reason.ilike(like),
            )
        )
        .order_by(Item.llm_score.desc(), Item.keyword_score.desc(), Item.discovered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().unique().all()
    return [_serialize(i) for i in items]
