"""Langfuse tracing: `run_config` is the config for every agent call; without keys it is just the thread id.

The users' 👍/👎 on an answer are written as a score on the same trace (`trace_id`, `score_feedback`)."""

import logging

from catix.settings import settings

log = logging.getLogger("catix.tracing")

_enabled = False
if settings.langfuse_public_key and settings.langfuse_secret_key:
    from langfuse import Langfuse

    # Keys come from .env, not os.environ, so the client is created explicitly; CallbackHandler picks it up.
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        host=str(settings.langfuse_host).rstrip("/"),  # a trailing slash makes the SDK post to //api/..., which redirects and loses the data
    )
    _enabled = True


def run_config(thread_id: str, user_id: str | None = None, name: str | None = None) -> dict:
    """Config for one LLM run: the conversation thread and, when tracing is on, the Langfuse session, user and name."""
    config: dict = {"configurable": {"thread_id": thread_id}}
    if name:
        config["run_name"] = name
    if _enabled:
        from langfuse.langchain import CallbackHandler

        config["callbacks"] = [CallbackHandler()]
        config["metadata"] = {"langfuse_session_id": thread_id, **({"langfuse_user_id": user_id} if user_id else {})}
    return config


def log_status() -> None:
    """Say at startup (after logging is configured) whether and where traces go."""
    if _enabled:
        log.info("langfuse tracing on (%s)", settings.langfuse_host)
    else:
        log.warning("langfuse tracing is off: set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")


def flush() -> None:
    if _enabled:
        from langfuse import get_client

        get_client().flush()


def enabled() -> bool:
    return _enabled


def trace_id(config: dict) -> str | None:
    """The Langfuse trace of a finished run made with `config` (None when tracing is off)."""
    for handler in config.get("callbacks", []):
        if getattr(handler, "last_trace_id", None):
            return handler.last_trace_id
    return None


def score_feedback(trace: str, user_id: int, good: bool) -> None:
    """A user's thumbs up (1) or down (0) on the answer of `trace`; the same user changing their mind replaces it."""
    if not _enabled:
        return
    from langfuse import get_client

    get_client().create_score(
        name="user-feedback",
        value=1.0 if good else 0.0,
        trace_id=trace,
        score_id=f"{trace}-{user_id}",
        data_type="NUMERIC",
        comment="👍" if good else "👎",
    )
