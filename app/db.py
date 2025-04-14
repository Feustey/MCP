# app/db.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from fastapi import Request, Depends
from motor.core import AgnosticDatabase, AgnosticClient, AgnosticCollection
from typing import List, Dict, Any

# Charger les variables d'environnement depuis .env.local
load_dotenv('.env.local')

# Configuration MongoDB
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "daznode")

# Configuration MongoDB de production
PROD_MONGO_URL = os.getenv("PROD_MONGO_URL", "mongodb://localhost:27017")
PROD_MONGO_DB = os.getenv("PROD_MONGO_DB", "daznode_prod")

# Configuration LNbits
LNBITS_INKEY = os.getenv("LNBITS_INKEY")
if not LNBITS_INKEY:
    raise ValueError("La variable d'environnement LNBITS_INKEY n'est pas définie dans le fichier .env")

# Configuration des en-têtes pour l'API LNbits
LNBITS_HEADERS = {
    "X-Api-Key": LNBITS_INKEY,
    "Content-type": "application/json"
}

# Crée une instance client Motor qui sera partagée
# La connexion est poolée et gérée automatiquement par Motor
client: AgnosticClient = AsyncIOMotorClient(MONGO_URL)

# Accède à la base de données spécifique
db: AgnosticDatabase = client[MONGO_DB]

# Crée une instance client Motor pour la base de données de production
prod_client: AgnosticClient = AsyncIOMotorClient(PROD_MONGO_URL)
prod_db: AgnosticDatabase = prod_client[PROD_MONGO_DB]

# Fonction dépendance pour injecter la base de données dans les routes
async def get_database() -> AgnosticDatabase:
    """FastAPI dependency to get the database instance."""
    return db

# Optionnel : fonction dépendance pour injecter une collection spécifique
# Cela peut être utile si vous travaillez toujours avec la même collection
def get_node_collection() -> AgnosticCollection:
    """FastAPI dependency to get the 'nodes' collection."""
    return db.nodes

# Fonction pour obtenir les en-têtes LNbits
def get_lnbits_headers():
    return LNBITS_HEADERS

# Fonction pour obtenir la base de données de production
async def get_prod_database() -> AgnosticDatabase:
    return prod_db

# Fonction pour lister les collections dans la base de données
async def list_collections(db: AgnosticDatabase) -> List[str]:
    return await db.list_collection_names()

# Fonction pour compter les documents dans une collection
async def count_documents(collection: AgnosticCollection) -> int:
    return await collection.count_documents({})

# Fonction pour obtenir un échantillon de documents d'une collection
async def get_sample_documents(collection: AgnosticCollection, limit: int = 5) -> List[Dict[str, Any]]:
    cursor = collection.find().limit(limit)
    return await cursor.to_list(length=limit)

# Fonction pour obtenir un résumé de la base de données
async def get_db_summary(db: AgnosticDatabase) -> Dict[str, Any]:
    collections = await list_collections(db)
    summary = {}
    
    for collection_name in collections:
        collection = db[collection_name]
        count = await count_documents(collection)
        sample = await get_sample_documents(collection)
        summary[collection_name] = {
            "count": count,
            "sample": sample
        }
    
    return summary

# Remarque : Le middleware original get_db(request: Request) n'est plus
# nécessaire si nous utilisons les dépendances FastAPI comme ci-dessus.
# L'injection via Depends() est plus explicite et idiomatique pour FastAPI.

# async def get_db(request: Request):
#    # Cette approche injecte la db dans l'état de l'application,
#    # accessible via request.app.state.db
#    # Moins courant que l'injection par dépendance.
#    return request.app.state.db 