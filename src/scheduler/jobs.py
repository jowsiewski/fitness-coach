"""Background scheduler jobs for syncing data from Intervals.icu."""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import settings
from src.integrations.intervals_icu.client import IntervalsICUClient
from src.models.database import async_session_factory
from src.models.tables import ActivityRecord, WellnessRecord

logger = logging.getLogger(__name__)


async def _sync_activities() -> None:
    """Fetch activities from last 7 days and upsert into DB."""
    newest = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    logger.info("Syncing activities from %s to %s", oldest, newest)

    async with IntervalsICUClient() as client:
        activities = await client.get_activities(oldest=oldest, newest=newest)

    logger.info("Fetched %d activities from Intervals.icu", len(activities))

    async with async_session_factory() as session:
        for act in activities:
            record = ActivityRecord(
                id=str(act["id"]),
                start_date=act.get("start_date_local", act.get("start_date", "")),
                type=act.get("type", "Ride"),
                name=act.get("name"),
                moving_time=act.get("moving_time"),
                distance=act.get("distance"),
                training_load=act.get("icu_training_load"),
                intensity=act.get("icu_intensity"),
                average_watts=act.get("average_watts"),
                normalized_power=act.get("icu_weighted_avg_watts"),
                average_hr=act.get("average_heartrate"),
                max_hr=act.get("max_heartrate"),
                calories=act.get("calories"),
                elevation_gain=act.get("total_elevation_gain"),
                ftp_at_time=act.get("icu_ftp"),
            )
            await session.merge(record)
        await session.commit()

    logger.info("Synced %d activities to database", len(activities))


async def _sync_wellness() -> None:
    """Fetch wellness data from last 14 days and upsert into DB."""
    newest = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    logger.info("Syncing wellness from %s to %s", oldest, newest)

    async with IntervalsICUClient() as client:
        wellness_data = await client.get_wellness(oldest=oldest, newest=newest)

    logger.info("Fetched %d wellness records from Intervals.icu", len(wellness_data))

    async with async_session_factory() as session:
        for w in wellness_data:
            record = WellnessRecord(
                id=str(w["id"]),
                weight=w.get("weight"),
                resting_hr=w.get("restingHR"),
                hrv=w.get("hrv"),
                hrv_sdnn=w.get("hrvSDNN"),
                sleep_time=w.get("sleepTime"),
                sleep_score=w.get("sleepScore"),
                atl=w.get("atl"),
                ctl=w.get("ctl"),
                ramp_rate=w.get("rampRate"),
                spo2=w.get("spO2avg"),
                steps=w.get("steps"),
                kcal_consumed=w.get("kcalConsumed"),
            )
            await session.merge(record)
        await session.commit()

    logger.info("Synced %d wellness records to database", len(wellness_data))


def _run_sync_activities() -> None:
    """Sync wrapper: run async sync_activities in a new event loop."""
    try:
        asyncio.run(_sync_activities())
    except Exception:
        logger.exception("Failed to sync activities")


def _run_sync_wellness() -> None:
    """Sync wrapper: run async sync_wellness in a new event loop."""
    try:
        asyncio.run(_sync_wellness())
    except Exception:
        logger.exception("Failed to sync wellness")


def _run_daily_report() -> None:
    """Placeholder for daily report — Discord integration TBD."""
    logger.info("Daily report would be sent here")


def start_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the background scheduler.

    Returns the running BackgroundScheduler instance so the caller can
    shut it down later with ``scheduler.shutdown(wait=False)``.
    """
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        _run_sync_activities,
        trigger="interval",
        minutes=settings.sync_interval_minutes,
        id="sync_activities",
        name="Sync activities from Intervals.icu",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_sync_wellness,
        trigger="interval",
        minutes=settings.sync_interval_minutes,
        id="sync_wellness",
        name="Sync wellness from Intervals.icu",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_daily_report,
        trigger="cron",
        hour=20,
        minute=0,
        id="daily_report",
        name="Daily fitness report",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started — sync every %d min, daily report at 20:00",
        settings.sync_interval_minutes,
    )
    return scheduler
