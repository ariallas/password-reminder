from typing import Any

from loguru import logger
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from src.config import settings


class EngineManager:
    def __init__(self, sessionmaker: async_sessionmaker, **kw: Any) -> None:
        self._kw = kw
        self._sessionmaker = sessionmaker

    async def __aenter__(self) -> None:
        logger.info("Setting up DB engine")
        self._engine = create_async_engine(**self._kw)
        self._sessionmaker.configure(bind=self._engine)

    async def __aexit__(self, *exc: object) -> None:
        logger.info("Disposing of DB engine")
        await self._engine.dispose()

    def get_engine(self) -> AsyncEngine:
        return self._engine

    async def test_connection(self) -> None:
        logger.info("Testing DB connection")
        async with self._engine.connect() as conn:
            await conn.execute(text("SELECT 1"))


db_sessionmaker = async_sessionmaker(None, expire_on_commit=False)

url_object = URL.create(
    "postgresql+asyncpg",
    username=settings.db_secrets.postgres_user.get_secret_value(),
    password=settings.db_secrets.postgres_password.get_secret_value(),
    host=settings.db_secrets.postgres_host,
    port=settings.db_secrets.postgres_port,
    database=settings.db_database,
)

db_engine_manager = EngineManager(
    db_sessionmaker,
    url=url_object,
    echo=settings.debug.enable_sqlalchemy_logs,
    echo_pool="debug" if settings.debug.enable_sqlalchemy_logs else False,
    pool_pre_ping=True,
    pool_size=1,
    connect_args={"timeout": 10.0},
    pool_recycle=3600,
)


class Base(MappedAsDataclass, AsyncAttrs, DeclarativeBase):
    pass
