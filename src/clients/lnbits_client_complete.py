import httpx
import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LNBitsClientComplete:
    """Client LNBits complet avec tous les endpoints opérationnels pour la production."""
    
    def __init__(self, api_url: str, admin_key: str, invoice_key: str):
        self.api_url = api_url.rstrip('/')
        self.admin_key = admin_key
        self.invoice_key = invoice_key
        self.headers = {
            "X-Api-Key": admin_key,
            "Content-type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_wallet_details(self) -> Dict[str, Any]:
        """Récupère les détails du wallet."""
        url = f"{self.api_url}/api/v1/wallet"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des détails du wallet")
            return response.json()

    async def create_invoice(self, amount: int, memo: str = "") -> Dict[str, Any]:
        """Crée une facture Lightning."""
        url = f"{self.api_url}/api/v1/payments"
        data = {
            "out": False,
            "amount": amount,
            "memo": memo
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la création de la facture")
            return response.json()

    async def pay_invoice(self, bolt11: str) -> Dict[str, Any]:
        """Paie une facture Lightning."""
        url = f"{self.api_url}/api/v1/payments"
        data = {
            "out": True,
            "bolt11": bolt11
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors du paiement de la facture")
            return response.json()

    async def get_payments(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Récupère l'historique des paiements."""
        url = f"{self.api_url}/api/v1/payments"
        params = {"limit": limit, "offset": offset}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des paiements")
            return response.json()

    async def check_invoice_status(self, payment_hash: str) -> Dict[str, Any]:
        """Vérifie le statut d'une facture."""
        url = f"{self.api_url}/api/v1/payments/{payment_hash}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la vérification du statut de la facture")
            return response.json()

    async def get_wallet_balance(self) -> int:
        """Récupère le solde du wallet."""
        wallet_details = await self.get_wallet_details()
        return wallet_details.get("balance", 0)

    async def decode_invoice(self, bolt11: str) -> Dict[str, Any]:
        """Décode une facture Lightning."""
        url = f"{self.api_url}/api/v1/payments/decode"
        data = {"data": bolt11}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors du décodage de la facture")
            return response.json()

    async def get_node_info(self) -> Dict[str, Any]:
        """Récupère les informations du nœud."""
        url = f"{self.api_url}/api/v1/node"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des informations du nœud")
            return response.json()

    async def list_channels(self) -> List[Dict[str, Any]]:
        """Liste tous les canaux du nœud."""
        url = f"{self.api_url}/api/v1/channels"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des canaux")
            return response.json()

    async def update_channel_policy(self, channel_id: str, base_fee: int, fee_rate: int) -> Dict[str, Any]:
        """Met à jour la politique de frais d'un canal."""
        url = f"{self.api_url}/api/v1/channel/{channel_id}/policy"
        data = {
            "base_fee_msat": base_fee,
            "fee_rate": fee_rate
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la mise à jour de la politique du canal")
            return response.json()

    async def get_network_info(self) -> Dict[str, Any]:
        """Récupère les informations du réseau Lightning."""
        url = f"{self.api_url}/api/v1/network/info"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des informations du réseau")
            return response.json()

    async def get_routing_hints(self) -> List[Dict[str, Any]]:
        """Récupère les hints de routage pour le nœud."""
        url = f"{self.api_url}/api/v1/network/routes/hints"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur lors de la récupération des hints de routage")
            return response.json() 