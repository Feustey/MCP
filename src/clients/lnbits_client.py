import httpx
import json
import logging
import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from functools import wraps

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de retry
MAX_RETRIES = 3
RETRY_DELAY = 2  # secondes
RETRY_BACKOFF = 2  # multiplicateur pour backoff exponentiel

def retry_on_failure(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """
    Décorateur pour retry automatique avec backoff exponentiel.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (RETRY_BACKOFF ** attempt)
                        logger.warning(
                            f"Erreur lors de l'appel à {func.__name__} (tentative {attempt + 1}/{max_retries}): {e}. "
                            f"Nouvelle tentative dans {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Échec définitif après {max_retries} tentatives: {e}")
                except httpx.HTTPStatusError as e:
                    # Ne pas retry sur les erreurs 4xx (sauf 429 Too Many Requests)
                    if e.response.status_code == 429:
                        last_exception = e
                        if attempt < max_retries - 1:
                            wait_time = delay * (RETRY_BACKOFF ** attempt)
                            logger.warning(f"Rate limit atteint. Retry dans {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            raise
                    else:
                        raise
            raise last_exception
        return wrapper
    return decorator


class LNBitsClient:
    """Client pour interagir avec l'API LNBits avec retry automatique et rate limiting."""
    
    def __init__(self, url: str = None, api_key: str = None, admin_key: Optional[str] = None, invoice_key: Optional[str] = None):
        # Priorité aux variables d'environnement
        self.url = (url or os.getenv("LNBITS_URL", "https://192.168.0.45:5000")).rstrip("/")
        self.api_key = api_key or os.getenv("LNBITS_API_KEY") or os.getenv("LNBITS_INVOICE_KEY", "votre_api_key_testnet")
        self.admin_key = admin_key or os.getenv("LNBITS_ADMIN_KEY") or self.api_key
        self.invoice_key = invoice_key or os.getenv("LNBITS_INVOICE_KEY") or self.api_key
        self.timeout = 30  # Timeout en secondes
        self.rate_limit_requests = 100  # Requêtes par minute
        self.rate_limit_window = 60  # secondes
        self._request_timestamps = []
        
        logger.info(f"LNBitsClient initialisé avec URL: {self.url}")
        
    async def _check_rate_limit(self):
        """Vérifie et applique le rate limiting."""
        now = datetime.now().timestamp()
        
        # Nettoyer les timestamps hors de la fenêtre
        self._request_timestamps = [
            ts for ts in self._request_timestamps 
            if now - ts < self.rate_limit_window
        ]
        
        # Vérifier si on a atteint la limite
        if len(self._request_timestamps) >= self.rate_limit_requests:
            oldest = self._request_timestamps[0]
            wait_time = self.rate_limit_window - (now - oldest)
            if wait_time > 0:
                logger.warning(f"Rate limit atteint. Attente de {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
        
        # Ajouter le timestamp actuel
        self._request_timestamps.append(now)
    
    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, admin: bool = False, invoice: bool = False) -> Dict:
        """
        Effectue une requête à l'API LNBits avec retry automatique et rate limiting.
        
        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de l'API
            data: Données à envoyer (pour POST/PUT)
            admin: Si True, utilise la clé admin
            invoice: Si True, utilise la clé invoice
            
        Returns:
            Réponse de l'API sous forme de dictionnaire
        """
        # Appliquer le rate limiting
        await self._check_rate_limit()
        
        url = f"{self.url}{endpoint}"
        
        # Sélection de la clé API appropriée
        if admin:
            api_key = self.admin_key
        elif invoice:
            api_key = self.invoice_key
        else:
            api_key = self.api_key
            
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # Utiliser un timeout configuré avec httpx
        timeout_config = httpx.Timeout(self.timeout, connect=10.0)
        
        try:
            async with httpx.AsyncClient(timeout=timeout_config, verify=False) as client:  # verify=False pour les certificats self-signed
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Méthode HTTP non supportée: {method}")
                
                response.raise_for_status()
                
                # Gérer les réponses vides
                if response.text:
                    return response.json()
                else:
                    return {"success": True}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Erreur de requête: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la requête à {url}: {str(e)}")
            raise
    
    # Méthodes originales pour la gestion du nœud
    
    async def get_wallet_info(self) -> Dict:
        """Récupère les informations du portefeuille."""
        return await self._make_request("GET", "/api/v1/wallet")
    
    async def set_fee_policy(self, base_fee_msat: int = 1000, fee_rate: int = 100) -> Dict:
        """
        Configure la politique de frais du nœud.
        
        Args:
            base_fee_msat: Frais de base en millisatoshis
            fee_rate: Taux de frais en ppm (parties par million)
            
        Returns:
            Réponse de l'API
        """
        data = {
            "base_fee_msat": base_fee_msat,
            "fee_rate": fee_rate
        }
        return await self._make_request("POST", "/api/v1/lnurlp/fee-policy", data, admin=True)
    
    async def set_channel_policies(self, target_local_ratio: float = 0.5, rebalance_threshold: float = 0.3) -> Dict:
        """
        Configure les politiques de gestion des canaux.
        
        Args:
            target_local_ratio: Ratio cible de liquidité locale (0-1)
            rebalance_threshold: Seuil de déclenchement du rééquilibrage (0-1)
            
        Returns:
            Réponse de l'API
        """
        data = {
            "target_local_ratio": target_local_ratio,
            "rebalance_threshold": rebalance_threshold
        }
        return await self._make_request("POST", "/api/v1/lnurlp/channel-policies", data, admin=True)
    
    async def configure_peer_selection(self, target_nodes: List[str] = None, min_capacity: int = 100000) -> Dict:
        """
        Configure les critères de sélection de pairs.
        
        Args:
            target_nodes: Liste des pubkeys des nœuds cibles
            min_capacity: Capacité minimale des canaux en sats
            
        Returns:
            Réponse de l'API
        """
        data = {
            "target_nodes": target_nodes or [],
            "min_capacity": min_capacity
        }
        return await self._make_request("POST", "/api/v1/lnurlp/peer-policy", data, admin=True)
    
    async def get_node_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du nœud.
        
        Returns:
            Statistiques du nœud
        """
        return await self._make_request("GET", "/api/v1/lnurlp/stats")
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des canaux du nœud.
        
        Returns:
            Liste des canaux
        """
        return await self._make_request("GET", "/api/v1/lnurlp/channels")
    
    # Nouvelles méthodes pour le scan de liquidité
    
    async def get_node_channels(self, node_pubkey: str) -> List[Dict[str, Any]]:
        """
        Récupère les canaux d'un nœud spécifique.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Liste des canaux du nœud
        """
        try:
            # En fonction de l'API: si le nœud est le nôtre, utiliser get_channels,
            # sinon faire une requête spécifique (simulée ici)
            if node_pubkey == await self._get_own_pubkey():
                return await self.get_channels()
            else:
                # Simulation de requête vers l'API (à adapter à l'API réelle)
                data = {"node_pubkey": node_pubkey}
                return await self._make_request("GET", f"/api/v1/network/node/{node_pubkey}/channels")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des canaux du nœud {node_pubkey}: {str(e)}")
            # En cas d'erreur, renvoyer une liste vide plutôt que de lever une exception
            return []
    
    async def _get_own_pubkey(self) -> str:
        """
        Récupère la clé publique du nœud local.
        
        Returns:
            Clé publique du nœud
        """
        try:
            info = await self._make_request("GET", "/api/v1/wallet", admin=True)
            return info.get("id", "")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la clé publique: {str(e)}")
            return ""
    
    async def send_test_payment(self, 
                               source_node: str, 
                               target_node: str, 
                               amount_sats: int = 500000, 
                               channel_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Envoie un paiement test pour vérifier la liquidité d'un canal.
        
        Args:
            source_node: Nœud source du paiement
            target_node: Nœud cible du paiement
            amount_sats: Montant du paiement en sats
            channel_hint: ID du canal à utiliser si spécifié
            
        Returns:
            Résultat du paiement test
        """
        try:
            # Préparer les données du paiement
            payment_data = {
                "source": source_node,
                "destination": target_node,
                "amount_sats": amount_sats,
                "test_only": True  # Indique que c'est un paiement de test sans transfert réel
            }
            
            if channel_hint:
                payment_data["channel_hint"] = channel_hint
            
            # Effectuer la requête de paiement de test
            # Note: Endpoint spécifique pour les tests de liquidité (à adapter à l'API réelle)
            result = await self._make_request("POST", "/api/v1/lnurlp/test-payment", payment_data, admin=True)
            
            # Vérifier la réussite du paiement
            success = result.get("success", False)
            
            if success:
                logger.info(f"Test de paiement réussi de {source_node[:8]}... vers {target_node[:8]}...")
            else:
                logger.info(f"Test de paiement échoué de {source_node[:8]}... vers {target_node[:8]}...: {result.get('error', 'Raison inconnue')}")
            
            return {
                "success": success,
                "amount": amount_sats,
                "source": source_node,
                "target": target_node,
                "channel": channel_hint,
                "error": result.get("error", "") if not success else "",
                "time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du test de paiement: {str(e)}")
            return {
                "success": False,
                "amount": amount_sats,
                "source": source_node,
                "target": target_node,
                "channel": channel_hint,
                "error": str(e),
                "time": datetime.now().isoformat()
            }
    
    # ========== Endpoints LNBits Complets pour P2.1 ==========
    
    async def get_node_info(self) -> Dict[str, Any]:
        """Récupère les informations du nœud Lightning."""
        return await self._make_request("GET", "/lightning/api/v1/node_info", admin=True)
    
    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un canal spécifique."""
        return await self._make_request("GET", f"/lightning/api/v1/channel/{channel_id}", admin=True)
    
    async def update_channel_policy(
        self, 
        channel_point: str, 
        base_fee_msat: int, 
        fee_rate_ppm: int,
        time_lock_delta: int = 40,
        min_htlc_msat: int = 1000,
        max_htlc_msat: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Met à jour la politique de frais d'un canal.
        
        Args:
            channel_point: Point du canal (txid:output_index)
            base_fee_msat: Frais de base en millisatoshis
            fee_rate_ppm: Taux de frais en ppm
            time_lock_delta: Délai de timelock
            min_htlc_msat: HTLC minimum en msat
            max_htlc_msat: HTLC maximum en msat (optionnel)
        """
        data = {
            "channel_point": channel_point,
            "base_fee_msat": base_fee_msat,
            "fee_rate": fee_rate_ppm,
            "time_lock_delta": time_lock_delta,
            "min_htlc": min_htlc_msat
        }
        
        if max_htlc_msat:
            data["max_htlc"] = max_htlc_msat
        
        return await self._make_request("POST", "/lightning/api/v1/channel_policy", data, admin=True)
    
    async def get_forwarding_history(
        self, 
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        num_max_events: int = 1000
    ) -> Dict[str, Any]:
        """
        Récupère l'historique des forwards.
        
        Args:
            start_time: Timestamp de début (secondes)
            end_time: Timestamp de fin (secondes)
            num_max_events: Nombre maximum d'événements
        """
        params = {"num_max_events": num_max_events}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        endpoint = f"/lightning/api/v1/forwarding_history?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        return await self._make_request("GET", endpoint, admin=True)
    
    async def create_invoice(
        self, 
        amount: int, 
        memo: str = "", 
        expiry: int = 3600
    ) -> Dict[str, Any]:
        """
        Crée une facture Lightning.
        
        Args:
            amount: Montant en satoshis
            memo: Description de la facture
            expiry: Expiration en secondes
        """
        data = {
            "out": False,
            "amount": amount,
            "memo": memo,
            "expiry": expiry
        }
        return await self._make_request("POST", "/api/v1/payments", data, invoice=True)
    
    async def pay_invoice(self, payment_request: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """
        Paie une facture Lightning.
        
        Args:
            payment_request: BOLT11 payment request
            amount: Montant en sats (optionnel pour invoices avec montant)
        """
        data = {"out": True, "bolt11": payment_request}
        if amount:
            data["amount"] = amount
        
        return await self._make_request("POST", "/api/v1/payments", data, admin=True)
    
    async def list_payments(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Liste les paiements récents."""
        result = await self._make_request("GET", f"/api/v1/payments?limit={limit}")
        return result if isinstance(result, list) else []
    
    async def open_channel(
        self, 
        node_pubkey: str, 
        local_amt: int,
        push_amt: int = 0,
        target_conf: int = 6,
        sat_per_vbyte: Optional[int] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """
        Ouvre un nouveau canal.
        
        Args:
            node_pubkey: Clé publique du pair
            local_amt: Montant local en satoshis
            push_amt: Montant à pousser vers le pair
            target_conf: Confirmations cibles
            sat_per_vbyte: Frais en sat/vbyte
            private: Canal privé ou public
        """
        data = {
            "node_pubkey": node_pubkey,
            "local_funding_amount": local_amt,
            "push_sat": push_amt,
            "target_conf": target_conf,
            "private": private
        }
        
        if sat_per_vbyte:
            data["sat_per_vbyte"] = sat_per_vbyte
        
        return await self._make_request("POST", "/lightning/api/v1/open_channel", data, admin=True)
    
    async def close_channel(
        self, 
        channel_point: str, 
        force: bool = False,
        target_conf: int = 6,
        sat_per_vbyte: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ferme un canal.
        
        Args:
            channel_point: Point du canal (txid:output_index)
            force: Fermeture forcée ou coopérative
            target_conf: Confirmations cibles
            sat_per_vbyte: Frais en sat/vbyte
        """
        data = {
            "channel_point": channel_point,
            "force": force,
            "target_conf": target_conf
        }
        
        if sat_per_vbyte:
            data["sat_per_vbyte"] = sat_per_vbyte
        
        return await self._make_request("POST", "/lightning/api/v1/close_channel", data, admin=True)
    
    async def get_balance(self) -> Dict[str, Any]:
        """Récupère les balances du wallet et des canaux."""
        wallet_balance = await self._make_request("GET", "/lightning/api/v1/balance/wallet", admin=True)
        channel_balance = await self._make_request("GET", "/lightning/api/v1/balance/channels", admin=True)
        
        return {
            "wallet": wallet_balance,
            "channels": channel_balance
        }
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Récupère les informations du réseau Lightning."""
        return await self._make_request("GET", "/lightning/api/v1/network_info", admin=True)
    
    async def describe_graph(self) -> Dict[str, Any]:
        """Récupère le graphe complet du réseau."""
        return await self._make_request("GET", "/lightning/api/v1/graph", admin=True)
    
    async def get_channel_balance_ratio(self, channel_id: str) -> float:
        """
        Calcule le ratio de balance local/remote d'un canal.
        
        Returns:
            Ratio entre 0 et 1 (0.5 = parfaitement équilibré)
        """
        channel = await self.get_channel_info(channel_id)
        local = int(channel.get("local_balance", 0))
        remote = int(channel.get("remote_balance", 0))
        total = local + remote
        
        return local / total if total > 0 else 0.5 