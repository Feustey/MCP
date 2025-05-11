"""
Exemple d'utilisation des clients LNBits unifiés.

Ce script montre comment utiliser les différents clients LNBits pour:
1. Vérifier le solde du wallet
2. Créer et payer des factures
3. Gérer les canaux et leurs politiques de frais
"""

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from src.unified_clients import (
    LNBitsClient,
    LNBitsChannelClient,
    ChannelPolicy,
    LNBitsError
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Récupérer les clés API depuis les variables d'environnement
LNBITS_URL = os.getenv("LNBITS_URL", "https://demo.lnbits.com")
INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
ADMIN_KEY = os.getenv("LNBITS_ADMIN_KEY")

async def demo_wallet_operations():
    """Démontre les opérations de base du wallet"""
    logger.info("=== Démo des opérations de wallet ===")
    
    # Créer le client principal
    client = LNBitsClient(
        url=LNBITS_URL,
        invoice_key=INVOICE_KEY,
        admin_key=ADMIN_KEY
    )
    
    try:
        # Vérifier la connexion
        if await client.check_connection():
            logger.info("✅ Connexion à LNBits établie")
        else:
            logger.error("❌ Impossible de se connecter à LNBits")
            return
        
        # Récupérer les informations du wallet
        wallet_info = await client.get_wallet_details()
        logger.info(f"📊 Informations du wallet: ID={wallet_info.id}, Nom={wallet_info.name}")
        logger.info(f"💰 Solde: {wallet_info.balance} sats")
        
        # Créer une facture
        invoice = await client.create_invoice(
            amount=100,
            memo="Test de l'API unifiée LNBits"
        )
        logger.info(f"🧾 Facture créée: {invoice.payment_request[:30]}...")
        logger.info(f"📝 Hash de paiement: {invoice.payment_hash}")
        
        # Vérifier le statut de la facture
        paid = await client.check_invoice_status(invoice.payment_hash)
        logger.info(f"💲 Statut de la facture: {'Payée' if paid else 'Non payée'}")
        
        # Récupérer l'historique des paiements
        payments = await client.get_payments(limit=5)
        logger.info(f"📜 Derniers paiements: {len(payments)} entrées")
        for payment in payments[:3]:  # Afficher les 3 premiers
            logger.info(f"  - {payment.get('amount')} sats, {payment.get('time')}")
    
    except LNBitsError as e:
        logger.error(f"❌ Erreur LNBits: {e}")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
    finally:
        await client.close()

async def demo_channel_operations():
    """Démontre les opérations sur les canaux"""
    logger.info("\n=== Démo des opérations sur les canaux ===")
    
    # Créer le client de gestion des canaux
    channel_client = LNBitsChannelClient(
        url=LNBITS_URL,
        admin_key=ADMIN_KEY
    )
    
    try:
        # Récupérer la liste des canaux
        channels = await channel_client.list_channels()
        logger.info(f"📊 Nombre total de canaux: {len(channels)}")
        
        # Afficher les canaux actifs
        active_channels = [c for c in channels if c.active]
        logger.info(f"✅ Canaux actifs: {len(active_channels)}/{len(channels)}")
        
        for channel in active_channels[:3]:  # Afficher les 3 premiers canaux actifs
            logger.info(f"  - Canal {channel.short_id or channel.id[:10]}")
            logger.info(f"    Capacité: {channel.capacity} sats")
            logger.info(f"    Balance locale: {channel.local_balance} sats")
            logger.info(f"    Balance distante: {channel.remote_balance} sats")
            logger.info(f"    Frais actuels: {channel.fee_base_msat} msat + {channel.fee_rate_ppm} ppm")
        
        # Récupérer les soldes globaux des canaux
        balances = await channel_client.get_channel_balances()
        logger.info(f"💰 Solde total des canaux: {balances['total_balance']} sats")
        
        # Récupérer l'historique de forwarding
        today = datetime.now().strftime("%Y-%m-%d")
        one_month_ago = datetime.now().replace(month=datetime.now().month-1).strftime("%Y-%m-%d")
        
        forwarding = await channel_client.get_forwarding_history(
            start_date=one_month_ago,
            end_date=today,
            limit=10
        )
        
        logger.info(f"🔄 Transactions de forwarding récentes: {len(forwarding)}")
        total_fees = sum(tx.get('fee', 0) for tx in forwarding)
        logger.info(f"💸 Frais totaux collectés: {total_fees} sats")
        
        # Exemple de mise à jour de politique de frais (commenté pour éviter les modifications accidentelles)
        """
        if active_channels:
            # Créer une nouvelle politique
            new_policy = ChannelPolicy(
                base_fee_msat=1000,  # 1 sat
                fee_rate_ppm=500,    # 0.05%
                min_htlc_msat=1000   # 1 sat
            )
            
            # Mettre à jour la politique d'un canal spécifique
            channel = active_channels[0]
            if channel.channel_point:
                success = await channel_client.update_channel_policy(
                    channel_point=channel.channel_point,
                    policy=new_policy
                )
                logger.info(f"🔄 Mise à jour de la politique: {'Réussie' if success else 'Échouée'}")
        """
    
    except LNBitsError as e:
        logger.error(f"❌ Erreur LNBits: {e}")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
    finally:
        await channel_client.close()

async def main():
    """Fonction principale"""
    logger.info("Démarrage de la démo des clients LNBits unifiés")
    
    # Exécuter les démos
    await demo_wallet_operations()
    await demo_channel_operations()
    
    logger.info("Démo terminée")

if __name__ == "__main__":
    asyncio.run(main()) 