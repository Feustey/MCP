#!/usr/bin/env python3
"""
Script pour configurer LNbits avec un nœud Umbrel local
"""

import os
import sys
import argparse
import requests
import json
import subprocess
import base64
from pathlib import Path
from dotenv import load_dotenv

def base64_to_hex(base64_str: str) -> str:
    """Convertit une chaîne base64 en hexadécimal"""
    try:
        # Remplacer les caractères URL-safe par les caractères base64 standard
        base64_standard = base64_str.replace('-', '+').replace('_', '/')
        # Ajouter le padding si nécessaire
        padding = 4 - (len(base64_standard) % 4)
        if padding != 4:
            base64_standard += '=' * padding
        
        # Décoder le base64 en bytes
        decoded = base64.b64decode(base64_standard)
        # Convertir les bytes en hexadécimal
        return decoded.hex()
    except Exception as e:
        print(f"Erreur lors de la conversion base64 vers hex: {str(e)}")
        return None

def extract_macaroon_from_lndconnect(lndconnect: str) -> str:
    """Extrait le macaroon de l'URL lndconnect"""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(lndconnect)
        query = parse_qs(parsed.query)
        if 'macaroon' in query:
            # Convertir le macaroon base64 en hexadécimal
            macaroon_base64 = query['macaroon'][0]
            macaroon_hex = base64_to_hex(macaroon_base64)
            if macaroon_hex:
                return macaroon_hex
    except Exception as e:
        print(f"Erreur lors de l'extraction du macaroon: {str(e)}")
    return None

def load_sensitive_data():
    """Charge les données sensibles depuis le fichier .env"""
    load_dotenv()
    
    lndconnect = os.getenv("LNDCONNECT")
    
    if not lndconnect:
        print("Erreur: LNDCONNECT manquant dans le fichier .env")
        return None, None
    
    # Extraire le macaroon de l'URL lndconnect
    macaroon = extract_macaroon_from_lndconnect(lndconnect)
    if not macaroon:
        print("Erreur: Impossible d'extraire le macaroon de l'URL lndconnect")
        return None, None
    
    print(f"Macaroon extrait: {macaroon[:30]}...")
    return macaroon, lndconnect

def format_macaroon(macaroon: str) -> str:
    """Formate le macaroon pour l'API LND"""
    # Si le macaroon est déjà en hexadécimal, le retourner tel quel
    if all(c in '0123456789abcdefABCDEF' for c in macaroon):
        return macaroon
    
    # Essayer différents décodages
    try:
        # Essayer de décoder en base64 standard
        macaroon_bytes = base64.b64decode(macaroon)
        return macaroon_bytes.hex()
    except:
        try:
            # Essayer de décoder en base64 URL-safe
            macaroon_bytes = base64.urlsafe_b64decode(macaroon)
            return macaroon_bytes.hex()
        except:
            try:
                # Essayer de décoder directement de l'UTF-8
                return macaroon.encode('utf-8').hex()
            except:
                # Si rien ne fonctionne, retourner le macaroon tel quel
                return macaroon

def test_umbrel_connection(umbrel_url: str, macaroon: str):
    """Teste la connexion au nœud Umbrel et vérifie les services"""
    print(f"\nTest de connexion à Umbrel ({umbrel_url})...")
    
    # Configuration des headers avec le macaroon brut
    headers = {
        "Grpc-Metadata-macaroon": macaroon
    }
    
    # Liste des endpoints à tester (API REST LND)
    endpoints = {
        "GetInfo": "/v1/getinfo",
        "ListChannels": "/v1/channels",
        "WalletBalance": "/v1/balance/blockchain",
        "ListPeers": "/v1/peers",
        "NetworkInfo": "/v1/graph/info"
    }
    
    results = {}
    
    for name, endpoint in endpoints.items():
        try:
            print(f"\nTest de {name}...")
            response = requests.get(
                f"{umbrel_url}{endpoint}",
                headers=headers,
                timeout=10,
                verify=False  # Désactive la vérification SSL pour le domaine local
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {name}: OK")
                print(f"  Détails: {json.dumps(data, indent=2)}")
                results[name] = True
            else:
                print(f"✗ {name}: Erreur {response.status_code}")
                print(f"  Message: {response.text}")
                results[name] = False
                
        except requests.exceptions.Timeout:
            print(f"✗ {name}: Timeout")
            results[name] = False
        except requests.exceptions.ConnectionError:
            print(f"✗ {name}: Erreur de connexion")
            results[name] = False
        except Exception as e:
            print(f"✗ {name}: Erreur inattendue - {str(e)}")
            results[name] = False
    
    # Résumé des tests
    print("\nRésumé des tests:")
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    print(f"Tests réussis: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("✓ Tous les tests ont réussi!")
        return True
    else:
        print("⚠ Certains tests ont échoué. Vérifiez les détails ci-dessus.")
        return False

def install_lnbits():
    """Installe LNbits localement"""
    print("\nInstallation de LNbits...")
    
    # Vérifier si git est installé
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Erreur: git n'est pas installé. Veuillez installer git d'abord.")
        return False
    
    # Cloner le dépôt LNbits
    try:
        subprocess.run(["git", "clone", "https://github.com/lnbits/lnbits.git"], check=True)
        print("✓ Dépôt LNbits cloné avec succès")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du clonage du dépôt: {str(e)}")
        return False
    
    # Installer les dépendances
    try:
        os.chdir("lnbits")
        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
        print("✓ Dépendances installées avec succès")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'installation des dépendances: {str(e)}")
        return False
    
    return True

def setup_lnbits_umbrel(umbrel_url: str, macaroon: str, lndconnect: str, lnbits_url: str = None):
    """Configure LNbits avec un nœud Umbrel local"""
    
    # Tester la connexion à Umbrel
    if not test_umbrel_connection(umbrel_url, macaroon):
        print("\n⚠ La connexion à Umbrel présente des problèmes.")
        choice = input("Voulez-vous continuer malgré tout? (o/n): ").strip().lower()
        if choice != 'o':
            return False
    
    # Configuration de LNbits
    if not lnbits_url:
        lnbits_url = "http://localhost:5000"
    
    # Créer le fichier de configuration
    config = {
        "LNBITS_URL": lnbits_url,
        "LNBITS_API_KEY": "",  # Sera rempli après la création du wallet
        "USE_LNBITS": "true",
        "UMBREL_URL": umbrel_url,
        "LND_RPC_URL": f"{umbrel_url}:8080",  # Port 8080 pour l'API LND
        "LND_MACAROON": macaroon,
        "LNDCONNECT": lndconnect,
        "LND_CERT_PATH": ""  # Optionnel si vous utilisez un certificat
    }
    
    # Créer le fichier .env dans le dossier lnbits
    env_path = Path("lnbits/.env")
    with open(env_path, "w") as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print(f"\nConfiguration sauvegardée dans {env_path}")
    print("\nInstructions pour démarrer LNbits:")
    print("1. Assurez-vous d'être dans le dossier lnbits:")
    print("   cd lnbits")
    print("\n2. Démarrez le serveur LNbits:")
    print("   uvicorn lnbits.app:app --host 0.0.0.0 --port 5000 --reload")
    print("\n3. Accédez à LNbits dans votre navigateur:")
    print(f"   {lnbits_url}")
    print("\n4. Créez un nouveau wallet dans l'interface web")
    print("5. Copiez la clé API générée et mettez-la à jour dans le fichier .env")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Configuration de LNbits avec Umbrel")
    parser.add_argument(
        "--umbrel-url",
        default="https://umbrel.local:8080",
        help="URL de votre nœud Umbrel (défaut: https://umbrel.local:8080)"
    )
    parser.add_argument(
        "--lnbits-url",
        help="URL de votre instance LNbits (optionnel)"
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Ne pas installer LNbits (utiliser une installation existante)"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Tester uniquement la connexion à Umbrel sans installer LNbits"
    )
    
    args = parser.parse_args()
    
    try:
        # Charger les données sensibles
        macaroon, lndconnect = load_sensitive_data()
        if not macaroon or not lndconnect:
            sys.exit(1)
        
        # Tester la connexion à Umbrel
        if not test_umbrel_connection(args.umbrel_url, macaroon):
            if args.test_only:
                sys.exit(1)
            choice = input("\nVoulez-vous continuer malgré tout? (o/n): ").strip().lower()
            if choice != 'o':
                sys.exit(1)
        
        if args.test_only:
            print("\nTest terminé.")
            sys.exit(0)
        
        # Installer LNbits si nécessaire
        if not args.skip_install:
            if not install_lnbits():
                sys.exit(1)
        
        # Configurer LNbits avec Umbrel
        success = setup_lnbits_umbrel(args.umbrel_url, macaroon, lndconnect, args.lnbits_url)
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"Erreur lors de la configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 