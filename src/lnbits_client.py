import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
import aiohttp

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LNBitsClientError(Exception):
    """Exception personnalisée pour les erreurs LNBits"""
    pass

class LNBitsClient:
    """
    Client pour interagir avec l'API LNbits.
    """
    def __init__(self, endpoint: str, api_key: str):
        """
        Initialise le client LNbits.

        Args:
            endpoint: L'URL de base de l'instance LNbits
            api_key: La clé API pour l'authentification
        """
        if not endpoint or not api_key:
            raise ValueError("L'endpoint LNbits et la clé API sont requis.")

        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-Api-Key': api_key,
            'Content-type': 'application/json'
        }
        self._client = None

    async def __aenter__(self):
        """Support du context manager asynchrone"""
        await self.ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fermeture du client lors de la sortie du context"""
        await self.close()

    async def ensure_connected(self):
        """S'assure que le client est connecté"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint,
                headers=self.headers,
                timeout=30.0
            )

    async def close(self):
        """Ferme le client HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _make_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Effectue une requête HTTP vers l'API LNBits"""
        if not self._client:
            await self.ensure_connected()

        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
            raise LNBitsClientError(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Erreur de requête: {str(e)}")
            raise LNBitsClientError(f"Erreur de requête: {str(e)}")

    async def get_local_node_info(self) -> Dict[str, Any]:
        """Récupère les informations du nœud local"""
        return await self._make_request("GET", "/api/v1/node/info")

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un canal"""
        return await self._make_request("GET", f"/api/v1/channel/{channel_id}")

    async def update_channel_policy(self, channel_id: str, base_fee: int, fee_rate: float) -> Dict[str, Any]:
        """Met à jour la politique d'un canal"""
        data = {
            'base_fee_msat': base_fee,
            'fee_rate': fee_rate
        }
        return await self._make_request("PUT", f"/api/v1/channel/{channel_id}/policy", json=data)

    async def create_invoice(self, amount: int, memo: str = "") -> Dict[str, Any]:
        """Crée une facture Lightning"""
        data = {
            'amount': amount,
            'memo': memo
        }
        return await self._make_request("POST", "/api/v1/payments", json=data)

    async def pay_invoice(self, bolt11: str) -> Dict[str, Any]:
        """Paye une facture Lightning"""
        data = {
            'bolt11': bolt11
        }
        return await self._make_request("POST", "/api/v1/payments", json=data)

    async def get_transactions(self) -> Dict[str, Any]:
        """Récupère l'historique des transactions"""
        return await self._make_request("GET", "/api/v1/payments")

    async def _get_cached_response(self, query: str) -> Optional[str]:
        """Récupère une réponse en cache si disponible."""
        try:
            cache_key = f"rag:response:{hash(query)}"
            cached_data = await self._make_request("GET", f"/api/v1/cache/{cache_key}")
            
            if cached_data:
                data = json.loads(cached_data)
                if datetime.fromisoformat(data["expires_at"]) > datetime.now():
                    return data["response"]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {e}")
        return None

    async def _cache_response(self, query: str, response: str):
        """Met en cache une réponse."""
        try:
            cache_key = f"rag:response:{hash(query)}"
            expires_at = datetime.now() + timedelta(hours=1)
            
            data = {
                "response": response,
                "expires_at": expires_at.isoformat(),
                "cached_at": datetime.now().isoformat()
            }
            
            await self._make_request(
                "POST",
                f"/api/v1/cache/{cache_key}",
                json=data
            )
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {e}")

    async def handle_lnbits_response(self, response: aiohttp.ClientResponse) -> Dict:
        """Gère la réponse de l'API LNBits"""
        if response.status_code == 204:  # No Content
            return {}
        if response.status_code != 200:
            error_msg = response.text
            raise LNBitsClientError(f"Erreur API LNBits ({response.status_code}): {error_msg}")
        return response.json()

    async def get_wallet_info(self) -> Dict:
        """Récupère les informations du wallet LNBits"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/api/v1/wallet",
                    headers={"X-Api-Key": self.headers["X-Api-Key"]}
                ) as response:
                    return await self.handle_lnbits_response(response)
        except LNBitsClientError as e:
            logger.error(f"Erreur lors de la récupération des informations du wallet: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération des informations du wallet: {str(e)}")
            raise LNBitsClientError(f"Erreur inattendue: {str(e)}") 