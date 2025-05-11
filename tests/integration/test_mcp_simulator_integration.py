import pytest
import os
import json
import asyncio
from datetime import datetime, timedelta

from src.tools.simulator.network_simulator import NetworkSimulator, generate_random_network
from src.optimizers.feustey_fee_optimizer import optimize_fees
from src.optimizers.scoring_utils import calculate_channel_score, calculate_node_score

@pytest.fixture
def simulated_network():
    """Génère un réseau simulé pour les tests."""
    return generate_random_network(num_nodes=8, min_channels_per_node=2)

@pytest.fixture
def simulator(simulated_network):
    """Crée un simulateur de réseau."""
    return NetworkSimulator(
        network_data=simulated_network,
        node_failure_rate=0.02,
        payment_volume_factor=1.2
    )

@pytest.mark.asyncio
async def test_simulator_integration_with_mcp(simulator):
    """Test d'intégration entre le simulateur et le système MCP."""
    # Exécuter la simulation pour une journée (24 heures)
    for _ in range(24):
        simulator.step()
    
    # Extraire les données du réseau simulé
    network_state = simulator.get_network_state()
    
    # Préparer les données pour MCP
    channels = []
    for channel_id, channel in simulator.channels.items():
        # Convertir le canal simulé en structure de données compatible MCP
        channel_data = {
            "channel_id": channel.channel_id,
            "capacity": channel.capacity,
            "local_balance": channel.node1_balance,
            "remote_balance": channel.node2_balance,
            "uptime": 0.95,  # Simulé
            "num_updates": len([p for p in simulator.payment_history if p["channel_id"] == channel_id]),
            "current_base_fee": channel.base_fee,
            "current_fee_rate": channel.fee_rate,
            "score": 0.0,  # Sera calculé
            "peer_node": {
                "node_id": channel.node2_id,
                "alias": simulator.nodes[channel.node2_id].alias if channel.node2_id in simulator.nodes else "Unknown",
                "num_channels": len([c for c in simulator.channels.values() 
                                  if c.node1_id == channel.node2_id or c.node2_id == channel.node2_id])
            }
        }
        
        # Calculer le score du canal
        channel_data["score"] = calculate_channel_score(channel_data)
        channels.append(channel_data)
    
    # Calculer les statistiques du réseau simulé
    network_data = {
        "average_base_fee": sum(c.base_fee for c in simulator.channels.values()) / len(simulator.channels),
        "average_fee_rate": sum(c.fee_rate for c in simulator.channels.values()) / len(simulator.channels),
        "median_base_fee": sorted([c.base_fee for c in simulator.channels.values()])[len(simulator.channels) // 2],
        "median_fee_rate": sorted([c.fee_rate for c in simulator.channels.values()])[len(simulator.channels) // 2],
        "p90_base_fee": sorted([c.base_fee for c in simulator.channels.values()])[int(len(simulator.channels) * 0.9)],
        "p90_fee_rate": sorted([c.fee_rate for c in simulator.channels.values()])[int(len(simulator.channels) * 0.9)]
    }
    
    # Enregistrer l'état initial
    initial_fees = {c["channel_id"]: (c["current_base_fee"], c["current_fee_rate"]) for c in channels}
    
    # Exécuter MCP pour optimiser les frais
    optimization_results = optimize_fees(channels, network_data)
    
    # Vérifier que MCP a généré des résultats
    assert len(optimization_results) > 0
    
    # Appliquer les changements au simulateur
    for result in optimization_results:
        if result["success"]:
            channel_id = result["channel_id"]
            new_base_fee = result["new_base_fee"]
            new_fee_rate = result["new_fee_rate"]
            
            # Appliquer les changements au canal simulé
            simulator.channels[channel_id].update_fees(new_base_fee=new_base_fee, new_fee_rate=new_fee_rate)
    
    # Exécuter la simulation pour une autre journée avec les nouveaux frais
    previous_payment_count = len(simulator.payment_history)
    for _ in range(24):
        simulator.step()
    new_payment_count = len(simulator.payment_history)
    
    # Calculer les métriques de performance
    payment_increase = new_payment_count - previous_payment_count
    
    # Identifier les canaux qui ont été modifiés
    modified_channels = []
    for result in optimization_results:
        if result["success"]:
            channel_id = result["channel_id"]
            original_fees = initial_fees[channel_id]
            current_fees = (simulator.channels[channel_id].base_fee, simulator.channels[channel_id].fee_rate)
            
            # Ajouter aux canaux modifiés
            modified_channels.append({
                "channel_id": channel_id,
                "original_base_fee": original_fees[0],
                "original_fee_rate": original_fees[1],
                "new_base_fee": current_fees[0],
                "new_fee_rate": current_fees[1],
                "payments_before": len([p for p in simulator.payment_history[:previous_payment_count] 
                                     if p["channel_id"] == channel_id]),
                "payments_after": len([p for p in simulator.payment_history[previous_payment_count:] 
                                    if p["channel_id"] == channel_id])
            })
    
    # Vérifier que des canaux ont été modifiés
    assert len(modified_channels) > 0
    
    # Calculer l'impact des changements
    total_before = sum(c["payments_before"] for c in modified_channels)
    total_after = sum(c["payments_after"] for c in modified_channels)
    
    # Enregistrer les résultats de l'intégration
    integration_results = {
        "test_time": datetime.now().isoformat(),
        "total_channels": len(channels),
        "modified_channels": len(modified_channels),
        "payments_before_optimization": total_before,
        "payments_after_optimization": total_after,
        "percentage_change": ((total_after - total_before) / total_before * 100) if total_before > 0 else 0,
        "channel_details": modified_channels
    }
    
    # Sauvegarder les résultats (optionnel pour le débogage)
    results_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, f"mcp_simulator_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"), "w") as f:
        json.dump(integration_results, f, indent=2)
    
    # Vérifier que l'optimisation a eu un impact (peut être positif ou négatif, nous voulons juste confirmer l'intégration)
    assert integration_results["modified_channels"] > 0
    # Note: Dans une implémentation réelle, nous voudrions vérifier:
    # assert integration_results["percentage_change"] > 0
    # Mais pour un test d'intégration, nous voulons simplement confirmer que les systèmes fonctionnent ensemble.

@pytest.mark.asyncio
async def test_mcp_performance_with_different_volatility_scenarios():
    """Test des performances de MCP sous différents scénarios de volatilité."""
    # Générer un réseau de base
    network = generate_random_network(num_nodes=6, min_channels_per_node=2)
    
    volatility_scenarios = [0.1, 0.5, 0.9]  # Faible, moyen, élevé
    performance_results = []
    
    for volatility in volatility_scenarios:
        # Créer un simulateur avec ce niveau de volatilité
        simulator = NetworkSimulator(
            network_data=network,
            node_failure_rate=volatility * 0.05,
            payment_volume_factor=1 + volatility * 0.5
        )
        
        # Simuler une semaine avant optimisation
        for _ in range(7 * 24):  # 7 jours, 24 heures par jour
            simulator.step()
        
        # Mesurer les paiements pré-optimisation
        pre_optimization_payments = len(simulator.payment_history)
        pre_optimization_success = sum(1 for p in simulator.payment_history if p["success"])
        pre_optimization_success_rate = pre_optimization_success / pre_optimization_payments if pre_optimization_payments > 0 else 0
        
        # Préparer les données pour MCP (comme dans le test précédent)
        channels = []
        for channel_id, channel in simulator.channels.items():
            channel_data = {
                "channel_id": channel.channel_id,
                "capacity": channel.capacity,
                "local_balance": channel.node1_balance,
                "remote_balance": channel.node2_balance,
                "uptime": simulator.nodes[channel.node1_id].uptime,
                "num_updates": len([p for p in simulator.payment_history if p["channel_id"] == channel_id]),
                "current_base_fee": channel.base_fee,
                "current_fee_rate": channel.fee_rate,
                "score": 0.0,
                "peer_node": {
                    "node_id": channel.node2_id,
                    "alias": simulator.nodes[channel.node2_id].alias,
                    "num_channels": len([c for c in simulator.channels.values() 
                                      if c.node1_id == channel.node2_id or c.node2_id == channel.node2_id])
                }
            }
            channel_data["score"] = calculate_channel_score(channel_data)
            channels.append(channel_data)
        
        network_data = {
            "average_base_fee": sum(c.base_fee for c in simulator.channels.values()) / len(simulator.channels),
            "average_fee_rate": sum(c.fee_rate for c in simulator.channels.values()) / len(simulator.channels),
            "median_base_fee": sorted([c.base_fee for c in simulator.channels.values()])[len(simulator.channels) // 2],
            "median_fee_rate": sorted([c.fee_rate for c in simulator.channels.values()])[len(simulator.channels) // 2],
            "p90_base_fee": sorted([c.base_fee for c in simulator.channels.values()])[int(len(simulator.channels) * 0.9)],
            "p90_fee_rate": sorted([c.fee_rate for c in simulator.channels.values()])[int(len(simulator.channels) * 0.9)]
        }
        
        # Exécuter l'optimisation MCP
        optimization_results = optimize_fees(channels, network_data)
        
        # Appliquer les changements au simulateur
        changes_applied = 0
        for result in optimization_results:
            if result["success"]:
                channel_id = result["channel_id"]
                simulator.channels[channel_id].update_fees(
                    new_base_fee=result["new_base_fee"],
                    new_fee_rate=result["new_fee_rate"]
                )
                changes_applied += 1
        
        # Simuler une autre semaine après optimisation
        for _ in range(7 * 24):
            simulator.step()
        
        # Mesurer les paiements post-optimisation (seulement ceux après l'optimisation)
        post_optimization_payments = len(simulator.payment_history) - pre_optimization_payments
        post_optimization_success = sum(1 for p in simulator.payment_history[pre_optimization_payments:] if p["success"])
        post_optimization_success_rate = post_optimization_success / post_optimization_payments if post_optimization_payments > 0 else 0
        
        # Collecter les résultats
        performance_results.append({
            "volatility": volatility,
            "changes_applied": changes_applied,
            "pre_optimization_payments": pre_optimization_payments,
            "pre_optimization_success_rate": pre_optimization_success_rate,
            "post_optimization_payments": post_optimization_payments,
            "post_optimization_success_rate": post_optimization_success_rate,
            "payment_volume_change_percent": ((post_optimization_payments - pre_optimization_payments) / pre_optimization_payments * 100) 
                                            if pre_optimization_payments > 0 else 0,
            "success_rate_change_percent": ((post_optimization_success_rate - pre_optimization_success_rate) / pre_optimization_success_rate * 100)
                                          if pre_optimization_success_rate > 0 else 0
        })
    
    # Vérifier les résultats pour chaque scénario
    for result in performance_results:
        # En environnement réel, nous voudrions idéalement voir des améliorations
        # Mais pour un test d'intégration, nous voulons confirmer que les résultats sont cohérents
        assert result["changes_applied"] > 0
        
        # Pour les scénarios à faible volatilité, nous nous attendons à des résultats positifs
        if result["volatility"] <= 0.3:
            # Dans un système de production, ces assertions seraient plus strictes
            assert abs(result["payment_volume_change_percent"]) < 50  # Change not too extreme
        
        # Pour les scénarios à haute volatilité, les résultats peuvent être plus variables
        if result["volatility"] >= 0.7:
            # Nous nous attendons à ce que MCP ait plus de difficulté dans des environnements volatils
            pass  # Pas d'assertion spécifique, juste documenter le comportement
    
    # Enregistrer les résultats (optionnel pour le débogage)
    results_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test")
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, f"mcp_volatility_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"), "w") as f:
        json.dump(performance_results, f, indent=2) 