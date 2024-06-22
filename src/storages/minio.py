from minio import Minio

from src.config import settings

minio_client: Minio = Minio(
    endpoint=settings.minio.endpoint,
    access_key=settings.minio.access_key,
    secret_key=settings.minio.secret_key.get_secret_value(),
    secure=False,
)
