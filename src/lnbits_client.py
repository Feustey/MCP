import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LNBitsClientError(Exception):
    """Exception personnalisée pour les erreurs du client LNbits."""
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
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(
            base_url=self.endpoint,
            headers=self.headers,
            timeout=30.0
        )

    async def close(self):
        """Ferme le client HTTP sous-jacent."""
        if hasattr(self, 'client'):
            await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Méthode helper pour faire des requêtes API."""
        try:
            response = await self.client.request(method, path, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:  # No Content
                return None
                
            return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"Timeout lors de la connexion à LNbits: {e}")
            raise LNBitsClientError(f"Timeout: {e}")
        except httpx.RequestError as e:
            logger.error(f"Erreur de connexion à LNbits: {e}")
            raise LNBitsClientError(f"Erreur de connexion: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur API LNbits ({e.response.status_code}): {e.response.text}")
            raise LNBitsClientError(f"Erreur API: {e.response.text}")
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")
            raise LNBitsClientError(f"Erreur inattendue: {e}")

    async def get_local_node_info(self) -> Dict[str, Any]:
        """Récupère les informations du nœud local."""
        try:
            channels = await self._request("GET", "/api/v1/channels")
            current_peers = set()
            
            if isinstance(channels, list):
                for chan in channels:
                    if isinstance(chan, dict):
                        peer_key = chan.get('remote_pubkey') or chan.get('peer_id')
                        if peer_key:
                            current_peers.add(peer_key)
            
            return {
                'pubkey': None,  # Non disponible via l'API documentée
                'current_peers': current_peers
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations du nœud: {e}")
            raise

    async def create_invoice(self, amount: int, memo: str = "") -> Dict[str, Any]:
        """Crée une facture Lightning."""
        try:
            return await self._request(
                "POST",
                "/api/v1/payments",
                json={
                    "out": False,
                    "amount": amount,
                    "memo": memo
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création de la facture: {e}")
            raise

    async def pay_invoice(self, bolt11: str) -> Dict[str, Any]:
        """Paye une facture Lightning."""
        try:
            return await self._request(
                "POST",
                "/api/v1/payments",
                json={
                    "out": True,
                    "bolt11": bolt11
                }
            )
        except Exception as e:
            logger.error(f"Erreur lors du paiement de la facture: {e}")
            raise

    async def get_transactions(self) -> List[Dict[str, Any]]:
        """Récupère l'historique des transactions."""
        try:
            return await self._request("GET", "/api/v1/payments")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transactions: {e}")
            raise

    async def _get_cached_response(self, query: str) -> Optional[str]:
        """Récupère une réponse en cache si disponible."""
        try:
            cache_key = f"rag:response:{hash(query)}"
            cached_data = await self._request("GET", f"/api/v1/cache/{cache_key}")
            
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
            
            await self._request(
                "POST",
                f"/api/v1/cache/{cache_key}",
                json=data
            )
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {e}")

    async def ensure_connected(self):
        """S'assure que les connexions sont établies."""
        try:
            await self._request("GET", "/api/v1/health")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la connexion: {e}")
            raise

    async def close_connections(self):
        """Ferme toutes les connexions."""
        await self.close() 