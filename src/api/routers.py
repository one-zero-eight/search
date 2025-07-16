from src.modules.act.routes import router as act_router
from src.modules.ask.routes import router as ask_router
from src.modules.moodle.routes import router as moodle_router
from src.modules.parsers.routes import router as parsers_router
from src.modules.search.routes import router as search_router
from src.modules.telegram.routes import router as telegram_router

routers = [search_router, ask_router, act_router, telegram_router, moodle_router, parsers_router]

__all__ = ["routers"]
