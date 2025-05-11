"""
Client LNBits principal - Implémentation unifiée des fonctionnalités de base de LNBits.

Ce client fournit une interface standardisée pour les opérations principales de LNbits:
- Gestion des invoices
- Gestion du solde
- Paiement de factures
"""

import httpx
from typing import Dict, Any, Optional, List, Union
import logging
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel

# Import du mode interne/externe
from lnbits_internal.settings_wrapper import USE_INTERNAL_LNBITS

# Client de base et définitions d'erreurs
from src.unified_clients.lnbits_base_client import LNBitsBaseClient, LNBitsError, LNBitsErrorType

# Import direct des services internes si disponible
if USE_INTERNAL_LNBITS:
    try:
        from lnbits_internal.core.services import create_invoice as internal_create_invoice
        from lnbits_internal.core.services import pay_invoice as internal_pay_invoice
        HAS_INTERNAL_LNBITS = True
    except ImportError:
        logging.getLogger(__name__).warning("Impossible d'importer les services internes LNbits")
        HAS_INTERNAL_LNBITS = False
else:
    HAS_INTERNAL_LNBITS = False

logger = logging.getLogger(__name__)

class InvoiceResponse(BaseModel):
    """Modèle de réponse pour une facture créée"""
    payment_hash: str
    payment_request: str
    checking_id: str
    lnurl_response: Optional[Dict[str, Any]] = None

class PaymentResponse(BaseModel):
    """Modèle de réponse pour un paiement effectué"""
    payment_hash: str
    checking_id: str
    fee: int = 0
    preimage: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class WalletInfo(BaseModel):
    """Informations sur un wallet"""
    id: str
    name: str
    balance: int
    
class ChannelInfo(BaseModel):
    """Informations sur un canal"""
    id: str
    short_id: Optional[str] = None
    channel_point: Optional[str] = None
    remote_pubkey: str
    capacity: int
    local_balance: int
    remote_balance: int
    active: bool
    status: str
    fee_base_msat: Optional[int] = None
    fee_rate_ppm: Optional[int] = None

class LNBitsClient(LNBitsBaseClient):
    """Client principal pour interagir avec l'API LNBits"""
    
    def __init__(
        self,
        url: str,
        invoice_key: Optional[str] = None,
        admin_key: Optional[str] = None,
        timeout: float = 30.0,
        use_internal: Optional[bool] = None
    ):
        """
        Initialise le client LNbits.
        
        Args:
            url: URL de l'instance LNbits externe (ignoré si mode interne)
            invoice_key: Clé invoice pour l'API
            admin_key: Clé admin pour l'API
            timeout: Timeout pour les requêtes HTTP
            use_internal: Force l'utilisation du mode interne (True) ou externe (False)
                         Si None, utilise la configuration par défaut
        """
        # Détermination du mode en fonction des paramètres
        self.use_internal = use_internal if use_internal is not None else USE_INTERNAL_LNBITS and HAS_INTERNAL_LNBITS
        
        # Message de log selon le mode
        if self.use_internal:
            logger.info("Utilisation du mode LNbits interne")
        else:
            logger.info(f"Utilisation du mode LNbits externe avec URL: {url}")
            super().__init__(url, invoice_key, admin_key, timeout)
        
        # Stockage des clés pour le mode interne
        if self.use_internal:
            self.invoice_key = invoice_key
            self.admin_key = admin_key
    
    async def get_wallet_details(self) -> WalletInfo:
        """Récupère les détails du wallet"""
        if self.use_internal:
            try:
                # Utilisation de l'API interne
                from lnbits_internal.core.crud.wallets import get_wallet
                from lnbits_internal.core.crud.users import get_user
                
                # Récupération des informations du wallet et user
                wallet_id = self.admin_key or self.invoice_key
                wallet = await get_wallet(wallet_id)
                
                return WalletInfo(
                    id=wallet.id,
                    name=wallet.name,
                    balance=wallet.balance_msat // 1000
                )
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des détails du wallet (mode interne): {str(e)}")
                raise LNBitsError(
                    f"Échec de récupération des détails du wallet: {str(e)}",
                    error_type=LNBitsErrorType.REQUEST_ERROR
                )
        else:
            # Mode externe - utiliser l'API HTTP
            return await super().get_wallet_details()

    async def get_balance(self) -> int:
        """Récupère le solde du wallet en satoshis"""
        try:
            wallet = await self.get_wallet_details()
            return wallet.balance
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du solde: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération du solde: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def create_invoice(
        self, 
        amount: int, 
        memo: str = "", 
        expiry: int = 3600
    ) -> InvoiceResponse:
        """Crée une facture Lightning (invoice)
        
        Args:
            amount: Montant en satoshis
            memo: Description de la facture
            expiry: Durée de validité en secondes (défaut: 1 heure)
            
        Returns:
            InvoiceResponse: Réponse contenant les détails de la facture
        """
        if self.use_internal:
            try:
                # Utilisation de l'API interne
                wallet_id = self.invoice_key or self.admin_key
                
                # Appel direct à la fonction interne
                payment_hash, payment_request = await internal_create_invoice(
                    wallet_id=wallet_id,
                    amount=amount,
                    memo=memo,
                    expiry=expiry
                )
                
                return InvoiceResponse(
                    payment_hash=payment_hash,
                    payment_request=payment_request,
                    checking_id=payment_hash
                )
            except Exception as e:
                logger.error(f"Erreur lors de la création de la facture (mode interne): {str(e)}")
                raise LNBitsError(
                    f"Échec de création de la facture: {str(e)}",
                    error_type=LNBitsErrorType.REQUEST_ERROR
                )
        else:
            # Mode externe - utiliser l'API HTTP
            return await super().create_invoice(amount, memo, expiry)

    async def pay_invoice(self, bolt11: str, fee_limit_msat: Optional[int] = None) -> PaymentResponse:
        """Paie une facture Lightning (BOLT11)
        
        Args:
            bolt11: Chaîne BOLT11 à payer
            fee_limit_msat: Limite de frais en millsatoshis (optionnel)
            
        Returns:
            PaymentResponse: Réponse contenant les détails du paiement
        """
        if self.use_internal:
            try:
                # Utilisation de l'API interne
                wallet_id = self.admin_key  # Nécessite la clé admin
                
                # Appel direct à la fonction interne
                payment_hash, checking_id, fee_msat, preimage = await internal_pay_invoice(
                    wallet_id=wallet_id,
                    bolt11=bolt11,
                    fee_limit_msat=fee_limit_msat
                )
                
                return PaymentResponse(
                    payment_hash=payment_hash,
                    checking_id=checking_id,
                    fee=fee_msat // 1000,
                    preimage=preimage,
                    success=True
                )
            except Exception as e:
                logger.error(f"Erreur lors du paiement de la facture (mode interne): {str(e)}")
                return PaymentResponse(
                    payment_hash="",
                    checking_id="",
                    success=False,
                    error_message=str(e)
                )
        else:
            # Mode externe - utiliser l'API HTTP
            return await super().pay_invoice(bolt11, fee_limit_msat)

    async def check_invoice_status(self, payment_hash: str) -> bool:
        """Vérifie si une facture a été payée
        
        Args:
            payment_hash: Hash de paiement de la facture
            
        Returns:
            bool: True si la facture a été payée, False sinon
        """
        try:
            result = await self._execute_with_retry(
                method="get",
                endpoint=f"api/v1/payments/{payment_hash}",
                use_admin_key=False
            )
            
            # Vérifier si le paiement est réussi
            return result.get("paid", False)
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut de la facture: {str(e)}")
            return False

    async def get_payments(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Récupère l'historique des paiements
        
        Args:
            limit: Nombre maximum de paiements à récupérer
            offset: Index à partir duquel commencer
            
        Returns:
            List[Dict[str, Any]]: Liste des paiements
        """
        try:
            params = {"limit": limit, "offset": offset}
            
            result = await self._execute_with_retry(
                method="get",
                endpoint="api/v1/payments",
                use_admin_key=True,
                params=params
            )
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des paiements: {str(e)}")
            raise LNBitsError(
                f"Échec de récupération des paiements: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    async def decode_invoice(self, bolt11: str) -> Dict[str, Any]:
        """Décode une facture Lightning (BOLT11)
        
        Args:
            bolt11: Chaîne BOLT11 à décoder
            
        Returns:
            Dict[str, Any]: Informations décodées de la facture
        """
        try:
            data = {"data": bolt11}
            
            result = await self._execute_with_retry(
                method="post",
                endpoint="api/v1/payments/decode",
                use_admin_key=False,
                json_data=data
            )
            
            return result
        except Exception as e:
            logger.error(f"Erreur lors du décodage de la facture: {str(e)}")
            raise LNBitsError(
                f"Échec du décodage de la facture: {str(e)}",
                error_type=LNBitsErrorType.REQUEST_ERROR
            )

    # Méthode pour vérifier le mode courant
    def is_internal_mode(self) -> bool:
        """Retourne True si le client utilise le mode interne, sinon False"""
        return self.use_internal 