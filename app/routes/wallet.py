# app/routes/wallet.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.services.lnbits import LNbitsService
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(prefix="/wallet", tags=["Wallet"])

# Modèles Pydantic pour les requêtes et réponses
class InvoiceRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Montant en sats")
    memo: Optional[str] = Field("", max_length=128, description="Description de la facture")

class PaymentRequest(BaseModel):
    bolt11: str = Field(..., min_length=1, description="Facture Lightning à payer")

@router.get(
    "/balance",
    summary="Obtenir le solde du portefeuille",
    description="Récupère les détails du portefeuille, y compris le solde actuel."
)
async def get_balance():
    """Obtenir le solde et les détails du portefeuille."""
    service = LNbitsService()
    return await service.get_wallet_details()

@router.get(
    "/transactions",
    summary="Historique des transactions",
    description="Récupère l'historique des transactions du portefeuille."
)
async def get_transactions():
    """Obtenir l'historique des transactions."""
    service = LNbitsService()
    return await service.get_transactions()

@router.post(
    "/invoice",
    summary="Créer une facture",
    description="Crée une nouvelle facture Lightning pour recevoir un paiement."
)
async def create_invoice(request: InvoiceRequest):
    """Créer une nouvelle facture Lightning."""
    service = LNbitsService()
    return await service.create_invoice(request.amount, request.memo)

@router.post(
    "/pay",
    summary="Payer une facture",
    description="Paie une facture Lightning avec le solde du portefeuille."
)
async def pay_invoice(request: PaymentRequest):
    """Payer une facture Lightning."""
    service = LNbitsService()
    return await service.pay_invoice(request.bolt11) 