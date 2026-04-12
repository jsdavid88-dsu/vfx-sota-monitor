"""X/Twitter feed source — Crawl4AI for account pages + nitter RSS fallback.

Strategy:
1. Try nitter RSS first (structured, reliable when available)
2. Fall back to Crawl4AI scraping of x.com profile page
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

# Public nitter instances (may go down — try multiple)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]


def _try_nitter_rss(handle: str, max_items: int) -> list[dict] | None:
    """Try fetching tweets via nitter RSS."""
    for base in NITTER_INSTANCES:
        rss_url = f"{base}/{handle}/rss"
        try:
            r = httpx.get(rss_url, timeout=10, follow_redirects=True)
            if r.status_code != 200:
                continue

            root = ElementTree.fromstring(r.text)
            items = root.findall(".//item")
            results = []

            for item in items[:max_items]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                pub_date = item.findtext("pubDate")
                description = item.findtext("description") or ""

                # Extract tweet ID from link
                tweet_id = link.rstrip("/").split("/")[-1] if link else ""
                if not tweet_id.isdigit():
                    tweet_id = hashlib.sha1(link.encode()).hexdigest()[:16]

                published_at = None
                if pub_date:
                    try:
                        published_at = datetime.strptime(
                            pub_date, "%a, %d %b %Y %H:%M:%S %Z"
                        )
                    except ValueError:
                        pass

                results.append({
                    "source": "x",
                    "external_id": tweet_id,
                    "url": link.replace(base, "https://x.com") if base in link else link,
                    "title": title[:500] or f"@{handle}",
                    "excerpt": re.sub(r"<[^>]+>", "", description)[:1000] or None,
                    "content_md": None,
                    "image_url": None,
                    "author": f"@{handle}",
                    "published_at": published_at,
                    "tags": ["x"],
                    "feed_metadata": {"handle": handle, "via": "nitter"},
                })

            if results:
                logger.info(f"X @{handle}: {len(results)} tweets via nitter")
                return results
        except Exception:
            continue

    return None  # All nitter instances failed


def _crawl4ai_fallback(handle: str, max_items: int, tags: list[str]) -> list[dict]:
    """Fall back to Crawl4AI for scraping X profile."""
    try:
        import asyncio
        import os
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        async def _crawl():
            cfg = BrowserConfig(headless=True, verbose=False)
            run_cfg = CrawlerRunConfig(verbose=False, word_count_threshold=10)
            async with AsyncWebCrawler(config=cfg) as crawler:
                result = await crawler.arun(
                    url=f"https://x.com/{handle}",
                    config=run_cfg,
                )
                if not result.success:
                    return []

                # Extract tweet-like content from markdown
                md = result.markdown or ""
                items = []
                # Simple heuristic: split by probable tweet boundaries
                chunks = re.split(r"\n(?=@|\d+h|\d+d|\d+m)", md)
                for chunk in chunks[:max_items]:
                    text = chunk.strip()[:500]
                    if len(text) < 20:
                        continue
                    eid = hashlib.sha1(text.encode()).hexdigest()[:16]
                    items.append({
                        "source": "x",
                        "external_id": eid,
                        "url": f"https://x.com/{handle}",
                        "title": text[:200],
                        "excerpt": text[:500] or None,
                        "content_md": None,
                        "image_url": None,
                        "author": f"@{handle}",
                        "published_at": None,
                        "tags": ["x"] + tags,
                        "feed_metadata": {"handle": handle, "via": "crawl4ai"},
                    })
                return items

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(_crawl())).result()
        else:
            return asyncio.run(_crawl())

    except Exception as e:
        logger.warning(f"X @{handle} crawl4ai fallback failed: {e}")
        return []


def fetch_x_feed(accounts: list[dict], max_per_account: int = 10) -> list[dict]:
    """Fetch tweets from X accounts. Tries nitter RSS first, then Crawl4AI."""
    all_items: list[dict] = []

    for acc in accounts:
        handle = acc.get("handle", "")
        tags = acc.get("tags", [])
        if not handle:
            continue

        # Try nitter RSS first
        results = _try_nitter_rss(handle, max_per_account)
        if results:
            for r in results:
                r["tags"] = ["x"] + tags
            all_items.extend(results)
            continue

        # Fallback to Crawl4AI
        results = _crawl4ai_fallback(handle, max_per_account, tags)
        all_items.extend(results)

    logger.info(f"X feed: {len(all_items)} tweets from {len(accounts)} accounts")
    return all_items
