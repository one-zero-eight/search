from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.cors import CORSMiddleware

import src.api.logging_  # noqa: F401
from src.api import docs
from src.api.docs import generate_unique_operation_id
from src.api.lifespan import lifespan
from src.api.routers import routers
from src.config import settings

# App definition
app = FastAPI(
    title=docs.TITLE,
    summary=docs.SUMMARY,
    description=docs.DESCRIPTION,
    version=docs.VERSION,
    contact=docs.CONTACT_INFO,
    license_info=docs.LICENSE_INFO,
    servers=[
        {"url": settings.api_settings.app_root_path, "description": "Current"},
        {
            "url": "https://api.innohassle.ru/search/v0",
            "description": "Production environment",
        },
        {
            "url": "https://api.innohassle.ru/search/staging-v0",
            "description": "Staging environment",
        },
    ],
    swagger_ui_parameters={
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "filter": True,
    },
    root_path=settings.api_settings.app_root_path,
    root_path_in_servers=False,
    generate_unique_id_function=generate_unique_operation_id,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.api_settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Redirect root to docs
@app.get("/", tags=["Root"], include_in_schema=False)
async def redirect_to_docs(request: Request):
    return RedirectResponse(url=request.url_for("swagger_ui_html"))


@app.get("/docs", tags=["System"], include_in_schema=False)
async def swagger_ui_html(request: Request):
    from fastapi.openapi.docs import get_swagger_ui_html

    root_path = request.scope.get("root_path", "").rstrip("/")
    openapi_url = root_path + app.openapi_url

    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="https://api.innohassle.ru/swagger/swagger-ui-bundle.js",
        swagger_css_url="https://api.innohassle.ru/swagger/swagger-ui.css",
        swagger_favicon_url="https://api.innohassle.ru/swagger/favicon.png",
        swagger_ui_parameters={"tryItOutEnabled": True, "persistAuthorization": True, "filter": True},
    )


for _router in routers:
    app.include_router(_router)
