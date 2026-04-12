"""Feed crawler — runs Crawl4AI + Reddit feed sources and persists feed_items.

Scheduled via APScheduler. Can also be triggered manually via admin API.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models import CrawlRun, FeedItem
from app.sources.feed_reddit import fetch_reddit_feed
from app.sources.crawl4ai_src import fetch_crawl4ai_feed

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "feed_queries.yaml"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        logger.warning(f"feed_queries.yaml not found at {CONFIG_PATH}")
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


async def _persist(db: AsyncSession, items: list[dict]) -> int:
    """Upsert feed items, return count of new rows."""
    new_count = 0
    for it in items:
        stmt = (
            sqlite_insert(FeedItem)
            .values(
                source=it["source"],
                external_id=it["external_id"],
                url=it["url"],
                title=it["title"][:2000] if it.get("title") else "(no title)",
                excerpt=it.get("excerpt"),
                content_md=it.get("content_md"),
                image_url=it.get("image_url"),
                author=it.get("author"),
                published_at=it.get("published_at"),
                tags=it.get("tags", []),
                feed_metadata=it.get("feed_metadata", {}),
            )
            .on_conflict_do_nothing(index_elements=["source", "external_id"])
        )
        result = await db.execute(stmt)
        if result.rowcount:
            new_count += 1
    await db.commit()
    return new_count


async def crawl_feed_source(source: str) -> dict:
    """Run a single feed source.

    source: 'firecrawl' | 'reddit'
    """
    cfg = _load_config()
    loop = asyncio.get_running_loop()

    async with SessionLocal() as db:
        run = CrawlRun(source=f"feed_{source}", started_at=datetime.utcnow())
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            items: list[dict] = []
            if source == "crawl4ai":
                queries = cfg.get("firecrawl_queries") or []
                items = await loop.run_in_executor(
                    None, lambda: fetch_crawl4ai_feed(queries)
                )
            elif source == "reddit":
                rcfg = cfg.get("reddit") or {}
                items = await loop.run_in_executor(
                    None,
                    lambda: fetch_reddit_feed(
                        rcfg.get("subreddits", []),
                        rcfg.get("keywords", []),
                        rcfg.get("days_back", 3),
                        rcfg.get("max_per_sub", 15),
                    ),
                )
            else:
                raise ValueError(f"Unknown feed source: {source}")

            new_count = await _persist(db, items)

            run.finished_at = datetime.utcnow()
            run.items_found = len(items)
            run.items_new = new_count
            await db.commit()

            logger.info(f"[feed:{source}] fetched={len(items)} new={new_count}")
            return {"source": source, "fetched": len(items), "new": new_count}
        except Exception as e:
            logger.exception(f"feed crawl_source({source}) failed")
            run.finished_at = datetime.utcnow()
            run.error = str(e)[:2000]
            await db.commit()
            return {"source": source, "error": str(e)}


async def crawl_feed_all() -> list[dict]:
    """Run all feed sources sequentially."""
    results = []
    for src in ["crawl4ai", "reddit"]:
        results.append(await crawl_feed_source(src))
    return results
