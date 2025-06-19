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