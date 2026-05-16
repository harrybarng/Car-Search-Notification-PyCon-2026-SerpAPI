from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.storage import load_schedule, save_schedule

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_JOB_ID = "daily_car_search"


def _should_skip() -> bool:
    schedule = load_schedule()
    if not schedule.last_run_at:
        return False
    buffer = timedelta(hours=schedule.buffer_hours)
    return datetime.utcnow() - schedule.last_run_at < buffer


def _run_job() -> None:
    from services.search import run_search
    from services.notify import send_pushover
    from services.storage import load_criteria, load_matches

    schedule = load_schedule()
    if not schedule.enabled:
        logger.info("Scheduled job fired but scheduling is disabled. Skipping.")
        return

    if not load_criteria():
        logger.info("Scheduled job skipped — no search criteria defined.")
        return

    if _should_skip():
        logger.info("Scheduled job skipped — within buffer window of last manual run.")
        return

    logger.info("Scheduled search starting.")
    new_count, errors, _ = run_search()

    if errors:
        for e in errors:
            logger.warning("Search error: %s", e)

    if new_count > 0:
        matches = [m for m in load_matches() if not m.notified]
        send_pushover(matches)
        from services.storage import save_matches
        all_matches = load_matches()
        for m in all_matches:
            m.notified = True
        save_matches(all_matches)

    schedule.last_run_at = __import__("datetime").datetime.utcnow()
    save_schedule(schedule)


def _apply_schedule() -> None:
    global _scheduler
    if _scheduler is None:
        return

    schedule = load_schedule()
    if _scheduler.get_job(_JOB_ID):
        _scheduler.remove_job(_JOB_ID)

    if not schedule.enabled:
        return

    hour, minute = schedule.run_at.split(":")
    _scheduler.add_job(
        _run_job,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id=_JOB_ID,
        replace_existing=True,
    )
    logger.info("Scheduled daily search at %s.", schedule.run_at)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    _apply_schedule()
    logger.info("Background scheduler started.")


def refresh_schedule() -> None:
    """Call after saving schedule changes to apply them immediately."""
    _apply_schedule()


def record_manual_run() -> None:
    """Update last_run_at after a manual search so the buffer window applies."""
    from datetime import datetime
    schedule = load_schedule()
    schedule.last_run_at = datetime.utcnow()
    save_schedule(schedule)
