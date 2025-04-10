import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def drop_mcp_database():
    mongo_url = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
    client = AsyncIOMotorClient(mongo_url)
    
    try:
        await client.drop_database('mcp')
        logger.info("✅ Base de données 'mcp' supprimée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression de la base 'mcp': {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(drop_mcp_database()) 