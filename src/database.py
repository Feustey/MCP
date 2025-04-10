import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DEFAULT_DB_NAME = os.getenv("MONGODB_DB_NAME", "dazlng")

# Client asynchrone pour les opérations asynchrones
async_client = AsyncIOMotorClient(MONGODB_URI)

# Client synchrone pour les opérations synchrones si nécessaire
sync_client = MongoClient(MONGODB_URI)

async def get_database(db_name: str = DEFAULT_DB_NAME):
    """Retourne une instance de la base de données"""
    return async_client[db_name]

def get_sync_database(db_name: str = DEFAULT_DB_NAME):
    """Retourne une instance synchrone de la base de données"""
    return sync_client[db_name]

async def close_mongo_connection():
    """Ferme la connexion à MongoDB"""
    async_client.close()
    sync_client.close() 