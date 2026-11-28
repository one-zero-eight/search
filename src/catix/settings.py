from datetime import time
from functools import cached_property
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from environment variables or `.env` (names are case-insensitive, e.g. LLM_ROUTE)."""

    # (hide_input_in_errors: a malformed value is named, never printed, as it may hold a password: DEEPSEEK_PROXY)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True)

    llm_route: HttpUrl = HttpUrl("http://localhost:8080/v1")
    # llama.cpp serves whatever model it was started with, the name is informational.
    llm_model: str = "local"
    # Bearer key of the model server (vLLM --api-key, e.g. on Modal). llama.cpp / 1Cat-vLLM without a key ignore it.
    llm_api_key: SecretStr = SecretStr("not-needed")
    llm_max_tokens: int = Field(4096, gt=0)
    # The agent's. 0: the same question gets the same answer; with 0.3 the model chose other searches each time, and they
    # found other messages. Still not exact: the server batches several questions, which moves the numbers a little.
    llm_temperature: float = Field(0.0, ge=0)
    # Qwen "thinking" before answering: slightly more careful, but 2-10x slower on this hardware
    # and sometimes runs out of tokens with an empty answer.
    llm_thinking: bool = False
    # Every model call thinks, including post-tool decisions and small talk (PlanThinkingMiddleware).
    # Per-call supervisor budget for reasoning and output.
    llm_plan_max_tokens: int = Field(8192, gt=0)
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
    # Questions the agent answers at once in a bot; the others wait their turn (agent/questions.py). 12 questions at once
    # on 1Cat-vLLM (2026-11-01; mean wait, first and last answer): 1 at a time 74 s, 13 s, 136 s; 4 at once 71 s, 25 s,
    # 106-111 s; 6 at once 70-78 s, 37 s, 97-105 s; 2 or 3 at once no sooner than 1.
    agent_parallel_questions: int = Field(4, gt=0)
    # Send each model call the priority of its question (agent/questions.py PRIORITY), for a server started with
    # --scheduling-policy priority. 1Cat-vLLM without it accepted one too; upstream vLLM may refuse it.
    llm_priority: bool = True
    # A long conversation is summarized before the next question when the prompt that question would have reaches this many
    # tokens: the whole history, tool results included, counted from its text at 2.5 characters a token (agent/core.py
    # estimate_tokens, ~13% above the server's count on a real chat), plus the system prompt and the tool schemas (~7k,
    # prompt_floor). The model's window is 32768 and every call reserves `llm_plan_max_tokens` (8192) of it for the answer,
    # so a prompt may take 24.5k; 13k (~11.5k real) leaves ~13k for what the question itself reads (a schedule, a catalogue
    # search and an API read were 11k tokens in a real chat). The results of earlier questions are removed before this is
    # counted (agent/core.py PruneOldToolResults). The last `agent_summarize_keep_messages` messages stay as they are.
    agent_summarize_trigger_tokens: int = Field(13000, gt=0)
    agent_summarize_keep_messages: int = Field(4, ge=2)

    # Arize Phoenix (docker-compose.yml): where the OpenInference spans of the agent go, e.g. http://localhost:6006. Unset = no
    # tracing (agent/tracing.py).
    phoenix_endpoint: HttpUrl | None = None
    phoenix_project: str = "catix"
    # How services write their logs (catix/common/logs.py); prod sets json.
    log_format: Literal["console", "json"] = "console"

    innohassle_api: HttpUrl = HttpUrl("https://api.innohassle.ru")
    # Optional complete API roots replacing /events/v1 and /clubs/v0, not the gateway or Accounts/JWKS.
    innohassle_events_api: HttpUrl | None = None
    innohassle_clubs_api: HttpUrl | None = None
    # Independently running MCP HTTP server; Docker uses the private http://mcp:8010/mcp endpoint.
    innohassle_mcp_url: HttpUrl = HttpUrl("http://127.0.0.1:8010/mcp")
    # Token of a service with the `users` scope: it lets us ask InNoHassle which study group a Telegram id belongs to.
    # The only InNoHassle token: the rest (clubs, events, maps, group timetables) is public. Without it groups are chosen with /mygroup.
    innohassle_service_token: SecretStr | None = None
    # InNoHassle Sport (sport.innopolis.university): shared API tools read the asker's sport and check them in to a
    # training with their own Sport token, which only the site has (api/auth.py verify_asker, innohassle/mcp_sport.py).
    sport_api: HttpUrl = HttpUrl("https://sport.innopolis.university/api/v3")
    # DeepSeek Search & Fetch, for what the knowledge base lacks (agent/web_tools.py). Unset: the agent has
    # no web search. Only the agent's own query goes there, never who asks.
    deepseek_api_key: SecretStr | None = None
    # Optional HTTP proxy for Search & Fetch:
    # http://[user:password@]host:port (https:// for a proxy reached over TLS). Unset: directly.
    deepseek_proxy: SecretStr | None = None
    # Off for now: the groups InNoHassle gives are not the right ones yet, so users set theirs with /mygroup.
    innohassle_groups: bool = False
    innohassle_cache_ttl: int = Field(600, ge=0, description="Seconds in the shared cache (Redis); 0: not cached.")
    # The Google Form behind the agent's leave_feedback tool (agent/feedback_tools.py): the one-zero-eight feedback form by
    # default; point these at a copy of it (same three fields) to try the tool without writing to the team's responses.
    feedback_form_url: str = "https://docs.google.com/forms/d/e/1FAIpQLSc5049bPYh7VIu44vbaroN3B6XprsuZV17WtagNYbfXzvW9JQ/formResponse"
    feedback_subject_field: str = "entry.1256372940"   # Subject / Тема (required)
    feedback_text_field: str = "entry.1356945135"      # Feedback / Обратная связь (required)
    feedback_contact_field: str = "entry.1696474646"   # Your Telegram (optional)

    # Telegram userbot (MTProto). api_id / api_hash come from https://my.telegram.org -> API development tools.
    tg_api_id: int | None = None
    tg_api_hash: SecretStr | None = None
    # Session file grants full access to the account: keep it private, it is git-ignored.
    tg_session: Path = Path("data/telegram")
    # Proxy for the userbot, where the network blocks Telegram's data centres (the bot is not affected: it talks HTTPS to
    # api.telegram.org). socks5://[user:password@]host:port, socks4://host:port, http(s)://host:port, or
    # mtproxy://SECRET@host:port (a hex secret, plain or "dd..."; fake-TLS "ee..." secrets are not supported by Telethon).
    tg_proxy: SecretStr | None = None
    # Only the starting list: copied into the database once, after that the chats and topics the userbot listens to
    # are chosen on the site (/search/admin).
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

    # User-account session; independent of Telegram and never included in backups.
    max_session: Path = Path("data/max/account.db")

    # Redis (docker-compose.yml): the bots put the ids of newly stored messages on a stream that wakes the worker's embedders
    # (`catix-worker`); every process keeps its cache there (common/cache.py: InNoHassle, Sport, DeepSeek, /listen). Without it the
    # bots publish nothing and nothing is cached.
    redis_url: str | None = None
    # Telegram ids that always get the alerts.
    admin_telegram_ids: list[int] = []
    # InNoHassle ids (the `uid` of their tokens) of the fixed cAtIx admins; more are added on the site (/search/admin).
    admin_innohassle_ids: list[str] = []
    # The HTTP API (`catix-api`, src/catix/api/): the search service's paths and the users' personal calendars
    # (/users/my-calendar.ics), behind an HTTPS proxy. In a container it listens on all interfaces: Docker's published
    # port reaches the container's own network, not its loopback (on 127.0.0.1 a request to it got an empty reply).
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    # The prefix the proxy serves the API under (e.g. /search/v0 for https://host/search/v0/users/my-calendar.ics),
    # whether it strips the prefix or passes it on. Empty: the API is at the root of the domain.
    api_root_path: str = Field("", pattern=r"^(/\S*[^/])?$")
    # Origins that may call the API from a browser, as a regex.
    api_cors_allow_origin_regex: str = ".*"
    # Start time of a change whose message names only the day: the calendar does not show all-day events.
    changes_default_time: time = time(9, 0)

    # Postgres (docker-compose.yml) with pg_search (BM25) and pgvector.
    database_url: str | None = None
    # Password of the read-only role ctx_reader that runs the model's SQL (created by `catix-db init`).
    reader_password: SecretStr | None = None
    # OpenAI-compatible /v1/embeddings server (llama.cpp --embedding, bge-m3) on the GPU machine.
    embeddings_route: HttpUrl = HttpUrl("http://localhost:8081/v1")
    embeddings_model: str = "bge-m3"
    embeddings_query_prefix: str = (
        ""  # before a query (not a document), for a model that wants an instruction; bge-m3 does not
    )
    search_candidates: int = Field(30, gt=0)
    docs_search_candidates: int = Field(30, gt=0)
    search_ef: int = Field(400, ge=1, le=1000)
    # OCR of scanned documents (docs/sources/lighton.py): LightOnOCR on the GPU server (catix-ocr.service), an
    # OpenAI-compatible server. A scan waits only when its server does not answer and Tesseract is missing too.
    ocr_route: HttpUrl | None = HttpUrl("http://127.0.0.1:9931/v1")
    ocr_model: str = "lighton"
    ocr_parallel: int = Field(1, gt=0, description="Pages sent at once, of one scan or several, and scans open at once; the "
                              "OCR server reads one page at a time, Tesseract runs this many processes while it is away.")
    # OpenAI-compatible /v1/rerank server (llama.cpp --reranking, bge-reranker-v2-m3). Without a route the search
    # keeps the order of the hybrid ranking. With one, `rerank_candidates` messages are re-scored against the
    # query and the best few go to the model.
    reranker_route: HttpUrl = HttpUrl("http://localhost:8083/v1")
    reranker_model: str = "bge-reranker-v2-m3"
    rerank_candidates: int = Field(30, gt=0)
    docs_rerank_candidates: int = Field(30, gt=0)
    rerank_queries: int = Field(9, gt=0)
    # Fresher documents first: after the reranker, a document's score is multiplied by 1 - rate × (its age in years - 1), not
    # below the floor; a document up to a year old, an undated one and a site page (its date is the day it was read) keep theirs.
    docs_freshness_rate: float = Field(0.03, ge=0)
    docs_freshness_floor: float = Field(0.85, gt=0, le=1)
    # How much of a piece the reranker reads. At 1000 the answer of a piece that puts it near the end was cut off: on the
    # 57-question set 2000 kept hit@5 as it was and found the answer in the top 8 for 1.8 points more of the questions,
    # on the 159 generated ones it raised hit@1 by 3 points and MRR from 0.561 to 0.583.
    rerank_max_chars: int = Field(2000, gt=0)
    # The chat search (store.py) does without the reranker by default: on experiments/eval_search.py the fused ranking
    # alone found every answer in the first 10 (the reranker's cutoff dropped one) in 0.05 s instead of 0.85 s, and the
    # agent reads all 15 hits anyway. The wiki search always reranks: without it hit@5 falls from 91% to 75%.
    rerank_chats: bool = True
    # Messages the reranker scores below this are dropped, even if fewer than the limit are left (none at all is a
    # valid answer: nothing relevant). The scale is the server's own (llama.cpp gives raw scores, not 0..1), so
    # pick the value from the scores the search logs at DEBUG level. None = no cutoff.
    # -3.0 comes from a handful of real queries with bge-reranker-v2-m3: answers sit at about -0.5..+1, off-topic
    # noise at -4..-5.
    rerank_min_score: float | None = -3.0
    # A message of a chat search is about the question when its second best score over the queries (two angles agree)
    # is this or above. A search with none, or with none that an earlier search had not found, is empty for the guard
    # (agent/core.py), and two in a row end the searching. On 47 searches of the traces and the labelled set, those that
    # found what was asked (physical education, bed linen, the military office, the map) gave -1.32 or above, those the
    # chats helper reworded in vain (a camera for an online exam, administrator rights, choosing electives) -2.02 at
    # best. Called empty wrongly, a search costs little: what it found stays before the model, which reports a round earlier.
    chat_relevant_score: float = -1.5
    # The same for a piece of the wiki (search_wiki). Here the score tells apart only a search for what the wiki does not
    # hold (a misspelt name, the age of a teacher: -3.24 to -4.12 at best, the list of teachers coming back each time):
    # a piece the docs helper cited in its report scored as low as -1.86, and searches it cited nothing of scored as high
    # as 2.64. Of 159 generated questions, the 90 that found their source page found it at -0.63 or above; the two
    # below -2.5 did not find it.
    docs_relevant_score: float = -2.5
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

    archive_preview_cache: Path = Path("data/archive-previews")  # a cache of previewed archive members (api/search.py), not a store of documents
    # Course programmes (docs/sources/rpd.py) of every cohort on the site, not only the latest one of each programme: a student of
    # 2024 studies by the programme of 2024.
    docs_rpd_all_years: bool = True

    # Old SQLite file, only read by `catix-db migrate`.
    messages_db: Path = Path("raw/telegram.db")
    sites_file: Path = Path("sites.yaml")  # the seed of the catalog of sites: `catix-docs sites catalog import` loads it into Postgres (docs/sources/sites.py)
    timezone: str = "Europe/Moscow"

    @field_validator("innohassle_events_api", "innohassle_clubs_api", mode="before")
    @classmethod
    def _service_api_root(cls, value):
        if value is None or value == "":
            return None
        raw = str(value)
        parsed = urlsplit(raw)
        if parsed.username is not None or parsed.password is not None or "?" in raw or "#" in raw:
            raise ValueError("Service API URLs must not contain credentials, query or fragment.")
        return value

    @field_validator("innohassle_mcp_url", mode="before")
    @classmethod
    def _mcp_url_without_context(cls, value):
        # HttpUrl normalizes empty userinfo away; reject it before conversion.
        raw = str(value)
        parsed = urlsplit(raw)
        if parsed.username is not None or parsed.password is not None or "?" in raw or "#" in raw:
            raise ValueError("MCP URLs must not contain credentials, query or fragment.")
        return value

    @field_validator("deepseek_api_key", "deepseek_proxy")
    @classmethod
    def _empty_is_unset(cls, value: SecretStr | None) -> SecretStr | None:
        """`DEEPSEEK_API_KEY=` in .env is no key (and so no web search), not an empty one."""
        return value if value is not None and value.get_secret_value().strip() else None

    @field_validator("deepseek_proxy")
    @classmethod
    def _http_proxy(cls, value: SecretStr | None) -> SecretStr | None:
        """A malformed DEEPSEEK_PROXY stops the start, as a malformed TG_PROXY stops the userbot's."""
        if value is None:
            return None
        url = value.get_secret_value().strip()
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or not parts.port:
            raise ValueError("DEEPSEEK_PROXY is an HTTP proxy with a host and a port, e.g. http://user:password@host:3128")
        return SecretStr(url)

    @cached_property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


settings = Settings()
