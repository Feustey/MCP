import logging
from fastapi import FastAPI
from typing import Optional

# Import des composants originaux
from .core.services import create_invoice, pay_invoice
from .decorators import (
    check_admin,
    check_super_user,
    check_user_exists,
    require_admin_key,
    require_invoice_key,
)
from .exceptions import InvoiceError, PaymentError

# Import des composants pour l'intégration
from .settings_wrapper import setup_lnbits_environment, init_lnbits_db, disable_background_tasks

# Configuration du logging
logger = logging.getLogger("lnbits_internal")

# Création de l'application FastAPI
core_app = None

def initialize_lnbits() -> Optional[FastAPI]:
    """
    Initialise l'application LNbits et retourne l'instance FastAPI.
    
    Returns:
        L'application FastAPI LNbits si l'initialisation réussit, sinon None
    """
    global core_app
    
    try:
        # Configuration de l'environnement
        setup_lnbits_environment()
        
        # Initialisation de la base de données
        if not init_lnbits_db():
            logger.error("Échec de l'initialisation de la base de données LNbits")
            return None
        
        # Import tardif pour éviter les imports circulaires
        from .app import app as lnbits_app
        
        # Désactivation de tous les événements lifespan pour éviter les tâches de fond
        if hasattr(lnbits_app, "router") and hasattr(lnbits_app.router, "lifespan_context"):
            lnbits_app.router.lifespan_context = None
        
        # Configuration de l'application
        # Supprimer les middlewares et UI inutiles
        stripped_app = FastAPI(
            title="MCP LNbits Internal API",
            description="API LNbits intégrée pour MCP",
            version="0.1.0"
        )
        
        # Ne conserver que les routes API essentielles - filtrer strictement
        for route in lnbits_app.routes:
            if hasattr(route, "path") and route.path.startswith("/api/v1/"):
                # Filtrage additionnel: supprimer les endpoints non essentiels
                endpoint = route.path.split("/api/v1/")[1] if "/api/v1/" in route.path else ""
                
                # Liste des endpoints essentiels à conserver
                essential_endpoints = [
                    "payments",         # Création/gestion des factures
                    "wallet",           # Informations wallet
                    "payments/decode",  # Décodage des factures
                    "payments/bolt11",  # Paiement des factures
                    "channels"          # Gestion des canaux
                ]
                
                if any(endpoint.startswith(ep) for ep in essential_endpoints):
                    stripped_app.routes.append(route)
                    logger.debug(f"Conservé endpoint: {route.path}")
                else:
                    logger.debug(f"Filtré endpoint non essentiel: {route.path}")
        
        core_app = stripped_app
        
        # Désactiver explicitement toutes les tâches de fond restantes
        disable_background_tasks()
        
        # Logging des routes disponibles
        route_count = len(core_app.routes)
        logger.info(f"Application LNbits interne initialisée avec succès ({route_count} endpoints API)")
        
        return core_app
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de LNbits: {e}")
        return None

# Exposer les services directement - pas de wrapper inutile
async def direct_create_invoice(wallet_id: str, amount: int, memo: str = "", expiry: int = 3600) -> dict:
    """
    Crée une facture Lightning (invoice) directement, sans passer par un wrapper.
    
    Args:
        wallet_id: ID du wallet
        amount: Montant en satoshis
        memo: Description de la facture
        expiry: Durée de validité en secondes
        
    Returns:
        Dict avec payment_hash, payment_request et checking_id
    """
    payment_hash, payment_request = await create_invoice(
        wallet_id=wallet_id,
        amount=amount,
        memo=memo,
        expiry=expiry
    )
    
    return {
        "payment_hash": payment_hash,
        "payment_request": payment_request,
        "checking_id": payment_hash
    }

async def direct_pay_invoice(wallet_id: str, bolt11: str, fee_limit_msat: Optional[int] = None) -> dict:
    """
    Paie une facture Lightning (BOLT11) directement, sans passer par un wrapper.
    
    Args:
        wallet_id: ID du wallet
        bolt11: Chaîne BOLT11 à payer
        fee_limit_msat: Limite de frais en millsatoshis
        
    Returns:
        Dict avec les détails du paiement
    """
    try:
        payment_hash, checking_id, fee_msat, preimage = await pay_invoice(
            wallet_id=wallet_id,
            bolt11=bolt11,
            fee_limit_msat=fee_limit_msat
        )
        
        return {
            "success": True,
            "payment_hash": payment_hash,
            "checking_id": checking_id,
            "fee": fee_msat // 1000,
            "preimage": preimage
        }
    except Exception as e:
        logger.error(f"Erreur lors du paiement de la facture: {e}")
        return {
            "success": False,
            "error": str(e),
            "payment_hash": "",
            "fee": 0
        }

__all__ = [
    # decorators
    "require_admin_key",
    "require_invoice_key",
    "check_admin",
    "check_super_user",
    "check_user_exists",
    # services
    "pay_invoice",
    "create_invoice",
    # exceptions
    "PaymentError",
    "InvoiceError",
    # integration
    "core_app",
    "initialize_lnbits",
    # direct services - pas de wrapper
    "direct_create_invoice",
    "direct_pay_invoice"
]

# Initialiser LNbits automatiquement lors de l'import
initialize_lnbits()
