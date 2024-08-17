from __future__ import annotations

from typing import Annotated, Literal

from ezconfig import (
    EzconfigPydanticSettings,
    ReadableFromVault,
    init_settings_multienv,
)
from pydantic import BaseModel, SecretStr, field_validator


class DbSecrets(BaseModel):
    postgres_host: str
    postgres_port: int
    postgres_user: SecretStr
    postgres_password: SecretStr


class ExternalDBSecrets(BaseModel):
    host: str
    port: int
    user: SecretStr
    password: SecretStr


class ADSecrets(BaseModel):
    url: str
    user: SecretStr
    password: SecretStr


class SMTPSecrets(BaseModel):
    hostname: str
    port: int
    username: SecretStr
    password: SecretStr


class DebugFeatures(BaseModel):
    run_immediately: bool
    enable_sqlalchemy_logs: bool
    email_disabled: bool
    portal_notification_disabled: bool


PortalApplication = Literal["application1", "application2"]


class AppSettings(EzconfigPydanticSettings):
    notification_api_base_url: str
    application_id: Annotated[SecretStr, ReadableFromVault]
    portal_application_ids: Annotated[dict[PortalApplication, SecretStr], ReadableFromVault]
    enabled_portal_applications: list[PortalApplication]

    db_database: str
    db_secrets: Annotated[DbSecrets, ReadableFromVault]

    externaldb_database: str
    externaldb_secrets: Annotated[ExternalDBSecrets, ReadableFromVault]
    externaldb_group_names_to_include: list[str]
    externaldb_group_names_to_exclude: list[str]

    active_directory: Annotated[ADSecrets, ReadableFromVault]
    search_base: str

    debug: DebugFeatures

    smtp_sender_name: str
    smtp_secrets: Annotated[SMTPSecrets, ReadableFromVault]

    schedule_main: str
    notify_at_days_to_expiry: list[int]

    email_subject: str
    email_content_html: str
    email_content_plain: str
    portal_title: str
    portal_summary: str

    @field_validator("notify_at_days_to_expiry")
    @classmethod
    def sort_days_to_expiry(cls, days_to_expiry: list[int]) -> list[int]:
        return sorted(days_to_expiry)


settings = init_settings_multienv(
    {
        "prod": ["config/notifications.yaml", "config/settings_prod.yaml"],
        "test": ["config/notifications.yaml", "config/settings_test.yaml"],
    },
    AppSettings,
)
