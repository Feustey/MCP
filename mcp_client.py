import os
import aiohttp
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    """Client pour communiquer avec le service MCP."""
    
    def __init__(self, jwt_token: str):
        """
        Initialise le client MCP.
        :param jwt_token: Le token JWT fourni par Dazlng pour l'authentification
        """
        self.base_url = os.getenv("MCP_URL", "http://localhost:8000")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jwt_token}"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Effectue une requête HTTP vers MCP."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, json=data, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()
    
    async def query_rag(self, query_text: str) -> Dict[str, Any]:
        """Envoie une requête RAG à MCP."""
        return await self._make_request("POST", "/query", {"query_text": query_text})
    
    async def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du système MCP."""
        return await self._make_request("GET", "/stats")
    
    async def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère l'historique des requêtes récentes."""
        return await self._make_request("GET", f"/recent-queries?limit={limit}")
    
    async def ingest_documents(self, directory: str) -> Dict[str, Any]:
        """Ingère des documents dans le système MCP."""
        return await self._make_request("POST", "/ingest", {"directory": directory}) 