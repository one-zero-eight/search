import httpx

from src.config import settings


def get_ml_service_client() -> httpx.AsyncClient:
    """
    Creates async connection with the ml service.
    """
    return httpx.AsyncClient(
        base_url=settings.ml_service.api_url,
        headers={"X-API-KEY": settings.ml_service.api_key.get_secret_value()},
    )
