import os

from src.config import settings as general_settings


class Settings:
    @property
    def mongo_connection_uri(self) -> str:
        return general_settings.api_settings.db_url.get_secret_value()

    LANCEDB_URI = os.getenv("LANCEDB_URI", "./lance_data")
    LANCEDB_EMBEDDING_DIM = int(os.getenv("LANCEDB_EMBEDDING_DIM", "384"))
    RESOURCES = os.getenv("RESOURCES", "CampusLifeEntry,EduWikiEntry,HotelEntry").split(",")


settings = Settings()
