# app/routes/wallet.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from app.services.lnbits import LNbitsService
from pydantic import BaseModel, Field
from typing import Optional, List
from app.auth import verify_jwt_and_get_tenant

router = APIRouter(prefix="/wallet", tags=["Wallet"])

# Modèles Pydantic pour les requêtes et réponses
class InvoiceRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Montant en sats")
    memo: Optional[str] = Field("", max_length=128, description="Description de la facture")

class PaymentRequest(BaseModel):
    bolt11: str = Field(..., min_length=1, description="Facture Lightning à payer")

@router.get(
    "/balance",
    summary="Solde du Portefeuille Lightning",
    description="Récupère le solde et les détails complets du portefeuille Lightning via LNbits",
    responses={
        200: {
            "description": "Détails du portefeuille récupérés",
            "content": {
                "application/json": {
                    "example": {
                        "id": "wallet_abc123",
                        "name": "Mon Wallet Principal",
                        "balance": 125000,
                        "currency": "sats",
                        "created_at": "2025-01-01T00:00:00Z"
                    }
                }
            }
        },
        401: {"description": "Non authentifié - JWT invalide"},
        500: {"description": "Erreur serveur"}
    }
)
async def get_balance(authorization: str = Header(..., alias="Authorization")):
    """
    **💰 Solde du Portefeuille Lightning**

    Récupère les informations complètes du portefeuille Lightning incluant:
    - Balance actuelle en satoshis
    - Identifiant du wallet
    - Nom et métadonnées
    - Date de création

    **Authentification:** Requiert un JWT valide dans le header `Authorization: Bearer <token>`
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    service = LNbitsService(tenant_id=tenant_id)
    return await service.get_wallet_details()

@router.get(
    "/transactions",
    summary="Historique des Transactions",
    description="Récupère l'historique complet des transactions Lightning (reçues et envoyées)",
    responses={
        200: {
            "description": "Liste des transactions",
            "content": {
                "application/json": {
                    "example": {
                        "transactions": [
                            {
                                "id": "tx_123",
                                "type": "incoming",
                                "amount": 50000,
                                "fee": 100,
                                "status": "settled",
                                "timestamp": "2025-01-09T12:00:00Z"
                            }
                        ],
                        "count": 1
                    }
                }
            }
        }
    }
)
async def get_transactions():
    """
    **📜 Historique des Transactions Lightning**

    Récupère l'historique complet des transactions incluant:
    - Paiements reçus (factures payées)
    - Paiements envoyés
    - Frais associés
    - Statut de chaque transaction
    - Horodatage
    """
    service = LNbitsService()
    return await service.get_transactions()

@router.post(
    "/invoice",
    summary="Créer une Facture Lightning",
    description="Génère une nouvelle facture Lightning (BOLT11) pour recevoir un paiement",
    responses={
        200: {
            "description": "Facture créée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "payment_hash": "abc123...",
                        "payment_request": "lnbc500u1p...",
                        "checking_id": "check_xyz",
                        "amount": 50000,
                        "memo": "Paiement pour service",
                        "expires_at": "2025-01-09T13:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Montant invalide"},
        500: {"description": "Erreur création facture"}
    }
)
async def create_invoice(request: InvoiceRequest):
    """
    **🧾 Créer une Facture Lightning (BOLT11)**

    Génère une facture Lightning pour recevoir un paiement.

    **Paramètres:**
    - `amount`: Montant en satoshis (> 0)
    - `memo`: Description optionnelle (max 128 caractères)

    **Retourne:**
    - `payment_request`: Facture BOLT11 à partager
    - `payment_hash`: Hash unique du paiement
    - Expiration de la facture
    """
    service = LNbitsService()
    return await service.create_invoice(request.amount, request.memo)

@router.post(
    "/pay",
    summary="Payer une Facture Lightning",
    description="Effectue un paiement Lightning en décodant et payant une facture BOLT11",
    responses={
        200: {
            "description": "Paiement effectué avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "payment_hash": "def456...",
                        "amount_paid": 50000,
                        "fee": 100,
                        "status": "complete",
                        "preimage": "xyz789...",
                        "timestamp": "2025-01-09T12:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Facture invalide ou expirée"},
        402: {"description": "Solde insuffisant"},
        500: {"description": "Échec du paiement"}
    }
)
async def pay_invoice(request: PaymentRequest):
    """
    **⚡ Payer une Facture Lightning**

    Effectue un paiement Lightning instantané.

    **Paramètres:**
    - `bolt11`: Facture Lightning BOLT11 (commence par lnbc...)

    **Processus:**
    1. Décodage de la facture
    2. Vérification du solde disponible
    3. Routage optimal via le réseau Lightning
    4. Paiement atomique (tout ou rien)

    **Retourne:**
    - Hash du paiement
    - Montant payé + frais
    - Preimage (preuve de paiement)
    - Statut final
    """
    service = LNbitsService()
    return await service.pay_invoice(request.bolt11) 