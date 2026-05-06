from src.modules.ask.routes import router as ask_router
from src.modules.moodle.routes import router as moodle_router
from src.modules.parsers.routes import router as parsers_router
from src.modules.search.routes import router as search_router

routers = [search_router, ask_router, moodle_router, parsers_router]

__all__ = ["routers"]
