from src.api.search.routes import router as search_router

routers = [
    search_router,
]

__all__ = ["routers"]
