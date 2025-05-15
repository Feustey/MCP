#!/usr/bin/env python3
"""
Script de test pour le système d'optimisation de nœud Lightning avec A/B testing
et boucle de retour pour ajuster l'heuristique.

Ce script simule un cycle complet de test et feedback.
"""

import asyncio
import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

from mcp.lnbits_client import LNBitsClient
from test_scenarios import TestScenarioManager, ActionTracker
from src.optimizers.optimize_feustey_config import calculate_score

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_scenario() -> Dict[str, Any]:
    """Crée un scénario de test simple avec des valeurs réalistes."""
    return {
        "id": f"test_scenario_{int(time.time())}",
        "name": "Scénario de test pour boucle de feedback",
        "description": "Configuration équilibrée pour tester le système",
        "fee_structure": {
            "base_fee_msat": 1000,
            "fee_rate": 200
        },
        "channel_policy": {
            "target_local_ratio": 0.6,
            "rebalance_threshold": 0.3
        },
        "peer_selection": {
            "min_capacity": 200000,
            "target_nodes": []
        }
    }

async def simulate_metrics_after(metrics_before: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simule les métriques après une action avec une amélioration basée sur la configuration.
    Dans un système réel, ces métriques viendraient des mesures réelles.
    """
    # Copier les métriques avant comme base
    metrics_after = metrics_before.copy()
    
    # Simuler une amélioration
    metrics_after["sats_forwarded_24h"] += random.randint(10000, 50000)  # +10k à +50k sats
    metrics_after["htlc_response_time"] *= random.uniform(0.8, 1.0)  # 0-20% plus rapide
    metrics_after["routing_success_rate"] = min(1.0, metrics_before["routing_success_rate"] * random.uniform(1.0, 1.1))  # 0-10% meilleur
    metrics_after["channel_balance_quality"] = min(1.0, metrics_before["channel_balance_quality"] * random.uniform(1.0, 1.2))  # 0-20% meilleur
    
    # Mise à jour du timestamp
    metrics_after["timestamp"] = datetime.now().isoformat()
    
    return metrics_after

async def test_feedback_loop():
    """Teste un cycle complet de la boucle de feedback."""
    print("\n=== Test du système de boucle de feedback ===")
    
    # Initialiser les composants
    client = LNBitsClient()  # Utilisera les variables d'environnement
    test_manager = TestScenarioManager(client)
    
    # 1. Créer un scénario de test
    scenario = await create_test_scenario()
    print(f"\nScénario de test créé: {scenario['name']}")
    
    # 2. Créer des scénarios pour A/B testing
    print("\nGénération des scénarios A/B/C...")
    scenarios = await test_manager.generate_a_b_test(scenario)
    
    for s in scenarios:
        print(f" - {s['type']}: {s.get('name', s['id'])}")
    
    # 3. Exécuter chaque scénario
    print("\nExécution des tests pour chaque scénario...")
    
    for s in scenarios:
        print(f"\nConfiguration du nœud avec le scénario {s['type']}...")
        await test_manager.configure_node(s)
        
        # Simuler le passage du temps (version accélérée pour test)
        print(f"Attente de résultats pour le scénario {s['id']}...")
        await asyncio.sleep(1)  # Dans un test réel, ce serait beaucoup plus long
        
        # Récupérer les métriques avant
        action_id = test_manager.active_tests.get(s['id'], {}).get("action_id")
        if not action_id:
            print(f"Erreur: action_id non trouvé pour {s['id']}")
            continue
            
        action_file = test_manager.action_tracker.actions_dir / f"{action_id}.json"
        with open(action_file, "r") as f:
            action_data = json.load(f)
        
        metrics_before = action_data["metrics_before"]
        
        # Simuler des métriques après test
        metrics_after = await simulate_metrics_after(metrics_before)
        
        # Mettre à jour avec les résultats simulés
        await test_manager.action_tracker.update_action_results(action_id, metrics_after)
        print(f"Métriques mises à jour pour {s['id']}")
        print(f"Delta sats forwardés: +{metrics_after['sats_forwarded_24h'] - metrics_before['sats_forwarded_24h']}")
    
    # 4. Identifier le gagnant
    print("\nIdentification du scénario gagnant...")
    scenario_ids = [s["id"] for s in scenarios]
    winner = await test_manager.action_tracker.identify_winners(scenario_ids)
    
    if winner:
        print(f"Scénario gagnant identifié: {winner['scenario_id']} ({winner['action_type']})")
        print(f"Delta sats forwardés: +{winner['delta_24h']}")
        
        # 5. Ajuster les poids si nécessaire
        if winner['action_type'] != "heuristic":
            print("\nLa configuration heuristique n'est pas la meilleure! Ajustement des poids...")
            new_weights = await test_manager.action_tracker.calculate_weight_adjustment()
            
            print("\nNouveaux poids pour l'heuristique:")
            for metric, weight in new_weights.items():
                print(f"  - {metric}: {weight:.2f}")
                
            # Test avec les nouveaux poids
            print("\nTest de scoring avec les nouveaux poids...")
            for s_id in scenario_ids:
                files = list(test_manager.action_tracker.actions_dir.glob(f"{s_id}_*.json"))
                if not files:
                    continue
                    
                with open(files[0], "r") as f:
                    s_data = json.load(f)
                
                metrics = s_data.get("metrics_after", {})
                old_score = calculate_score(metrics)
                new_score = calculate_score(metrics, new_weights)
                
                print(f"Scénario {s_id}: Score original {old_score:.2f}, nouveau score {new_score:.2f}")
    else:
        print("Impossible de déterminer un gagnant.")
    
    # 6. Nettoyage
    await test_manager.cleanup_tests()
    print("\nTest de la boucle de feedback terminé avec succès!")

async def run_test_cycle():
    # Initialiser le client LNBits (à adapter selon votre configuration)
    client = LNBitsClient()
    
    # Initialiser le gestionnaire de scénarios
    manager = TestScenarioManager(client)
    
    # Scénario de base avec l'heuristique optimisée
    base_scenario = {
        "name": "Configuration heuristique optimisée",
        "description": "Configuration basée sur l'analyse topologique et les performances",
        "fee_structure": {
            "base_fee_msat": 2000,
            "fee_rate": 300
        },
        "channel_policy": {
            "target_local_ratio": 0.55,
            "rebalance_threshold": 0.25
        },
        "peer_selection": {
            "min_capacity": 200000
        }
    }
    
    try:
        # Générer les scénarios A/B
        scenarios = await manager.generate_a_b_test(base_scenario)
        logger.info(f"Générés {len(scenarios)} scénarios pour le test A/B")
        
        # Tester chaque scénario
        for scenario in scenarios:
            logger.info(f"Test du scénario {scenario['id']} ({scenario['type']})")
            
            # Configurer le nœud avec le scénario
            success = await manager.configure_node(scenario)
            if not success:
                logger.error(f"Échec de la configuration pour le scénario {scenario['id']}")
                continue
                
            # Démarrer une session de test
            test_id = await manager.start_test_session(
                scenario_id=scenario['id'],
                duration_minutes=60,  # 1 heure de test
                payment_count=100     # 100 paiements simulés
            )
            
            logger.info(f"Session de test {test_id} démarrée pour le scénario {scenario['id']}")
            
            # Attendre 1 heure pour la collecte des données
            await asyncio.sleep(3600)
            
            # Récupérer les métriques finales
            metrics = await manager.get_test_metrics(test_id)
            logger.info(f"Métriques finales pour {scenario['id']}: {metrics}")
            
        # Nettoyer les tests et générer le rapport final
        await manager.cleanup_tests()
        
        logger.info("Cycle de test terminé avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du cycle de test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_test_cycle()) 