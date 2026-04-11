"""GitHub source — recent repositories matching VFX category keywords.

Uses PyGithub with optional GITHUB_TOKEN for higher rate limits.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from github import Auth, Github, GithubException

from app.config import settings
from app.sources.base import FetchedItem

logger = logging.getLogger(__name__)


def _get_client() -> Github:
    if settings.github_token:
        return Github(auth=Auth.Token(settings.github_token), per_page=30)
    return Github(per_page=30)


def _build_query(keywords: list[str], topics: list[str], days_back: int) -> str:
    """Build a GitHub search query from category keywords/topics."""
    # Quote multi-word keywords
    kw_parts = []
    for kw in keywords[:5]:  # Cap to avoid query length limit
        if " " in kw:
            kw_parts.append(f'"{kw}"')
        else:
            kw_parts.append(kw)

    topic_parts = [f"topic:{t}" for t in topics[:3]]

    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date().isoformat()

    parts: list[str] = []
    if kw_parts:
        parts.append("(" + " OR ".join(kw_parts) + ")")
    if topic_parts:
        parts.append("(" + " OR ".join(topic_parts) + ")")
    parts.append(f"pushed:>={since_date}")

    return " ".join(parts)


def fetch_github(
    keywords: list[str] | None = None,
    topics: list[str] | None = None,
    days_back: int = 7,
    max_results: int = 30,
) -> list[FetchedItem]:
    """Search GitHub for repositories matching keywords/topics.

    Note: GitHub search API allows ~30 req/min authenticated.
    Caller should sleep between category calls.
    """
    keywords = keywords or []
    topics = topics or []
    if not keywords and not topics:
        return []

    query = _build_query(keywords, topics, days_back)
    logger.info(f"GitHub query: {query}")

    items: list[FetchedItem] = []
    try:
        g = _get_client()
        results = g.search_repositories(query=query, sort="updated", order="desc")

        for i, repo in enumerate(results):
            if i >= max_results:
                break
            try:
                pushed = repo.pushed_at
                if pushed and pushed.tzinfo is None:
                    pushed = pushed.replace(tzinfo=timezone.utc)

                items.append(
                    FetchedItem(
                        source="github",
                        external_id=repo.full_name,
                        url=repo.html_url,
                        title=repo.name,
                        abstract=repo.description or "",
                        authors=repo.owner.login if repo.owner else None,
                        published_at=pushed,
                        metadata={
                            "stars": repo.stargazers_count,
                            "forks": repo.forks_count,
                            "language": repo.language,
                            "topics": repo.get_topics() if callable(getattr(repo, "get_topics", None)) else [],
                            "open_issues": repo.open_issues_count,
                        },
                    )
                )
            except GithubException as e:
                logger.warning(f"GitHub repo parse failed: {e}")
                continue
    except GithubException as e:
        logger.error(f"GitHub search failed: {e}")
        return items

    # Tiny sleep to stay under secondary rate limits
    time.sleep(0.5)
    logger.info(f"GitHub: {len(items)} repos")
    return items
