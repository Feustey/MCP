import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def check_connection():
    load_dotenv('.env.production')
    
    uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('MONGODB_DB_NAME')
    
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    
    try:
        # Vérifier les collections
        collections = await db.list_collection_names()
        print(f"Collections trouvées : {collections}")
        
        # Compter les documents dans nodes
        nodes_count = await db.nodes.count_documents({})
        print(f"Nombre de documents dans nodes : {nodes_count}")
        
        print("✅ Connexion à la base de données réussie")
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_connection())
