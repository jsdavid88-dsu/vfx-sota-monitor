"""Night batch pipeline — runs at 21:00 KST daily.

1. Process pending submissions (URL → crawl, keyword → search+crawl)
2. Run grouper to unify cross-source items
3. Aggregate free_tags → detect category promotion candidates
4. (Future) Arca researcher for deep investigation of new items

All steps are sequential and fault-tolerant — one step failing
doesn't block the rest.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import Item, ItemCategory, Submission, CategorySuggestion

logger = logging.getLogger(__name__)

PROMOTION_THRESHOLD = 5  # items with same tag before suggesting category


async def _process_url_submission(db: AsyncSession, sub: Submission) -> int | None:
    """Crawl a submitted URL, create an item if relevant. Returns item_id or None."""
    try:
        from app.sources.crawl4ai_src import _crawl_url
        page = await _crawl_url(sub.input_value)
        if not page:
            return None

        title = page.get("title") or sub.input_value[:200]
        markdown = page.get("markdown") or ""
        description = page.get("description") or markdown[:500]

        external_id = hashlib.sha1(sub.input_value.encode("utf-8")).hexdigest()[:24]

        stmt = (
            sqlite_insert(Item)
            .values(
                source="submission",
                external_id=external_id,
                url=sub.input_value,
                title=title[:2000],
                abstract=description[:5000] or None,
                item_metadata={"submitted_by": sub.submitted_by, "submission_id": sub.id},
                keyword_score=0,
                llm_score=0,
                priority="WATCH",
                status="submitted",
                free_tags=["제보"],
            )
            .on_conflict_do_nothing(index_elements=["source", "external_id"])
        )
        await db.execute(stmt)
        await db.flush()

        row = (
            await db.execute(
                select(Item.id).where(Item.source == "submission", Item.external_id == external_id)
            )
        ).scalar_one_or_none()
        return row
    except Exception as e:
        logger.warning(f"Failed to process URL submission {sub.id}: {e}")
        return None


async def _process_keyword_submission(db: AsyncSession, sub: Submission) -> int | None:
    """Search for a keyword, crawl top result, create item if relevant."""
    try:
        from app.sources.crawl4ai_src import search_crawl4ai
        results = await search_crawl4ai(sub.input_value, limit=1, tags=["제보"])
        if not results:
            return None

        best = results[0]
        external_id = hashlib.sha1(best["url"].encode("utf-8")).hexdigest()[:24]

        stmt = (
            sqlite_insert(Item)
            .values(
                source="submission",
                external_id=external_id,
                url=best["url"],
                title=(best.get("title") or sub.input_value)[:2000],
                abstract=(best.get("excerpt") or "")[:5000] or None,
                item_metadata={
                    "submitted_by": sub.submitted_by,
                    "submission_id": sub.id,
                    "search_query": sub.input_value,
                },
                keyword_score=0,
                llm_score=0,
                priority="WATCH",
                status="submitted",
                free_tags=["제보"],
            )
            .on_conflict_do_nothing(index_elements=["source", "external_id"])
        )
        await db.execute(stmt)
        await db.flush()

        row = (
            await db.execute(
                select(Item.id).where(Item.source == "submission", Item.external_id == external_id)
            )
        ).scalar_one_or_none()
        return row
    except Exception as e:
        logger.warning(f"Failed to process keyword submission {sub.id}: {e}")
        return None


async def step_process_submissions() -> dict:
    """Step 1: Process all pending submissions."""
    processed = 0
    failed = 0

    async with SessionLocal() as db:
        stmt = select(Submission).where(Submission.status == "pending").order_by(Submission.created_at)
        subs = list((await db.execute(stmt)).scalars().all())

        for sub in subs:
            sub.status = "processing"
            await db.flush()

            item_id = None
            if sub.input_type == "url":
                item_id = await _process_url_submission(db, sub)
            elif sub.input_type == "keyword":
                item_id = await _process_keyword_submission(db, sub)

            if item_id:
                sub.status = "done"
                sub.result_item_id = item_id
                processed += 1
            else:
                sub.status = "rejected"
                sub.reject_reason = "크롤 실패 또는 유의미한 결과 없음"
                failed += 1

            sub.processed_at = datetime.now(timezone.utc)

        await db.commit()

    logger.info(f"[night] submissions: {processed} processed, {failed} failed")
    return {"processed": processed, "failed": failed}


async def step_run_grouper() -> dict:
    """Step 2: Re-run item grouper."""
    try:
        from app.tasks.grouper import group_items
        result = await group_items()
        logger.info(f"[night] grouper: {result}")
        return result
    except Exception as e:
        logger.exception("[night] grouper failed")
        return {"error": str(e)}


async def step_detect_promotions() -> dict:
    """Step 3: Aggregate free_tags and create category suggestions for popular tags."""
    from sqlalchemy import text

    created = 0
    async with SessionLocal() as db:
        # Count free_tags across items
        stmt = text("""
            SELECT j.value AS tag, COUNT(*) AS cnt
            FROM items, json_each(items.free_tags) AS j
            WHERE j.value NOT IN ('제보')
            GROUP BY j.value
            HAVING cnt >= :threshold
            ORDER BY cnt DESC
        """)
        rows = (await db.execute(stmt, {"threshold": PROMOTION_THRESHOLD})).fetchall()

        for tag, count in rows:
            # Skip if suggestion already exists
            existing = (
                await db.execute(
                    select(CategorySuggestion).where(CategorySuggestion.tag == tag)
                )
            ).scalar_one_or_none()

            if existing:
                existing.item_count = count
                continue

            sug = CategorySuggestion(
                tag=tag,
                item_count=count,
                status="pending",
            )
            db.add(sug)
            created += 1

        await db.commit()

    logger.info(f"[night] promotions: {len(rows)} tags above threshold, {created} new suggestions")
    return {"tags_above_threshold": len(rows), "new_suggestions": created}


async def run_night_batch() -> list[dict]:
    """Full night batch pipeline."""
    logger.info("=== Night batch started ===")
    results = []

    # Step 1: submissions
    r = await step_process_submissions()
    results.append({"step": "submissions", **r})

    # Step 2: grouper
    r = await step_run_grouper()
    results.append({"step": "grouper", **r})

    # Step 3: tag promotion detection
    r = await step_detect_promotions()
    results.append({"step": "promotions", **r})

    logger.info(f"=== Night batch done: {results} ===")
    return results
