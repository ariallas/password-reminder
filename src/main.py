import asyncio
import traceback

from apscheduler.events import EVENT_JOB_ERROR, JobExecutionEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src import metrics
from src.active_directory import ADSyncer
from src.config import settings
from src.database import db_engine_manager
from src.database.db_utils import prepare_databse
from src.externaldb import ExternalDBSyncer
from src.notification.notificator import Notificator
from src.utils import http_session_manager

externaldb_syncer = ExternalDBSyncer()
ad_syncer = ADSyncer()
notificator = Notificator()


async def async_main() -> None:
    metrics.start_server()

    async with db_engine_manager, http_session_manager:
        await db_engine_manager.test_connection()
        await prepare_databse()

        externaldb_syncer.test_connection()
        ad_syncer.test_connection()

        if settings.debug.run_immediately:
            await sync_and_notify()
        else:
            await run_scheduler()


async def sync_and_notify() -> None:
    metrics.runs.inc()

    await externaldb_syncer.sync()
    await ad_syncer.sync()
    await notificator.send_all()


async def run_scheduler() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_listener(error_logger, EVENT_JOB_ERROR)

    scheduler.add_job(
        func=sync_and_notify,
        trigger=CronTrigger.from_crontab(settings.schedule_main),
        misfire_grace_time=60,
    )

    logger.info("Running scheduler forever")
    scheduler.start()
    while True:
        await asyncio.sleep(3600)


def error_logger(event: JobExecutionEvent) -> None:
    metrics.errors.inc()
    logger.error(f"Job {event.job_id} raised {event.exception}\n{event.traceback}")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
    except Exception:
        logger.error(traceback.format_exc())
