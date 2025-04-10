import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def test_connection():
    # Définir l'URL de connexion
    mongo_url = "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng"
    
    try:
        # Tenter la connexion
        client = AsyncIOMotorClient(mongo_url)
        
        # Vérifier la connexion en exécutant une commande simple
        await client.admin.command('ping')
        print("✅ Connexion à MongoDB réussie !")
        
        # Lister les bases de données
        databases = await client.list_database_names()
        print("\nBases de données disponibles :")
        for db in databases:
            print(f"- {db}")
            
    except Exception as e:
        print(f"❌ Erreur de connexion : {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection()) 