import asyncio
import os
from dotenv import load_dotenv
from prisma import Prisma

async def test_connection():
    load_dotenv()
    prisma = Prisma()
    db_url = os.getenv('DATABASE_URL', 'Non définie')
    print(f"DATABASE_URL chargée : {db_url[:20]}... (longueur: {len(db_url)})")
    
    try:
        print("Tentative de connexion Prisma...")
        await prisma.connect()
        print("Succès de la connexion Prisma !")
        await prisma.disconnect()
        print("Déconnexion réussie.")
    except Exception as e:
        print(f"Échec de la connexion Prisma: {e}")
        # Afficher plus de détails si possible
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"Cause : {e.__cause__}")
        if hasattr(e, '__context__') and e.__context__:
            print(f"Contexte : {e.__context__}")

if __name__ == "__main__":
    asyncio.run(test_connection()) 