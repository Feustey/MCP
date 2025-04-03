#!/usr/bin/env python3
"""
Script pour configurer LNbits avec le testnet Bitcoin
"""

import os
import sys
import argparse
import requests
import json
import time
from getpass import getpass

def setup_lnbits_testnet():
    """Configure LNbits avec le testnet Bitcoin"""
    print("Configuration de LNbits avec le testnet Bitcoin")
    print("=============================================")
    
    # Demander l'URL de LNbits
    lnbits_url = input("URL de LNbits (défaut: https://testnet.lnbits.com): ").strip()
    if not lnbits_url:
        lnbits_url = "https://testnet.lnbits.com"
    
    # Vérifier que l'URL est accessible
    try:
        response = requests.get(f"{lnbits_url}/api/v1/health")
        if response.status_code != 200:
            print(f"Erreur: Impossible de se connecter à {lnbits_url}")
            print(f"Code de statut: {response.status_code}")
            print(f"Réponse: {response.text}")
            return False
        print(f"Connexion à {lnbits_url} réussie!")
    except Exception as e:
        print(f"Erreur lors de la connexion à {lnbits_url}: {str(e)}")
        return False
    
    # Demander la clé API
    api_key = getpass("Clé API LNbits (laisser vide pour en créer une nouvelle): ").strip()
    
    if not api_key:
        # Créer un nouveau wallet et obtenir une clé API
        try:
            print("Création d'un nouveau wallet...")
            response = requests.post(
                f"{lnbits_url}/api/v1/wallet",
                json={"name": "Testnet Wallet", "admin": "admin"}
            )
            
            if response.status_code != 201:
                print(f"Erreur lors de la création du wallet: {response.text}")
                return False
            
            wallet_data = response.json()
            api_key = wallet_data.get("admin", wallet_data.get("api_key"))
            
            if not api_key:
                print("Erreur: Impossible d'obtenir la clé API")
                return False
            
            print(f"Wallet créé avec succès!")
            print(f"Clé API: {api_key}")
            print("IMPORTANT: Conservez cette clé API en lieu sûr!")
        except Exception as e:
            print(f"Erreur lors de la création du wallet: {str(e)}")
            return False
    else:
        # Vérifier que la clé API est valide
        try:
            response = requests.get(
                f"{lnbits_url}/api/v1/wallet",
                headers={"X-Api-Key": api_key}
            )
            
            if response.status_code != 200:
                print(f"Erreur: La clé API n'est pas valide")
                print(f"Code de statut: {response.status_code}")
                print(f"Réponse: {response.text}")
                return False
            
            print("Clé API validée avec succès!")
        except Exception as e:
            print(f"Erreur lors de la validation de la clé API: {str(e)}")
            return False
    
    # Obtenir des informations sur le wallet
    try:
        response = requests.get(
            f"{lnbits_url}/api/v1/wallet",
            headers={"X-Api-Key": api_key}
        )
        
        if response.status_code != 200:
            print(f"Erreur lors de la récupération des informations du wallet: {response.text}")
            return False
        
        wallet_info = response.json()
        print("\nInformations du wallet:")
        print(f"ID: {wallet_info.get('id')}")
        print(f"Nom: {wallet_info.get('name')}")
        print(f"Balance: {wallet_info.get('balance')} sats")
    except Exception as e:
        print(f"Erreur lors de la récupération des informations du wallet: {str(e)}")
        return False
    
    # Créer un fichier .env pour stocker les informations
    env_content = f"""# Configuration LNbits pour le testnet
LNBITS_URL={lnbits_url}
LNBITS_API_KEY={api_key}
USE_LNBITS=true
"""
    
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        print("\nFichier .env créé avec succès!")
    except Exception as e:
        print(f"Erreur lors de la création du fichier .env: {str(e)}")
        return False
    
    print("\nConfiguration terminée avec succès!")
    print("Vous pouvez maintenant utiliser LNbits avec le testnet Bitcoin.")
    print("Pour tester, exécutez: python -m src.api.main")
    
    return True

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Configure LNbits avec le testnet Bitcoin")
    args = parser.parse_args()
    
    success = setup_lnbits_testnet()
    
    if not success:
        print("\nLa configuration a échoué.")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main() 