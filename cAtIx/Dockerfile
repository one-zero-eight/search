# One image for every cAtIx process: the command decides which one runs (see docker-compose.prod.yml).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first: this layer is rebuilt only when pyproject.toml or uv.lock change.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY db ./db
COPY courses.toml ./
RUN uv sync --frozen --no-dev
# The wiki of documents (OKF bundle): `catix-wiki index` puts it in the database (the `wiki` service of docker-compose.prod.yml).
# Last of the app layers: it changes most often.
COPY wiki ./wiki

# The Max API is served with a certificate of the Russian Ministry of Digital Development (see settings.max_root_ca).
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt -o /app/russian_root_ca.crt

ENV PATH="/app/.venv/bin:$PATH" MAX_ROOT_CA=/app/russian_root_ca.crt
# The Telegram session of the userbot and other state live in a volume mounted at /app/data.
RUN useradd --create-home app && mkdir -p /app/data && chown app /app/data
USER app

CMD ["catix-tgbot"]
