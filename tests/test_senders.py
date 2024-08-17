from unittest.mock import AsyncMock, MagicMock

import pytest

from src.notification.mailsender import Email, MailSender, MailSenderError
from src.notification.portalsender import PortalNotification, PortalNotificationError, PortalSender


@pytest.fixture()
def mailsender() -> MailSender:
    return MailSender()


email = Email(
    recipient="recipient",
    subject="subject",
    content_plain="content_plain",
    content_html="content_html",
)


async def test_sent_emails(mailsender: MailSender, sent_emails: list[Email]) -> None:
    """
    Проверка, что патч для MailSender.send работает корректно
    """
    await mailsender.send(email)

    assert len(sent_emails) == 1
    assert sent_emails[0] == email


async def test_mock_smtp_send(mailsender: MailSender, mock_smtp_send: AsyncMock) -> None:
    """
    Проверка, что мок для aiosmtplib.SMTP.send_message работает корректно
    """
    await mailsender.send(email)
    mock_smtp_send.assert_awaited_once()


async def test_email_send_error(mailsender: MailSender, mock_smtp_send: AsyncMock) -> None:
    """
    Проверка, что мок для aiosmtplib.SMTP.send_message работает корректно
    """
    mock_smtp_send.side_effect = Exception()
    with pytest.raises(MailSenderError):
        await mailsender.send(email)


@pytest.fixture()
def portalsender() -> PortalSender:
    return PortalSender()


notification = PortalNotification(
    title="test_title",
    summary="test_summary",
    content="test_content",
    user_id="test_user_id",
)


async def test_sent_portal(
    portalsender: PortalSender, sent_portal: list[PortalNotification]
) -> None:
    """
    Проверка, что патч для PortalSender.send работает корректно
    """
    await portalsender.send(notification)

    assert len(sent_portal) == 1
    assert sent_portal[0] == notification


async def test_mock_portal_send(portalsender: PortalSender, mock_portal_send: MagicMock) -> None:
    """
    Проверка, что мок для ClientSession.post работает корректно
    """
    await portalsender.send(notification)
    mock_portal_send.assert_called_once()


async def test_portal_send_error(portalsender: PortalSender, mock_portal_send: MagicMock) -> None:
    """
    Проверка, что мок для ClientSession.post работает корректно
    """
    mock_portal_send.side_effect = Exception()
    with pytest.raises(PortalNotificationError):
        await portalsender.send(notification)
