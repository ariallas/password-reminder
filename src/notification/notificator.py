from datetime import UTC, datetime
from typing import override

import jinja2
from loguru import logger
from sqlalchemy import select

from src import metrics
from src.config import settings
from src.database import db_sessionmaker
from src.database.models import DBUser
from src.notification.mailsender import Email, MailSender, MailSenderError
from src.notification.portalsender import PortalNotification, PortalNotificationError, PortalSender


class Notificator:
    """
    Отправляет уведомления об истечении пароля всем пользователям,
    удовлетворяющим условиям
    """

    def __init__(self) -> None:
        self._notificators: list[AbstractNotificator] = [
            MailNotificator(),
            PortalNotificator(),
        ]
        self._notify_at_days_to_expiry = settings.notify_at_days_to_expiry

    async def send_all(self) -> None:
        logger.info("Preparing user notifications")

        async with db_sessionmaker() as session:
            result = await session.scalars(select(DBUser))
            users = list(result)

        users_to_notify = [user for user in users if self._should_notify(user)]
        logger.info(f"Going to notify {len(users_to_notify)} users")

        for user in users_to_notify:
            await self._notify_user(user)

        logger.info("Updating 'last_notification' in DB")
        async with db_sessionmaker.begin() as session:
            session.add_all(users_to_notify)

    def _should_notify(self, user: DBUser) -> bool:
        return (
            user.ad_pwd_expires_in_days is not None
            and user.ad_pwd_expires_in_days in self._notify_at_days_to_expiry
        )

    async def _notify_user(self, user: DBUser) -> None:
        results = [await notificator.send(user) for notificator in self._notificators]
        if any(results):
            user.last_notification = datetime.now(UTC)


class AbstractNotificator:
    async def send(self, user: DBUser) -> bool: ...


_jinja_env = jinja2.Environment(
    undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True
)


class MailNotificator(AbstractNotificator):
    """
    Отправляет уведомление на почту пользователя, указанную во внешней БД
    """

    def __init__(self) -> None:
        self._mailsender = MailSender()

        self._subject_template = _jinja_env.from_string(settings.email_subject)
        self._content_plain_template = _jinja_env.from_string(settings.email_content_plain)
        self._content_html_template = _jinja_env.from_string(settings.email_content_html)

    @override
    async def send(self, user: DBUser) -> bool:
        if not user.externaldb_email:
            return False

        email = Email(
            recipient=user.externaldb_email,
            subject=self._subject_template.render(user=user),
            content_plain=self._content_plain_template.render(user=user),
            content_html=self._content_html_template.render(user=user),
        )
        try:
            await self._mailsender.send(email)
        except MailSenderError as e:
            metrics.errors.inc()
            logger.error(f"Mail notification to {user.ad_login} failed: {e}")
            return False

        metrics.notifications_sent.labels("email").inc()
        return True


class PortalNotificator(AbstractNotificator):
    """
    Отправляет уведомления на порталы, включенные в конфигурации
    """

    def __init__(self) -> None:
        self._portalsender = PortalSender()

        self._title_template = _jinja_env.from_string(settings.portal_title)
        self._summary_template = _jinja_env.from_string(settings.portal_summary)
        self._content_template = _jinja_env.from_string(settings.email_content_html)

    @override
    async def send(self, user: DBUser) -> bool:
        notif = PortalNotification(
            user_id=user.externaldb_id,
            title=self._title_template.render(user=user),
            summary=self._summary_template.render(user=user),
            content=self._content_template.render(user=user),
        )
        try:
            await self._portalsender.send(notif)
        except PortalNotificationError as e:
            metrics.errors.inc()
            logger.error(f"Portal notification to {user.ad_login} failed: {e}")
            return False

        metrics.notifications_sent.labels("portals").inc()
        return True
