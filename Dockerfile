# The image of every cAtIx process, in profiles: a process gets only what it uses (docker build --target <profile>).
# See docker-compose.prod.yml for which service runs which profile.
#
#   core    mcp, migrate                  Python only
#   ocr     tgbot, userbot, maxuserbot    + Tesseract (OCR of chat images)
#   api     api                           + Java and Poppler (private attachments: opendataloader, pdfplumber), libarchive (previews)
#   worker  worker                        + Java, Poppler, Tesseract, LibreOffice (the course files of Moodle)
#   docs    docs                          + everything the sources of the documents read, and Chromium
#   full    (the default target)          every profile together, for one image for everything
#
# The Python environment of a profile is built in a stage with git (the pinned PyMax dependency needs it for uv sync) and
# copied into a slim image that has no git, no uv and no build tools. The PDF readers (opendataloader-pdf, pdfplumber) and
# Playwright are dependency groups of pyproject.toml: only the profiles that read PDFs or open a browser install them.

ARG PYTHON=python:3.13-slim-bookworm

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# On the build server one of the PyPI CDN addresses (151.101.64.223) is not reachable: a connection to it hangs until the
# timeout, and DNS hands it out in turn. A short timeout and many retries make uv try the next address instead of failing.
ENV UV_HTTP_TIMEOUT=15 UV_HTTP_RETRIES=10
WORKDIR /app
# apt over HTTPS, with retries: on the build server plain HTTP from a container is throttled to ~200 kB/s and times out
# ("Unable to connect to deb.debian.org:http"), HTTPS is not (the base image has ca-certificates).
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|' /etc/apt/sources.list.d/debian.sources \
    && echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock .python-version ./
COPY vendor ./vendor

# Dependencies first: these layers are rebuilt only when pyproject.toml or uv.lock change; the project after them.
FROM build AS venv-core
RUN uv sync --frozen --no-dev --no-default-groups --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-default-groups

FROM build AS venv-pdf
RUN uv sync --frozen --no-dev --no-default-groups --group pdf --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-default-groups --group pdf

FROM build AS venv-docs
RUN uv sync --frozen --no-dev --no-default-groups --group pdf --group browser --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-default-groups --group pdf --group browser


# What every process has: the data of the repository it reads (db/schema.sql is found from src/, which the editable install of the
# project points to: the final stages copy src/ last, so a code change rebuilds only that layer), and a user of its own. Telegram and MAX account sessions and
# other state live in the volume mounted at /app/data.
FROM ${PYTHON} AS runtime
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|' /etc/apt/sources.list.d/debian.sources \
    && echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries
COPY db ./db
COPY courses.toml sites.yaml ./
RUN useradd --create-home app && mkdir -p /app/data && chown app /app/data

# The OS packages of a profile are separate stages, so that a profile lists only what it needs.
FROM runtime AS os-ocr
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

FROM runtime AS os-pdf
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless poppler-utils \
    && rm -rf /var/lib/apt/lists/*


FROM runtime AS core
COPY --from=venv-core /app/.venv ./.venv
COPY src ./src
USER app
CMD ["catix-mcp"]

FROM os-ocr AS ocr
COPY --from=venv-core /app/.venv ./.venv
COPY src ./src
USER app
CMD ["catix-tgbot"]

FROM os-pdf AS api
RUN apt-get update && apt-get install -y --no-install-recommends libarchive13 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=venv-pdf /app/.venv ./.venv
COPY src ./src
USER app
CMD ["catix-api"]

FROM os-pdf AS worker
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
    libreoffice-writer-nogui libreoffice-impress-nogui libreoffice-calc-nogui \
    && rm -rf /var/lib/apt/lists/*
COPY --from=venv-pdf /app/.venv ./.venv
COPY src ./src
USER app
CMD ["catix-worker"]

FROM os-pdf AS docs
RUN apt-get update && apt-get install -y --no-install-recommends libarchive13 tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
    chromium libreoffice-writer-nogui libreoffice-impress-nogui libreoffice-calc-nogui \
    && rm -rf /var/lib/apt/lists/*
COPY --from=venv-docs /app/.venv ./.venv
COPY src ./src
USER app
CMD ["catix-docs", "run", "--loop"]

# Everything in one image (the default target): the processes of every profile, the command decides which one runs.
FROM docs AS full
CMD ["catix-tgbot"]
