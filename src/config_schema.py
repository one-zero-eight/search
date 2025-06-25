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
    cors_allow_origin_regex: str = ".*"
    "Allowed origins for CORS: from which domains requests to the API are allowed. Specify as a regex: `https://.*\\.innohassle\\.ru`"
    db_url: SecretStr = Field(
        ...,
        examples=["mongodb://username:password@localhost:27017/db?authSource=admin"],
    )
    "URL of the MongoDB database"


class MlServiceSettings(CustomModel):
    api_url: str = "http://127.0.0.1:8002"
    "URL of ml service API"
    api_key: SecretStr
    "Secret key to access API"
    lancedb_uri: str = "./lance_data"
    "URI of the LanceDB database"
    infinity_url: str = "http://127.0.0.1:7997"
    "URL of the deployed Infinity engine API"
    bi_encoder: str = "jinaai/jina-embeddings-v3"
    "Model to use for embeddings (should be available on Infinity)"
    bi_encoder_dim: int = 768
    "Dimension of the bi-encoder"
    bi_encoder_search_limit_per_table: int = 10
    "Limit for the number of results from the bi-encoder"
    cross_encoder: str = "jinaai/jina-reranker-v2-base-multilingual"
    "Model to use for reranking (should be available on Infinity)"


class Settings(CustomModel):
    schema_: str = Field(None, alias="$schema")
    api_settings: ApiSettings
    ml_service: MlServiceSettings
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
