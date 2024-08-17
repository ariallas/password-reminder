from datetime import timedelta, timezone

import aiohttp
from loguru import logger

MSK = timezone(timedelta(hours=3))


class HttpSessionManager:
    """
    Утилита для удобной инициализации и закрытия сессии aiohttp через async with
    """

    async def __aenter__(self) -> None:
        logger.info("Setting up HTTP session")
        self._session = aiohttp.ClientSession()

    async def __aexit__(self, *exc: object) -> None:
        logger.info("Closing HTTP session")
        await self._session.close()

    def get_session(self) -> aiohttp.ClientSession:
        return self._session


http_session_manager = HttpSessionManager()
