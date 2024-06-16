from src.api.auth.routes import router as router_auth

routers = [router_auth]

__all__ = ["routers", *routers]
