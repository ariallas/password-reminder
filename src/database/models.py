from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.utils import MSK

LONG_AGO = datetime(1970, 1, 1, tzinfo=MSK)


class DBUser(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    externaldb_id: Mapped[str] = mapped_column(unique=True)
    externaldb_fio: Mapped[str]
    externaldb_group: Mapped[str]
    externaldb_email: Mapped[str]

    ad_login: Mapped[str]
    ad_disabled: Mapped[bool] = mapped_column(default=False)
    ad_pwd_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ad_pwd_expired: Mapped[bool] = mapped_column(default=False)

    last_ad_refresh: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=LONG_AGO)
    last_notification: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=LONG_AGO)

    @property
    def ad_pwd_expires_in_days(self) -> int | None:
        if not self.ad_pwd_expiry or self.ad_disabled or self.ad_pwd_expired:
            return None

        expiry_date = self.ad_pwd_expiry.astimezone(MSK).date()
        if self.ad_pwd_expiry.astimezone(MSK).time() <= time(hour=9, minute=0):
            expiry_date -= timedelta(days=1)

        now_date = datetime.now(MSK).date()
        return (expiry_date - now_date).days
