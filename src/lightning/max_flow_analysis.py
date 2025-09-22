"""
Max Flow Analysis pour Lightning Network - Métrique cruciale pour probabilité de succès des paiements
Utilise les algorithmes Edmonds-Karp et Ford-Fulkerson optimisés pour Lightning Network
"""

import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, deque
import logging
from datetime import datetime

logger = logging.getLogger("mcp.max_flow")

class LightningMaxFlowAnalyzer:
    """
    Analyseur Max Flow optimisé pour Lightning Network
    Calcule les probabilités de succès des paiements et l'optimisation de liquidité
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.channel_capacities = {}
        self.channel_balances = {}
        self.fee_rates = {}
        
    def build_network_graph(self, nodes: List[Dict], channels: List[Dict]) -> None:
        """Construit le graphe du réseau Lightning à partir des données"""
        self.graph.clear()
        self.channel_capacities.clear()
        self.channel_balances.clear()
        self.fee_rates.clear()
        
        # Ajouter les nœuds
        for node in nodes:
            self.graph.add_node(node['pubkey'], **node)
            
        # Ajouter les canaux avec capacités et balances
        for channel in channels:
            node1 = channel['node1_pub']
            node2 = channel['node2_pub']
            chan_id = channel['channel_id']
            
            capacity = channel.get('capacity', 0)
            balance1 = channel.get('node1_balance', capacity // 2)  # Estimation si inconnue
            balance2 = capacity - balance1
            
            # Canal bidirectionnel avec balances différentes
            self.graph.add_edge(node1, node2, 
                               channel_id=chan_id,
                               capacity=balance1,  # Liquidity sortante de node1
                               fee_rate=channel.get('node1_fee_rate', 0))
            
            self.graph.add_edge(node2, node1,
                               channel_id=chan_id, 
                               capacity=balance2,  # Liquidity sortante de node2
                               fee_rate=channel.get('node2_fee_rate', 0))
            
            self.channel_capacities[chan_id] = capacity
            self.channel_balances[chan_id] = (balance1, balance2)
            
    def calculate_max_flow(self, source: str, target: str, amount: int = None) -> Dict[str, Any]:
        """
        Calcule le max flow entre deux nœuds
        Retourne probabilité de succès et chemins optimaux
        """
        if source not in self.graph or target not in self.graph:
            return {"error": "Source ou target non trouvé dans le graphe"}
            
        try:
            # Max flow avec NetworkX (utilise Edmonds-Karp)
            flow_value, flow_dict = nx.maximum_flow(self.graph, source, target, capacity='capacity')
            
            # Chemins de flow
            paths = self._extract_flow_paths(flow_dict, source, target)
            
            # Probabilité de succès basée sur amount vs max_flow
            if amount:
                success_probability = min(1.0, flow_value / amount) if amount > 0 else 1.0
            else:
                success_probability = 1.0 if flow_value > 0 else 0.0
                
            return {
                "max_flow_value": flow_value,
                "success_probability": success_probability,
                "flow_paths": paths,
                "bottleneck_analysis": self._analyze_bottlenecks(paths),
                "liquidity_distribution": self._analyze_liquidity_distribution(source, target),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul max flow {source} -> {target}: {str(e)}")
            return {"error": str(e)}
    
    def analyze_payment_probability(self, source: str, target: str, amounts: List[int]) -> Dict[str, Any]:
        """
        Analyse la probabilité de succès pour différents montants de paiement
        Essentiel pour l'optimisation de routage
        """
        probabilities = {}
        
        for amount in amounts:
            result = self.calculate_max_flow(source, target, amount)
            if "error" not in result:
                probabilities[amount] = result["success_probability"]
            else:
                probabilities[amount] = 0.0
                
        return {
            "payment_probabilities": probabilities,
            "optimal_amount": self._find_optimal_payment_size(probabilities),
            "liquidity_threshold": self._calculate_liquidity_threshold(source, target),
            "recommendations": self._generate_payment_recommendations(probabilities)
        }
    
    def analyze_network_liquidity(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Analyse complète de la liquidité d'un nœud dans le réseau
        """
        if node_pubkey not in self.graph:
            return {"error": "Nœud non trouvé"}
            
        # Liquidité sortante totale
        outbound_liquidity = sum(
            self.graph[node_pubkey][neighbor].get('capacity', 0)
            for neighbor in self.graph[node_pubkey]
        )
        
        # Liquidité entrante totale  
        inbound_liquidity = sum(
            self.graph[neighbor][node_pubkey].get('capacity', 0)
            for neighbor in self.graph.predecessors(node_pubkey)
        )
        
        # Max flow vers les top nodes du réseau
        top_nodes = self._get_top_nodes_by_centrality(10)
        max_flows_to_top = {}
        
        for target in top_nodes:
            if target != node_pubkey:
                result = self.calculate_max_flow(node_pubkey, target)
                if "error" not in result:
                    max_flows_to_top[target] = result["max_flow_value"]
        
        return {
            "node_pubkey": node_pubkey,
            "outbound_liquidity": outbound_liquidity,
            "inbound_liquidity": inbound_liquidity,
            "liquidity_ratio": inbound_liquidity / outbound_liquidity if outbound_liquidity > 0 else 0,
            "max_flows_to_top_nodes": max_flows_to_top,
            "average_reachability": np.mean(list(max_flows_to_top.values())) if max_flows_to_top else 0,
            "liquidity_distribution_score": self._calculate_liquidity_distribution_score(node_pubkey)
        }
        
    def recommend_liquidity_rebalancing(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Recommandations de rééquilibrage basées sur l'analyse Max Flow
        """
        if node_pubkey not in self.graph:
            return {"error": "Nœud non trouvé"}
            
        neighbors = list(self.graph[node_pubkey].keys())
        rebalancing_ops = []
        
        for neighbor in neighbors:
            # Analyser le déséquilibre de canal
            out_capacity = self.graph[node_pubkey][neighbor].get('capacity', 0)
            in_capacity = self.graph[neighbor][node_pubkey].get('capacity', 0)
            
            total_capacity = out_capacity + in_capacity
            balance_ratio = out_capacity / total_capacity if total_capacity > 0 else 0
            
            # Recommander rééquilibrage si déséquilibré
            if balance_ratio < 0.2:  # Trop peu de liquidité sortante
                recommended_move = int(total_capacity * 0.3)  # Viser 30% sortant
                rebalancing_ops.append({
                    "type": "rebalance_inbound",
                    "target_node": neighbor,
                    "recommended_amount": recommended_move,
                    "current_ratio": balance_ratio,
                    "priority": "high" if balance_ratio < 0.1 else "medium"
                })
            elif balance_ratio > 0.8:  # Trop de liquidité sortante
                recommended_move = int(total_capacity * 0.3)  # Viser 70% sortant
                rebalancing_ops.append({
                    "type": "rebalance_outbound", 
                    "target_node": neighbor,
                    "recommended_amount": recommended_move,
                    "current_ratio": balance_ratio,
                    "priority": "medium"
                })
                
        return {
            "node_pubkey": node_pubkey,
            "rebalancing_operations": sorted(rebalancing_ops, key=lambda x: x['priority']),
            "estimated_improvement": self._estimate_rebalancing_improvement(node_pubkey, rebalancing_ops),
            "cost_analysis": self._analyze_rebalancing_costs(rebalancing_ops)
        }
    
    def _extract_flow_paths(self, flow_dict: Dict, source: str, target: str) -> List[Dict]:
        """Extrait les chemins de flow du dictionnaire NetworkX"""
        paths = []
        
        def dfs_paths(current, path, remaining_flow):
            if current == target and remaining_flow > 0:
                paths.append({
                    "path": path.copy(),
                    "flow_amount": remaining_flow,
                    "hop_count": len(path) - 1
                })
                return
                
            for neighbor, flow_amount in flow_dict.get(current, {}).items():
                if flow_amount > 0 and neighbor not in path:
                    path.append(neighbor)
                    dfs_paths(neighbor, path, min(remaining_flow, flow_amount))
                    path.pop()
        
        dfs_paths(source, [source], float('inf'))
        return paths
    
    def _analyze_bottlenecks(self, paths: List[Dict]) -> Dict[str, Any]:
        """Identifie les goulots d'étranglement dans les chemins de flow"""
        if not paths:
            return {"bottlenecks": [], "analysis": "Aucun chemin disponible"}
            
        # Compter l'utilisation des arêtes
        edge_usage = defaultdict(int)
        for path in paths:
            nodes = path["path"]
            for i in range(len(nodes) - 1):
                edge = (nodes[i], nodes[i+1])
                edge_usage[edge] += path["flow_amount"]
        
        # Identifier les bottlenecks (arêtes les plus utilisées)
        sorted_edges = sorted(edge_usage.items(), key=lambda x: x[1], reverse=True)
        bottlenecks = sorted_edges[:5]  # Top 5 bottlenecks
        
        return {
            "bottlenecks": [{"edge": edge, "utilization": usage} for edge, usage in bottlenecks],
            "total_paths": len(paths),
            "average_hop_count": np.mean([p["hop_count"] for p in paths])
        }
    
    def _analyze_liquidity_distribution(self, source: str, target: str) -> Dict[str, Any]:
        """Analyse la distribution de liquidité entre source et target"""
        # Calculer la distribution des capacités des canaux sur les chemins courts
        try:
            shortest_paths = list(nx.all_shortest_paths(self.graph, source, target))
            capacities = []
            
            for path in shortest_paths[:10]:  # Limiter à 10 chemins
                path_capacities = []
                for i in range(len(path) - 1):
                    if self.graph.has_edge(path[i], path[i+1]):
                        capacity = self.graph[path[i]][path[i+1]].get('capacity', 0)
                        path_capacities.append(capacity)
                if path_capacities:
                    capacities.extend(path_capacities)
            
            if capacities:
                return {
                    "mean_capacity": np.mean(capacities),
                    "std_capacity": np.std(capacities),
                    "min_capacity": min(capacities),
                    "max_capacity": max(capacities),
                    "capacity_distribution": "uniform" if np.std(capacities) < np.mean(capacities) * 0.5 else "skewed"
                }
            else:
                return {"analysis": "Aucune donnée de capacité disponible"}
                
        except nx.NetworkXNoPath:
            return {"analysis": "Aucun chemin trouvé entre source et target"}
    
    def _get_top_nodes_by_centrality(self, count: int) -> List[str]:
        """Obtient les top nodes par centralité (degree centrality)"""
        centrality = nx.degree_centrality(self.graph.to_undirected())
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        return [node for node, _ in sorted_nodes[:count]]
    
    def _find_optimal_payment_size(self, probabilities: Dict[int, float]) -> Dict[str, Any]:
        """Trouve la taille de paiement optimale"""
        if not probabilities:
            return {"optimal_amount": 0, "confidence": 0.0}
            
        # Trouver le montant maximal avec probabilité > 0.9
        high_prob_amounts = [amount for amount, prob in probabilities.items() if prob > 0.9]
        
        if high_prob_amounts:
            optimal = max(high_prob_amounts)
            return {"optimal_amount": optimal, "confidence": probabilities[optimal]}
        else:
            # Sinon, prendre le montant avec la meilleure probabilité
            best_amount = max(probabilities, key=probabilities.get)
            return {"optimal_amount": best_amount, "confidence": probabilities[best_amount]}
    
    def _calculate_liquidity_threshold(self, source: str, target: str) -> int:
        """Calcule le seuil de liquidité critique"""
        result = self.calculate_max_flow(source, target)
        if "error" not in result:
            return result["max_flow_value"]
        return 0
    
    def _generate_payment_recommendations(self, probabilities: Dict[int, float]) -> List[str]:
        """Génère des recommandations basées sur les probabilités"""
        recommendations = []
        
        if not probabilities:
            return ["Aucune donnée disponible pour générer des recommandations"]
            
        max_amount = max(probabilities.keys())
        max_prob = max(probabilities.values())
        
        if max_prob < 0.5:
            recommendations.append("⚠️ Probabilité de succès faible - considérer des canaux alternatifs")
        elif max_prob > 0.95:
            recommendations.append("✅ Excellente connectivité - paiements fiables jusqu'à " + str(max_amount))
        
        # Analyser la courbe de probabilité
        amounts = sorted(probabilities.keys())
        probs = [probabilities[a] for a in amounts]
        
        # Trouver le point de chute critique
        for i in range(1, len(probs)):
            if probs[i-1] > 0.8 and probs[i] < 0.5:
                recommendations.append(f"📉 Chute critique de probabilité à {amounts[i]} sats")
                break
                
        return recommendations
    
    def _calculate_liquidity_distribution_score(self, node_pubkey: str) -> float:
        """Score de distribution de liquidité (0-1, 1 = optimal)"""
        neighbors = list(self.graph[node_pubkey].keys())
        if len(neighbors) < 2:
            return 0.0
            
        # Calculer la variance des capacités sortantes
        capacities = [self.graph[node_pubkey][neighbor].get('capacity', 0) for neighbor in neighbors]
        mean_cap = np.mean(capacities)
        
        if mean_cap == 0:
            return 0.0
            
        # Score basé sur l'uniformité (moins de variance = mieux)
        cv = np.std(capacities) / mean_cap  # Coefficient de variation
        return max(0.0, 1.0 - cv)  # Score inversé
    
    def _estimate_rebalancing_improvement(self, node_pubkey: str, operations: List[Dict]) -> Dict[str, float]:
        """Estime l'amélioration après rééquilibrage"""
        current_score = self._calculate_liquidity_distribution_score(node_pubkey)
        
        # Simulation simplifiée de l'amélioration
        if not operations:
            return {"current_score": current_score, "estimated_improvement": 0.0}
            
        # Estimer l'amélioration basée sur le nombre d'opérations prioritaires
        high_priority_ops = len([op for op in operations if op["priority"] == "high"])
        estimated_improvement = min(0.3, high_priority_ops * 0.1)  # Max 30% improvement
        
        return {
            "current_score": current_score,
            "estimated_score": min(1.0, current_score + estimated_improvement),
            "estimated_improvement": estimated_improvement
        }
    
    def _analyze_rebalancing_costs(self, operations: List[Dict]) -> Dict[str, Any]:
        """Analyse des coûts de rééquilibrage"""
        if not operations:
            return {"total_cost": 0, "operations": 0}
            
        total_amount = sum(op.get("recommended_amount", 0) for op in operations)
        
        # Estimation coût (0.1% du montant + frais base)
        estimated_cost = total_amount * 0.001 + len(operations) * 1000  # 1000 sats par opération
        
        return {
            "total_amount_to_move": total_amount,
            "operations_count": len(operations),
            "estimated_cost_sats": int(estimated_cost),
            "cost_percentage": estimated_cost / total_amount * 100 if total_amount > 0 else 0
        }