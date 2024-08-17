"""
Для локального тестового запуска разных модулей
"""

import asyncio
import traceback

from loguru import logger
from sqlalchemy import select

from src.active_directory import ADSyncer
from src.database import db_engine_manager, db_sessionmaker
from src.database.db_utils import prepare_databse
from src.database.models import DBUser
from src.externaldb import ExternalDBSyncer
from src.notification.notificator import Notificator
from src.utils import http_session_manager

# ruff: noqa


async def async_main() -> None:
    async with db_engine_manager, http_session_manager:
        await prepare_databse()
        await run_syncers()
        await run_notificator()


async def run_notificator() -> None:
    n = Notificator()
    async with db_sessionmaker() as session:
        result = await session.scalars(select(DBUser).where(DBUser.ad_login == "test_user"))
        user = result.one()
    await n._notify_user(user)  # noqa: SLF001


async def run_syncers() -> None:
    extdb = ExternalDBSyncer()
    await extdb.sync()

    ad = ADSyncer()
    await ad.sync()


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
    except Exception:
        logger.error(traceback.format_exc())
