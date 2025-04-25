import httpx
from typing import Dict, Any
import logging
from .exceptions import LNPlusError

logger = logging.getLogger(__name__)

class LnbitsClient:
    def __init__(
        self, 
        base_url: str = "http://192.168.0.45:3007",
        admin_key: str = "fddac5fb8bf64eec944c89255b98dac4",
        invoice_key: str = "3fbbe7e0c2a24b43aa2c6ad6627f44eb"
    ):
        self.base_url = base_url
        self.admin_key = admin_key
        self.invoice_key = invoice_key
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Api-Key": admin_key}
        )

    async def sign_message(self, message: str) -> str:
        """Signe un message avec la clé privée du nœud via Lnbits"""
        try:
            response = await self._client.post(
                "/api/v1/signmessage",
                json={"message": message}
            )
            
            if response.status_code != 200:
                raise LNPlusError(f"Erreur Lnbits: {response.status_code} - {response.text}")
                
            data = response.json()
            if not data.get("signature"):
                raise LNPlusError("Signature non trouvée dans la réponse Lnbits")
                
            return data["signature"]
            
        except httpx.RequestError as e:
            logger.error(f"Erreur de connexion à Lnbits: {str(e)}")
            raise LNPlusError("Impossible de se connecter à Lnbits")

    async def get_balance(self) -> int:
        """Récupère le solde du wallet en satoshis"""
        try:
            # Utiliser la clé d'invocation pour les opérations de base
            response = await self._client.get(
                "/api/v1/wallet",
                headers={"X-Api-Key": self.invoice_key}
            )
            
            if response.status_code != 200:
                raise LNPlusError(f"Erreur Lnbits: {response.status_code} - {response.text}")
                
            data = response.json()
            if "balance" not in data:
                raise LNPlusError("Solde non trouvé dans la réponse Lnbits")
                
            return data["balance"]
            
        except httpx.RequestError as e:
            logger.error(f"Erreur de connexion à Lnbits: {str(e)}")
            raise LNPlusError("Impossible de se connecter à Lnbits")
            
    async def close(self):
        """Ferme la connexion client"""
        await self._client.aclose() 