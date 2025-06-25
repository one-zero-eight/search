# InNoHassle Search

[![GitHub Actions pre-commit](https://img.shields.io/github/actions/workflow/status/one-zero-eight/search/pre-commit.yaml?label=pre-commit)](https://github.com/one-zero-eight/search/actions)

## Table of contents

Did you know that GitHub supports table of
contents [by default](https://github.blog/changelog/2021-04-13-table-of-contents-support-in-markdown-files/) 🤔

## About

This is an API for the search service in the InNoHassle ecosystem. The search should be carried out on services relevant to Innopolis University students ([moodle](https://moodle.innopolis.university/), [EduWiki](https://eduwiki.innopolis.university/index.php/AcademicCalendar), [Campus Life](http://campuslife.innopolis.ru/), etc.). The search expects to use AI to accept free-form queries from users in addition to just service keywords.

### Technologies

- [Python 3.11](https://www.python.org/downloads/) & [Poetry](https://python-poetry.org/docs/)
- [FastAPI](https://fastapi.tiangolo.com/) & [Pydantic](https://docs.pydantic.dev/latest/)
- Database and ORM: [MongoDB](https://www.mongodb.com/), [Beanie](https://beanie-odm.dev/)
- Formatting and linting: [Ruff](https://docs.astral.sh/ruff/), [pre-commit](https://pre-commit.com/)
- Deployment: [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/),
  [GitHub Actions](https://github.com/features/actions)

## Run with Docker

1. Set up project settings file (check [settings.schema.yaml](../InNoHassle-Search/settings.schema.yaml) for more info).
   ```bash
   cp settings.example.yaml settings.yaml
   ```
   Edit `settings.yaml` according to your needs.
2. Set up database settings for [docker-compose](https://docs.docker.com/compose/) container
      in `.env` file:х
      ```bash
      cp .env.example .env
      ```

1. Start all services:
   ```bash
   docker compose up
   ```

Now you can find API docs on http://localhost:8004/docs. Good job!


## Development

### Run locally [API]

1. Install [Python 3.11](https://www.python.org/downloads/)
2. Install [Poetry](https://python-poetry.org/docs/)
3. Install project dependencies with [Poetry](https://python-poetry.org/docs/cli/#options-2).
   ```bash
   poetry install
   ```
4. Set up [pre-commit](https://pre-commit.com/) hooks:

   ```bash
   poetry run pre-commit install --install-hooks -t pre-commit -t commit-msg
   ```
5. Check that your `settings.yaml` looks like:
   ```bash
   $schema: "./settings.schema.yaml"
   api_settings:
      db_url: "mongodb://mongoadmin:secret@localhost:27017/db?authSource=admin"
   minio:
      access_key: "minioadmin"
      secret_key: "password"
6. Set up a [MongoDB](https://www.mongodb.com/) and [Minio](https://min.io/) instances.

    - Set up database settings for [docker-compose](https://docs.docker.com/compose/) container
      in `.env` file:х
      ```bash
      cp .env.example .env
      ```
    - Run the database instance:
      ```bash
      docker compose up -d db minio
      ```
    - Make sure to set up the actual database connection in `settings.yaml`.
7. Run the ASGI server
   ```bash
   poetry run python -m src.api
   ```
   Check API docs on http://127.0.0.1:8001/docs

8. Run ml client
   ```bash
   poetry run python -m src.ml_service
   ```
9. Run Infinity engine:
   ```bash
   poetry run infinity_emb v2 --model-id jinaai/jina-embeddings-v3 --model-id jinaai/jina-reranker-v2-base-multilingual
   ```
   (Or specify url of deployed Infinity in settings.yaml)
**Set up PyCharm integrations**

1. Ruff ([plugin](https://plugins.jetbrains.com/plugin/20574-ruff)).
   It will lint and format your code.
   Make sure to enable `Use ruff format` option in plugin settings.
2. Pydantic ([plugin](https://plugins.jetbrains.com/plugin/12861-pydantic)).
   It will fix PyCharm issues with
   type-hinting.
3. Conventional commits ([plugin](https://plugins.jetbrains.com/plugin/13389-conventional-commit)).
   It will help you
   to write [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/).


### Authentication

We use our own IAM service for
authentication - [InNoHassle Accounts](https://github.com/one-zero-eight/InNoHassle-Accounts).
To authenticate the user, you need to pass the `Authorization` header with the `Bearer: <jwt_token>`.
How to get token:

1. First of all, go to [innohassle.ru](https://innohassle.ru) and log in if you are not logged in (or register). That
   will add cookie with
   account secret needed for the next step.
2. Go to [Accounts](https://api.innohassle.ru/accounts/v0/docs#/Tokens/tokens_generate_my_token) API and execute the
   the method `GET /tokens/generate-my-token`, copy the token from the response.
3. Go to the Swagger of API you want to authenticate and click on the `Authorize` button in the top right corner, paste
   the token
   in the `Value` field and click `Authorize`. Now you can use protected endpoints from the Swagger.

### Deployment

We use Docker with Docker Compose plugin to run the website on servers.

1. Copy the file with environment variables: `cp .env.example .env`
2. Change environment variables in the `.env` file
3. Copy the file with settings: `cp settings.example.yaml settings.yaml`
4. Change settings in the `settings.yaml` file according to your needs
   (check [settings.schema.yaml](../InNoHassle-Search/settings.schema.yaml) for more info)
5. Install Docker with Docker Compose
6. Build a Docker image: `docker compose build --pull`
7. Run the container: `docker compose up --detach`
8. Check the logs: `docker compose logs -f`

## Contributing

We are open to contributions of any kind.
You can help us with code, bugs, design, documentation, media, new ideas, etc.
If you are interested in contributing, please read
our [contribution guide](https://github.com/one-zero-eight/.github/blob/main/CONTRIBUTING.md).
