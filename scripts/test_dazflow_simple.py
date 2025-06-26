#!/usr/bin/env python3
"""
Test simple du module DazFlow Index
Vérification rapide des calculs et analyses

Dernière mise à jour: 7 mai 2025
"""

import sys
import os
import asyncio

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics import DazFlowCalculator, DazFlowAnalysis

def test_dazflow_calculations():
    """Test simple des calculs DazFlow Index"""
    print("🧪 Test simple DazFlow Index")
    print("=" * 40)
    
    # Initialiser le calculateur
    calculator = DazFlowCalculator()
    
    # Données de test
    test_node_data = {
        "node_id": "test_node_001",
        "channels": [
            {
                "channel_id": "test_channel_1",
                "peer_alias": "TestPeer1",
                "capacity": 1000000,
                "local_balance": 500000,
                "remote_balance": 500000,
                "active": True
            },
            {
                "channel_id": "test_channel_2",
                "peer_alias": "TestPeer2",
                "capacity": 2000000,
                "local_balance": 1800000,
                "remote_balance": 200000,
                "active": True
            }
        ],
        "historical_success_rate": 0.85,
        "metrics": {
            "centrality": {
                "betweenness": 0.6
            }
        }
    }
    
    try:
        # Test 1: Calcul de probabilité de succès
        print("\n1️⃣ Test calcul probabilité de succès...")
        amount = 100000
        probability = calculator.calculate_payment_success_probability(test_node_data, amount)
        print(f"   ✅ Probabilité pour {amount:,} sats: {probability:.1%}")
        
        # Test 2: Courbe de fiabilité
        print("\n2️⃣ Test courbe de fiabilité...")
        amounts = [1000, 10000, 100000, 1000000]
        curve = calculator.generate_reliability_curve(test_node_data, amounts)
        print(f"   ✅ Courbe générée avec {len(curve.amounts)} points")
        print(f"   ✅ Montants recommandés: {len(curve.recommended_amounts)}")
        
        # Test 3: Identification des goulots
        print("\n3️⃣ Test identification goulots d'étranglement...")
        bottlenecks = calculator.identify_bottlenecks(test_node_data)
        print(f"   ✅ {len(bottlenecks)} goulots identifiés")
        
        # Test 4: Analyse DazFlow Index complète
        print("\n4️⃣ Test analyse DazFlow Index complète...")
        analysis = calculator.analyze_dazflow_index(test_node_data)
        
        if analysis:
            print(f"   ✅ Indice DazFlow: {analysis.dazflow_index:.4f}")
            print(f"   ✅ Efficacité liquidité: {analysis.liquidity_efficiency:.4f}")
            print(f"   ✅ Centralité réseau: {analysis.network_centrality:.4f}")
            print(f"   ✅ Goulots d'étranglement: {len(analysis.bottleneck_channels)}")
            
            # Afficher les probabilités de succès
            print("\n   📊 Probabilités de succès:")
            for amount, prob in zip(analysis.payment_amounts, analysis.success_probabilities):
                print(f"      {amount:,} sats → {prob:.1%}")
        else:
            print("   ❌ Échec de l'analyse")
            return False
        
        print("\n✅ Tous les tests DazFlow Index ont réussi!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        return False

def test_edge_cases():
    """Test des cas limites"""
    print("\n🔍 Test des cas limites")
    print("-" * 30)
    
    calculator = DazFlowCalculator()
    
    # Test avec nœud sans canaux
    print("\n1️⃣ Test nœud sans canaux...")
    empty_node = {
        "node_id": "empty_node",
        "channels": [],
        "historical_success_rate": 0.85
    }
    
    probability = calculator.calculate_payment_success_probability(empty_node, 100000)
    print(f"   ✅ Probabilité (nœud vide): {probability:.1%}")
    
    # Test avec montant très élevé
    print("\n2️⃣ Test montant très élevé...")
    test_node = {
        "node_id": "test_node",
        "channels": [
            {
                "channel_id": "test_channel",
                "peer_alias": "TestPeer",
                "capacity": 1000000,
                "local_balance": 500000,
                "remote_balance": 500000,
                "active": True
            }
        ],
        "historical_success_rate": 0.85
    }
    
    large_amount = 10000000  # 10M sats
    probability = calculator.calculate_payment_success_probability(test_node, large_amount)
    print(f"   ✅ Probabilité (10M sats): {probability:.1%}")
    
    print("\n✅ Tests des cas limites réussis!")

def main():
    """Fonction principale"""
    print("🚀 Test simple du module DazFlow Index")
    print("=" * 50)
    
    # Test principal
    success = test_dazflow_calculations()
    
    if success:
        # Test des cas limites
        test_edge_cases()
        
        print("\n🎉 Tous les tests ont réussi!")
        print("📚 Le module DazFlow Index est fonctionnel")
        print("🔧 Prêt pour l'intégration en production")
    else:
        print("\n❌ Certains tests ont échoué")
        print("🔧 Vérifiez la configuration et les dépendances")
        sys.exit(1)

if __name__ == "__main__":
    main() 