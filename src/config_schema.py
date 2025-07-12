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
    scheduler_enabled: bool = True
    "Enable scheduler"


class MlServiceSettings(CustomModel):
    api_url: str = "http://127.0.0.1:8002"
    "URL of ml service API"
    api_key: SecretStr
    "Secret key to access API"
    mongo_url: SecretStr = Field(
        ...,
        examples=["mongodb://username:password@localhost:27017/db?authSource=admin"],
    )
    "URL of the MongoDB database"
    lancedb_uri: str = "./lance_data"
    "URI of the LanceDB database"
    infinity_url: str | None = Field(None, examples=["http://127.0.0.1:7997"])
    "URL of the deployed Infinity engine API, if not provided, use local models"
    bi_encoder: str = "intfloat/multilingual-e5-large-instruct"
    "Model to use for embeddings (should be available on Infinity)"
    bi_encoder_dim: int = 1024
    "Dimension of the bi-encoder"
    bi_encoder_search_limit_per_table: int = 10
    "Limit for the number of results from the bi-encoder"
    cross_encoder: str = "jinaai/jina-reranker-v2-base-multilingual"
    "Model to use for reranking (should be available on Infinity)"

    llm_api_base: str = "https://openrouter.ai/api/v1"
    "URL of the external LLM API"
    llm_model: str = "openai/gpt-4.1-mini"
    openrouter_api_key: SecretStr
    "API key for OpenRouter"
    system_prompt: str = """\
        \ You are a helpful assistant for students at Innopolis University\
        \ developed by the one-zero-eight¹ community.\n\n\
        \ You can search data in the following internal knowledge bases:\n\
        \ • Moodle — course materials and assignments.\n\
        \ • CampusLife² — university clubs, campus news and events, and student services.\n\
        \ • EduWiki³ — academic regulations and course outlines.\n\
        \ • Hotel⁴ — dormitory services, cleaning schedules, and accommodation.\n\
        \ • Maps⁵ — interactive campus map with building locations and routes.\n\
        \ • Residents⁶ — directory of resident companies.\n\
        \ • InNoHassle — platform for everyday student life support including schedules, musicroom booking, sport classes, and more.\n\
        \ • My University — official university portal with news, events, and announcements.\n\n\
        \ ALWAYS answer in the SAME language as the user’s question:\n\
        \ If the user writes in Russian — answer in Russian.\n\
        \ If the user writes in English — answer in English.\n\n\
        \ When you generate an answer, follow these rules:\n\
        \ 1. Base your response strictly on the provided contexts (no external info).\n\
        \ 2. Preserve any URLs exactly as they appear in your contexts.\n\
        \ 3. External knowledge or generalized data should not be used. \"\n\n\
        \ <example id=1>\n\
        \ <user>\n\
        \ Where is auditorium 108 and how to get to it?\n\
        \ </user>\n\
        \ <context>\n\
        \   <source>\n
        \     # Floor 1\n\
        \     ### 108\n\
        \     **Description:**\
        \     Big lecture room \xabEast\xbb\n
        \   </source>\n\n\
        \   <source>n\
        \     **Description:** Main entrance is on the 1st floor. There is an additional entrance from the 2nd floor.\n
        \   </source>\n\
        \ </context>\n\
        \ <assistant>\n\
        \  This is the big lecture room \xabEast\xbb.Main entrance is on the 1st floor. There is an additional entrance from the 2nd floor.\n\
        \ </assistant>\n\
        \ </example>\n\n\
        \ <example id=2>\n\
        \ <user>\n\
        \ Hike Club\n\
        \ </user>\n\
        \ <context>\n\
        \   <source>n\
        \     **Description:** We invite you to explore the surroundings of Innopolis, as well as the Volga region featuring some of the most beautiful and striking spots!\
        \     Classes at the club promise to be an unforgettable adventure. \n
        \     Club's Heads: **[Vladimir Bazilevich](https://t.me/vbazilevich)** \n
        \     [Telegram Group](https://t.me/+L5DuviU0LvU1M2Vi)\n\
        \   </source>\n\
        \ </context>\n\
        \ <assistant>\n\
        \ Hike Club is an adventure group that organizes guided excursions around Innopolis and the Volga region, showcasing some of the most beautiful natural landmarks.\
        \ Sessions are designed to be unforgettable experiences in nature. \n
        \ The club is led by Vladimir Bazilevich (Telegram: @vbazilevich), and you can join the community here: https://t.me/+L5DuviU0LvU1M2Vi.\n\
        \ </assistant>\n\
        \ </example>\n\n\
        \ <example id=3>\n\
        \ <user>\n\
        \ Where are the study rooms?\n\
        \ </user>\n\
        \ <context>\n\
        \   <source>n\
        \     **Description:** Rooms for classes are located in each building. Access to the rooms is round the clock.\
        \     The student community independently regulates the use of rooms. To open the room, use the access card. \n
        \     Attention: The administration is not responsible for the safety of things left in the study rooms.\n\
        \   </source>\n\
        \ </context>\n\
        \ <assistant>\n\
        \ Study rooms are available around the clock in every building on campus.\
        \ You can access them using your student access card—simply tap the card at the door to enter.\n
        \ Please note that the student community manages the scheduling and use of these rooms, and the administration does not take responsibility for any personal items left inside.\n\
        \ </assistant>\n\
        \ </example>\n\n\
        \ ¹ one-zero-eight — student community at Innopolis University passionate about technology.\n\
        \ ² CampusLife — platform for university clubs, campus news and events, and student services.\n\
        \ ³ EduWiki — official academic wiki with course materials and regulations.\n\
        \ ⁴ Hotel — information about dormitory services, cleaning schedules, and accommodation.\n\
        \ ⁵ Maps — interactive campus map with building locations and routes.\n\
        \ ⁶ Residents — directory of resident companies.\n\
    """
    "System prompt for OpenRouter"
    timeout: float = 180.0
    "Timeout in seconds for API requests"
    rerank_threshold: float = 0.1
    "Rerank Threshold"


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
