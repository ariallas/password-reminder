from dataclasses import dataclass
from typing import Any

from loguru import logger

from src.config import settings
from src.utils import http_session_manager


@dataclass
class PortalNotification:
    user_id: str
    title: str
    summary: str
    content: str
    prevent_disappearance: bool = True


class PortalNotificationError(Exception):
    def __init__(self, notification: PortalNotification, error: str) -> None:
        msg = f"Error notifying user {notification.user_id} via portals: {error}"
        super().__init__(msg)
        self.notification = notification


class PortalSender:
    """
    Отправляет уведомления во внешний сервис по REST API
    """

    def __init__(self) -> None:
        self._base_url = settings.notification_api_base_url
        self._application_id = settings.application_id.get_secret_value()
        self._sendto_application_ids = [
            app_id.get_secret_value()
            for app_name, app_id in settings.portal_application_ids.items()
            if app_name in settings.enabled_portal_applications
        ]

    async def send(self, notification: PortalNotification) -> None:
        logger.debug(f"Sending portal notification to {notification.user_id}")

        if settings.debug.portal_notification_disabled:
            logger.warning(
                "Portal notifications are disabled - "
                f"message to '{notification.user_id}' will not be sent"
            )
            return

        request_body = {
            "title": notification.title,
            "summary": notification.summary,
            "content": notification.content,
            "users": [notification.user_id],
            "preventDisappearance": notification.prevent_disappearance,
            "apps": self._sendto_application_ids,
        }
        headers = {"Application-Id": self._application_id}

        http_session = http_session_manager.get_session()

        try:
            async with http_session.post(
                self._base_url + "/notification",
                json=request_body,
                timeout=20,
                headers=headers,
            ) as response:
                is_ok = response.ok
                response_body: dict[str, Any] = await response.json()
        except Exception as e:
            raise PortalNotificationError(notification, repr(e)) from e

        if not is_ok or not response_body.get("success", False):
            error = f"Negative response recieved:\n{response_body}"
            raise PortalNotificationError(notification, error)

        logger.debug(f"Succesfully sent portal notif to user {notification.user_id}")
