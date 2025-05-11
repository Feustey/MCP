"""
Wrapper simplifié pour l'utilisation du client LNbits.
Ce module fournit une interface simplifiée pour interagir avec LNbits,
que ce soit en mode interne ou externe.
"""

import os
import logging
from typing import Optional, Dict, Any, List

from src.unified_clients.lnbits_client import LNBitsClient
from src.unified_clients.lnbits_base_client import LNBitsError, LNBitsErrorType
from lnbits_internal.settings_wrapper import USE_INTERNAL_LNBITS

logger = logging.getLogger(__name__)

# Chargement des variables d'environnement depuis config.py
from config import LNBITS_URL, LNBITS_ADMIN_KEY, LNBITS_INVOICE_KEY

class LNBitsWrapper:
    """Wrapper simplifié pour l'API LNbits avec gestion intégrée des modes interne/externe"""
    
    _instance = None
    _client = None
    
    @classmethod
    def get_client(cls) -> LNBitsClient:
        """
        Retourne une instance singleton du client LNbits.
        """
        if cls._client is None:
            cls._client = LNBitsClient(
                url=LNBITS_URL,
                admin_key=LNBITS_ADMIN_KEY,
                invoice_key=LNBITS_INVOICE_KEY
            )
            logger.info(f"Client LNbits initialisé en mode {'interne' if cls._client.is_internal_mode() else 'externe'}")
        return cls._client
    
    @classmethod
    async def create_invoice(cls, amount: int, memo: str = "") -> Dict[str, str]:
        """
        Crée une facture Lightning (invoice).
        
        Args:
            amount: Montant en satoshis
            memo: Description de la facture
            
        Returns:
            Dict avec payment_hash, payment_request et checking_id
        """
        client = cls.get_client()
        try:
            invoice = await client.create_invoice(amount=amount, memo=memo)
            return {
                "payment_hash": invoice.payment_hash,
                "payment_request": invoice.payment_request,
                "checking_id": invoice.checking_id
            }
        except LNBitsError as e:
            logger.error(f"Erreur lors de la création de la facture: {e}")
            raise
    
    @classmethod
    async def pay_invoice(cls, bolt11: str, fee_limit_msat: Optional[int] = None) -> Dict[str, Any]:
        """
        Paie une facture Lightning (BOLT11).
        
        Args:
            bolt11: Chaîne BOLT11 à payer
            fee_limit_msat: Limite de frais en millsatoshis (optionnel)
            
        Returns:
            Dict avec les détails du paiement et success=True/False
        """
        client = cls.get_client()
        try:
            payment = await client.pay_invoice(bolt11, fee_limit_msat)
            return {
                "success": payment.success,
                "payment_hash": payment.payment_hash,
                "fee": payment.fee,
                "preimage": payment.preimage,
                "error": payment.error_message
            }
        except LNBitsError as e:
            logger.error(f"Erreur lors du paiement de la facture: {e}")
            return {
                "success": False,
                "error": str(e),
                "payment_hash": "",
                "fee": 0
            }
    
    @classmethod
    async def get_wallet_balance(cls) -> int:
        """
        Récupère le solde du wallet en satoshis.
        
        Returns:
            Solde en satoshis
        """
        client = cls.get_client()
        try:
            return await client.get_balance()
        except LNBitsError as e:
            logger.error(f"Erreur lors de la récupération du solde: {e}")
            raise
    
    @classmethod
    async def get_node_channels(cls, node_pubkey: str) -> List[Dict[str, Any]]:
        """
        Récupère les canaux d'un nœud spécifique.
        
        Args:
            node_pubkey: Clé publique du nœud
            
        Returns:
            Liste des canaux du nœud
        """
        client = cls.get_client()
        try:
            return await client.get_node_channels(node_pubkey)
        except LNBitsError as e:
            logger.error(f"Erreur lors de la récupération des canaux: {e}")
            return []
    
    @classmethod
    def is_internal_mode(cls) -> bool:
        """
        Vérifie si le client utilise le mode interne ou externe.
        
        Returns:
            True si mode interne, False si mode externe
        """
        client = cls.get_client()
        return client.is_internal_mode() 