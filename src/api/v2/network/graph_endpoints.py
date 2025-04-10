from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import networkx as nx
import json
from datetime import datetime
from src.auth.jwt import get_current_user
from src.auth.models import User

# Importer le service existant d'analyse de graphe
from mcp.graph_analysis import build_graph, calculate_centralities

# Créer le router
router = APIRouter(
    prefix="/network",
    tags=["Network Graph Analysis v2"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Modèles de données
class GraphParameters(BaseModel):
    """Paramètres pour l'analyse de graphe"""
    depth: int = Field(3, description="Profondeur d'exploration du graphe", ge=1, le=10)
    max_nodes: int = Field(500, description="Nombre maximum de nœuds", ge=10, le=5000)
    include_metrics: bool = Field(True, description="Inclure les métriques de centralité")
    node_filter: Optional[List[str]] = Field(None, description="Filtrer par pubkeys spécifiques")
    cluster_algorithm: Optional[str] = Field("louvain", description="Algorithme de clustering (louvain, modularity, hierarchical)")
    filter_min_channels: Optional[int] = Field(None, description="Nombre minimum de canaux")
    filter_min_capacity: Optional[float] = Field(None, description="Capacité minimale en BTC")

class CommunityInfo(BaseModel):
    """Information sur une communauté dans le graphe"""
    community_id: int = Field(..., description="Identifiant de la communauté")
    node_count: int = Field(..., description="Nombre de nœuds dans la communauté")
    total_channels: int = Field(..., description="Nombre total de canaux dans la communauté")
    total_capacity: float = Field(..., description="Capacité totale de la communauté en BTC")
    central_nodes: List[str] = Field(..., description="Nœuds les plus centraux dans la communauté")

class GraphResponse(BaseModel):
    """Réponse de l'analyse de graphe"""
    total_nodes: int = Field(..., description="Nombre total de nœuds dans le graphe")
    total_edges: int = Field(..., description="Nombre total d'arêtes dans le graphe")
    average_degree: float = Field(..., description="Degré moyen des nœuds")
    density: float = Field(..., description="Densité du graphe")
    diameter: Optional[int] = Field(None, description="Diamètre du graphe (distance maximale)")
    average_path_length: Optional[float] = Field(None, description="Longueur moyenne des chemins")
    clustering_coefficient: float = Field(..., description="Coefficient de clustering moyen")
    connected_components: int = Field(..., description="Nombre de composantes connexes")
    communities: Optional[List[CommunityInfo]] = Field(None, description="Informations sur les communautés")
    top_nodes: Dict[str, List[str]] = Field(..., description="Top nœuds par différentes métriques")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Horodatage de l'analyse")

class TopologyFormat(BaseModel):
    """Format de la réponse pour la topologie"""
    format: str = Field("json", description="Format de sortie (json, graphml, gexf)")
    include_weights: bool = Field(True, description="Inclure les poids des arêtes")
    include_metadata: bool = Field(True, description="Inclure les métadonnées des nœuds")
    compressed: bool = Field(False, description="Compresser la sortie")

def detect_communities(G: nx.Graph, algorithm: str = "louvain") -> Dict[str, int]:
    """
    Détecte les communautés dans le graphe en utilisant différents algorithmes
    
    Args:
        G: Le graphe NetworkX
        algorithm: L'algorithme à utiliser (louvain, modularity, hierarchical)
        
    Returns:
        Un dictionnaire avec les nœuds comme clés et les communautés comme valeurs
    """
    try:
        if algorithm == "louvain":
            from community import best_partition
            return best_partition(G)
        elif algorithm == "modularity":
            from networkx.algorithms.community import greedy_modularity_communities
            communities = list(greedy_modularity_communities(G))
            # Convertir le format pour être cohérent
            result = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    result[node] = i
            return result
        elif algorithm == "hierarchical":
            from networkx.algorithms.community import girvan_newman
            import itertools
            comp = girvan_newman(G)
            # Limiter à 2 niveaux pour des raisons de performance
            limited_comp = itertools.islice(comp, 2)
            communities = list(limited_comp)
            # Utiliser le dernier niveau
            last_level = list(communities[-1])
            result = {}
            for i, comm in enumerate(last_level):
                for node in comm:
                    result[node] = i
            return result
        else:
            # Fallback sur l'algorithme de clustering par coefficient
            from networkx.algorithms import clustering
            clusters = clustering(G)
            # Normaliser en groupes distincts (simpliste)
            sorted_nodes = sorted(clusters.items(), key=lambda x: x[1], reverse=True)
            result = {}
            current_cluster = 0
            current_value = -1
            for node, value in sorted_nodes:
                if current_value != value:
                    current_cluster += 1
                    current_value = value
                result[node] = current_cluster
            return result
    except ImportError:
        # Si les bibliothèques de communauté ne sont pas disponibles
        return {node: 0 for node in G.nodes()}  # Une seule communauté

def analyze_graph(G: nx.Graph, params: GraphParameters) -> GraphResponse:
    """
    Effectue une analyse complète du graphe avec les paramètres spécifiés
    
    Args:
        G: Le graphe NetworkX
        params: Les paramètres d'analyse
        
    Returns:
        Les résultats de l'analyse sous forme de GraphResponse
    """
    if G.number_of_nodes() == 0:
        raise ValueError("Graphe vide, impossible d'effectuer l'analyse")
    
    # Statistiques de base
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()
    
    # Calculer le degré moyen
    degrees = [d for _, d in G.degree()]
    average_degree = sum(degrees) / len(degrees) if degrees else 0
    
    # Densité du graphe
    density = nx.density(G)
    
    # Coefficient de clustering
    clustering_coefficient = nx.average_clustering(G)
    
    # Composantes connexes
    connected_components = nx.number_connected_components(G)
    
    # Initialiser les variables pour les métriques qui peuvent être coûteuses
    diameter = None
    average_path_length = None
    communities_info = None
    
    # Si le graphe n'est pas trop grand, calculer des métriques plus coûteuses
    if total_nodes <= 1000:
        # Calculer le diamètre et la longueur moyenne des chemins pour chaque composante
        components = list(nx.connected_components(G))
        weighted_diameter = 0
        weighted_path_length = 0
        total_component_nodes = 0
        
        for component in components:
            if len(component) > 1:  # Ignorer les nœuds isolés
                subgraph = G.subgraph(component)
                try:
                    # Calculer pour cette composante
                    component_diameter = nx.diameter(subgraph)
                    component_path_length = nx.average_shortest_path_length(subgraph)
                    
                    # Pondérer par la taille de la composante
                    weighted_diameter += component_diameter * len(component)
                    weighted_path_length += component_path_length * len(component)
                    total_component_nodes += len(component)
                except nx.NetworkXError:
                    # En cas d'erreur, ignorer cette composante
                    pass
        
        # Calculer les moyennes pondérées
        if total_component_nodes > 0:
            diameter = int(weighted_diameter / total_component_nodes)
            average_path_length = weighted_path_length / total_component_nodes
    
    # Analyse des communautés si demandée
    if params.include_metrics and params.cluster_algorithm:
        try:
            # Détecter les communautés
            community_map = detect_communities(G, params.cluster_algorithm)
            
            # Organiser les informations par communauté
            community_data = {}
            for node, comm_id in community_map.items():
                if comm_id not in community_data:
                    community_data[comm_id] = {
                        "nodes": [],
                        "channels": 0,
                        "capacity": 0.0
                    }
                community_data[comm_id]["nodes"].append(node)
                community_data[comm_id]["channels"] += G.degree(node)
            
            # Corriger le nombre de canaux (chaque canal est compté deux fois)
            for comm_id in community_data:
                community_data[comm_id]["channels"] //= 2
            
            # Calculer les centralités pour trouver les nœuds centraux
            centralities = calculate_centralities(G)
            
            # Créer la liste des informations sur les communautés
            communities_info = []
            for comm_id, data in community_data.items():
                # Trouver les nœuds les plus centraux dans cette communauté
                community_nodes = data["nodes"]
                community_betweenness = {
                    node: centralities[node]["betweenness"] 
                    for node in community_nodes 
                    if node in centralities
                }
                central_nodes = sorted(
                    community_betweenness.keys(),
                    key=lambda x: community_betweenness[x],
                    reverse=True
                )[:5]  # Top 5 des nœuds centraux
                
                communities_info.append(CommunityInfo(
                    community_id=comm_id,
                    node_count=len(community_nodes),
                    total_channels=data["channels"],
                    total_capacity=data["capacity"],
                    central_nodes=central_nodes
                ))
        except Exception as e:
            # En cas d'erreur dans l'analyse des communautés
            print(f"Erreur lors de l'analyse des communautés: {e}")
            communities_info = None
    
    # Trouver les nœuds les plus importants par différentes métriques
    top_nodes = {}
    
    if params.include_metrics:
        # Utiliser les centralités calculées précédemment
        centralities = calculate_centralities(G)
        
        # Top 10 nœuds par degré
        top_nodes["degree"] = sorted(
            G.nodes(),
            key=lambda x: centralities.get(x, {}).get("degree", 0),
            reverse=True
        )[:10]
        
        # Top 10 nœuds par betweenness
        top_nodes["betweenness"] = sorted(
            G.nodes(),
            key=lambda x: centralities.get(x, {}).get("betweenness", 0),
            reverse=True
        )[:10]
        
        # Top 10 nœuds par closeness
        top_nodes["closeness"] = sorted(
            G.nodes(),
            key=lambda x: centralities.get(x, {}).get("closeness", 0),
            reverse=True
        )[:10]
        
        # Top 10 nœuds par eigenvector
        top_nodes["eigenvector"] = sorted(
            G.nodes(),
            key=lambda x: centralities.get(x, {}).get("eigenvector", 0),
            reverse=True
        )[:10]
    
    # Assembler la réponse
    return GraphResponse(
        total_nodes=total_nodes,
        total_edges=total_edges,
        average_degree=average_degree,
        density=density,
        diameter=diameter,
        average_path_length=average_path_length,
        clustering_coefficient=clustering_coefficient,
        connected_components=connected_components,
        communities=communities_info,
        top_nodes=top_nodes
    )

@router.post("/graph", response_model=GraphResponse)
async def analyze_network_graph(
    params: GraphParameters = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Analyse avancée du graphe du réseau Lightning.
    
    Cette endpoint effectue une analyse approfondie du graphe du réseau Lightning,
    en calculant diverses métriques et en identifiant les structures importantes.
    
    Les résultats peuvent être utilisés pour visualiser le réseau, identifier les nœuds
    centraux et comprendre la topologie du réseau Lightning.
    """
    try:
        # Dans une implémentation réelle, vous récupéreriez les données des nœuds depuis votre base de données
        # Ici, nous allons simuler des données pour l'exemple
        filtered_nodes_data = []  # À remplacer par l'appel au service approprié
        
        # Construction du graphe à partir des données filtrées
        G = build_graph(filtered_nodes_data)
        
        # Filtrer le graphe selon les paramètres si nécessaire
        if params.node_filter:
            G = G.subgraph(set(params.node_filter) & set(G.nodes()))
        
        if params.filter_min_channels:
            G = G.subgraph([n for n, d in G.degree() if d >= params.filter_min_channels])
        
        # Analyser le graphe
        graph_analysis = analyze_graph(G, params)
        
        return graph_analysis
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse du graphe: {str(e)}")

@router.get("/topology")
async def get_network_topology(
    format: str = Query("json", description="Format de sortie (json, graphml, gexf)"),
    depth: int = Query(2, description="Profondeur d'exploration du graphe", ge=1, le=5),
    center_node: Optional[str] = Query(None, description="Nœud central pour l'exploration"),
    include_weights: bool = Query(True, description="Inclure les poids des arêtes"),
    include_metadata: bool = Query(True, description="Inclure les métadonnées des nœuds"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la topologie du réseau Lightning dans différents formats.
    
    Cette endpoint permet d'obtenir la structure du réseau Lightning dans
    différents formats adaptés à la visualisation et à l'analyse.
    
    Les formats disponibles sont:
    - json: Format JSON standard pour les applications web
    - graphml: Format GraphML pour les logiciels d'analyse de graphe
    - gexf: Format GEXF pour Gephi et autres outils de visualisation
    """
    try:
        # Dans une implémentation réelle, vous récupéreriez les données des nœuds depuis votre base de données
        # Ici, nous allons simuler des données pour l'exemple
        filtered_nodes_data = []  # À remplacer par l'appel au service approprié
        
        # Construction du graphe à partir des données filtrées
        G = build_graph(filtered_nodes_data)
        
        # Si un nœud central est spécifié, filtrer pour n'inclure que ce nœud et ses voisins jusqu'à la profondeur spécifiée
        if center_node and center_node in G:
            # Trouver tous les nœuds à la distance spécifiée
            nodes_at_depth = {center_node}
            current_depth = 0
            frontier = {center_node}
            
            while current_depth < depth:
                next_frontier = set()
                for node in frontier:
                    next_frontier.update(G.neighbors(node))
                frontier = next_frontier - nodes_at_depth  # Éviter de revisiter les nœuds
                nodes_at_depth.update(frontier)
                current_depth += 1
            
            # Créer un sous-graphe avec ces nœuds
            G = G.subgraph(nodes_at_depth)
        
        # Préparer les données selon le format demandé
        if format == "json":
            # Format JSON pour les applications web
            nodes = []
            for node in G.nodes():
                node_data = {
                    "id": node,
                    "connections": len(list(G.neighbors(node)))
                }
                if include_metadata:
                    # Ajouter des métadonnées si disponibles
                    node_data["metadata"] = {"alias": f"Node {node[:8]}"}  # Exemple, à remplacer par les vraies données
                nodes.append(node_data)
            
            edges = []
            for u, v in G.edges():
                edge_data = {
                    "source": u,
                    "target": v
                }
                if include_weights:
                    edge_data["weight"] = 1  # Exemple, à remplacer par les vraies données
                edges.append(edge_data)
            
            result = {
                "nodes": nodes,
                "edges": edges
            }
            
            return result
        
        elif format == "graphml":
            # Format GraphML pour les logiciels d'analyse de graphe
            import io
            from networkx.readwrite import graphml
            
            if include_metadata:
                # Ajouter des attributs aux nœuds si nécessaire
                for node in G.nodes():
                    G.nodes[node]["alias"] = f"Node {node[:8]}"  # Exemple
            
            if include_weights:
                # Ajouter des poids aux arêtes si nécessaire
                for u, v in G.edges():
                    G[u][v]["weight"] = 1  # Exemple
            
            # Écrire dans un buffer
            buffer = io.StringIO()
            graphml.write_graphml(G, buffer)
            
            # Retourner le contenu du buffer
            return {"content": buffer.getvalue(), "format": "graphml"}
        
        elif format == "gexf":
            # Format GEXF pour Gephi
            import io
            from networkx.readwrite import gexf
            
            if include_metadata:
                # Ajouter des attributs aux nœuds si nécessaire
                for node in G.nodes():
                    G.nodes[node]["alias"] = f"Node {node[:8]}"  # Exemple
            
            if include_weights:
                # Ajouter des poids aux arêtes si nécessaire
                for u, v in G.edges():
                    G[u][v]["weight"] = 1  # Exemple
            
            # Écrire dans un buffer
            buffer = io.StringIO()
            gexf.write_gexf(G, buffer)
            
            # Retourner le contenu du buffer
            return {"content": buffer.getvalue(), "format": "gexf"}
        
        else:
            raise ValueError(f"Format non supporté: {format}")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de la topologie: {str(e)}") 