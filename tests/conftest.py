from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from src.config import settings
from src.notification.mailsender import Email
from src.notification.portalsender import PortalNotification


@pytest.fixture(autouse=True, scope="session")
def _adjust_settings() -> None:
    settings.smtp_secrets.hostname = "http://localhost"
    settings.notification_api_base_url = "http://localhost"

    settings.debug.email_disabled = False
    settings.debug.portal_notification_disabled = False


@pytest.fixture()
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[Email]:
    _sent_emails: list[Email] = []

    async def _send(_: object, email: Email) -> None:
        _sent_emails.append(email)

    monkeypatch.setattr("src.notification.mailsender.MailSender.send", _send)
    return _sent_emails


@pytest.fixture(autouse=True)
def mock_smtp_send(mocker: MockerFixture) -> AsyncMock:
    smtp_mock = AsyncMock()
    mocker.patch("src.notification.mailsender.aiosmtplib.SMTP", return_value=smtp_mock)
    return smtp_mock.__aenter__.return_value.send_message


@pytest.fixture()
def sent_portal(monkeypatch: pytest.MonkeyPatch) -> list[PortalNotification]:
    _sent_notifs: list[PortalNotification] = []

    async def _send(_: object, notification: PortalNotification) -> None:
        _sent_notifs.append(notification)

    monkeypatch.setattr("src.notification.portalsender.PortalSender.send", _send)
    return _sent_notifs


@pytest.fixture(autouse=True)
def mock_portal_send(mocker: MockerFixture) -> MagicMock:
    session_mock = MagicMock()
    mocker.patch(
        "src.notification.portalsender.http_session_manager.get_session",
        return_value=session_mock,
    )
    response_mock = session_mock.post.return_value.__aenter__.return_value
    response_mock.json = AsyncMock()
    response_mock.json.return_value = MagicMock()
    return session_mock.post
