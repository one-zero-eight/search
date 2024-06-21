from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from __base__ import CustomDocument


class MongoDBStorage:
    """
    Storage class from SQLAlchemy adapted to Mongo with Beanie
    let it be for now I guess
    """

    client: AsyncIOMotorClient

    def __init__(self, uri: str, database: str) -> None:
        self.client = AsyncIOMotorClient(uri)
        self.database = self.client[database]

    @classmethod
    def from_url(cls, uri: str, database: str) -> "MongoDBStorage":
        return cls(uri, database)

    async def init(self) -> None:
        await init_beanie(self.database, document_models=[CustomDocument])

    async def close_connection(self):
        self.client.close()


# To initialize the storage
# storage = MongoDBStorage.from_url(settings.api_settings.db_url, "example_database")
