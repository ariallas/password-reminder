from dataclasses import dataclass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from loguru import logger

from src.config import settings


@dataclass
class Email:
    recipient: str
    subject: str
    content_plain: str
    content_html: str


class MailSender:
    def __init__(self) -> None:
        self._smtp = aiosmtplib.SMTP(
            hostname=settings.smtp_secrets.hostname,
            port=settings.smtp_secrets.port,
            username=settings.smtp_secrets.username.get_secret_value(),
            password=settings.smtp_secrets.password.get_secret_value(),
            validate_certs=False,
        )
        self._sender_mail = settings.smtp_secrets.username.get_secret_value()
        self._sender_name = settings.smtp_sender_name

    async def send(self, email: Email) -> None:
        logger.debug(f"Sending email to {email.recipient}")

        if settings.debug.email_disabled:
            logger.warning(f"Email is disabled - message to '{email.recipient}' will not be sent")
            return

        message = MIMEMultipart("alternative")
        message["From"] = f"{Header(self._sender_name).encode()} <{self._sender_mail}>"
        message["Subject"] = email.subject
        message["To"] = email.recipient

        message.attach(MIMEText(email.content_plain, "plain", "utf-8"))
        message.attach(MIMEText(email.content_html, "html", "utf-8"))

        try:
            async with self._smtp as smtp:
                await smtp.send_message(message)
        except Exception as e:
            raise MailSenderError(email, e) from e

        logger.debug(f"Succesfully sent email to {email.recipient}")


class MailSenderError(Exception):
    def __init__(self, email: Email, exc: Exception) -> None:
        msg = f"Error sending email to {email.recipient}: {exc!r}"
        super().__init__(msg)
        self.email = email
