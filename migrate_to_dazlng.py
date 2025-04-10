import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_data():
    # Connexion MongoDB
    mongo_url = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
    client = AsyncIOMotorClient(mongo_url)
    
    # Bases de données source et destination
    mcp_db = client.mcp
    dazlng_db = client.dazlng
    
    collections = ['documents', 'recommendations', 'nodes', 'system_stats', 'history']
    
    for collection_name in collections:
        try:
            # Comptage des documents dans la collection source
            count = await mcp_db[collection_name].count_documents({})
            logger.info(f"Collection {collection_name}: {count} documents à migrer")
            
            if count > 0:
                # Récupération des documents
                documents = await mcp_db[collection_name].find({}).to_list(length=None)
                
                # Insertion dans la nouvelle base
                result = await dazlng_db[collection_name].insert_many(documents)
                
                logger.info(f"✅ {len(result.inserted_ids)} documents migrés vers dazlng.{collection_name}")
                
                # Suppression des documents de l'ancienne base
                await mcp_db[collection_name].delete_many({})
                logger.info(f"🗑️ Documents supprimés de mcp.{collection_name}")
            else:
                logger.info(f"ℹ️ Aucun document à migrer pour {collection_name}")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la migration de {collection_name}: {str(e)}")

async def main():
    try:
        logger.info("Début de la migration des données de mcp vers dazlng...")
        await migrate_data()
        logger.info("Migration terminée avec succès!")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 