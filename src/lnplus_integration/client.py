import httpx
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
import logging
from functools import lru_cache
from .models import LightningSwap, SwapCreationRequest, NodeMetrics, Rating
from .config import get_lnplus_settings
from .exceptions import (
    LNPlusError,
    LNPlusAPIError,
    LNPlusAuthError,
    LNPlusValidationError,
    LNPlusRateLimitError,
    LNPlusNetworkError
)
from .lnbits_client import LnbitsClient
from .metrics import metrics
from .circuit_breaker import circuit_breaker
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

class LNPlusClient:
    def __init__(self, lnbits_admin_key: str = None):
        self.settings = get_lnplus_settings()
        self._client = None
        self._auth_token = None
        self._token_expiry = None
        self._lnbits = LnbitsClient(admin_key=lnbits_admin_key)
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)

    async def ensure_connected(self):
        """Assure que le client est connecté et authentifié"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.settings.base_url,
                timeout=self.settings.timeout
            )
            await self._authenticate()

    async def _get_message_to_sign(self) -> Tuple[str, datetime]:
        """Récupère un message à signer depuis l'API"""
        try:
            response = await self._make_request(
                "GET",
                "/get_message",
                max_retries=1  # Pas de retry pour l'authentification
            )
            return response["message"], datetime.fromisoformat(response["expires_at"])
        except LNPlusError as e:
            logger.error(f"Erreur lors de la récupération du message à signer: {str(e)}")
            raise

    async def _verify_signature(self, message: str, signature: str) -> Dict[str, Any]:
        """Vérifie la signature auprès de l'API"""
        try:
            response = await self._make_request(
                "POST",
                "/verify_signature",
                data={"message": message, "signature": signature},
                max_retries=1  # Pas de retry pour l'authentification
            )
            return response
        except LNPlusError as e:
            logger.error(f"Erreur lors de la vérification de la signature: {str(e)}")
            raise

    async def _authenticate(self):
        """Authentifie le client auprès de l'API LN+"""
        try:
            # Obtenir le message à signer
            message, expires_at = await self._get_message_to_sign()
            
            # Signer le message via Lnbits
            signature = await self._lnbits.sign_message(message)
            
            # Vérifier la signature
            auth_data = await self._verify_signature(message, signature)
            if not auth_data.get("node_found"):
                raise LNPlusAuthError("Nœud non trouvé ou non autorisé")
            
            # Stocker les informations d'authentification
            self._auth_token = auth_data.get("pubkey")
            self._token_expiry = expires_at
            
        except Exception as e:
            logger.error(f"Erreur d'authentification LN+: {str(e)}")
            raise LNPlusAuthError("Échec de l'authentification")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Any:
        """Effectue une requête avec gestion des erreurs et métriques"""
        start_time = datetime.now()
        
        try:
            # Vérifier le rate limiting
            if await rate_limiter.should_throttle():
                raise LNPlusRateLimitError("Limite de taux dépassée")
            
            # Utiliser le circuit breaker
            response = await circuit_breaker.execute(
                self._client.request,
                method,
                endpoint,
                json=data,
                params=params,
                headers={"Authorization": f"Bearer {self._auth_token}"} if self._auth_token else {}
            )
            
            # Enregistrer les métriques
            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_request(method, endpoint, str(response.status_code), duration)
            
            if response.status_code >= 400:
                if response.status_code == 401:
                    raise LNPlusAuthError("Non authentifié")
                elif response.status_code == 403:
                    raise LNPlusAuthError("Accès refusé")
                elif response.status_code == 429:
                    raise LNPlusRateLimitError("Trop de requêtes")
                else:
                    raise LNPlusAPIError(f"Erreur API: {response.status_code}")
                    
            return response.json()
            
        except httpx.RequestError as e:
            metrics.record_request(method, endpoint, "network_error", 
                                 (datetime.now() - start_time).total_seconds())
            raise LNPlusNetworkError(f"Erreur réseau: {str(e)}")

    @lru_cache(maxsize=100)
    async def get_node_metrics(self, node_id: str) -> NodeMetrics:
        """Récupère les métriques d'un nœud avec cache"""
        try:
            response = await self._make_request(
                "GET",
                f"/nodes/{node_id}/metrics"
            )
            return NodeMetrics(**response)
        except LNPlusError as e:
            logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
            raise

    async def get_swaps(self, filters: Optional[Dict] = None) -> List[LightningSwap]:
        """Récupère les swaps avec filtres optionnels"""
        try:
            response = await self._make_request(
                "GET",
                "/swaps",
                params=filters
            )
            swaps = [LightningSwap(**swap) for swap in response["swaps"]]
            metrics.update_swap_count(len(swaps))
            return swaps
        except LNPlusError as e:
            logger.error(f"Erreur lors de la récupération des swaps: {str(e)}")
            raise

    async def create_swap(self, swap_request: SwapCreationRequest) -> LightningSwap:
        """Crée un nouveau swap"""
        try:
            response = await self._make_request(
                "POST",
                "/swaps",
                data=swap_request.dict()
            )
            return LightningSwap(**response)
        except LNPlusValidationError as e:
            logger.error(f"Données invalides pour la création du swap: {str(e)}")
            raise
        except LNPlusError as e:
            logger.error(f"Erreur lors de la création du swap: {str(e)}")
            raise

    async def get_node_rating(self, node_id: str) -> Rating:
        """Récupère la note d'un nœud"""
        try:
            response = await self._make_request(
                "GET",
                f"/nodes/{node_id}/rating"
            )
            return Rating(**response)
        except LNPlusError as e:
            logger.error(f"Erreur lors de la récupération de la note: {str(e)}")
            raise

    async def get_node(self, node_id: str) -> NodeMetrics:
        """Récupère les métriques d'un nœud"""
        response = await self._make_request("GET", f"/nodes/{node_id}")
        return NodeMetrics(**response)

    async def create_rating(
        self,
        target_node_id: str,
        is_positive: bool,
        comment: str
    ) -> Rating:
        """Crée une notation pour un nœud"""
        data = {
            "target_node_id": target_node_id,
            "is_positive": is_positive,
            "comment": comment
        }
        response = await self._make_request("POST", "/ratings", json=data)
        return Rating(**response)

    async def get_node_reputation(self, node_id: str) -> Dict[str, Any]:
        """Récupère la réputation d'un nœud"""
        return await self._make_request("GET", f"/nodes/{node_id}/reputation")

    async def get_balance(self) -> int:
        """Récupère le solde du wallet en satoshis"""
        try:
            balance = await self._lnbits.get_balance()
            metrics.update_balance(balance)
            return balance
        except LNPlusError as e:
            logger.error(f"Erreur lors de la récupération du solde: {str(e)}")
            raise

    async def close(self):
        """Ferme les connexions client"""
        if self._client:
            await self._client.aclose()
        await self._lnbits.close() 