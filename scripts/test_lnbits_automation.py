#!/usr/bin/env python3
"""
Script pour tester les automatisations avec LNbits sur le testnet
"""

import os
import sys
import argparse
import asyncio
import json
from dotenv import load_dotenv
from src.automation_manager import AutomationManager

# Charger les variables d'environnement
load_dotenv()

async def test_lnbits_automation():
    """Test des automatisations avec LNbits"""
    print("Test des automatisations avec LNbits sur le testnet")
    print("================================================")
    
    # Vérifier que LNbits est configuré
    lnbits_url = os.environ.get("LNBITS_URL")
    lnbits_api_key = os.environ.get("LNBITS_API_KEY")
    use_lnbits = os.environ.get("USE_LNBITS", "false").lower() == "true"
    
    if not use_lnbits or not lnbits_url or not lnbits_api_key:
        print("Erreur: LNbits n'est pas correctement configuré.")
        print("Exécutez d'abord: python scripts/setup_lnbits_testnet.py")
        return False
    
    print(f"URL LNbits: {lnbits_url}")
    print(f"Clé API configurée: {'Oui' if lnbits_api_key else 'Non'}")
    
    # Créer une instance de AutomationManager
    automation_manager = AutomationManager(
        lncli_path=os.environ.get("LNCLI_PATH", "lncli"),
        rebalance_lnd_path=os.environ.get("REBALANCE_LND_PATH", "rebalance-lnd"),
        lnbits_url=lnbits_url,
        lnbits_api_key=lnbits_api_key,
        use_lnbits=True
    )
    
    # Demander l'ID du canal à tester
    channel_id = input("ID du canal à tester: ").strip()
    if not channel_id:
        print("Erreur: L'ID du canal est requis.")
        return False
    
    # Menu des tests
    while True:
        print("\nMenu des tests:")
        print("1. Mettre à jour les frais")
        print("2. Rééquilibrer le canal")
        print("3. Appliquer une stratégie de rééquilibrage personnalisée")
        print("4. Afficher l'historique des automatisations")
        print("5. Quitter")
        
        choice = input("\nChoix: ").strip()
        
        if choice == "1":
            # Test de mise à jour des frais
            try:
                base_fee = int(input("Frais de base (msats): ").strip())
                fee_rate = float(input("Taux de frais (ppm): ").strip())
                
                print("\nMise à jour des frais en cours...")
                result = await automation_manager.update_fee_rate(channel_id, base_fee, fee_rate)
                
                print("\nRésultat:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except ValueError:
                print("Erreur: Les valeurs doivent être des nombres.")
            except Exception as e:
                print(f"Erreur: {str(e)}")
        
        elif choice == "2":
            # Test de rééquilibrage
            try:
                amount = int(input("Montant à rééquilibrer (sats): ").strip())
                direction = input("Direction (outgoing/incoming, défaut: outgoing): ").strip() or "outgoing"
                
                print("\nRééquilibrage en cours...")
                result = await automation_manager.rebalance_channel(channel_id, amount, direction)
                
                print("\nRésultat:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except ValueError:
                print("Erreur: Le montant doit être un nombre.")
            except Exception as e:
                print(f"Erreur: {str(e)}")
        
        elif choice == "3":
            # Test de stratégie de rééquilibrage personnalisée
            try:
                target_ratio = float(input("Ratio cible (0.0 à 1.0, défaut: 0.5): ").strip() or "0.5")
                
                print("\nApplication de la stratégie de rééquilibrage en cours...")
                result = await automation_manager.custom_rebalance_strategy(channel_id, target_ratio)
                
                print("\nRésultat:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except ValueError:
                print("Erreur: Le ratio doit être un nombre entre 0.0 et 1.0.")
            except Exception as e:
                print(f"Erreur: {str(e)}")
        
        elif choice == "4":
            # Affichage de l'historique
            limit = input("Nombre d'entrées à afficher (défaut: 10): ").strip()
            try:
                limit = int(limit) if limit else 10
                history = automation_manager.get_automation_history(limit=limit)
                
                print("\nHistorique des automatisations:")
                print(json.dumps(history, indent=2, ensure_ascii=False))
            except ValueError:
                print("Erreur: Le nombre d'entrées doit être un nombre.")
            except Exception as e:
                print(f"Erreur: {str(e)}")
        
        elif choice == "5":
            # Quitter
            print("Au revoir!")
            break
        
        else:
            print("Choix invalide. Veuillez réessayer.")
    
    return True

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Test des automatisations avec LNbits sur le testnet")
    args = parser.parse_args()
    
    success = asyncio.run(test_lnbits_automation())
    
    if not success:
        print("\nLes tests ont échoué.")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main() 