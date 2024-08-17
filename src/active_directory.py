from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Self

from ldap3 import SAFE_SYNC, Connection, Server
from ldap3.core.exceptions import LDAPException
from loguru import logger
from sqlalchemy import select

from src.config import settings
from src.database import db_sessionmaker
from src.database.models import DBUser
from src.utils import MSK


@dataclass
class ADUser:
    login: str
    disabled: bool
    pwd_expiry: datetime | None
    pwd_expired: bool


class ADSyncer:
    """
    Синхронизирует БД приложения с Active Directory
    """

    def __init__(self) -> None:
        self._ad = ADClient()

    def test_connection(self) -> None:
        self._ad.test_connection()

    async def sync(self) -> None:
        logger.info("Syncing with AD")

        async with db_sessionmaker() as session:
            result = await session.scalars(select(DBUser))
            users = list(result)

        users = [user for user in users if self._should_be_synced(user)]
        logger.info(f"Refreshing AD data for {len(users)} users")

        with self._ad:
            for user in users:
                self._sync_one_user(user)

        logger.info("Saving refreshed AD data to DB")
        async with db_sessionmaker.begin() as session:
            session.add_all(users)

        logger.success("Done syncing with AD")

    def _sync_one_user(self, user: DBUser) -> None:
        try:
            ad_user = self._ad.get_user(user.ad_login)
        except ADError as e:
            logger.opt(exception=e).error("Error getting user from AD")
            return

        if not ad_user:
            logger.warning(f"User {user.ad_login} not found in AD")
        else:
            user.ad_disabled = ad_user.disabled
            user.ad_pwd_expiry = ad_user.pwd_expiry
            user.ad_pwd_expired = ad_user.pwd_expired
            user.last_ad_refresh = datetime.now(MSK)
        logger.debug(f"User {user.ad_login} password expires in {user.ad_pwd_expires_in_days} days")

    def _should_be_synced(self, user: DBUser) -> bool:
        if (
            user.ad_pwd_expires_in_days is None
            and datetime.now(MSK) - user.last_ad_refresh >= timedelta(days=14)
        ) or user.ad_pwd_expires_in_days in settings.notify_at_days_to_expiry:
            return True
        return False


class ADClient:
    """
    Клиент для Active Directory
    Технические подробности взяты из: https://github.com/moreati/ActiveDirectory-Python/blob/master/activedirectory.py
    """

    def __init__(self) -> None:
        self._server = Server(settings.active_directory.url)
        self._conn = Connection(
            self._server,
            user=settings.active_directory.user.get_secret_value(),
            password=settings.active_directory.password.get_secret_value(),
            client_strategy=SAFE_SYNC,
            auto_bind=False,
        )
        self._search_base = settings.search_base

    def test_connection(self) -> None:
        logger.info("Testing AD connection")
        with self:
            pass

    def __enter__(self) -> Self:
        status, result, _, _ = self._conn.bind()
        if not status:
            err = f"Error connecting to AD server: {result['description']}"
            raise ADError(err)

        return self

    def __exit__(self, *exc: object) -> None:
        self._conn.unbind()

    def get_user(self, login: str) -> ADUser | None:
        logger.debug(f"Looking for user {login} in AD")

        status, result, response = self._get_user_from_ad(login)

        if not status or not response:
            logger.debug(f"Did not find user {login} in AD: {result!s}")
            return None

        user = response[0]
        return ADUser(
            login=login,
            disabled=self._user_get_disabled(user),
            pwd_expiry=self._user_get_pwd_expiry_from(user),
            pwd_expired=self._user_get_pwd_expired(user),
        )

    def _get_user_from_ad(self, login: str) -> tuple[bool, dict, dict]:
        if not self._conn.bound:
            raise ADError("Connection to AD must be bound before making requests")

        try:
            status, result, response, _ = self._conn.search(
                self._search_base,
                f"(sAMAccountName={login})",
                attributes=[
                    "userAccountControl",
                    "msDS-UserPasswordExpiryTimeComputed",  # Вычисленная дата истечения пароля, учитывает FGPP (гранулированные политики паролей)
                    "msDS-User-Account-Control-Computed",
                ],
            )
        except LDAPException as e:
            raise ADError(f"AD search for user {login} failed: {e!r}") from e
        return status, result, response

    def _user_get_disabled(self, user: Any) -> bool:
        uac = int(user["attributes"]["userAccountControl"])
        return bool(uac & 0x00000002)

    def _user_get_pwd_expired(self, user: Any) -> bool:
        uac_live = int(user["attributes"]["msDS-User-Account-Control-Computed"])
        return bool(uac_live & 0x00800000)

    def _user_get_pwd_expiry_from(self, user: Any) -> datetime | None:
        expiry_time = int(user["attributes"]["msDS-UserPasswordExpiryTimeComputed"])

        # A value of 0 or 0x7FFFFFFFFFFFFFFF indicates that the account never expires.
        if expiry_time in (0, 0x7FFFFFFFFFFFFFFF):
            return None

        return self._ad_time_to_datetime(expiry_time)

    def _ad_time_to_datetime(self, ad_time: int) -> datetime:
        # AD's date format is 100 nanosecond intervals since Jan 1 1601 in GMT.
        # To convert to seconds, divide by 10000000.
        return datetime(1601, 1, 1, tzinfo=UTC) + timedelta(seconds=ad_time / 10000000)


class ADError(Exception):
    pass
