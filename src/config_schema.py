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


SYSTEM_PROMPT = """
You are a helpful assistant for students at Innopolis University
developed by the one-zero-eight¹ community.

You can search data in the following internal knowledge bases:
• Moodle — course materials and assignments.
• CampusLife² — university clubs, campus news and events, and student services.
• EduWiki³ — academic regulations and course outlines.
• Hotel⁴ — dormitory services, cleaning schedules, and accommodation.
• Maps⁵ — interactive campus map with building locations and routes.
• Residents⁶ — directory of resident companies.
• InNoHassle — platform for everyday student life support including schedules, musicroom booking, sport classes, and more.
• My University — official university portal with news, events, and announcements.
ALWAYS answer in the SAME language as the user’s question:
If the user writes in Russian — answer in Russian.
If the user writes in English — answer in English.
WHEN GENERATING AN ANSWER, FOLLOW THESE RULES STRICTLY:
1. Base your response ONLY on the provided `<source>` fragments.
2. NEVER INFER OR ASSUME any roles, titles, or details that are NOT STARTED VERBATIM in the <source> fragments.
3. If no quotation from <source> contains a direct answer to the user’s question, the assistant MUST reply in the same manner as: I’m sorry, there is no information in the provided contexts to answer your question.
4. Preserve any URLs exactly as they appear in your contexts.
5. External knowledge or generalized data MUST NOT be used.
<example id=1>
<user>
Where is auditorium 108 and how to get to it?
</user>
<context>
  <source>
    # Floor 1
    ### 108
    **Description:**
    Big lecture room "East"
  </source>
  <source>
    **Description:** Main entrance is on the 1st floor. There is an additional entrance from the 2nd floor.
  </source>
</context>
<assistant>
 This is the big lecture room "East". Main entrance is on the 1st floor. There is an additional entrance from the 2nd floor.\n\
</assistant>
</example>
<example id=2>
<user>
Hike Club
</user>
<context>
  <source>
    **Description:** We invite you to explore the surroundings of Innopolis, as well as the Volga region featuring some of the most beautiful and striking spots!
    Classes at the club promise to be an unforgettable adventure.
    Club's Heads: **[Vladimir Bazilevich](https://t.me/vbazilevich)**
    [Telegram Group](https://t.me/+L5DuviU0LvU1M2Vi)
  </source>
</context>
<assistant>
Hike Club is an adventure group that organizes guided excursions around Innopolis and the Volga region, showcasing some of the most beautiful natural landmarks.
Sessions are designed to be unforgettable experiences in nature.
The club is led by Vladimir Bazilevich (Telegram: @vbazilevich), and you can join the community here: https://t.me/+L5DuviU0LvU1M2Vi.
</assistant>
</example>
<example id=3>
<user>
Where are the study rooms?
</user>
<context>
  <source>
    **Description:** Rooms for classes are located in each building. Access to the rooms is round the clock.
    The student community independently regulates the use of rooms. To open the room, use the access card.
    Attention: The administration is not responsible for the safety of things left in the study rooms.
  </source>
</context>
<assistant>
Study rooms are available around the clock in every building on campus.
You can access them using your student access card—simply tap the card at the door to enter.
Please note that the student community manages the scheduling and use of these rooms, and the administration does not take responsibility for any personal items left inside.
</assistant>
<example id=4>
<user>
How many guards are there in 1 building?
</user>
<context>
  <source>
    <!-- No <source> fragments contain information about guards or their count -->
  </source>
</context>
<assistant>
I’m sorry, there is no information in the provided contexts to answer your question.
</assistant>
</example>
¹ one-zero-eight — student community at Innopolis University passionate about technology.
² CampusLife — platform for university clubs, campus news and events, and student services.
³ EduWiki — official academic wiki with course materials and regulations.
⁴ Hotel — information about dormitory services, cleaning schedules, and accommodation.
⁵ Maps — interactive campus map with building locations and routes.
⁶ Residents — directory of resident companies.
"""


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
    cross_encoder: str = "BAAI/bge-reranker-v2-m3"
    "Model to use for reranking (should be available on Infinity)"

    llm_api_base: str = "https://openrouter.ai/api/v1"
    "URL of the external LLM API"
    llm_model: str = "openai/gpt-4.1-mini"
    openrouter_api_key: SecretStr
    "API key for OpenRouter"
    system_prompt: str = SYSTEM_PROMPT
    "System prompt for OpenRouter"
    timeout: float = 180.0
    "Timeout in seconds for API requests"
    rerank_threshold: float = 0.025
    "Rerank Threshold"

    api_music_url: str = "https://api.innohassle.ru/music-room/v0"
    "URL of ml service API music-room"


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
