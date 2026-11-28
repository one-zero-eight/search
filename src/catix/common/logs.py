"""Logging of every service (its `main()` calls `setup()`): the stdlib loggers of the code and of the libraries, uvicorn's
access lines included, go through structlog. LOG_FORMAT=console (the default) for reading, json for prod (one object a line)."""

import logging
import sys

import structlog

from catix.settings import settings


def setup() -> None:
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if settings.log_format == "json":
        render = [structlog.processors.format_exc_info, structlog.processors.JSONRenderer(ensure_ascii=False)]
    else:
        render = [structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())]
    structlog.configure(
        processors=[*shared, structlog.stdlib.PositionalArgumentsFormatter(), structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler()  # stderr, as basicConfig did
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *render],
        )
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
