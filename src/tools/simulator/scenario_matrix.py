#!/usr/bin/env python3
"""
Générateur de matrices de scénarios pour le simulateur stochastique de nœuds Lightning.
Ce module permet de générer des combinaisons paramétriques pour tester le moteur de décision.

Dernière mise à jour: 7 mai 2025
"""

import itertools
import random
import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scenario_matrix")

class ScenarioMatrix:
    """
    Générateur de matrices de scénarios pour tester le moteur de décision
    dans diverses configurations combinatoires.
    """
    
    def __init__(self, custom_dimensions: Optional[Dict[str, List[Any]]] = None):
        """
        Initialise le générateur de scénarios avec des dimensions personnalisables
        
        Args:
            custom_dimensions: Dimensions personnalisées pour la matrice
        """
        # Dimensions par défaut
        self.dimensions = {
            "node_centrality": [0.1, 0.5, 0.9],          # Périphérique à central
            "volume_level": [10, 100, 1000],             # Forwards/jour
            "liquidity_balance": [0.2, 0.5, 0.8],        # Distribution liquidité
            "fee_policy": ["aggressive", "moderate", "passive"],
            "network_volatility": [0.1, 0.3, 0.6],       # Stabilité du réseau
            "channel_age": [7, 30, 180, 365],            # Âge en jours
            "channel_capacity": [1000000, 5000000, 15000000]  # Capacité en sats
        }
        
        # Remplacer par des dimensions personnalisées si fournies
        if custom_dimensions:
            self.dimensions.update(custom_dimensions)
            
        # Configuration des valeurs numériques pour les politiques de frais
        self.fee_policies = {
            "passive": {"base_fee": 1, "fee_rate": 1},
            "moderate": {"base_fee": 1000, "fee_rate": 500},
            "aggressive": {"base_fee": 5000, "fee_rate": 2000}
        }
        
        logger.info(f"Matrice de scénarios initialisée avec {self._count_combinations()} combinaisons possibles")
    
    def _count_combinations(self) -> int:
        """
        Compte le nombre total de combinaisons possibles
        
        Returns:
            Nombre de combinaisons
        """
        return np.prod([len(values) for values in self.dimensions.values()])
    
    def generate_scenario_combinations(self, sample_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Génère toutes les combinaisons possibles ou un échantillon représentatif
        
        Args:
            sample_size: Taille de l'échantillon à générer (optionnel)
            
        Returns:
            Liste de dictionnaires contenant les paramètres des scénarios
        """
        # Générer tous les produits cartésiens possibles
        keys = list(self.dimensions.keys())
        all_combinations = list(itertools.product(*self.dimensions.values()))
        
        # Si un échantillon est demandé et plus petit que le total
        if sample_size and sample_size < len(all_combinations):
            selected_combinations = self._stratified_sampling(all_combinations, sample_size)
        else:
            selected_combinations = all_combinations
        
        # Convertir en liste de dictionnaires
        scenarios = []
        for combo in selected_combinations:
            scenario = dict(zip(keys, combo))
            
            # Convertir les valeurs de politique de frais en valeurs numériques
            if "fee_policy" in scenario:
                policy_name = scenario["fee_policy"]
                if policy_name in self.fee_policies:
                    # Fusionner les détails de la politique
                    scenario.update(self.fee_policies[policy_name])
            
            scenarios.append(scenario)
        
        return scenarios
    
    def _stratified_sampling(self, combinations: List[Tuple], sample_size: int) -> List[Tuple]:
        """
        Effectue un échantillonnage stratifié pour assurer une bonne couverture
        
        Args:
            combinations: Liste de toutes les combinaisons
            sample_size: Taille de l'échantillon à prélever
            
        Returns:
            Échantillon représentatif des combinaisons
        """
        # Si le nombre de combinaisons est faible, retourner tout
        if len(combinations) <= sample_size:
            return combinations
            
        # Grouper par node_centrality pour stratifier
        strata = {}
        for i, combo in enumerate(combinations):
            # Utiliser le premier élément (node_centrality) comme strate
            stratum = combo[0]
            if stratum not in strata:
                strata[stratum] = []
            strata[stratum].append(i)
        
        # Calculer combien prendre de chaque strate
        stratum_sizes = {}
        remaining = sample_size
        
        # Répartir proportionnellement
        total = len(combinations)
        for stratum, indices in strata.items():
            stratum_proportion = len(indices) / total
            stratum_sizes[stratum] = max(1, int(stratum_proportion * sample_size))
            remaining -= stratum_sizes[stratum]
        
        # Distribuer les échantillons restants
        strata_keys = list(strata.keys())
        while remaining > 0:
            stratum = random.choice(strata_keys)
            stratum_sizes[stratum] += 1
            remaining -= 1
        
        # Prélever l'échantillon stratifié
        selected_indices = []
        for stratum, size in stratum_sizes.items():
            candidates = strata[stratum]
            if len(candidates) <= size:
                selected_indices.extend(candidates)
            else:
                selected_indices.extend(random.sample(candidates, size))
        
        # Retourner les combinaisons sélectionnées
        return [combinations[i] for i in selected_indices]
    
    def generate_channel_parameters(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère les paramètres d'un canal basés sur un scénario
        
        Args:
            scenario: Paramètres du scénario
            
        Returns:
            Paramètres du canal
        """
        # Valeurs par défaut
        defaults = {
            "capacity": 5000000,
            "local_balance": 2500000,
            "remote_balance": 2500000,
            "total_forwards": 100,
            "successful_forwards": 95,
            "local_fee_base_msat": 1000,
            "local_fee_rate": 500,
            "centrality_score": 0.5,
            "htlc_success_rate": 0.95,
            "uptime": 0.99,
            "fee_competitiveness": 0.5,
            "channel_stability": 0.9,
            "peer_retention_rate": 0.95,
            "revenue": 0,
            "opportunity_cost": 0,
            "capital_efficiency": 0.5,
            "rebalancing_cost": 0,
            "active": True,
            "channel_id": f"sim_{random.randint(100000, 999999)}",
            "remote_pubkey": f"0{random.randint(10000000, 99999999)}",
            "avg_forward_size": 50000
        }
        
        # Créer un canal de base
        channel = defaults.copy()
        
        # Appliquer les paramètres du scénario
        if "channel_capacity" in scenario:
            channel["capacity"] = scenario["channel_capacity"]
            
        if "liquidity_balance" in scenario:
            # Calculer les balances en fonction du ratio
            liquidity_ratio = scenario["liquidity_balance"]
            channel["local_balance"] = int(channel["capacity"] * liquidity_ratio)
            channel["remote_balance"] = channel["capacity"] - channel["local_balance"]
            
        if "volume_level" in scenario:
            # Définir le volume de forwards avec un peu de bruit
            base_volume = scenario["volume_level"]
            noise = random.uniform(0.8, 1.2)
            channel["total_forwards"] = int(base_volume * noise)
            
            # Calculer les forwards réussis en fonction de la centralité
            success_rate = 0.7 + 0.25 * scenario.get("node_centrality", 0.5)
            channel["successful_forwards"] = int(channel["total_forwards"] * success_rate)
            channel["htlc_success_rate"] = success_rate
            
        # Appliquer les frais selon la politique
        if "base_fee" in scenario and "fee_rate" in scenario:
            channel["local_fee_base_msat"] = scenario["base_fee"] * 1000  # Convertir en msat
            channel["local_fee_rate"] = scenario["fee_rate"]
            
        # Appliquer la centralité
        if "node_centrality" in scenario:
            channel["centrality_score"] = scenario["node_centrality"]
            # La centralité influence l'uptime et la stabilité
            channel["uptime"] = 0.9 + 0.09 * scenario["node_centrality"]
            channel["channel_stability"] = 0.7 + 0.3 * scenario["node_centrality"]
            
        # Appliquer la volatilité du réseau
        if "network_volatility" in scenario:
            # Plus la volatilité est élevée, plus le taux de réussite est bas
            volatility = scenario["network_volatility"]
            channel["htlc_success_rate"] *= (1 - volatility / 2)
            channel["channel_stability"] *= (1 - volatility / 3)
            channel["fee_competitiveness"] = random.uniform(0.3, 0.7)
            
        # Ajouter du bruit aléatoire pour plus de réalisme
        for key in ["htlc_success_rate", "uptime", "channel_stability", "peer_retention_rate"]:
            if key in channel:
                channel[key] = min(1.0, max(0.0, channel[key] * random.uniform(0.95, 1.05)))
                
        # Dériver quelques métriques
        channel["capital_efficiency"] = channel["successful_forwards"] / max(1, channel["capacity"] / 100000)
        
        return channel
    
    def generate_network_topology(self, num_nodes: int, num_channels: int, 
                                scenario: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Génère une topologie de réseau simplifiée selon les paramètres du scénario
        
        Args:
            num_nodes: Nombre de nœuds dans le réseau
            num_channels: Nombre de canaux entre les nœuds
            scenario: Paramètres du scénario (optionnel)
            
        Returns:
            Dictionnaire contenant la topologie du réseau
        """
        if not scenario:
            # Utiliser des valeurs par défaut modérées
            scenario = {
                "node_centrality": 0.5,
                "network_volatility": 0.3
            }
            
        # Générer les nœuds
        nodes = []
        for i in range(num_nodes):
            # Varier la centralité autour de la valeur de référence
            if "node_centrality" in scenario:
                base_centrality = scenario["node_centrality"]
                variation = random.uniform(-0.2, 0.2)
                centrality = max(0.1, min(0.9, base_centrality + variation))
            else:
                centrality = random.uniform(0.1, 0.9)
                
            nodes.append({
                "pubkey": f"0{i+100000}",
                "alias": f"Node_{i+1}",
                "centrality": centrality,
                "channels_count": 0
            })
            
        # Générer les canaux
        channels = []
        
        # Garantir que chaque nœud a au moins un canal
        for i in range(num_nodes):
            # Trouver un autre nœud pour créer un canal
            j = (i + 1) % num_nodes
            
            # Créer le canal
            channel_params = self.generate_channel_parameters(scenario)
            channel_params["node1_index"] = i
            channel_params["node2_index"] = j
            channels.append(channel_params)
            
            # Incrémenter le compteur de canaux
            nodes[i]["channels_count"] += 1
            nodes[j]["channels_count"] += 1
            
        # Ajouter des canaux supplémentaires
        remaining_channels = num_channels - num_nodes
        
        for _ in range(remaining_channels):
            # Sélectionner deux nœuds distincts
            i, j = random.sample(range(num_nodes), 2)
            
            # Créer le canal
            channel_params = self.generate_channel_parameters(scenario)
            channel_params["node1_index"] = i
            channel_params["node2_index"] = j
            channels.append(channel_params)
            
            # Incrémenter le compteur de canaux
            nodes[i]["channels_count"] += 1
            nodes[j]["channels_count"] += 1
            
        # Calculer les métriques de centralité basées sur le degré
        max_channels = max(node["channels_count"] for node in nodes)
        for node in nodes:
            # Normaliser la centralité de degré
            node["degree_centrality"] = node["channels_count"] / max(1, max_channels)
            
        return {
            "nodes": nodes,
            "channels": channels,
            "network_parameters": {
                "volatility": scenario.get("network_volatility", 0.3),
                "average_centrality": sum(node["centrality"] for node in nodes) / num_nodes,
                "density": (2 * num_channels) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0
            }
        } 