from fastapi import FastAPI

from src.api.docs import generate_unique_operation_id
from src.ml_service import docs
from src.ml_service.lifespan import lifespan
from src.modules.ml.schemas import ChatResult, ChatTask, SearchResult, SearchTask

# App definition
app = FastAPI(
    title=docs.TITLE,
    version=docs.VERSION,
    contact=docs.CONTACT_INFO,
    license_info=docs.LICENSE_INFO,
    servers=[],
    swagger_ui_parameters={
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "filter": True,
    },
    root_path_in_servers=False,
    generate_unique_id_function=generate_unique_operation_id,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    redirect_slashes=False,
)

# Highly likely will be removed in the future. All responses will be manually rewritten.
BASIC_RESPONSES = {
    200: {"description": "Success"},
    403: {"description": "Invalid API key"},  # allow only backend to communicate with it
}


@app.get("/search", responses=BASIC_RESPONSES)
async def search_info(task: SearchTask) -> SearchResult:
    ...


# Update info in vector db
# @app.put("/search", responses=BASIC_RESPONSES)
# async def update_search_db(task: UpdateTask) -> UpdateResult:...

# Add info in vector db
# @app.post("/search", responses=BASIC_RESPONSES)
# async def update_search_db(task: AddTask) -> AddResult:...


@app.get("/chat", responses=BASIC_RESPONSES)
async def ask_llm(task: ChatTask) -> ChatResult:
    ...


# TODO: add swagger docs

# # Redirect root to docs
# @app.get("/", tags=["Root"], include_in_schema=False)
# async def redirect_to_docs(request: Request):
#     return RedirectResponse(url=request.url_for("swagger_ui_html"))
#
#
# @app.get("/docs", tags=["System"], include_in_schema=False)
# async def swagger_ui_html(request: Request):
#     from fastapi.openapi.docs import get_swagger_ui_html
#
#     root_path = request.scope.get("root_path", "").rstrip("/")
#     openapi_url = root_path + app.openapi_url
#
#     return get_swagger_ui_html(
#         openapi_url=openapi_url,
#         title=app.title + " - Swagger UI",
#         swagger_js_url="https://api.innohassle.ru/swagger/swagger-ui-bundle.js",
#         swagger_css_url="https://api.innohassle.ru/swagger/swagger-ui.css",
#         swagger_favicon_url="https://api.innohassle.ru/swagger/favicon.png",
#         swagger_ui_parameters={"tryItOutEnabled": True, "persistAuthorization": True, "filter": True},
#     )
