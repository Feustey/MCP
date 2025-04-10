import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime
import json

async def show_recommendations():
    mongo_url = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
    client = AsyncIOMotorClient(mongo_url)
    db = client.dazlng
    
    try:
        # Récupération des dernières recommandations
        cursor = db.recommendations.find().sort("created_at", -1).limit(5)
        recommendations = await cursor.to_list(length=5)
        
        print("\n🔍 Dernières recommandations générées :\n")
        for rec in recommendations:
            print(f"📊 Recommandation du {rec['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📝 Contenu: {rec['content']}")
            print(f"💡 Contexte: {json.dumps(rec['context'], indent=2)}")
            print(f"🎯 Score de confiance: {rec['confidence_score']}")
            print(f"🏷️ Source: {rec['source']}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(show_recommendations()) 