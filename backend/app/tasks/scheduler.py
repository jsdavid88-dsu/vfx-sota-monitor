"""APScheduler setup — daily crawl + night batch."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.crawler import crawl_all
from app.tasks.feed_crawler import crawl_feed_all
from app.tasks.night_batch import run_night_batch

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    # 연구 크롤 — 매일 09:00 KST
    _scheduler.add_job(
        crawl_all,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_research_crawl",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # 피드 크롤 — 6시간마다 (00:15, 06:15, 12:15, 18:15 KST)
    _scheduler.add_job(
        crawl_feed_all,
        trigger=CronTrigger(hour="0,6,12,18", minute=15),
        id="feed_crawl",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # 야간 배치 — 매일 21:00 KST
    # 제보 처리 + 그룹핑 + 태그 승격 감지
    _scheduler.add_job(
        run_night_batch,
        trigger=CronTrigger(hour=21, minute=0),
        id="night_batch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — research: 09:00 KST, feed: 6h, night batch: 21:00 KST"
    )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
