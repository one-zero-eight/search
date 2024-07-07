from src.modules.compute.routes import router as compute_router
from src.modules.moodle.routes import router as moodle_router
from src.modules.search.routes import router as search_router
from src.modules.telegram.routes import router as telegram_router

routers = [search_router, telegram_router, moodle_router, compute_router]

__all__ = ["routers"]
