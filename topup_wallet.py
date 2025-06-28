#!/usr/bin/env python3
"""
Script pour approvisionner un wallet LNBits en testnet.
"""

import asyncio
import httpx
from dotenv import load_dotenv
import os
import logging
import json
import sys
from typing import Optional, Tuple
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

class WalletTopupError(Exception):
    """Exception personnalisée pour les erreurs de topup."""
    pass

class WalletTopupManager:
    """Gestionnaire pour l'approvisionnement de wallet LNBits."""
    
    def __init__(self):
        self.url = os.getenv("LNBITS_URL", "http://192.168.0.45:5000").rstrip("/")
        self.admin_key = os.getenv("LNBITS_ADMIN_KEY")
        self.network = os.getenv("LNBITS_NETWORK", "").lower()
        
        # Validation des variables d'environnement
        if not self.admin_key:
            raise WalletTopupError("LNBITS_ADMIN_KEY non définie dans les variables d'environnement")
        
        # Configuration SSL selon l'environnement
        self.verify_ssl = os.getenv("LNBITS_VERIFY_SSL", "true").lower() == "true"
        
        self.headers = {
            "X-Api-Key": self.admin_key,
            "Content-Type": "application/json"
        }
    
    def validate_amount(self, amount: int) -> bool:
        """
        Valide le montant d'approvisionnement.
        
        Args:
            amount: Montant en sats
            
        Returns:
            True si le montant est valide
            
        Raises:
            WalletTopupError: Si le montant est invalide
        """
        if amount <= 0:
            raise WalletTopupError("Le montant doit être positif")
        
        if amount > 100_000_000:  # 100M sats max
            raise WalletTopupError("Le montant maximum autorisé est 100,000,000 sats")
        
        return True
    
    def confirm_testnet_operation(self) -> bool:
        """
        Demande confirmation si on n'est pas en testnet.
        
        Returns:
            True si l'opération doit continuer
        """
        if self.network != "testnet":
            logger.warning("ATTENTION: LNBits ne semble pas configuré en testnet.")
            logger.warning("Ajoutez LNBITS_NETWORK=testnet dans .env pour éviter d'utiliser des sats réels.")
            
            confirm = input("Êtes-vous sûr de vouloir continuer ? (oui/non): ").strip().lower()
            return confirm in ["oui", "o", "yes", "y"]
        
        return True
    
    async def get_wallet_info(self, client: httpx.AsyncClient) -> dict:
        """
        Récupère les informations du wallet.
        
        Args:
            client: Client HTTP async
            
        Returns:
            Informations du wallet
            
        Raises:
            WalletTopupError: Si la récupération échoue
        """
        try:
            response = await client.get(f"{self.url}/api/v1/wallet", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
            raise WalletTopupError(f"Impossible de récupérer les informations du wallet: {e}")
        except httpx.RequestError as e:
            logger.error(f"Erreur de requête: {str(e)}")
            raise WalletTopupError(f"Erreur de connexion: {e}")
    
    async def topup_via_admin_endpoint(self, client: httpx.AsyncClient, wallet_id: str, amount: int) -> bool:
        """
        Tente l'approvisionnement via l'endpoint admin.
        
        Args:
            client: Client HTTP async
            wallet_id: ID du wallet
            amount: Montant à ajouter
            
        Returns:
            True si le topup a réussi
        """
        try:
            payload = {"id": wallet_id, "amount": amount}
            response = await client.put(f"{self.url}/admin/api/v1/topup/", headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Wallet approvisionné avec {amount} sats via endpoint admin!")
            logger.info(f"Résultat: {result}")
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Endpoint admin de topup non disponible")
                return False
            else:
                logger.error(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
                raise WalletTopupError(f"Erreur lors du topup admin: {e}")
    
    async def generate_testnet_invoices(self, client: httpx.AsyncClient, amount: int) -> bool:
        """
        Génère des factures testnet pour approvisionnement manuel.
        
        Args:
            client: Client HTTP async
            amount: Montant total à générer
            
        Returns:
            True si les factures ont été générées
        """
        if self.network != "testnet":
            logger.error("Génération de factures testnet non autorisée en mode production")
            return False
        
        max_invoice = 10_000_000  # 10M sats max par facture
        remaining = amount
        invoice_num = 1
        
        logger.info(f"Génération de factures testnet pour {amount} sats...")
        
        try:
            while remaining > 0:
                invoice_amount = min(remaining, max_invoice)
                invoice_payload = {
                    "out": False,
                    "amount": invoice_amount,
                    "memo": f"Topup testnet {invoice_amount} sats (partie {invoice_num})"
                }
                
                response = await client.post(f"{self.url}/api/v1/payments", headers=self.headers, json=invoice_payload)
                response.raise_for_status()
                invoice_data = response.json()
                bolt11 = invoice_data.get("payment_request")
                
                if bolt11:
                    logger.info(f"Facture BOLT11 générée (partie {invoice_num}): {bolt11}")
                    print(f"\nVeuillez payer cette facture sur un faucet testnet (partie {invoice_num}):\n{bolt11}\n")
                else:
                    logger.error(f"Facture invalide générée pour la partie {invoice_num}")
                    return False
                
                remaining -= invoice_amount
                invoice_num += 1
            
            logger.info("Toutes les factures ont été générées. Payez-les pour créditer le wallet.")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP lors de la génération de facture: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la génération de factures: {e}")
            return False
    
    async def topup_wallet(self, amount: int) -> bool:
        """
        Approvisionne le wallet LNBits avec des sats.
        
        Args:
            amount: Montant en sats à ajouter au wallet
            
        Returns:
            True si l'opération a réussi
        """
        # Validation du montant
        self.validate_amount(amount)
        
        # Confirmation si nécessaire
        if not self.confirm_testnet_operation():
            logger.info("Opération annulée par l'utilisateur.")
            return False
        
        # Configuration du client HTTP
        timeout = httpx.Timeout(30.0, connect=10.0)
        
        try:
            async with httpx.AsyncClient(timeout=timeout, verify=self.verify_ssl) as client:
                # Obtenir les informations du wallet
                wallet_info = await self.get_wallet_info(client)
                wallet_id = wallet_info.get("id")
                current_balance = wallet_info.get("balance", 0)
                
                if not wallet_id:
                    raise WalletTopupError("ID du wallet non trouvé dans la réponse")
                
                logger.info(f"ID du wallet: {wallet_id}")
                logger.info(f"Solde actuel: {current_balance} sats")
                
                # Tentative de topup via endpoint admin
                if await self.topup_via_admin_endpoint(client, wallet_id, amount):
                    # Vérifier le nouveau solde
                    updated_wallet = await self.get_wallet_info(client)
                    new_balance = updated_wallet.get("balance", 0)
                    logger.info(f"Nouveau solde: {new_balance} sats")
                    logger.info(f"Différence: +{new_balance - current_balance} sats")
                    return True
                
                # Fallback vers génération de factures testnet
                logger.info("Tentative d'approvisionnement via factures testnet...")
                return await self.generate_testnet_invoices(client, amount)
                
        except WalletTopupError:
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            raise WalletTopupError(f"Erreur inattendue: {e}")

def main():
    """Fonction principale avec gestion d'erreurs robuste."""
    try:
        # Parsing des arguments
        amount = 10000  # Par défaut
        if len(sys.argv) > 1:
            try:
                amount = int(sys.argv[1])
            except ValueError:
                logger.error("Le montant doit être un nombre entier.")
                logger.info("Usage: python topup_wallet.py [montant_en_sats]")
                sys.exit(1)
        
        # Création et exécution du gestionnaire
        manager = WalletTopupManager()
        success = asyncio.run(manager.topup_wallet(amount))
        
        if success:
            logger.info("Opération terminée avec succès!")
            sys.exit(0)
        else:
            logger.warning("Opération terminée avec des avertissements.")
            sys.exit(0)
            
    except WalletTopupError as e:
        logger.error(f"Erreur de topup: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Opération interrompue par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 