from loguru import logger

import src.database.models  # noqa: F401
from src.database import Base, db_engine_manager


async def prepare_databse() -> None:
    logger.info("Creating tables, if required")
    async with db_engine_manager.get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def purge_database() -> None:
    logger.info("Purging everything in the database")
    async with db_engine_manager.get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
