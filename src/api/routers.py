from src.modules.search.routes import router as search_router
from src.modules.preview.routes import router as preview_router
from src.modules.telegram.routes import router as telegram_router

routers = [
    search_router,
    preview_router,
    telegram_router,
]

__all__ = ["routers"]
