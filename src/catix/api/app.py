"""The HTTP API (`catix-api`): the paths and JSON of the InNoHassle search service, answered by cAtIx.

    GET  /search/search                    cards from the wiki          POST /ask/   the agent, a conversation by chat_id
    POST /search/search/{id}/feedback      likes of the cards           POST /act/   mock (cAtIx has no actions)
    /moodle/*                            mocks (no Moodle)
    POST /{section}/parse                incremental source updates
"""

import logging
import re

import uvicorn
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from catix.api import ask, parsers, search, stubs
from catix.settings import settings

log = logging.getLogger("catix.api")


def unique_operation_id(route: APIRoute) -> str:
    """operationId = tag + function name: clients generate their code from it."""
    operation_id = f"{route.tags[0]}_{route.name}".lower() if route.tags else route.name.lower()
    return re.sub(r"\W+", "_", operation_id)


app = FastAPI(
    title="InNoHassle Search API",
    summary="Search service for InNoHassle ecosystem.",
    description="Answers questions about Innopolis University with cAtIx: its wiki, the chats and the campus.\n\n"
    "Note: API is unstable. Endpoints and models may change in the future.",
    version="0.1.0",
    contact={"name": "one-zero-eight (Telegram)", "url": "https://t.me/one_zero_eight"},
    license_info={"name": "MIT License", "identifier": "MIT"},
    servers=[
        {"url": settings.api_root_path, "description": "Current"},
        {"url": "https://api.innohassle.ru/search/v0", "description": "Production environment"},
        {"url": "https://api.innohassle.ru/search/staging-v0", "description": "Staging environment"},
    ],
    root_path=settings.api_root_path,
    root_path_in_servers=False,
    generate_unique_id_function=unique_operation_id,
    docs_url=None,
    redoc_url=None,
    redirect_slashes=False,
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.api_cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"], include_in_schema=False)
async def redirect_to_docs(request: Request):
    return RedirectResponse(url=request.url_for("swagger_ui_html"))


@app.get("/docs", tags=["System"], include_in_schema=False)
async def swagger_ui_html(request: Request):
    root_path = request.scope.get("root_path", "").rstrip("/")
    return get_swagger_ui_html(
        openapi_url=root_path + app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="https://api.innohassle.ru/swagger/swagger-ui-bundle.js",
        swagger_css_url="https://api.innohassle.ru/swagger/swagger-ui.css",
        swagger_favicon_url="https://api.innohassle.ru/swagger/favicon.png",
        swagger_ui_parameters={"tryItOutEnabled": True, "persistAuthorization": True, "filter": True},
    )


for _router in (search.router, ask.router, stubs.moodle, parsers.router):
    app.include_router(_router)


def main() -> None:
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, forwarded_allow_ips="*")
