import httpx
import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LNBitsClient:
    """Client pour interagir avec l'API LNBits."""
    
    def __init__(self, url: str = None, api_key: str = None, admin_key: Optional[str] = None, invoice_key: Optional[str] = None):
        # Priorité aux variables d'environnement
        self.url = (url or os.getenv("LNBITS_URL", "https://192.168.0.45:5000")).rstrip("/")
        self.api_key = api_key or os.getenv("LNBITS_API_KEY") or os.getenv("LNBITS_INVOICE_KEY", "votre_api_key_testnet")
        self.admin_key = admin_key or os.getenv("LNBITS_ADMIN_KEY") or self.api_key
        self.invoice_key = invoice_key or os.getenv("LNBITS_INVOICE_KEY") or self.api_key
        self.timeout = 30  # Timeout en secondes
        
        logger.info(f"LNBitsClient initialisé avec URL: {self.url}")
        
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, admin: bool = False, invoice: bool = False) -> Dict:
        """
        Effectue une requête à l'API LNBits.
        
        Args:
            method: Méthode HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint de l'API
            data: Données à envoyer (pour POST/PUT)
            admin: Si True, utilise la clé admin
            invoice: Si True, utilise la clé invoice
            
        Returns:
            Réponse de l'API sous forme de dictionnaire
        """
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
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                return response.json()
                
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