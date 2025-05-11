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

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

async def topup_wallet(amount=10000):
    """
    Approvisionne le wallet LNBits avec des sats testnet.
    En testnet, LNBits permet d'approvisionner artificiellement le wallet.
    Args:
        amount: Montant en sats à ajouter au wallet (défaut: 10000 sats)
    """
    url = os.getenv("LNBITS_URL", "http://192.168.0.45:5000")
    admin_key = os.getenv("LNBITS_ADMIN_KEY", "fddac5fb8bf64eec944c89255b98dac4")
    
    headers = {
        "X-Api-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    # Vérifier si nous sommes en testnet
    network = os.getenv("LNBITS_NETWORK", "")
    if network.lower() != "testnet":
        logger.warning("ATTENTION: Il semble que LNBits ne soit pas configuré en testnet.")
        logger.warning("Ajoutez LNBITS_NETWORK=testnet dans .env pour éviter d'utiliser des sats réels.")
        confirm = input("Êtes-vous sûr de vouloir continuer ? (oui/non) ")
        if confirm.lower() not in ["oui", "o", "yes", "y"]:
            logger.info("Opération annulée.")
            return False
    
    # Obtenir l'ID du wallet
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            # Obtenir les informations du wallet
            response = await client.get(f"{url}/api/v1/wallet", headers=headers)
            response.raise_for_status()
            wallet_info = response.json()
            wallet_id = wallet_info.get("id")
            
            logger.info(f"ID du wallet: {wallet_id}")
            logger.info(f"Solde actuel: {wallet_info.get('balance', 0)} sats")
            
            # Topup via l'endpoint admin (fonctionne uniquement en testnet)
            payload = {
                "id": wallet_id,
                "amount": amount
            }
            try:
                # Tentative de topup direct (testnet LNbits)
                response = await client.put(f"{url}/admin/api/v1/topup/", headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Wallet approvisionné avec {amount} sats!")
                logger.info(f"Résultat: {result}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.error("Endpoint /admin/api/v1/topup/ non disponible. Création de factures à payer via un faucet testnet...")
                    # Générer plusieurs factures si nécessaire
                    max_invoice = 10_000_000
                    remaining = amount
                    invoice_num = 1
                    while remaining > 0:
                        invoice_amount = min(remaining, max_invoice)
                        invoice_payload = {
                            "out": False,
                            "amount": invoice_amount,
                            "memo": f"Topup testnet {invoice_amount} sats (partie {invoice_num})"
                        }
                        try:
                            invoice_resp = await client.post(f"{url}/api/v1/payments", headers=headers, json=invoice_payload)
                            invoice_resp.raise_for_status()
                            invoice_data = invoice_resp.json()
                            bolt11 = invoice_data.get("payment_request")
                            logger.info(f"Facture BOLT11 générée (partie {invoice_num}) : {bolt11}")
                            print(f"\nVeuillez payer cette facture sur un faucet testnet pour créditer le wallet (partie {invoice_num}) :\n{bolt11}\n")
                        except Exception as inv_e:
                            logger.error(f"Erreur lors de la création de la facture (partie {invoice_num}): {inv_e}")
                            break
                        remaining -= invoice_amount
                        invoice_num += 1
                    return False
                else:
                    logger.error(f"Erreur HTTP {e.response.status_code}: {e.response.text}")
                    return False
            
            # Vérifier le nouveau solde
            response = await client.get(f"{url}/api/v1/wallet", headers=headers)
            response.raise_for_status()
            updated_wallet = response.json()
            
            logger.info(f"Nouveau solde: {updated_wallet.get('balance', 0)} sats")
            return True
            
    except httpx.RequestError as e:
        logger.error(f"Erreur de requête: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return False

if __name__ == "__main__":
    # Si des arguments sont fournis, utiliser le premier comme montant
    import sys
    amount = 10000  # Par défaut
    if len(sys.argv) > 1:
        try:
            amount = int(sys.argv[1])
        except ValueError:
            logger.error(f"Le montant doit être un nombre entier. Utilisation de la valeur par défaut: {amount} sats.")
    
    asyncio.run(topup_wallet(amount)) 