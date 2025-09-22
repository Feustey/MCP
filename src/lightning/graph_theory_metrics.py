"""
Métriques de théorie des graphes pour Lightning Network
Analyse de centralité, hubness, hopness, transitivité, densité
"""

import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import math

logger = logging.getLogger("mcp.graph_theory")

class LightningGraphAnalyzer:
    """
    Analyseur de métriques avancées de théorie des graphes pour Lightning Network
    """
    
    def __init__(self):
        self.graph = nx.Graph()
        self.directed_graph = nx.DiGraph() 
        self.channel_capacities = {}
        self.node_features = {}
        
    def build_graph(self, nodes: List[Dict], channels: List[Dict]) -> None:
        """Construit les graphes dirigé et non-dirigé"""
        self.graph.clear()
        self.directed_graph.clear()
        self.channel_capacities.clear()
        self.node_features.clear()
        
        # Ajouter nœuds avec métadonnées
        for node in nodes:
            pubkey = node['pubkey']
            features = {
                'alias': node.get('alias', ''),
                'color': node.get('color', ''),
                'capacity': node.get('total_capacity', 0),
                'num_channels': node.get('num_channels', 0),
                'last_update': node.get('last_update', 0)
            }
            
            self.graph.add_node(pubkey, **features)
            self.directed_graph.add_node(pubkey, **features)
            self.node_features[pubkey] = features
            
        # Ajouter canaux
        for channel in channels:
            node1 = channel['node1_pub']
            node2 = channel['node2_pub'] 
            capacity = channel.get('capacity', 0)
            chan_id = channel['channel_id']
            
            # Graphe non-dirigé pour métriques globales
            self.graph.add_edge(node1, node2, capacity=capacity, channel_id=chan_id)
            
            # Graphe dirigé pour analyse de flow
            fee1 = channel.get('node1_fee_rate', 0)
            fee2 = channel.get('node2_fee_rate', 0)
            
            self.directed_graph.add_edge(node1, node2, capacity=capacity, fee_rate=fee1, channel_id=chan_id)
            self.directed_graph.add_edge(node2, node1, capacity=capacity, fee_rate=fee2, channel_id=chan_id)
            
            self.channel_capacities[chan_id] = capacity
    
    def calculate_centrality_metrics(self, node_pubkey: str = None) -> Dict[str, Any]:
        """
        Calcule toutes les métriques de centralité pour un nœud ou le réseau entier
        """
        if self.graph.number_of_nodes() == 0:
            return {"error": "Graphe vide"}
            
        try:
            results = {}
            
            if node_pubkey:
                # Métriques pour un nœud spécifique
                if node_pubkey not in self.graph:
                    return {"error": f"Nœud {node_pubkey} non trouvé"}
                    
                results = self._calculate_single_node_centrality(node_pubkey)
            else:
                # Métriques pour tout le réseau
                results = self._calculate_network_centrality_metrics()
                
            results['timestamp'] = datetime.utcnow().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Erreur calcul centralité: {str(e)}")
            return {"error": str(e)}
    
    def calculate_hubness_metrics(self, top_n: int = 50) -> Dict[str, Any]:
        """
        Calcule les métriques de hubness - identification des nœuds centraux
        """
        try:
            # Degree centrality pondérée par capacité
            weighted_degrees = {}
            for node in self.graph.nodes():
                total_capacity = sum(
                    self.graph[node][neighbor].get('capacity', 0) 
                    for neighbor in self.graph[node]
                )
                weighted_degrees[node] = {
                    'degree': self.graph.degree(node),
                    'weighted_degree': total_capacity,
                    'avg_channel_capacity': total_capacity / max(1, self.graph.degree(node))
                }
            
            # Betweenness centrality pour identifier les hubs de routage
            betweenness = nx.betweenness_centrality(self.graph, k=min(1000, self.graph.number_of_nodes()))
            
            # Closeness centrality pour mesurer l'efficacité de routage
            closeness = nx.closeness_centrality(self.graph)
            
            # Eigenvector centrality pour l'influence dans le réseau
            try:
                eigenvector = nx.eigenvector_centrality(self.graph, max_iter=1000)
            except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
                eigenvector = {}
                logger.warning("Eigenvector centrality failed to converge")
            
            # Combiner toutes les métriques
            hub_scores = {}
            for node in self.graph.nodes():
                hub_scores[node] = {
                    'hubness_score': self._calculate_hubness_score(
                        weighted_degrees.get(node, {}),
                        betweenness.get(node, 0),
                        closeness.get(node, 0),
                        eigenvector.get(node, 0)
                    ),
                    'degree': weighted_degrees.get(node, {}).get('degree', 0),
                    'weighted_degree': weighted_degrees.get(node, {}).get('weighted_degree', 0),
                    'betweenness': betweenness.get(node, 0),
                    'closeness': closeness.get(node, 0),
                    'eigenvector': eigenvector.get(node, 0),
                    'alias': self.node_features.get(node, {}).get('alias', node[:16])
                }
            
            # Top hubs
            sorted_hubs = sorted(hub_scores.items(), key=lambda x: x[1]['hubness_score'], reverse=True)
            top_hubs = dict(sorted_hubs[:top_n])
            
            return {
                'top_hubs': top_hubs,
                'network_stats': {
                    'total_nodes': self.graph.number_of_nodes(),
                    'total_edges': self.graph.number_of_edges(),
                    'avg_hubness_score': np.mean([score['hubness_score'] for score in hub_scores.values()]),
                    'hubness_concentration': self._calculate_hubness_concentration(hub_scores)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul hubness: {str(e)}")
            return {"error": str(e)}
    
    def calculate_hopness_metrics(self, source_nodes: List[str] = None, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Calcule les métriques de hopness - efficacité de routage par distance
        """
        try:
            if source_nodes is None:
                # Sélectionner un échantillon représentatif de nœuds
                all_nodes = list(self.graph.nodes())
                source_nodes = np.random.choice(
                    all_nodes, 
                    size=min(sample_size, len(all_nodes)), 
                    replace=False
                ).tolist()
            
            hopness_results = {}
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Calcul parallèle des distances pour chaque nœud source
                futures = {
                    executor.submit(self._calculate_node_hopness, source): source 
                    for source in source_nodes
                }
                
                for future in futures:
                    source = futures[future]
                    try:
                        result = future.result(timeout=30)
                        hopness_results[source] = result
                    except Exception as e:
                        logger.warning(f"Erreur hopness pour {source}: {str(e)}")
            
            # Agréger les résultats
            aggregate_hopness = self._aggregate_hopness_results(hopness_results)
            
            return {
                'individual_hopness': hopness_results,
                'aggregate_metrics': aggregate_hopness,
                'sample_size': len(source_nodes),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul hopness: {str(e)}")
            return {"error": str(e)}
    
    def calculate_network_topology_metrics(self) -> Dict[str, Any]:
        """
        Calcule les métriques globales de topologie du réseau
        """
        try:
            if self.graph.number_of_nodes() == 0:
                return {"error": "Graphe vide"}
            
            # Métriques de base
            n_nodes = self.graph.number_of_nodes()
            n_edges = self.graph.number_of_edges()
            
            # Densité du graphe
            density = nx.density(self.graph)
            
            # Diamètre et rayon (sur plus grande composante connexe si nécessaire)
            if nx.is_connected(self.graph):
                diameter = nx.diameter(self.graph)
                radius = nx.radius(self.graph)
                giant_component_size = n_nodes
            else:
                # Plus grande composante connexe
                largest_cc = max(nx.connected_components(self.graph), key=len)
                giant_subgraph = self.graph.subgraph(largest_cc)
                diameter = nx.diameter(giant_subgraph)
                radius = nx.radius(giant_subgraph)
                giant_component_size = len(largest_cc)
            
            # Transitivité (clustering global)
            transitivity = nx.transitivity(self.graph)
            
            # Coefficient de clustering moyen
            avg_clustering = nx.average_clustering(self.graph)
            
            # Assortativité (tendance à se connecter à des nœuds similaires)
            try:
                degree_assortativity = nx.degree_assortativity_coefficient(self.graph)
            except:
                degree_assortativity = None
            
            # Métriques de capacité
            total_network_capacity = sum(self.channel_capacities.values())
            avg_channel_capacity = np.mean(list(self.channel_capacities.values())) if self.channel_capacities else 0
            
            # Distribution des degrés
            degrees = [self.graph.degree(n) for n in self.graph.nodes()]
            degree_distribution = {
                'mean': np.mean(degrees),
                'std': np.std(degrees),
                'min': min(degrees),
                'max': max(degrees),
                'median': np.median(degrees)
            }
            
            # Cut edges et articulation points (points critiques)
            cut_edges = list(nx.bridges(self.graph))
            articulation_points = list(nx.articulation_points(self.graph))
            
            return {
                'basic_metrics': {
                    'nodes': n_nodes,
                    'edges': n_edges,
                    'density': density,
                    'diameter': diameter,
                    'radius': radius,
                    'giant_component_ratio': giant_component_size / n_nodes
                },
                'clustering_metrics': {
                    'transitivity': transitivity,
                    'average_clustering': avg_clustering,
                    'degree_assortativity': degree_assortativity
                },
                'capacity_metrics': {
                    'total_network_capacity': total_network_capacity,
                    'average_channel_capacity': avg_channel_capacity,
                    'capacity_distribution': self._analyze_capacity_distribution()
                },
                'degree_distribution': degree_distribution,
                'critical_points': {
                    'cut_edges_count': len(cut_edges),
                    'articulation_points_count': len(articulation_points),
                    'network_robustness_score': self._calculate_robustness_score(cut_edges, articulation_points, n_nodes)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur métriques topologie: {str(e)}")
            return {"error": str(e)}
    
    def analyze_node_positioning(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Analyse complète de la position d'un nœud dans le réseau
        """
        if node_pubkey not in self.graph:
            return {"error": f"Nœud {node_pubkey} non trouvé"}
            
        try:
            # Métriques de centralité
            centrality = self._calculate_single_node_centrality(node_pubkey)
            
            # Position dans les rankings
            all_degrees = {n: self.graph.degree(n) for n in self.graph.nodes()}
            degree_rank = sorted(all_degrees.items(), key=lambda x: x[1], reverse=True)
            node_degree_rank = next(i for i, (n, _) in enumerate(degree_rank, 1) if n == node_pubkey)
            
            # Voisinage et influence locale
            neighbors = list(self.graph[node_pubkey])
            neighbor_degrees = [self.graph.degree(n) for n in neighbors]
            
            # Capacité et distribution
            node_capacity = sum(self.graph[node_pubkey][neighbor].get('capacity', 0) for neighbor in neighbors)
            capacity_distribution = [self.graph[node_pubkey][neighbor].get('capacity', 0) for neighbor in neighbors]
            
            # Métriques de positionnement stratégique
            strategic_metrics = self._calculate_strategic_positioning(node_pubkey)
            
            return {
                'node_pubkey': node_pubkey,
                'alias': self.node_features.get(node_pubkey, {}).get('alias', ''),
                'centrality_metrics': centrality,
                'ranking': {
                    'degree_rank': node_degree_rank,
                    'degree_percentile': (1 - node_degree_rank / len(degree_rank)) * 100
                },
                'local_neighborhood': {
                    'num_neighbors': len(neighbors),
                    'avg_neighbor_degree': np.mean(neighbor_degrees) if neighbor_degrees else 0,
                    'neighbor_degree_std': np.std(neighbor_degrees) if neighbor_degrees else 0,
                    'total_capacity': node_capacity,
                    'avg_channel_capacity': np.mean(capacity_distribution) if capacity_distribution else 0,
                    'capacity_std': np.std(capacity_distribution) if capacity_distribution else 0
                },
                'strategic_positioning': strategic_metrics,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse positionnement {node_pubkey}: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_single_node_centrality(self, node_pubkey: str) -> Dict[str, float]:
        """Calcule les métriques de centralité pour un nœud"""
        # Degree centrality
        degree_cent = nx.degree_centrality(self.graph)[node_pubkey]
        
        # Betweenness centrality (échantillonné pour performance)
        k = min(1000, self.graph.number_of_nodes())
        betweenness_cent = nx.betweenness_centrality(self.graph, k=k).get(node_pubkey, 0)
        
        # Closeness centrality
        closeness_cent = nx.closeness_centrality(self.graph).get(node_pubkey, 0)
        
        # Eigenvector centrality
        try:
            eigenvector_cent = nx.eigenvector_centrality(self.graph, max_iter=1000).get(node_pubkey, 0)
        except:
            eigenvector_cent = 0
            
        return {
            'degree_centrality': degree_cent,
            'betweenness_centrality': betweenness_cent,  
            'closeness_centrality': closeness_cent,
            'eigenvector_centrality': eigenvector_cent
        }
    
    def _calculate_network_centrality_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques de centralité pour tout le réseau"""
        # Calculer toutes les centralités
        degree_cent = nx.degree_centrality(self.graph)
        k = min(1000, self.graph.number_of_nodes())
        betweenness_cent = nx.betweenness_centrality(self.graph, k=k)
        closeness_cent = nx.closeness_centrality(self.graph)
        
        try:
            eigenvector_cent = nx.eigenvector_centrality(self.graph, max_iter=1000)
        except:
            eigenvector_cent = {}
            
        return {
            'degree_centrality': degree_cent,
            'betweenness_centrality': betweenness_cent,
            'closeness_centrality': closeness_cent,
            'eigenvector_centrality': eigenvector_cent,
            'centralization_metrics': {
                'degree_centralization': self._calculate_centralization(degree_cent),
                'betweenness_centralization': self._calculate_centralization(betweenness_cent),
                'closeness_centralization': self._calculate_centralization(closeness_cent)
            }
        }
    
    def _calculate_hubness_score(self, weighted_degree: Dict, betweenness: float, closeness: float, eigenvector: float) -> float:
        """Calcule un score composite de hubness"""
        degree = weighted_degree.get('degree', 0)
        w_degree = weighted_degree.get('weighted_degree', 0)
        
        # Normalisation et pondération
        normalized_degree = min(1.0, degree / 100)  # Normaliser à 100 connexions max
        normalized_w_degree = min(1.0, w_degree / 1e9)  # Normaliser à 1 BTC
        
        # Score composite pondéré
        hubness_score = (
            0.3 * normalized_degree +
            0.3 * normalized_w_degree +
            0.2 * betweenness +
            0.1 * closeness +
            0.1 * eigenvector
        )
        
        return hubness_score
    
    def _calculate_hubness_concentration(self, hub_scores: Dict) -> float:
        """Calcule la concentration des scores de hubness (indice de Gini)"""
        scores = [score['hubness_score'] for score in hub_scores.values()]
        if not scores:
            return 0.0
            
        # Calcul indice de Gini simplifié
        scores_sorted = sorted(scores)
        n = len(scores_sorted)
        cumsum = np.cumsum(scores_sorted)
        
        return (n + 1 - 2 * sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0
    
    def _calculate_node_hopness(self, source: str) -> Dict[str, Any]:
        """Calcule les métriques de hopness pour un nœud source"""
        try:
            # Plus courts chemins depuis ce nœud
            shortest_paths = nx.single_source_shortest_path_length(self.graph, source)
            
            # Distribution des distances
            distances = list(shortest_paths.values())
            reachable_nodes = len(distances) - 1  # Exclure le nœud lui-même
            
            if reachable_nodes == 0:
                return {'reachability': 0, 'avg_distance': float('inf'), 'efficiency': 0}
            
            avg_distance = sum(d for d in distances if d > 0) / reachable_nodes
            max_distance = max(distances)
            
            # Efficacité de routage (inverse de la distance moyenne)
            efficiency = 1.0 / avg_distance if avg_distance > 0 else 0
            
            # Distribution des distances
            distance_dist = {}
            for d in distances:
                distance_dist[d] = distance_dist.get(d, 0) + 1
            
            return {
                'reachability': reachable_nodes / (self.graph.number_of_nodes() - 1),
                'avg_distance': avg_distance,
                'max_distance': max_distance,
                'routing_efficiency': efficiency,
                'distance_distribution': distance_dist
            }
            
        except Exception as e:
            logger.error(f"Erreur hopness pour {source}: {str(e)}")
            return {'error': str(e)}
    
    def _aggregate_hopness_results(self, individual_results: Dict) -> Dict[str, Any]:
        """Agrège les résultats de hopness individuels"""
        valid_results = {k: v for k, v in individual_results.items() if 'error' not in v}
        
        if not valid_results:
            return {'error': 'Aucun résultat valide'}
        
        reachabilities = [r['reachability'] for r in valid_results.values()]
        avg_distances = [r['avg_distance'] for r in valid_results.values() if r['avg_distance'] != float('inf')]
        efficiencies = [r['routing_efficiency'] for r in valid_results.values()]
        
        return {
            'network_reachability': {
                'mean': np.mean(reachabilities),
                'std': np.std(reachabilities),
                'min': min(reachabilities),
                'max': max(reachabilities)
            },
            'network_distances': {
                'mean': np.mean(avg_distances) if avg_distances else float('inf'),
                'std': np.std(avg_distances) if avg_distances else 0,
                'median': np.median(avg_distances) if avg_distances else float('inf')
            },
            'routing_efficiency': {
                'mean': np.mean(efficiencies),
                'std': np.std(efficiencies),
                'network_efficiency_score': np.mean(efficiencies)
            }
        }
    
    def _analyze_capacity_distribution(self) -> Dict[str, Any]:
        """Analyse la distribution des capacités de canaux"""
        capacities = list(self.channel_capacities.values())
        if not capacities:
            return {}
            
        # Statistiques descriptives
        stats = {
            'mean': np.mean(capacities),
            'median': np.median(capacities),
            'std': np.std(capacities),
            'min': min(capacities),
            'max': max(capacities),
            'total': sum(capacities)
        }
        
        # Percentiles
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            stats[f'p{p}'] = np.percentile(capacities, p)
        
        # Coefficient de Gini pour l'inégalité
        stats['gini_coefficient'] = self._calculate_gini(capacities)
        
        return stats
    
    def _calculate_robustness_score(self, cut_edges: List, articulation_points: List, total_nodes: int) -> float:
        """Calcule un score de robustesse du réseau"""
        if total_nodes <= 1:
            return 0.0
            
        # Pénaliser les points critiques
        edge_penalty = len(cut_edges) / max(1, self.graph.number_of_edges())
        node_penalty = len(articulation_points) / total_nodes
        
        # Score de robustesse (0 = fragile, 1 = robuste)
        robustness = max(0.0, 1.0 - 2 * edge_penalty - node_penalty)
        return robustness
    
    def _calculate_strategic_positioning(self, node_pubkey: str) -> Dict[str, Any]:
        """Calcule les métriques de positionnement stratégique"""
        neighbors = list(self.graph[node_pubkey])
        
        # Connectivité avec des hubs (nœuds haute centralité)
        hub_connections = 0
        total_neighbor_centrality = 0
        
        for neighbor in neighbors:
            neighbor_degree = self.graph.degree(neighbor)
            total_neighbor_centrality += neighbor_degree
            if neighbor_degree > np.percentile([self.graph.degree(n) for n in self.graph.nodes()], 90):
                hub_connections += 1
        
        avg_neighbor_centrality = total_neighbor_centrality / len(neighbors) if neighbors else 0
        
        # Positionnement géographique dans le graphe
        try:
            eccentricity = nx.eccentricity(self.graph, node_pubkey)
        except nx.NetworkXError:
            eccentricity = float('inf')
        
        return {
            'hub_connections': hub_connections,
            'hub_connection_ratio': hub_connections / len(neighbors) if neighbors else 0,
            'avg_neighbor_centrality': avg_neighbor_centrality,
            'eccentricity': eccentricity,
            'strategic_score': self._calculate_strategic_score(hub_connections, avg_neighbor_centrality, eccentricity)
        }
    
    def _calculate_strategic_score(self, hub_connections: int, avg_neighbor_centrality: float, eccentricity: float) -> float:
        """Score composite de positionnement stratégique"""
        hub_score = min(1.0, hub_connections / 10)  # Normaliser à 10 connexions hub max
        centrality_score = min(1.0, avg_neighbor_centrality / 50)  # Normaliser
        eccentricity_score = max(0.0, 1.0 - eccentricity / 10) if eccentricity != float('inf') else 0
        
        return (hub_score * 0.4 + centrality_score * 0.4 + eccentricity_score * 0.2)
    
    def _calculate_centralization(self, centrality_dict: Dict[str, float]) -> float:
        """Calcule l'indice de centralisation du réseau"""
        if not centrality_dict:
            return 0.0
            
        values = list(centrality_dict.values())
        max_val = max(values)
        n = len(values)
        
        if n <= 2 or max_val == 0:
            return 0.0
        
        # Indice de centralisation de Freeman
        numerator = sum(max_val - val for val in values)
        denominator = (n - 1) * (n - 2) if n > 2 else 1
        
        return numerator / denominator
    
    def _calculate_gini(self, values: List[float]) -> float:
        """Calcule le coefficient de Gini"""
        if not values:
            return 0.0
            
        sorted_values = sorted(values)
        n = len(sorted_values)
        cumsum = np.cumsum(sorted_values)
        
        return (n + 1 - 2 * sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0