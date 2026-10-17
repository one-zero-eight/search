from datetime import time
from functools import cached_property
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables or `.env` (names are case-insensitive, e.g. LLM_ROUTE)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_route: HttpUrl = HttpUrl("http://localhost:8080/v1")
    # llama.cpp serves whatever model it was started with, the name is informational.
    llm_model: str = "local"
    llm_max_tokens: int = Field(4096, gt=0)
    llm_temperature: float = Field(0.3, ge=0)
    # Qwen "thinking" before answering: slightly more careful, but 2-10x slower on this hardware
    # and sometimes runs out of tokens with an empty answer.
    llm_thinking: bool = False
    # Next to every chat message the tools give the concrete dates its "завтра", "в пятницу" or "23 октября" mean
    # and how far they are from today (src/catix/common/dates.py); the model does not have to do date arithmetic.
    annotate_dates: bool = True
    agent_max_model_calls: int = Field(6, gt=0, description="Model calls per question, including tool rounds.")
    # Old tool results dominate the context of long chats; above this size (approximate tokens)
    # all but the last `agent_keep_tool_results` are replaced by a placeholder.
    agent_context_trigger_tokens: int = Field(6000, gt=0)
    agent_keep_tool_results: int = Field(3, ge=0)

    # Langfuse tracing of the agent (https://langfuse.com). Both keys set: every question is traced; otherwise off.
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    # .env uses LANGFUSE_BASE_URL (the name the Langfuse SDK itself reads); LANGFUSE_HOST also works.
    langfuse_host: HttpUrl = Field(HttpUrl("https://cloud.langfuse.com"), validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST"))

    innohassle_api: HttpUrl = HttpUrl("https://api.innohassle.ru")
    # Not needed for the public endpoints used so far (clubs, events.ics, maps).
    innohassle_token: SecretStr | None = None
    # Token of a service with the `users` scope: it lets us ask InNoHassle which study group a Telegram id belongs to.
    # A normal user token (scope `me`, the one above) cannot do that. Without it groups are chosen with /mygroup.
    innohassle_service_token: SecretStr | None = None
    innohassle_cache_ttl: int = Field(600, ge=0, description="Seconds.")

    # Telegram userbot (MTProto). api_id / api_hash come from https://my.telegram.org -> API development tools.
    tg_api_id: int | None = None
    tg_api_hash: SecretStr | None = None
    # Session file grants full access to the account: keep it private, it is git-ignored.
    tg_session: Path = Path("data/telegram")
    # Whitelist of chats to ingest: marked ids (-100...) or @usernames. JSON list in env: TG_CHATS='[-1001234, "@chat"]'
    tg_chats: list[int | str] = []
    tg_sync_days: int = Field(365, gt=0, description="How far back the first sync of a chat goes.")
    # Only these topics are stored from the listed forum chats: {chat id: [topic ids]}, e.g.
    # TG_TOPICS='{"-1001234567890": [5, 17]}'. Chats not listed here are stored whole. Topic 1 is
    # "General". Find topic ids with `catix-tguserbot topics <chat>` or the bot's /id command inside a topic.
    tg_topics: dict[int, list[int]] = {}
    # False: the bot answers from all stored chats, wherever and by whomever it is asked. True: a group answer uses
    # only public chats and that group, a private answer public chats and the chats the asker is known to belong to
    # (src/catix/tgbot/access.py). Off for now: the chats are course chats with nothing secret in them, and in groups with
    # hidden member lists membership cannot be found out at all.
    restrict_chat_access: bool = False
    # Private chats whose content may be shown to anyone, e.g. a course channel all students can join.
    # Public chats (with @username) are open automatically; everything else only to its members.
    tg_open_chats: list[int] = []

    # Bot API token from @BotFather. The bot stores messages of every group it is added to
    # (adding it is the admins' consent) and answers in DMs, on @mention, reply or /ask.
    tg_bot_token: SecretStr | None = None

    # Max messenger bot (https://dev.max.ru): token from the "MAX для бизнеса" bot. The Max API is served with a
    # certificate of the Russian Ministry of Digital Development, which is not in the usual CA lists: the root
    # certificate (https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt) is added to the trusted ones.
    max_bot_token: SecretStr | None = None
    max_root_ca: Path = Path("data/russian_root_ca.crt")

    # Schedule changes found in chats (changes.py): reschedules, room changes, cancellations. A change reaches the
    # calendar feed only after an admin approves it in Telegram.
    # Redis (docker-compose.yml): the bots put the ids of newly stored messages on a stream, the worker `catix-worker`
    # reads it. Without it the bots publish nothing.
    redis_url: str | None = None
    changes_enabled: bool = True
    # Telegram ids that approve changes; empty = the owner of INNOHASSLE_TOKEN.
    admin_telegram_ids: list[int] = []
    # The feed is served at /feed/<token>.ics on feed_port; InNoHassle links it as an external calendar, so it must
    # be reachable from the internet over HTTPS (a tunnel or reverse proxy). Without a token there is no feed.
    feed_token: SecretStr | None = None
    feed_port: int = 8090
    feed_days_back: int = Field(30, gt=0, description="How far into the past the feed goes.")
    # Start time of a change whose message names only the day: the calendar does not show all-day events.
    changes_default_time: time = time(9, 0)

    # Postgres (docker-compose.yml) with pg_search (BM25) and pgvector.
    database_url: str | None = None
    # Password of the read-only role ctx_reader that runs the model's SQL (created by `catix-db init`).
    reader_password: SecretStr | None = None
    # OpenAI-compatible /v1/embeddings server (llama.cpp --embedding, bge-m3) on the GPU machine.
    embeddings_route: HttpUrl = HttpUrl("http://localhost:8081/v1")
    embeddings_model: str = "bge-m3"
    # Longer messages are cut before embedding: the start carries the meaning, and cost grows with length.
    embeddings_max_chars: int = Field(2000, gt=0)
    embed_workers: int = Field(2, gt=0, description="Parallel embedding requests; ~2-4 saturates the GPU server.")
    embed_batch: int = Field(64, gt=0, description="Messages per embeddings request.")

    # Messages that arrive while a write is running are written together, up to this many per transaction.
    ingest_max_batch: int = Field(500, gt=0)

    # Old SQLite file, only read by `catix-db migrate`.
    messages_db: Path = Path("raw/telegram.db")
    courses_file: Path = Path("courses.toml")
    timezone: str = "Europe/Moscow"

    @cached_property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


settings = Settings()
