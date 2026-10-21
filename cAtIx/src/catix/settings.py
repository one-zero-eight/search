from datetime import time
from functools import cached_property
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, Field, HttpUrl, SecretStr, field_validator
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
    # Every user message is screened before the agent (agent/guardrail.py, always on). Repeated attacks (agent/guardrail.py -> abuse.py): from the 3rd stopped message in a day the refusal carries a warning, from
    # the 5th the user is paused (15 minutes, doubled for each repeat, at most a day); nobody is messaged (see /abuse). Only what the
    # screen stops is counted; the agent refuses off-topic requests (a joke, some code) itself. Admins are exempt.
    abuse_enabled: bool = True
    abuse_warn_at: int = Field(3, gt=0)
    abuse_pause_at: int = Field(5, gt=0)
    abuse_window_hours: int = Field(24, gt=0)
    abuse_pause_minutes: int = Field(15, gt=0)
    abuse_pause_max_hours: int = Field(24, gt=0)
    abuse_forget_days: int = Field(7, gt=0, description="After this long without a pause the next one is short again.")
    agent_max_model_calls: int = Field(6, gt=0, description="Model calls per question, including tool rounds.")
    # Old tool results dominate the context of long chats; above this size (approximate tokens)
    # all but the last `agent_keep_tool_results` are replaced by a placeholder.
    agent_context_trigger_tokens: int = Field(6000, gt=0)
    agent_keep_tool_results: int = Field(3, ge=0)
    # A long conversation is summarized before the next question when the questions and answers of it (tool results are
    # not counted: they are cut above) reach this many tokens (approximate: Russian is about 1.8x more in reality), so
    # that the history never grows to the model's window (the llama.cpp slot, e.g. 17k). The last
    # `agent_summarize_keep_messages` messages stay as they are.
    agent_summarize_trigger_tokens: int = Field(3000, gt=0)
    agent_summarize_keep_messages: int = Field(4, ge=2)

    # Arize Phoenix (docker-compose.yml): where the OpenInference spans of the agent go, e.g. http://localhost:6006. Unset = no
    # tracing (agent/tracing.py).
    phoenix_endpoint: HttpUrl | None = None
    phoenix_project: str = "catix"

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
    # Only the starting list: copied into the database once, after that the chats and topics the userbot listens to
    # are chosen in the bot (/listen).
    # Whitelist of chats to ingest: marked ids (-100...) or @usernames. JSON list in env: TG_CHATS='[-1001234, "@chat"]'
    tg_chats: list[int | str] = []
    tg_sync_days: int = Field(365, gt=0, description="How far back the first sync of a chat goes.")
    # Only these topics are stored from the listed forum chats: {chat id: [topic ids]}, e.g.
    # TG_TOPICS='{"-1001234567890": [5, 17]}'. Chats not listed here are stored whole. Topic 1 is
    # "General". Find topic ids with `catix-tguserbot topics <chat>` or the bot's /id command inside a topic.
    tg_topics: dict[int, list[int]] = {}

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
    # Public HTTPS address of the feed server (a reverse proxy or tunnel in front of feed_port), e.g. https://cal.example.com.
    # With it (and feed_token) the bot's /calendar hands out the group and personal calendar links.
    feed_public_url: HttpUrl | None = None
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
    # OpenAI-compatible /v1/rerank server (llama.cpp --reranking, bge-reranker-v2-m3). Without a route the search
    # keeps the order of the hybrid ranking. With one, `rerank_candidates` messages are re-scored against the
    # query and the best few go to the model.
    reranker_route: HttpUrl | None = None
    reranker_model: str = "bge-reranker-v2-m3"
    rerank_candidates: int = Field(60, gt=0)
    # Messages the reranker scores below this are dropped, even if fewer than the limit are left (none at all is a
    # valid answer: nothing relevant). The scale is the server's own (llama.cpp gives raw scores, not 0..1), so
    # pick the value from the scores the search logs at DEBUG level. None = no cutoff.
    # -3.0 comes from a handful of real queries with bge-reranker-v2-m3: answers sit at about -0.5..+1, off-topic
    # noise at -4..-5.
    rerank_min_score: float | None = -3.0
    # Longer messages are cut before embedding: the start carries the meaning, and cost grows with length.
    embeddings_max_chars: int = Field(2000, gt=0)
    embed_workers: int = Field(2, gt=0, description="Parallel embedding requests; ~2-4 saturates the GPU server.")
    embed_batch: int = Field(64, gt=0, description="Messages per embeddings request.")

    # Alerts to the admins in Telegram (worker/health.py): a model, the embeddings or the reranker stop answering,
    # or more than `alert_queue_max` messages wait for a vector for several checks in a row.
    alerts: bool = True
    alert_check_seconds: int = Field(60, gt=0)
    alert_queue_max: int = Field(500, gt=0)

    # Live search in Telegram (live_search.py): chats set to "only search" in /listen are not stored; the userbot searches
    # them with Telegram's own search when a question needs it, `live_search_per_chat` hits per keyword and chat, the best
    # `live_search_results` of them go to the model. The request waits `live_search_timeout` seconds for the userbot.
    live_search_per_chat: int = Field(15, gt=0)
    live_search_results: int = Field(4, gt=0)
    live_search_timeout: float = Field(10.0, gt=0)

    # Messages that are certainly noise (a bare greeting, "+", emoji only, a word of three letters) are not stored at
    # all (ingest/noise.py). Existing ones are removed with `catix-db prune-noise`.
    drop_noise: bool = True

    # Messages that arrive while a write is running are written together, up to this many per transaction.
    ingest_max_batch: int = Field(500, gt=0)

    # Old SQLite file, only read by `catix-db migrate`.
    messages_db: Path = Path("raw/telegram.db")
    courses_file: Path = Path("courses.toml")
    timezone: str = "Europe/Moscow"

    @field_validator("feed_public_url", mode="before")
    @classmethod
    def _feed_url_scheme(cls, value: object) -> object:
        """`FEED_PUBLIC_URL=name.tuna.am` is what a tunnel prints: it means https, and an empty value means off."""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            if "://" not in value:
                return f"https://{value}"
        return value

    @cached_property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


settings = Settings()
