# app/services/lnbits.py
import httpx
from fastapi import HTTPException, status
from app.db import get_lnbits_headers
import os
from dotenv import load_dotenv

load_dotenv()

# URL de base de l'API LNbits depuis le fichier .env
LNBITS_URL = os.getenv("LNBITS_URL", "http://192.168.0.45:5000")

class LNbitsService:
    def __init__(self):
        self.headers = get_lnbits_headers()
        self.base_url = LNBITS_URL

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