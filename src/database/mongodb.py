from typing import Any
from pymongo import MongoClient
from src.config import get_settings

def get_mongodb_client() -> MongoClient:
    """Retourne une instance du client MongoDB."""
    settings = get_settings()
    client = MongoClient(settings.database_url)
    return client 