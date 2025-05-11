import pytest
import asyncio
import json
import random
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.tools.simulator.network_simulator import (
    NetworkSimulator,
    SimulatedChannel,
    SimulatedNode,
    simulate_network_behavior,
    generate_random_network
)

@pytest.fixture
def basic_network():
    """Génère un réseau de base pour les tests."""
    return {
        "nodes": [
            {"node_id": "node1", "alias": "Alice", "capacity": 10000000},
            {"node_id": "node2", "alias": "Bob", "capacity": 8000000},
            {"node_id": "node3", "alias": "Charlie", "capacity": 6000000},
            {"node_id": "node4", "alias": "Dave", "capacity": 5000000}
        ],
        "channels": [
            {"channel_id": "chan1_2", "node1_id": "node1", "node2_id": "node2", "capacity": 3000000, "base_fee": 1000, "fee_rate": 1},
            {"channel_id": "chan1_3", "node1_id": "node1", "node2_id": "node3", "capacity": 2000000, "base_fee": 500, "fee_rate": 2},
            {"channel_id": "chan2_3", "node1_id": "node2", "node2_id": "node3", "capacity": 1500000, "base_fee": 800, "fee_rate": 1.5},
            {"channel_id": "chan2_4", "node1_id": "node2", "node2_id": "node4", "capacity": 2500000, "base_fee": 600, "fee_rate": 0.8},
            {"channel_id": "chan3_4", "node1_id": "node3", "node2_id": "node4", "capacity": 1800000, "base_fee": 700, "fee_rate": 1.2}
        ]
    }

class TestSimulatedChannel:
    """Tests pour les canaux simulés."""
    
    def test_channel_init(self):
        """Test de l'initialisation d'un canal simulé."""
        channel = SimulatedChannel(
            channel_id="test_chan",
            node1_id="node1",
            node2_id="node2",
            capacity=5000000,
            base_fee=1000,
            fee_rate=1
        )
        
        assert channel.channel_id == "test_chan"
        assert channel.capacity == 5000000
        assert channel.base_fee == 1000
        assert channel.fee_rate == 1
        assert channel.node1_balance + channel.node2_balance == 5000000
        assert channel.is_active is True
    
    def test_channel_send_payment(self):
        """Test d'envoi de paiement sur un canal."""
        channel = SimulatedChannel(
            channel_id="test_chan",
            node1_id="node1", 
            node2_id="node2",
            capacity=5000000,
            base_fee=1000,
            fee_rate=1
        )
        
        # Forcer l'équilibre initial connu
        channel.node1_balance = 3000000
        channel.node2_balance = 2000000
        
        # Envoi de node1 à node2
        result = channel.send_payment(from_node="node1", amount=1000000)
        
        assert result["success"] is True
        assert channel.node1_balance == 2000000
        assert channel.node2_balance == 3000000
        
        # Envoi insuffisant
        result = channel.send_payment(from_node="node1", amount=3000000)
        
        assert result["success"] is False
        assert "Fonds insuffisants" in result["message"]
        assert channel.node1_balance == 2000000  # Inchangé
    
    def test_channel_update_fees(self):
        """Test de mise à jour des frais d'un canal."""
        channel = SimulatedChannel(
            channel_id="test_chan",
            node1_id="node1",
            node2_id="node2",
            capacity=5000000,
            base_fee=1000,
            fee_rate=1
        )
        
        result = channel.update_fees(new_base_fee=1500, new_fee_rate=2)
        
        assert result["success"] is True
        assert channel.base_fee == 1500
        assert channel.fee_rate == 2
        
        # Test avec un montant négatif
        result = channel.update_fees(new_base_fee=-100, new_fee_rate=2)
        
        assert result["success"] is False
        assert channel.base_fee == 1500  # Inchangé

class TestSimulatedNode:
    """Tests pour les nœuds simulés."""
    
    def test_node_init(self):
        """Test de l'initialisation d'un nœud simulé."""
        node = SimulatedNode(
            node_id="test_node",
            alias="Test Node",
            capacity=10000000
        )
        
        assert node.node_id == "test_node"
        assert node.alias == "Test Node"
        assert node.capacity == 10000000
        assert node.is_online is True
        assert node.uptime == 1.0
    
    def test_node_toggle_status(self):
        """Test de basculement d'état d'un nœud."""
        node = SimulatedNode(
            node_id="test_node",
            alias="Test Node",
            capacity=10000000
        )
        
        assert node.is_online is True
        
        node.toggle_status()
        
        assert node.is_online is False
        
        node.toggle_status()
        
        assert node.is_online is True
    
    def test_node_update_uptime(self):
        """Test de mise à jour du temps de fonctionnement d'un nœud."""
        node = SimulatedNode(
            node_id="test_node",
            alias="Test Node",
            capacity=10000000
        )
        
        # Simuler une panne de 10% du temps
        node.uptime = 1.0
        for _ in range(90):
            node.update_uptime(online=True)
        for _ in range(10):
            node.update_uptime(online=False)
        
        assert 0.85 <= node.uptime <= 0.95

class TestNetworkSimulator:
    """Tests pour le simulateur de réseau."""
    
    def test_simulator_init(self, basic_network):
        """Test de l'initialisation du simulateur."""
        simulator = NetworkSimulator(network_data=basic_network)
        
        assert len(simulator.nodes) == 4
        assert len(simulator.channels) == 5
        assert simulator.current_time is not None
    
    def test_simulator_step(self, basic_network):
        """Test d'une étape de simulation."""
        simulator = NetworkSimulator(network_data=basic_network)
        
        initial_time = simulator.current_time
        simulator.step()
        
        assert simulator.current_time > initial_time
        assert simulator.current_time - initial_time == timedelta(minutes=simulator.time_step_minutes)
    
    @patch('random.random')
    def test_node_failure_simulation(self, mock_random, basic_network):
        """Test de simulation de panne de nœud."""
        # Configurer le mock pour forcer une panne
        mock_random.return_value = 0.01  # En dessous du seuil par défaut
        
        simulator = NetworkSimulator(network_data=basic_network, node_failure_rate=0.05)
        
        # État initial
        all_online = all(node.is_online for node in simulator.nodes.values())
        assert all_online is True
        
        # Simuler une étape avec panne
        simulator.simulate_node_failures()
        
        # Au moins un nœud devrait être hors ligne
        any_offline = any(not node.is_online for node in simulator.nodes.values())
        assert any_offline is True
    
    def test_payment_simulation(self, basic_network):
        """Test de simulation de paiements."""
        simulator = NetworkSimulator(network_data=basic_network)
        
        # État initial des canaux
        channel = list(simulator.channels.values())[0]
        initial_node1_balance = channel.node1_balance
        initial_node2_balance = channel.node2_balance
        
        # Simuler des paiements
        payments = simulator.simulate_payments(num_payments=10)
        
        # Vérifier les résultats
        assert len(payments) == 10
        
        # Vérifier que des balances ont changé
        any_balance_changed = False
        for chan in simulator.channels.values():
            if (chan.node1_balance != initial_node1_balance or 
                chan.node2_balance != initial_node2_balance):
                any_balance_changed = True
                break
        
        assert any_balance_changed is True
    
    def test_fee_update_simulation(self, basic_network):
        """Test de simulation de mise à jour des frais."""
        simulator = NetworkSimulator(network_data=basic_network)
        
        # État initial
        channel = list(simulator.channels.values())[0]
        initial_base_fee = channel.base_fee
        initial_fee_rate = channel.fee_rate
        
        # Simuler des mises à jour de frais
        updates = simulator.simulate_fee_updates(update_probability=1.0)  # 100% de probabilité
        
        # Vérifier les résultats
        assert len(updates) > 0
        
        # Vérifier que des frais ont changé
        any_fee_changed = False
        for chan in simulator.channels.values():
            if chan.base_fee != initial_base_fee or chan.fee_rate != initial_fee_rate:
                any_fee_changed = True
                break
        
        assert any_fee_changed is True

@pytest.mark.parametrize("volatility", [0.1, 0.5, 0.9])
def test_simulate_network_with_volatility(basic_network, volatility):
    """Test de simulation avec différents niveaux de volatilité."""
    simulator = NetworkSimulator(
        network_data=basic_network,
        node_failure_rate=volatility * 0.1,  # Plus de pannes avec volatilité élevée
        payment_volume_factor=1 + volatility  # Plus de paiements avec volatilité élevée
    )
    
    # Exécuter plusieurs étapes de simulation
    for _ in range(10):
        simulator.step()
    
    # Calculer des métriques de volatilité
    offline_count = sum(1 for node in simulator.nodes.values() if not node.is_online)
    
    if volatility >= 0.5:
        # Avec une volatilité élevée, on s'attend à plus de nœuds hors ligne
        assert offline_count > 0
    
    # Vérifier les transactions
    payment_history = simulator.payment_history
    assert len(payment_history) > 0
    
    # Vérifier le taux d'échec des paiements en fonction de la volatilité
    failed_payments = sum(1 for payment in payment_history if not payment["success"])
    failure_rate = failed_payments / len(payment_history) if payment_history else 0
    
    if volatility > 0.7:
        # Avec une volatilité très élevée, on s'attend à plus d'échecs
        assert failure_rate > 0.1

def test_generate_random_network():
    """Test de génération d'un réseau aléatoire."""
    network = generate_random_network(num_nodes=10, min_channels_per_node=2)
    
    assert len(network["nodes"]) == 10
    # Chaque nœud devrait avoir au moins 2 canaux
    # Total minimum de canaux: (10 nodes * 2 channels) / 2 (car chaque canal relie 2 nœuds)
    assert len(network["channels"]) >= 10
    
    # Vérifier la connectivité - il devrait y avoir un chemin entre chaque paire de nœuds
    simulator = NetworkSimulator(network_data=network)
    
    nodes = list(simulator.nodes.keys())
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            # Une heuristique simple: vérifier qu'il existe un chemin
            # En réalité, un algorithme de routage plus complexe serait nécessaire
            connection_found = False
            for channel in network["channels"]:
                if ((channel["node1_id"] == nodes[i] and channel["node2_id"] == nodes[j]) or
                    (channel["node1_id"] == nodes[j] and channel["node2_id"] == nodes[i])):
                    connection_found = True
                    break
            
            # Si aucune connexion directe n'est trouvée, on vérifie les connexions indirectes
            # Note: ceci est une heuristique très simplifiée pour le test
            if not connection_found:
                indirect_connections = False
                for k in range(len(nodes)):
                    if k != i and k != j:
                        connection1 = False
                        connection2 = False
                        for channel in network["channels"]:
                            if ((channel["node1_id"] == nodes[i] and channel["node2_id"] == nodes[k]) or
                                (channel["node1_id"] == nodes[k] and channel["node2_id"] == nodes[i])):
                                connection1 = True
                            if ((channel["node1_id"] == nodes[k] and channel["node2_id"] == nodes[j]) or
                                (channel["node1_id"] == nodes[j] and channel["node2_id"] == nodes[k])):
                                connection2 = True
                        if connection1 and connection2:
                            indirect_connections = True
                            break
                
                # On accepte soit une connexion directe, soit au moins une connexion indirecte
                assert indirect_connections

@pytest.mark.asyncio
async def test_simulate_network_behavior():
    """Test de la fonction de simulation complète du comportement du réseau."""
    network = generate_random_network(num_nodes=5, min_channels_per_node=2)
    
    simulation_days = 7
    results = await simulate_network_behavior(
        network_data=network, 
        simulation_days=simulation_days,
        time_step_minutes=60,
        volatility=0.3
    )
    
    assert "network_state" in results
    assert "payment_history" in results
    assert "fee_update_history" in results
    assert "daily_statistics" in results
    
    # Vérifier que la simulation a fonctionné pour la période demandée
    assert len(results["daily_statistics"]) == simulation_days
    
    # Vérifier que des paiements ont été simulés
    assert len(results["payment_history"]) > 0
    
    # Vérifier que des mises à jour de frais ont été simulées
    assert len(results["fee_update_history"]) > 0
    
    # Vérifier les statistiques quotidiennes
    for day_stats in results["daily_statistics"]:
        assert "day" in day_stats
        assert "total_payments" in day_stats
        assert "success_rate" in day_stats
        assert "total_volume" in day_stats
        assert "node_uptime" in day_stats 