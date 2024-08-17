import asyncio

from src.database import db_engine_manager
from src.database.db_utils import purge_database


async def async_main() -> None:
    async with db_engine_manager:
        await purge_database()


if __name__ == "__main__":
    asyncio.run(async_main())
