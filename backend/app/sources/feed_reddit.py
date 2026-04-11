"""Reddit source for the Feed tab.

Different from sources/reddit_src.py (research tracking) — this uses a broader
keyword set and different subreddits to capture community workflows, tutorials,
and news. Output format is feed_item dicts, not FetchedItem (research).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings

logger = logging.getLogger(__name__)


def _get_reddit():
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        return None
    try:
        import praw  # noqa: WPS433

        return praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
            check_for_async=False,
        )
    except Exception as e:
        logger.warning(f"PRAW init failed: {e}")
        return None


def fetch_reddit_feed(
    subreddits: list[str],
    keywords: list[str],
    days_back: int = 3,
    max_per_sub: int = 15,
) -> list[dict]:
    reddit = _get_reddit()
    if not reddit:
        logger.info("Reddit credentials missing — skipping feed_reddit")
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp()
    kw_lower = [k.lower() for k in keywords]
    out: list[dict] = []

    for sub_name in subreddits:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.new(limit=max_per_sub):
                if post.created_utc < cutoff:
                    continue

                text = f"{post.title} {post.selftext or ''}".lower()
                if kw_lower and not any(kw in text for kw in kw_lower):
                    continue

                published = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                excerpt = (post.selftext or "")[:500] if post.selftext else None

                # Pick the thumbnail or preview image if post is an image/link
                image_url = None
                try:
                    if hasattr(post, "preview") and isinstance(post.preview, dict):
                        images = post.preview.get("images", [])
                        if images and images[0].get("source"):
                            image_url = images[0]["source"].get("url")
                    elif post.thumbnail and post.thumbnail.startswith("http"):
                        image_url = post.thumbnail
                except Exception:
                    pass

                # Determine matched tags
                matched_tags = [kw for kw in kw_lower if kw in text][:5]
                matched_tags = list({*matched_tags, sub_name.lower()})

                out.append({
                    "source": "reddit",
                    "external_id": post.id,
                    "url": f"https://reddit.com{post.permalink}",
                    "title": post.title[:500],
                    "excerpt": excerpt,
                    "content_md": None,
                    "image_url": image_url,
                    "author": str(post.author) if post.author else None,
                    "published_at": published,
                    "tags": matched_tags,
                    "feed_metadata": {
                        "subreddit": sub_name,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "upvote_ratio": post.upvote_ratio,
                        "is_self": post.is_self,
                        "flair": post.link_flair_text,
                    },
                })
        except Exception as e:
            logger.warning(f"Reddit feed sub '{sub_name}' failed: {e}")
            continue

    logger.info(f"Reddit feed: {len(out)} posts across {len(subreddits)} subs")
    return out
