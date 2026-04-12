"""X/Twitter feed source — fxtwitter API for content, multiple discovery methods.

Strategy:
1. Discover tweet IDs from known sources:
   - HF daily papers (authors often tweet their papers)
   - Reddit crossposts with x.com links
   - Manual tweet URLs from feed_queries.yaml
2. Fetch each tweet via api.fxtwitter.com (no API key needed)
3. Return structured feed items

This avoids needing X login or API keys entirely.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

TWEET_URL_RE = re.compile(r"(?:x|twitter)\.com/(\w+)/status/(\d+)")


def _fetch_tweet_fxtwitter(handle: str, tweet_id: str) -> dict | None:
    """Fetch a single tweet via api.fxtwitter.com → structured dict."""
    url = f"https://api.fxtwitter.com/{handle}/status/{tweet_id}"
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True)
        if r.status_code != 200:
            return None

        data = r.json()
        tweet = data.get("tweet") or {}
        if not tweet:
            return None

        text = tweet.get("text") or ""
        author = tweet.get("author") or {}
        handle = author.get("screen_name") or handle
        name = author.get("name") or handle

        # Parse timestamp
        published_at = None
        created = tweet.get("created_at") or tweet.get("created_timestamp")
        if created:
            try:
                if isinstance(created, (int, float)):
                    published_at = datetime.fromtimestamp(int(created), tz=timezone.utc)
                else:
                    published_at = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Media
        media = tweet.get("media") or {}
        image_url = None
        if media.get("photos"):
            image_url = media["photos"][0].get("url")
        elif media.get("videos"):
            image_url = media["videos"][0].get("thumbnail_url")

        return {
            "source": "x",
            "external_id": tweet_id,
            "url": tweet.get("url") or f"https://x.com/{handle}/status/{tweet_id}",
            "title": text[:200] if text else f"@{handle}",
            "excerpt": text[:1000] or None,
            "content_md": text,
            "image_url": image_url,
            "author": f"@{handle}" + (f" ({name})" if name != handle else ""),
            "published_at": published_at,
            "tags": ["x"],
            "feed_metadata": {
                "handle": handle,
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
                "replies": tweet.get("replies", 0),
                "views": tweet.get("views", 0),
            },
        }
    except Exception as e:
        logger.warning(f"fxtwitter fetch failed for {tweet_id}: {e}")
        return None


def _discover_tweet_ids_from_explicit(accounts: list[dict]) -> list[tuple[str, str]]:
    """Extract explicit tweet_urls from config."""
    pairs = []
    for acc in accounts:
        for url in acc.get("tweet_urls", []):
            m = TWEET_URL_RE.search(url)
            if m:
                pairs.append((m.group(1), m.group(2)))
    return pairs


def _discover_tweet_ids_from_feed_items() -> list[tuple[str, str]]:
    """Scan existing feed_items for x.com links (from Reddit, HF, etc.)."""
    try:
        import asyncio
        from sqlalchemy import select, text
        from app.database import SessionLocal
        from app.models import FeedItem

        async def _scan():
            async with SessionLocal() as db:
                # Look for x.com links in feed items from other sources
                stmt = text("""
                    SELECT url, excerpt, content_md FROM feed_items
                    WHERE source != 'x'
                    ORDER BY discovered_at DESC LIMIT 200
                """)
                rows = (await db.execute(stmt)).fetchall()
                pairs = []
                for url, excerpt, content in rows:
                    for text_field in [url or "", excerpt or "", content or ""]:
                        for m in TWEET_URL_RE.finditer(text_field):
                            pairs.append((m.group(1), m.group(2)))
                return pairs

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(_scan())).result()
        else:
            return asyncio.run(_scan())
    except Exception as e:
        logger.warning(f"Tweet discovery from feed_items failed: {e}")
        return []


def fetch_x_feed(accounts: list[dict], max_per_account: int = 10) -> list[dict]:
    """Fetch tweets from X via fxtwitter.

    Discovery sources:
    1. Explicit tweet_urls in config
    2. x.com links found in other feed items (Reddit posts, HF papers, etc.)
    """
    # Collect all tweet IDs to fetch
    all_pairs: list[tuple[str, str]] = []

    # From explicit config
    all_pairs.extend(_discover_tweet_ids_from_explicit(accounts))

    # From existing feed items (cross-posted links)
    all_pairs.extend(_discover_tweet_ids_from_feed_items())

    # Dedupe by tweet_id
    seen = set()
    unique_pairs = []
    for handle, tid in all_pairs:
        if tid not in seen:
            seen.add(tid)
            unique_pairs.append((handle, tid))

    # Fetch via fxtwitter
    items: list[dict] = []
    target_handles = {acc.get("handle", "").lower() for acc in accounts}

    for handle, tid in unique_pairs:
        # If we have target accounts, prioritize those
        item = _fetch_tweet_fxtwitter(handle, tid)
        if item:
            # Add account-specific tags
            for acc in accounts:
                if acc.get("handle", "").lower() == handle.lower():
                    item["tags"] = ["x"] + acc.get("tags", [])
                    break
            items.append(item)

        if len(items) >= max_per_account * len(accounts):
            break

    logger.info(f"X feed: {len(items)} tweets ({len(unique_pairs)} discovered)")
    return items
