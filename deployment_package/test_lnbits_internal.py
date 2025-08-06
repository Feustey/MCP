#!/usr/bin/env python3
"""
Script de test pour la fonctionnalité LNbits intégré.
Ce script vérifie que le module LNbits interne est correctement configuré et fonctionnel.
"""

import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_lnbits_internal")

# Ajoute le répertoire racine au path pour les imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Chargement de l'environnement
load_dotenv(os.path.join(ROOT_DIR, '.env'))

async def test_lnbits_internal():
    """
    Teste les fonctionnalités de base du module LNbits interne.
    """
    from lnbits_internal.settings_wrapper import USE_INTERNAL_LNBITS
    from lnbits_internal import core_app
    from src.lnbits_wrapper import LNBitsWrapper

    # Vérification du mode
    logger.info(f"Mode LNbits: {'INTERNE' if USE_INTERNAL_LNBITS else 'EXTERNE'}")
    logger.info(f"Application LNbits disponible: {'OUI' if core_app else 'NON'}")

    # Vérification du client
    client = LNBitsWrapper.get_client()
    logger.info(f"Client utilise le mode interne: {'OUI' if client.is_internal_mode() else 'NON'}")

    # Test du solde
    try:
        balance = await LNBitsWrapper.get_wallet_balance()
        logger.info(f"Solde actuel: {balance} sats")
    except Exception as e:
        logger.error(f"Échec de la récupération du solde: {e}")

    # Test de création de facture
    try:
        invoice = await LNBitsWrapper.create_invoice(amount=1000, memo="Test facture LNbits interne")
        logger.info(f"Facture créée avec succès:")
        logger.info(f"- Hash: {invoice['payment_hash']}")
        logger.info(f"- Bolt11: {invoice['payment_request'][:30]}...")
    except Exception as e:
        logger.error(f"Échec de la création de facture: {e}")

    # Liste des endpoints API disponibles
    if core_app:
        logger.info("\nEndpoints API LNbits disponibles:")
        for route in core_app.routes:
            if hasattr(route, "path"):
                logger.info(f"- {route.path} [{', '.join(route.methods)}]")

if __name__ == "__main__":
    try:
        asyncio.run(test_lnbits_internal())
    except KeyboardInterrupt:
        logger.info("Test interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur lors du test LNbits interne: {e}")
        sys.exit(1) 