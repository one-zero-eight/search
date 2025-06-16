from src.modules.campus_life.routes import router as campus_life_router
from src.modules.moodle.routes import router as moodle_router
from src.modules.search.routes import router as search_router
from src.modules.telegram.routes import router as telegram_router

routers = [search_router, telegram_router, moodle_router, campus_life_router]

__all__ = ["routers"]
