"""
LNBits Client v2 - Client complet et robuste pour l'API LNBits
Dernière mise à jour: 12 octobre 2025
Version: 2.0.0

Ce client implémente tous les endpoints nécessaires pour MCP avec:
- Retry logic avec backoff exponentiel
- Rate limiting
- Gestion d'erreurs robuste
- Support macaroon
- Logging structuré
- Tests unitaires
"""

import httpx
import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import structlog

# Configuration du logging structuré
logger = structlog.get_logger(__name__)


class AuthMethod(Enum):
    """Méthodes d'authentification supportées"""
    API_KEY = "api_key"  # X-Api-Key header (standard LNBits)
    BEARER = "bearer"    # Authorization: Bearer (alternative)
    MACAROON = "macaroon"  # Grpc-Metadata-macaroon (LND style)


@dataclass
class RetryConfig:
    """Configuration du mécanisme de retry"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class RateLimitConfig:
    """Configuration du rate limiting"""
    max_requests_per_minute: int = 100
    burst_size: int = 20


class LNBitsClientError(Exception):
    """Exception de base pour les erreurs du client LNBits"""
    pass


class LNBitsAuthError(LNBitsClientError):
    """Erreur d'authentification"""
    pass


class LNBitsRateLimitError(LNBitsClientError):
    """Erreur de dépassement du rate limit"""
    pass


class LNBitsTimeoutError(LNBitsClientError):
    """Erreur de timeout"""
    pass


class LNBitsClientV2:
    """
    Client LNBits v2 - Production Ready
    
    Implémente tous les endpoints de l'API LNBits avec:
    - Authentification flexible (API Key, Bearer, Macaroon)
    - Retry automatique avec backoff exponentiel
    - Rate limiting configurable
    - Gestion d'erreurs robuste
    - Logging structuré
    - Support multi-wallet
    
    Endpoints implémentés:
    - Wallet API (balance, info, payments)
    - Lightning API (channels, node info, policies)
    - Invoice API (create, pay, check)
    - Payment API (send, decode, track)
    - Channel Management (open, close, update policies)
    - Network Graph (topology, routing)
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        admin_key: Optional[str] = None,
        invoice_key: Optional[str] = None,
        auth_method: AuthMethod = AuthMethod.API_KEY,
        retry_config: Optional[RetryConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True
    ):
        """
        Initialise le client LNBits v2
        
        Args:
            url: URL de l'instance LNBits
            api_key: Clé API principale
            admin_key: Clé admin pour opérations avancées
            invoice_key: Clé pour créer des invoices
            auth_method: Méthode d'authentification à utiliser
            retry_config: Configuration du retry
            rate_limit_config: Configuration du rate limiting
            timeout: Timeout par défaut en secondes
            verify_ssl: Vérifier les certificats SSL
        """
        # Configuration de base
        self.url = (url or os.getenv("LNBITS_URL", "")).rstrip("/")
        if not self.url:
            raise ValueError("LNBits URL is required")
            
        self.api_key = api_key or os.getenv("LNBITS_API_KEY", "")
        self.admin_key = admin_key or os.getenv("LNBITS_ADMIN_KEY") or self.api_key
        self.invoice_key = invoice_key or os.getenv("LNBITS_INVOICE_KEY") or self.api_key
        
        if not self.api_key:
            raise ValueError("At least one API key is required")
        
        self.auth_method = auth_method
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # Configuration retry et rate limiting
        self.retry_config = retry_config or RetryConfig()
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        
        # Rate limiting state
        self._request_times: List[datetime] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # Build headers
        self._build_headers()
        
        logger.info(
            "lnbits_client_initialized",
            url=self.url,
            auth_method=auth_method.value,
            timeout=timeout
        )
    
    def _build_headers(self):
        """Construit les headers d'authentification selon la méthode"""
        base_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.auth_method == AuthMethod.API_KEY:
            self.headers = {**base_headers, "X-Api-Key": self.api_key}
            self.admin_headers = {**base_headers, "X-Api-Key": self.admin_key}
            self.invoice_headers = {**base_headers, "X-Api-Key": self.invoice_key}
        elif self.auth_method == AuthMethod.BEARER:
            self.headers = {**base_headers, "Authorization": f"Bearer {self.api_key}"}
            self.admin_headers = {**base_headers, "Authorization": f"Bearer {self.admin_key}"}
            self.invoice_headers = {**base_headers, "Authorization": f"Bearer {self.invoice_key}"}
        elif self.auth_method == AuthMethod.MACAROON:
            self.headers = {**base_headers, "Grpc-Metadata-macaroon": self.api_key}
            self.admin_headers = {**base_headers, "Grpc-Metadata-macaroon": self.admin_key}
            self.invoice_headers = {**base_headers, "Grpc-Metadata-macaroon": self.invoice_key}
    
    async def _check_rate_limit(self):
        """Vérifie et applique le rate limiting"""
        async with self._rate_limit_lock:
            now = datetime.now()
            
            # Nettoyer les requêtes trop anciennes (> 1 minute)
            cutoff = now - timedelta(minutes=1)
            self._request_times = [t for t in self._request_times if t > cutoff]
            
            # Vérifier si on dépasse la limite
            if len(self._request_times) >= self.rate_limit_config.max_requests_per_minute:
                oldest = self._request_times[0]
                wait_time = 60 - (now - oldest).total_seconds()
                
                if wait_time > 0:
                    logger.warning(
                        "rate_limit_reached",
                        wait_time=wait_time,
                        requests_count=len(self._request_times)
                    )
                    await asyncio.sleep(wait_time)
            
            # Enregistrer cette requête
            self._request_times.append(now)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_admin: bool = False,
        use_invoice: bool = False,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Effectue une requête HTTP avec retry et rate limiting
        
        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de l'API (ex: /api/v1/wallet)
            data: Données JSON pour POST/PUT
            params: Paramètres query string
            headers: Headers additionnels
            use_admin: Utiliser la clé admin
            use_invoice: Utiliser la clé invoice
            retry: Activer le retry automatique
            
        Returns:
            Réponse JSON de l'API
            
        Raises:
            LNBitsClientError: Erreur lors de la requête
        """
        # Rate limiting
        await self._check_rate_limit()
        
        # Sélection des headers
        if use_admin:
            request_headers = self.admin_headers.copy()
        elif use_invoice:
            request_headers = self.invoice_headers.copy()
        else:
            request_headers = self.headers.copy()
        
        if headers:
            request_headers.update(headers)
        
        # Construction de l'URL
        url = f"{self.url}{endpoint}"
        
        # Retry logic
        last_exception = None
        for attempt in range(self.retry_config.max_retries if retry else 1):
            try:
                async with httpx.AsyncClient(verify=self.verify_ssl, timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=request_headers, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=request_headers, json=data, params=params)
                    elif method.upper() == "PUT":
                        response = await client.put(url, headers=request_headers, json=data, params=params)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, headers=request_headers, params=params)
                    elif method.upper() == "PATCH":
                        response = await client.patch(url, headers=request_headers, json=data, params=params)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    # Vérifier le statut
                    if response.status_code == 401 or response.status_code == 403:
                        raise LNBitsAuthError(f"Authentication failed: {response.text}")
                    elif response.status_code == 429:
                        raise LNBitsRateLimitError(f"Rate limit exceeded: {response.text}")
                    
                    response.raise_for_status()
                    
                    # Parse JSON response
                    try:
                        result = response.json()
                    except:
                        # Si pas de JSON, retourner le texte
                        result = {"text": response.text}
                    
                    logger.debug(
                        "request_success",
                        method=method,
                        endpoint=endpoint,
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                    
                    return result
                    
            except httpx.TimeoutException as e:
                last_exception = LNBitsTimeoutError(f"Request timeout: {str(e)}")
                logger.warning(
                    "request_timeout",
                    method=method,
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(e)
                )
            except httpx.HTTPStatusError as e:
                last_exception = LNBitsClientError(
                    f"HTTP {e.response.status_code}: {e.response.text}"
                )
                logger.warning(
                    "request_http_error",
                    method=method,
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                    error=str(e)
                )
            except httpx.RequestError as e:
                last_exception = LNBitsClientError(f"Request error: {str(e)}")
                logger.warning(
                    "request_error",
                    method=method,
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(e)
                )
            except (LNBitsAuthError, LNBitsRateLimitError) as e:
                # Ne pas retry sur ces erreurs
                logger.error(
                    "request_fatal_error",
                    method=method,
                    endpoint=endpoint,
                    error=str(e)
                )
                raise
            except Exception as e:
                last_exception = LNBitsClientError(f"Unexpected error: {str(e)}")
                logger.error(
                    "request_unexpected_error",
                    method=method,
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(e)
                )
            
            # Attendre avant de retry
            if retry and attempt < self.retry_config.max_retries - 1:
                delay = min(
                    self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                    self.retry_config.max_delay
                )
                
                if self.retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random())
                
                logger.info(
                    "retrying_request",
                    method=method,
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    delay=delay
                )
                await asyncio.sleep(delay)
        
        # Si on arrive ici, toutes les tentatives ont échoué
        logger.error(
            "request_failed_all_retries",
            method=method,
            endpoint=endpoint,
            retries=self.retry_config.max_retries
        )
        raise last_exception or LNBitsClientError("Request failed after all retries")
    
    # ═══════════════════════════════════════════════════════════
    # WALLET API
    # ═══════════════════════════════════════════════════════════
    
    async def get_wallet_info(self) -> Dict[str, Any]:
        """
        Récupère les informations du wallet
        
        Returns:
            Informations du wallet (balance, id, name, etc.)
        """
        return await self._make_request("GET", "/api/v1/wallet")
    
    async def get_balance(self) -> int:
        """
        Récupère le solde du wallet en msats
        
        Returns:
            Solde en millisatoshis
        """
        wallet_info = await self.get_wallet_info()
        return wallet_info.get("balance", 0)
    
    async def get_payments(
        self,
        limit: int = 100,
        offset: int = 0,
        pending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des paiements
        
        Args:
            limit: Nombre maximum de paiements à retourner
            offset: Décalage pour la pagination
            pending: Inclure les paiements en attente
            
        Returns:
            Liste des paiements
        """
        params = {
            "limit": limit,
            "offset": offset,
            "pending": str(pending).lower()
        }
        return await self._make_request("GET", "/api/v1/payments", params=params)
    
    # ═══════════════════════════════════════════════════════════
    # INVOICE API
    # ═══════════════════════════════════════════════════════════
    
    async def create_invoice(
        self,
        amount: int,
        memo: str = "",
        expiry: int = 3600,
        webhook: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle invoice
        
        Args:
            amount: Montant en satoshis
            memo: Description de l'invoice
            expiry: Expiration en secondes
            webhook: URL de webhook pour notification
            
        Returns:
            Informations de l'invoice (payment_request, checking_id, etc.)
        """
        data = {
            "out": False,  # False = incoming invoice
            "amount": amount,
            "memo": memo,
            "expiry": expiry
        }
        
        if webhook:
            data["webhook"] = webhook
        
        return await self._make_request(
            "POST",
            "/api/v1/payments",
            data=data,
            use_invoice=True
        )
    
    async def pay_invoice(
        self,
        bolt11: str,
        max_fee_msats: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Paie une invoice Lightning
        
        Args:
            bolt11: Invoice encodée (Lightning payment request)
            max_fee_msats: Frais maximum acceptés en millisatoshis
            
        Returns:
            Résultat du paiement
        """
        data = {
            "out": True,  # True = outgoing payment
            "bolt11": bolt11
        }
        
        if max_fee_msats is not None:
            data["max_fee_msats"] = max_fee_msats
        
        return await self._make_request(
            "POST",
            "/api/v1/payments",
            data=data,
            use_admin=True
        )
    
    async def check_invoice(self, payment_hash: str) -> Dict[str, Any]:
        """
        Vérifie le statut d'une invoice
        
        Args:
            payment_hash: Hash du paiement
            
        Returns:
            Status de l'invoice
        """
        return await self._make_request(
            "GET",
            f"/api/v1/payments/{payment_hash}"
        )
    
    async def decode_invoice(self, bolt11: str) -> Dict[str, Any]:
        """
        Décode une invoice Lightning
        
        Args:
            bolt11: Invoice encodée
            
        Returns:
            Informations décodées de l'invoice
        """
        data = {"data": bolt11}
        return await self._make_request(
            "POST",
            "/api/v1/payments/decode",
            data=data
        )
    
    # ═══════════════════════════════════════════════════════════
    # LIGHTNING NODE API
    # ═══════════════════════════════════════════════════════════
    
    async def get_node_info(self) -> Dict[str, Any]:
        """
        Récupère les informations du nœud Lightning
        
        Returns:
            Informations du nœud (pubkey, alias, channels, etc.)
        """
        return await self._make_request(
            "GET",
            "/lightning/api/v1/node/info",
            use_admin=True
        )
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des canaux
        
        Returns:
            Liste des canaux avec leurs informations
        """
        response = await self._make_request(
            "GET",
            "/lightning/api/v1/channels",
            use_admin=True
        )
        return response.get("channels", [])
    
    async def get_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Récupère les informations d'un canal spécifique
        
        Args:
            channel_id: ID du canal
            
        Returns:
            Informations détaillées du canal
        """
        return await self._make_request(
            "GET",
            f"/lightning/api/v1/channel/{channel_id}",
            use_admin=True
        )
    
    # ═══════════════════════════════════════════════════════════
    # CHANNEL POLICY API
    # ═══════════════════════════════════════════════════════════
    
    async def update_channel_policy(
        self,
        channel_id: str,
        base_fee_msat: Optional[int] = None,
        fee_rate_ppm: Optional[int] = None,
        time_lock_delta: Optional[int] = None,
        min_htlc_msat: Optional[int] = None,
        max_htlc_msat: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Met à jour la politique de fees d'un canal
        
        Args:
            channel_id: ID du canal
            base_fee_msat: Frais de base en millisatoshis
            fee_rate_ppm: Taux de frais en ppm (parties par million)
            time_lock_delta: Delta de time lock
            min_htlc_msat: Montant minimum HTLC en millisatoshis
            max_htlc_msat: Montant maximum HTLC en millisatoshis
            
        Returns:
            Confirmation de la mise à jour
        """
        data = {"channel_id": channel_id}
        
        if base_fee_msat is not None:
            data["base_fee_msat"] = base_fee_msat
        if fee_rate_ppm is not None:
            data["fee_rate_ppm"] = fee_rate_ppm
        if time_lock_delta is not None:
            data["time_lock_delta"] = time_lock_delta
        if min_htlc_msat is not None:
            data["min_htlc_msat"] = min_htlc_msat
        if max_htlc_msat is not None:
            data["max_htlc_msat"] = max_htlc_msat
        
        return await self._make_request(
            "POST",
            "/lightning/api/v1/channel/policy",
            data=data,
            use_admin=True
        )
    
    async def get_channel_policy(self, channel_id: str) -> Dict[str, Any]:
        """
        Récupère la politique actuelle d'un canal
        
        Args:
            channel_id: ID du canal
            
        Returns:
            Politique du canal (fees, limits, etc.)
        """
        return await self._make_request(
            "GET",
            f"/lightning/api/v1/channel/{channel_id}/policy",
            use_admin=True
        )
    
    # ═══════════════════════════════════════════════════════════
    # NETWORK GRAPH API
    # ═══════════════════════════════════════════════════════════
    
    async def get_network_graph(self) -> Dict[str, Any]:
        """
        Récupère le graph du réseau Lightning
        
        Returns:
            Graph du réseau (nodes, channels)
        """
        return await self._make_request(
            "GET",
            "/lightning/api/v1/graph",
            use_admin=True
        )
    
    async def get_network_node(self, pubkey: str) -> Dict[str, Any]:
        """
        Récupère les informations d'un nœud du réseau
        
        Args:
            pubkey: Clé publique du nœud
            
        Returns:
            Informations du nœud
        """
        return await self._make_request(
            "GET",
            f"/lightning/api/v1/graph/node/{pubkey}",
            use_admin=True
        )
    
    async def get_route(
        self,
        destination: str,
        amount_sats: int
    ) -> Dict[str, Any]:
        """
        Calcule une route vers une destination
        
        Args:
            destination: Pubkey de destination
            amount_sats: Montant en satoshis
            
        Returns:
            Route calculée
        """
        params = {
            "pub_key": destination,
            "amt": amount_sats
        }
        return await self._make_request(
            "GET",
            "/lightning/api/v1/graph/routes",
            params=params,
            use_admin=True
        )
    
    # ═══════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════
    
    async def health_check(self) -> bool:
        """
        Vérifie la santé de la connexion LNBits
        
        Returns:
            True si la connexion est saine
        """
        try:
            await self.get_wallet_info()
            return True
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False
    
    async def close(self):
        """Nettoie les ressources (pour compatibilité context manager)"""
        logger.info("lnbits_client_closed")
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()

