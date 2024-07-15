from pathlib import Path

import yaml
from pydantic import Field, SecretStr

from src.custom_pydantic import CustomModel


class Accounts(CustomModel):
    """InNoHassle-Accounts integration settings"""

    api_url: str = "https://api.innohassle.ru/accounts/v0"
    "URL of the Accounts API"


class MinioSettings(CustomModel):
    endpoint: str = "127.0.0.1:9000"
    "URL of the target service."
    secure: bool = False
    "Use https connection to the service."
    region: str | None = None
    "Region of the service."
    bucket: str = "search"
    "Name of the bucket in the service."
    access_key: str = Field(..., examples=["minioadmin"])
    "Access key (user ID) of a user account in the service."
    secret_key: SecretStr = Field(..., examples=["password"])
    "Secret key (password) for the user account."


class ApiSettings(CustomModel):
    app_root_path: str = ""
    'Prefix for the API path (e.g. "/api/v0")'
    cors_allow_origins: list[str] = ["https://innohassle.ru", "https://pre.innohassle.ru", "http://localhost:3000"]
    "Allowed origins for CORS: from which domains requests to the API are allowed"
    cors_allow_origins_regex: str = None
    "Regular expression for allowed origins for CORS (.* for example)"
    db_url: SecretStr = Field(..., examples=["mongodb://username:password@localhost:27017/db?authSource=admin"])
    "URL of the MongoDB database"
    compute_service_token: str = "secret"
    "Access token for the compute service which is used for authentication"


class ComputeSetting(CustomModel):
    api_url: str = "http://127.0.0.1:8001"
    "URL of the Search API"
    auth_token: str = "secret"
    "Access token for the compute service which is used for authentication"
    corpora_update_period: float = 300
    "Period in seconds to fetch corpora from the API"
    check_search_queue_period: float = 0.1
    "Period in seconds to fetch tasks from the API"
    num_workers: int = 4
    "Number of workers to process tasks"
    qdrant_url: SecretStr = SecretStr("http://127.0.0.1:6333")
    "URL of the Qdrant service"
    qdrant_collection_name: str = "inh-search"
    "Name of the collection in the Qdrant service"
    bi_encoder_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    "Name of the bi-encoder model"
    bi_encoder_batch_size: int = 32
    "Batch size for the bi-encoder model"
    cross_encoder_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    "Name of the cross-encoder model"
    cross_encoder_batch_size: int = 32
    "Batch size for the cross-encoder model"


class Settings(CustomModel):
    schema_: str = Field(None, alias="$schema")
    api_settings: ApiSettings
    compute_settings: ComputeSetting = ComputeSetting()
    accounts: Accounts = Accounts()
    minio: MinioSettings

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
