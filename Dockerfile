# One image for every cAtIx process: the command decides which one runs (see docker-compose.prod.yml).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

# Git is required by the pinned PyMax dependency during uv sync. Keep standard TLS trust.
# Private attachment parsing needs Java 11+ and bounded PDF rendering through Poppler.
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates libarchive13 openjdk-17-jre-headless poppler-utils \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first: this layer is rebuilt only when pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock .python-version ./
COPY vendor ./vendor
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY db ./db
COPY courses.toml ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
# Telegram and MAX account sessions and other state live in the volume mounted at /app/data.
RUN useradd --create-home app && mkdir -p /app/data && chown app /app/data
USER app

CMD ["catix-tgbot"]
