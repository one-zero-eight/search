from pathlib import Path

import yaml
from pydantic import Field, SecretStr

from src.custom_pydantic import CustomModel


class Accounts(CustomModel):
    """InNoHassle-Accounts integration settings"""

    api_url: str = "https://api.innohassle.ru/accounts/v0"
    "URL of the Accounts API"
    api_jwt_token: SecretStr
    """
    JWT token for accessing the Accounts API as a service.
    Generate it here: https://api.innohassle.ru/accounts/v0/docs#/Tokens/tokens_generate_service_token
    """


class MinioSettings(CustomModel):
    endpoint: str = "127.0.0.1:9000"
    "URL of the target service."
    access_key: str = Field(..., examples=["minioadmin"])
    "Access key (user ID) of a user account in the service."
    secret_key: SecretStr = Field(..., examples=["password"])
    "Secret key (password) for the user account."


class ApiSettings(CustomModel):
    app_root_path: str = ""
    'Prefix for the API path (e.g. "/api/v0")'
    db_url: SecretStr = Field(..., examples=["mongodb://username:password@localhost:27017/db?authSource=admin"])


class Settings(CustomModel):
    schema_: str = Field(None, alias="$schema")
    api_settings: ApiSettings = Field(default_factory=ApiSettings)
    accounts: Accounts = Field(default_factory=Accounts)
    minio: MinioSettings = Field(default_factory=MinioSettings)

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path, encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            schema = {
                "$schema": "https://json-schema.org/draft-07/schema#",
                **cls.model_json_schema(),
            }
            yaml.dump(schema, f, sort_keys=False)
