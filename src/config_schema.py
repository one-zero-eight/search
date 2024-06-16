from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, SecretStr, ConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"


class BotSettings(BaseModel):
    environment: Environment = Environment.DEVELOPMENT
    bot_token: SecretStr = Field(..., description="Bot token from @BotFather")
    api_url: str
    redis_url: SecretStr | None = None


class Accounts(BaseModel):
    """InNoHassle-Accounts integration settings"""

    api_url: str = "https://api.innohassle.ru/accounts/v0"
    "URL of the Accounts API"
    api_jwt_token: SecretStr
    "JWT token for accessing the Accounts API as a service"
    telegram_login_url: str = "https://innohassle.ru/account/connect-telegram"
    "URL for connecting a Telegram account to an InNoHassle account"
    telegram_bot_username: str = "InNoHassleBot"
    "Username of the Accounts bot in Telegram"


class ApiSettings(BaseModel):
    app_root_path: str = Field("", description='Prefix for the API path (e.g. "/api/v0")')

    db_url: str = Field(
        "mongodb+srv://admin:admin@localhost",
        example="mongodb+srv://username:password@host",
    )

    bot_token: str = Field(
        ..., example="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", description="Bot token from @BotFather"
    )

    api_key: str = Field(
        ...,
        example="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        description="API key for access to the Music Room API",
    )


class Settings(BaseModel):
    model_config = ConfigDict(json_schema_extra={"title": "Settings"}, extra="ignore")
    api_settings: ApiSettings | None = None
    bot_settings: BotSettings | None = None
    accounts: Accounts | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path, encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            schema = {"$schema": "https://json-schema.org/draft-07/schema", **cls.model_json_schema()}
            yaml.dump(schema, f, sort_keys=False)
