import sys
import os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest
import logging
from fastapi.testclient import TestClient
from server import app

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_health():
    """Test de l'endpoint health."""
    try:
        client = TestClient(app=app)
        response = client.get("/health", timeout=5.0)
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
        assert response.json()["status"] == "healthy", "Statut inattendu"
        
        logger.info(f"✅ Test de santé réussi (status: {response.status_code})")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de santé: {str(e)}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_health()) 