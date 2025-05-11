"""
Interface directe à LNbits interne sans wrapper.
Ce module expose les fonctionnalités essentielles de LNbits directement, sans abstraction inutile.
Utilise une approche brutalement efficace pour maximiser les performances et la visibilité des erreurs.
"""

import os
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Import direct des services et modules LNbits essentiels
from lnbits_internal.core.services import (
    create_invoice as _create_invoice,
    pay_invoice as _pay_invoice,
)

from lnbits_internal.core.crud.wallets import (
    get_wallet as _get_wallet,
    get_wallet_for_key as _get_wallet_for_key
)

from lnbits_internal.core.crud.payments import (
    get_payments as _get_payments,
    get_payment as _get_payment,
)

# Import des clés depuis le settings_wrapper
from lnbits_internal.settings_wrapper import (
    get_admin_key,
    get_invoice_key,
    get_db_stats,
)

# Configuration du logging
logger = logging.getLogger("direct_lnbits")

# Constantes
DEFAULT_EXPIRY = 3600  # 1 heure par défaut

# Liste des derniers temps de réponse pour monitoring des performances
_response_times: List[float] = []
_max_response_times = 100  # Garde les 100 dernières mesures 

class InvoiceResult:
    """Structure légère contenant le résultat d'une création de facture"""
    def __init__(
        self, 
        payment_hash: str, 
        payment_request: str, 
        amount: int, 
        memo: str,
        timestamp: float = None
    ):
        self.payment_hash = payment_hash
        self.payment_request = payment_request
        self.amount = amount
        self.memo = memo
        self.timestamp = timestamp or time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_hash": self.payment_hash,
            "payment_request": self.payment_request,
            "amount": self.amount, 
            "memo": self.memo,
            "created_at": datetime.fromtimestamp(self.timestamp).isoformat()
        }

class PaymentResult:
    """Structure légère contenant le résultat d'un paiement"""
    def __init__(
        self,
        success: bool,
        payment_hash: str = "",
        fee_sat: int = 0,
        preimage: Optional[str] = None,
        error: Optional[str] = None,
        timestamp: float = None
    ):
        self.success = success
        self.payment_hash = payment_hash
        self.fee_sat = fee_sat
        self.preimage = preimage
        self.error = error
        self.timestamp = timestamp or time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "payment_hash": self.payment_hash,
            "fee_sat": self.fee_sat,
            "preimage": self.preimage,
            "error": self.error,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat()
        }

async def create_invoice(amount: int, memo: str = "", expiry: int = DEFAULT_EXPIRY) -> InvoiceResult:
    """
    Crée une facture Lightning directement avec la clé invoice
    
    Args:
        amount: Montant en satoshis
        memo: Description de la facture
        expiry: Durée de validité en secondes (défaut: 1 heure)
    
    Returns:
        InvoiceResult avec les détails de la facture
        
    Raises:
        Exception: En cas d'échec de création de la facture
    """
    start_time = time.time()
    
    try:
        # Récupération de la clé invoice
        invoice_key = get_invoice_key()
        if not invoice_key:
            raise ValueError("Aucune clé invoice configurée")
        
        # Récupération du wallet correspondant à la clé
        wallet = await _get_wallet_for_key(invoice_key, emit_fall_back=False)
        if not wallet:
            raise ValueError("Impossible de trouver le wallet pour la clé invoice")
        
        # Création de la facture
        payment_hash, payment_request = await _create_invoice(
            wallet_id=wallet.id,
            amount=amount,
            memo=memo,
            expiry=expiry
        )
        
        result = InvoiceResult(payment_hash, payment_request, amount, memo)
        
        # Mesure du temps de réponse
        response_time = time.time() - start_time
        _record_response_time(response_time)
        logger.debug(f"Invoice créée en {response_time:.3f}s: {payment_hash}")
        
        return result
    
    except Exception as e:
        # Mesure du temps de réponse même en cas d'erreur
        response_time = time.time() - start_time
        _record_response_time(response_time)
        
        logger.error(f"Erreur lors de la création de la facture: {str(e)} [{response_time:.3f}s]")
        raise

async def pay_invoice(bolt11: str, fee_limit_msat: Optional[int] = None) -> PaymentResult:
    """
    Paie une facture Lightning directement avec la clé admin
    
    Args:
        bolt11: Chaîne BOLT11 à payer
        fee_limit_msat: Limite de frais en millsatoshis (optionnel)
    
    Returns:
        PaymentResult avec les détails du paiement
    """
    start_time = time.time()
    
    try:
        # Récupération de la clé admin
        admin_key = get_admin_key()
        if not admin_key:
            raise ValueError("Aucune clé admin configurée")
        
        # Récupération du wallet correspondant à la clé
        wallet = await _get_wallet_for_key(admin_key, emit_fall_back=False)
        if not wallet:
            raise ValueError("Impossible de trouver le wallet pour la clé admin")
        
        # Paiement de la facture
        payment_hash, checking_id, fee_msat, preimage = await _pay_invoice(
            wallet_id=wallet.id,
            bolt11=bolt11,
            fee_limit_msat=fee_limit_msat
        )
        
        result = PaymentResult(
            success=True,
            payment_hash=payment_hash,
            fee_sat=fee_msat // 1000,
            preimage=preimage
        )
        
        # Mesure du temps de réponse
        response_time = time.time() - start_time
        _record_response_time(response_time)
        logger.debug(f"Paiement effectué en {response_time:.3f}s: {payment_hash}")
        
        return result
    
    except Exception as e:
        # Mesure du temps de réponse même en cas d'erreur
        response_time = time.time() - start_time
        _record_response_time(response_time)
        
        logger.error(f"Erreur lors du paiement de la facture: {str(e)} [{response_time:.3f}s]")
        return PaymentResult(success=False, error=str(e))

async def get_wallet_balance() -> int:
    """
    Récupère le solde du wallet en satoshis
    
    Returns:
        Solde en satoshis
    """
    start_time = time.time()
    
    try:
        # Récupération de la clé admin
        admin_key = get_admin_key()
        if not admin_key:
            invoice_key = get_invoice_key()
            if not invoice_key:
                raise ValueError("Aucune clé configurée")
            key = invoice_key
        else:
            key = admin_key
        
        # Récupération du wallet
        wallet = await _get_wallet_for_key(key, emit_fall_back=False)
        if not wallet:
            raise ValueError("Impossible de trouver le wallet")
        
        # Le solde est en millsatoshis dans LNbits
        balance_sat = wallet.balance_msat // 1000
        
        # Mesure du temps de réponse
        response_time = time.time() - start_time
        _record_response_time(response_time)
        
        return balance_sat
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du solde: {str(e)}")
        raise

async def check_payment_status(payment_hash: str) -> bool:
    """
    Vérifie si une facture a été payée
    
    Args:
        payment_hash: Hash du paiement à vérifier
    
    Returns:
        True si la facture a été payée, False sinon
    """
    try:
        payment = await _get_payment(payment_hash)
        return payment.paid if payment else False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut du paiement: {str(e)}")
        return False

async def get_recent_payments(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Récupère les paiements récents
    
    Args:
        limit: Nombre maximum de paiements à récupérer
    
    Returns:
        Liste des paiements récents
    """
    try:
        # Récupération de la clé admin
        admin_key = get_admin_key()
        if not admin_key:
            raise ValueError("Aucune clé admin configurée")
        
        # Récupération du wallet
        wallet = await _get_wallet_for_key(admin_key, emit_fall_back=False)
        if not wallet:
            raise ValueError("Impossible de trouver le wallet")
        
        # Récupération des paiements
        payments = await _get_payments(wallet_id=wallet.id, limit=limit)
        
        return [
            {
                "payment_hash": payment.payment_hash,
                "bolt11": payment.bolt11,
                "amount": payment.amount,
                "fee": payment.fee,
                "memo": payment.memo,
                "time": payment.time.isoformat() if payment.time else None,
                "paid": payment.paid,
                "preimage": payment.preimage
            }
            for payment in payments
        ]
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paiements: {str(e)}")
        return []

def get_performance_metrics() -> Dict[str, Any]:
    """
    Récupère des métriques de performance sur les opérations LNbits
    
    Returns:
        Dictionnaire avec les métriques de performance
    """
    if not _response_times:
        return {"error": "Aucune donnée de performance disponible"}
    
    import statistics
    
    try:
        metrics = {
            "count": len(_response_times),
            "avg_response_time_ms": statistics.mean(_response_times) * 1000,
            "min_response_time_ms": min(_response_times) * 1000,
            "max_response_time_ms": max(_response_times) * 1000,
            "p95_response_time_ms": sorted(_response_times)[int(len(_response_times) * 0.95)] * 1000 if len(_response_times) >= 20 else None,
            "db_stats": get_db_stats(),
        }
        return metrics
    except Exception as e:
        logger.error(f"Erreur lors du calcul des métriques de performance: {str(e)}")
        return {"error": str(e)}

def _record_response_time(time_seconds: float) -> None:
    """Enregistre un temps de réponse pour les métriques de performance"""
    _response_times.append(time_seconds)
    
    # Garde uniquement les dernières mesures
    if len(_response_times) > _max_response_times:
        _response_times.pop(0) 