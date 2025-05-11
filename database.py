from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from config import MONGO_URL

load_dotenv()

# Utilisation directe de MONGO_URL depuis config.py
MONGODB_URI = MONGO_URL

# Client asynchrone pour les opérations asynchrones
async_client = AsyncIOMotorClient(MONGODB_URI)
async_db = async_client.dazlng

# Client synchrone pour les opérations synchrones si nécessaire
sync_client = MongoClient(MONGODB_URI)
sync_db = sync_client.dazlng

async def get_database():
    """Retourne l'instance de la base de données asynchrone"""
    return async_db

def get_sync_database():
    """Retourne l'instance de la base de données synchrone"""
    return sync_db

async def close_mongo_connection():
    """Ferme les connexions MongoDB"""
    async_client.close()
    sync_client.close() 