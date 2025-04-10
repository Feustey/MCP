import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clean_recommendations():
    mongo_url = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
    client = AsyncIOMotorClient(mongo_url)
    db = client.dazlng
    
    try:
        # Suppression des recommandations avec source "test" ou confidence_score = 0
        result = await db.recommendations.delete_many({
            "$or": [
                {"source": {"$in": ["test", "rag"]}},
                {"confidence_score": 0},
                {"content": {"$regex": "CVE-2023"}}  # Supprime les recommandations de test avec des CVE fictifs
            ]
        })
        
        logger.info(f"✅ {result.deleted_count} anciennes recommandations supprimées")
        
    except Exception as e:
        logger.error(f"❌ Erreur: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(clean_recommendations()) 