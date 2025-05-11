import networkx as nx
from typing import Dict, List, Any
import numpy as np

class NetworkTopologyAnalyzer:
    def __init__(self):
        self.graph = nx.Graph()
        
    def build_network_graph(self, channels: List[Dict[str, Any]]):
        """Construit le graphe du réseau à partir des données des canaux"""
        self.graph.clear()
        for channel in channels:
            self.graph.add_edge(
                channel["local_node_id"],
                channel["remote_node_id"],
                capacity=channel.get("capacity", 0),
                local_balance=channel.get("local_balance", 0)
            )
    
    def calculate_node_centrality(self, node_id: str) -> Dict[str, float]:
        """Calcule différentes mesures de centralité pour un nœud"""
        if not self.graph.has_node(node_id):
            return {}
            
        centrality_metrics = {
            "degree": nx.degree_centrality(self.graph)[node_id],
            "betweenness": nx.betweenness_centrality(self.graph)[node_id],
            "eigenvector": nx.eigenvector_centrality(self.graph, max_iter=1000)[node_id],
            "closeness": nx.closeness_centrality(self.graph)[node_id]
        }
        
        return centrality_metrics
        
    def calculate_node_influence(self, node_id: str) -> Dict[str, float]:
        """Calcule l'influence d'un nœud basée sur sa position et ses connexions"""
        if not self.graph.has_node(node_id):
            return {}
            
        # Calculer le PageRank comme mesure d'influence
        pagerank = nx.pagerank(self.graph)
        
        # Calculer la force des connexions (weighted degree)
        weighted_degree = 0
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)
            weighted_degree += edge_data.get("capacity", 0)
            
        return {
            "pagerank": pagerank[node_id],
            "weighted_degree": weighted_degree,
            "neighbor_count": self.graph.degree(node_id)
        }
        
    def get_topological_features(self, node_id: str) -> Dict[str, float]:
        """Combine toutes les métriques topologiques pour un nœud"""
        centrality = self.calculate_node_centrality(node_id)
        influence = self.calculate_node_influence(node_id)
        
        return {
            **centrality,
            **influence
        } 