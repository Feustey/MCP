import asyncio
import httpx
from dotenv import load_dotenv
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

async def test_connection():
    url = os.getenv("LNBITS_URL", "http://192.168.0.45:5000")
    admin_key = os.getenv("LNBITS_ADMIN_KEY", "fddac5fb8bf64eec944c89255b98dac4")
    
    headers = {
        "X-Api-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    logger.info(f"Test de connexion à {url}")
    logger.info(f"Headers: {headers}")
    
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            # Test avec un endpoint admin
            response = await client.get(f"{url}/api/v1/wallet", headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Réponse reçue : {data}")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Erreur de requête: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection()) 