import os

from src.config import settings as general_settings


class Settings:
    MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT = os.getenv("MONGO_PORT", "27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "db")

    @property
    def mongo_connection_uri(self) -> str:
        return general_settings.api_settings.db_url.get_secret_value()

    LANCEDB_URI = os.getenv("LANCEDB_URI", "./lance_data")
    LANCEDB_EMBEDDING_DIM = int(os.getenv("LANCEDB_EMBEDDING_DIM", "384"))
    BI_ENCODER_MODEL = os.getenv("BI_ENCODER_MODEL", "all-MiniLM-L6-v2")
    DEVICE = os.getenv("DEVICE", "cpu")
    RESOURCES = os.getenv("RESOURCES", "CampusLifeEntry,EduWikiEntry,HotelEntry").split(",")


settings = Settings()
