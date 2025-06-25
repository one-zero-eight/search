from functools import lru_cache

from pymongo import MongoClient

from src.config import settings


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    """
    Return a cached MongoClient instance.
    """
    return MongoClient(settings.ml_service.mongo_url.get_secret_value())


@lru_cache(maxsize=1)
def get_db():
    """
    Return a cached reference to the MongoDB database.
    """
    return get_mongo_client().get_default_database()


def get_all_documents(collection_name: str):
    """
    Fetch all documents from a MongoDB collection.
    """
    db = get_db()
    return list(db[collection_name].find())


def get_document_by_id(collection_name: str, doc_id):
    """
    Fetch a document by its _id.
    """
    db = get_db()
    return db[collection_name].find_one({"_id": doc_id})
