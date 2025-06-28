# app/services/lnbits.py
import httpx
from fastapi import HTTPException, status
from app.db import get_lnbits_headers
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any

load_dotenv()

# URL de base de l'API LNbits depuis le fichier .env
LNBITS_URL = os.getenv("LNBITS_URL", "http://192.168.0.45:5000")

class LNbitsService:
    def __init__(self):
        self.base_url = os.getenv("LNBITS_URL", "https://legend.lnbits.com")
        self.api_key = os.getenv("LNBITS_API_KEY")
        self.admin_key = os.getenv("LNBITS_ADMIN_KEY")
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.admin_headers = {
            "X-Api-Key": self.admin_key,
            "Content-Type": "application/json"
        }

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, admin: bool = False) -> Dict:
        """Effectue une requête HTTP vers l'API LNbits."""
        headers = self.admin_headers if admin else self.headers
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, json=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=e.response.status_code if hasattr(e, 'response') else status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

    async def get_network_nodes(self) -> Dict:
        """Récupère la liste des nœuds du réseau Lightning."""
        return await self._make_request("GET", "/api/v1/network/nodes")

    async def get_node_rankings(self) -> Dict:
        """Récupère les classements des nœuds Lightning."""
        return await self._make_request("GET", "/api/v1/network/rankings")

    async def get_network_stats(self) -> Dict:
        """Récupère les statistiques globales du réseau Lightning."""
        return await self._make_request("GET", "/api/v1/network/stats")

    async def get_fee_calculator(self) -> Dict:
        """Récupère le calculateur de frais Lightning."""
        return await self._make_request("GET", "/api/v1/tools/fee-calculator")

    async def get_decoder(self) -> Dict:
        """Récupère le décodeur d'objets Lightning."""
        return await self._make_request("GET", "/api/v1/tools/decoder")

    async def get_node_priorities(self, node_id: str) -> Dict:
        """Récupère les priorités améliorées d'un nœud."""
        return await self._make_request("GET", f"/api/v1/node/{node_id}/priorities")

    async def get_node_complete_status(self, node_id: str) -> Dict:
        """Récupère le statut complet d'un nœud."""
        return await self._make_request("GET", f"/api/v1/node/{node_id}/status")

    async def get_node_lnd_status(self, node_id: str) -> Dict:
        """Récupère le statut LND d'un nœud."""
        return await self._make_request("GET", f"/api/v1/node/{node_id}/lnd/status")

    async def get_node_amboss_info(self, node_id: str) -> Dict:
        """Récupère les informations Amboss d'un nœud."""
        return await self._make_request("GET", f"/api/v1/node/{node_id}/amboss")

    async def get_amboss_channel_recommendations(self) -> Dict:
        """Récupère les recommandations de canaux depuis Amboss."""
        return await self._make_request("GET", "/api/v1/channels/recommendations/amboss")

    async def get_unified_channel_recommendations(self) -> Dict:
        """Récupère les recommandations de canaux unifiées."""
        return await self._make_request("GET", "/api/v1/channels/recommendations/unified")

    async def get_wallet_details(self):
        """Obtenir les détails du portefeuille, y compris le solde."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/wallet",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Erreur lors de la communication avec LNbits: {str(e)}"
                )

    async def get_transactions(self):
        """Obtenir l'historique des transactions."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/payments",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Erreur lors de la récupération des transactions: {str(e)}"
                )

    async def create_invoice(self, amount: int, memo: str = ""):
        """Créer une facture Lightning.
        
        Args:
            amount: Montant en sats
            memo: Description de la facture
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/payments",
                    headers=self.headers,
                    json={
                        "out": False,
                        "amount": amount,
                        "memo": memo
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Erreur lors de la création de la facture: {str(e)}"
                )

    async def pay_invoice(self, bolt11: str):
        """Payer une facture Lightning.
        
        Args:
            bolt11: Facture Lightning au format BOLT11
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/payments",
                    headers=self.headers,
                    json={
                        "out": True,
                        "bolt11": bolt11
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Erreur lors du paiement de la facture: {str(e)}"
                )

    async def get_node_data(self, node_id: str) -> Dict[str, Any]:
        """
        Récupère les données complètes d'un nœud pour l'analyse Max Flow.
        
        Args:
            node_id: Identifiant du nœud
            
        Returns:
            Données du nœud avec canaux, métriques et historique
        """
        try:
            # Récupérer les informations de base du nœud
            node_status = await self.get_node_complete_status(node_id)
            node_amboss = await self.get_node_amboss_info(node_id)
            
            # Récupérer les canaux (simulation pour l'instant)
            channels = await self._get_node_channels(node_id)
            
            # Récupérer les métriques historiques
            metrics = await self._get_node_metrics(node_id)
            
            # Construire l'objet de données complet
            node_data = {
                "node_id": node_id,
                "channels": channels,
                "metrics": metrics,
                "status": node_status,
                "amboss_info": node_amboss,
                "historical_success_rate": 0.85  # Valeur par défaut
            }
            
            return node_data
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Erreur lors de la récupération des données du nœud: {str(e)}"
            )

    async def get_network_overview(self) -> Dict[str, Any]:
        """
        Récupère une vue d'ensemble du réseau pour l'analyse de santé globale.
        
        Returns:
            Vue d'ensemble du réseau avec métriques globales
        """
        try:
            # Récupérer les statistiques du réseau
            network_stats = await self.get_network_stats()
            network_nodes = await self.get_network_nodes()
            
            # Récupérer les données de quelques nœuds représentatifs
            sample_nodes = []
            if network_nodes.get("nodes"):
                # Prendre les 5 premiers nœuds comme échantillon
                for node in network_nodes["nodes"][:5]:
                    try:
                        node_data = await self.get_node_data(node.get("node_id", ""))
                        sample_nodes.append(node_data)
                    except Exception:
                        continue  # Ignorer les nœuds avec erreurs
            
            return {
                "network_stats": network_stats,
                "total_nodes": len(network_nodes.get("nodes", [])),
                "nodes": sample_nodes,
                "timestamp": "2025-01-07T00:00:00Z"
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Erreur lors de la récupération de la vue d'ensemble du réseau: {str(e)}"
            )

    async def _get_node_channels(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Récupère les canaux d'un nœud (simulation pour l'instant).
        
        Args:
            node_id: Identifiant du nœud
            
        Returns:
            Liste des canaux avec leurs métriques
        """
        # Simulation de données de canaux pour les tests
        # En production, cela viendrait de l'API LND ou d'une base de données
        import random
        
        channels = []
        num_channels = random.randint(5, 15)
        
        for i in range(num_channels):
            capacity = random.randint(1000000, 10000000)  # 1M à 10M sats
            local_balance = random.randint(0, capacity)
            remote_balance = capacity - local_balance
            
            channels.append({
                "channel_id": f"{node_id}_channel_{i}",
                "peer_alias": f"peer_{i}",
                "capacity": capacity,
                "local_balance": local_balance,
                "remote_balance": remote_balance,
                "active": random.choice([True, True, True, False]),  # 75% actifs
                "local_fee_rate": random.randint(100, 1000),
                "local_fee_base_msat": random.randint(1000, 5000),
                "successful_forwards": random.randint(10, 1000),
                "total_forwards": random.randint(15, 1200),
                "avg_forward_size": random.randint(10000, 100000)
            })
        
        return channels

    async def _get_node_metrics(self, node_id: str) -> Dict[str, Any]:
        """
        Récupère les métriques d'un nœud (simulation pour l'instant).
        
        Args:
            node_id: Identifiant du nœud
            
        Returns:
            Métriques du nœud
        """
        # Simulation de métriques pour les tests
        import random
        
        return {
            "centrality": {
                "betweenness": random.uniform(0.1, 0.9),
                "closeness": random.uniform(0.3, 0.8),
                "eigenvector": random.uniform(0.2, 0.7)
            },
            "activity": {
                "forwards_count": random.randint(50, 500),
                "success_rate": random.uniform(0.7, 0.98),
                "avg_fee_earned": random.randint(10, 500)
            },
            "additional": {
                "uptime": random.uniform(0.8, 1.0),
                "connection_stability": random.uniform(0.6, 0.95)
            }
        } 