import os


class Settings:
    MONGO_URI = os.getenv("MONGO_URI", None)
    MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME", None)
    MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD", None)
    MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT = os.getenv("MONGO_PORT", "27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "db")

    @property
    def mongo_connection_uri(self) -> str:
        if self.MONGO_URI:
            return self.MONGO_URI
        if self.MONGO_USER and self.MONGO_PASS:
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASS}@{self.MONGO_HOST}:{self.MONGO_PORT}/"
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/"

    LANCEDB_URI = os.getenv("LANCEDB_URI", "./lance_data")
    LANCEDB_EMBEDDING_DIM = int(os.getenv("LANCEDB_EMBEDDING_DIM", "384"))
    BI_ENCODER_MODEL = os.getenv("BI_ENCODER_MODEL", "all-MiniLM-L6-v2")
    DEVICE = os.getenv("DEVICE", "cpu")
    RESOURCES = os.getenv("RESOURCES", "CampusLifeEntry,EduWikiEntry,HotelEntry").split(",")


settings = Settings()
