"""Item grouper — unifies same research across arxiv/github/huggingface sources.

Strategy:
1. Fingerprint-based: normalize title/name to first N meaningful words
2. Cross-reference: if arxiv item has code_links pointing to github/hf item
   that exists, link them to same group

Runs after each crawl.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy import select, update as sql_update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SOURCE_ORDER
from app.database import SessionLocal
from app.models import Item, ItemGroup

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "for", "of", "and", "or", "with", "via", "to", "in",
    "on", "by", "from", "using", "through", "based", "towards", "learning",
    "model", "models", "method", "methods", "approach", "framework",
    "video", "image", "3d", "2d", "neural", "deep",
}


# ── Fingerprinting (pure logic, no DB) ──────────────────────────


def compute_fingerprint(item: Item) -> str:
    """Reduce a title/name to a canonical fingerprint string."""
    raw = ""
    if item.source == "arxiv":
        raw = item.title or ""
    elif item.source in ("github", "huggingface"):
        name = (item.external_id or "").split("/")[-1]
        raw = name or item.title or ""
    else:
        raw = item.title or ""

    words = re.findall(r"[a-z0-9]+", raw.lower())
    keep = [w for w in words if w not in STOP_WORDS and len(w) >= 2]
    fingerprint = " ".join(keep[:3])
    return fingerprint or raw[:50].lower()


def pick_primary(items: list[Item]) -> Item:
    """Pick the best representative from a group of items."""
    return sorted(
        items,
        key=lambda it: (
            SOURCE_ORDER.get(it.source, 9),
            -(it.llm_score or 0),
            -(it.keyword_score or 0),
        ),
    )[0]


# ── DB orchestration ────────────────────────────────────────────


async def _assign_groups(db: AsyncSession, items: list[Item]) -> tuple[int, int]:
    """First pass: assign group_id by fingerprint. Returns (created, linked)."""
    created = 0
    linked = 0

    fp_to_group: dict[str, int] = {}
    existing = (await db.execute(select(ItemGroup))).scalars().all()
    for g in existing:
        fp_to_group[g.fingerprint] = g.id

    for item in items:
        fp = compute_fingerprint(item)
        if not fp:
            continue

        if fp in fp_to_group:
            group_id = fp_to_group[fp]
        else:
            # Upsert to handle concurrent grouper runs safely
            stmt = (
                sqlite_insert(ItemGroup)
                .values(
                    fingerprint=fp,
                    canonical_name=item.title[:500] if item.title else fp,
                )
                .on_conflict_do_nothing(index_elements=["fingerprint"])
            )
            await db.execute(stmt)
            await db.flush()
            # Fetch the (possibly pre-existing) group id
            row = (
                await db.execute(
                    select(ItemGroup.id).where(ItemGroup.fingerprint == fp)
                )
            ).scalar_one()
            fp_to_group[fp] = row
            group_id = row
            created += 1

        if item.group_id != group_id:
            item.group_id = group_id
            linked += 1

    return created, linked


async def _merge_cross_references(db: AsyncSession, items: list[Item]) -> int:
    """Second pass: merge groups when arxiv code_links match github/hf items."""
    linked = 0
    arxiv_items = [i for i in items if i.source == "arxiv"]

    for ax in arxiv_items:
        md = ax.item_metadata or {}
        code_links = md.get("code_links") or []
        if not code_links:
            continue

        for link in code_links:
            if not isinstance(link, dict):
                continue
            repo_name = link.get("name", "")
            if not repo_name:
                continue

            matched_stmt = select(Item).where(
                Item.external_id == repo_name,
                Item.source.in_(("github", "huggingface")),
            )
            matched = (await db.execute(matched_stmt)).scalars().all()

            for m in matched:
                if not ax.group_id or m.group_id == ax.group_id:
                    continue
                if m.group_id:
                    await db.execute(
                        sql_update(Item)
                        .where(Item.group_id == m.group_id)
                        .values(group_id=ax.group_id)
                    )
                else:
                    m.group_id = ax.group_id
                linked += 1

    return linked


async def _update_primaries(db: AsyncSession) -> None:
    """Third pass: set primary_item_id per group."""
    groups = list((await db.execute(select(ItemGroup))).scalars().all())

    for g in groups:
        g_items = list(
            (await db.execute(select(Item).where(Item.group_id == g.id))).scalars().all()
        )
        if not g_items:
            continue
        primary = pick_primary(g_items)
        if g.primary_item_id != primary.id:
            g.primary_item_id = primary.id


async def group_items() -> dict:
    """Assign group_id to all items lacking one.

    Returns stats dict with created/linked counts.
    """
    async with SessionLocal() as db:
        stmt = select(Item).order_by(Item.discovered_at.asc())
        items = list((await db.execute(stmt)).scalars().all())

        created, linked = await _assign_groups(db, items)
        linked += await _merge_cross_references(db, items)
        await _update_primaries(db)

        await db.commit()

    logger.info(f"grouper: {created} groups created, {linked} items linked")
    return {"created": created, "linked": linked}
