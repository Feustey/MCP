#!/usr/bin/env python3
"""
Network Graph Synchronizer - Synchronisation du graphe Lightning Network

Ce module gère :
- Récupération du graphe complet via LNBits/LND
- Mise à jour incrémentale (déltas)
- Calculs de topologie (centralité, chemins, etc.)
- Cache et persistence MongoDB
- Nettoyage automatique des nœuds/canaux inactifs

Dernière mise à jour: 15 octobre 2025
"""

import logging
import asyncio
import networkx as nx
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from collections import defaultdict

from src.clients.lnbits_client import LNBitsClient

logger = logging.getLogger(__name__)


class NetworkGraphSync:
    """
    Gestionnaire de synchronisation du graphe Lightning Network.
    """
    
    def __init__(
        self,
        lnbits_client: LNBitsClient,
        db=None,
        sync_interval: int = 3600  # 1 heure par défaut
    ):
        """
        Initialise le synchroniseur.
        
        Args:
            lnbits_client: Client LNBits pour récupérer le graphe
            db: Instance MongoDB (optionnel)
            sync_interval: Intervalle entre syncs (secondes)
        """
        self.lnbits = lnbits_client
        self.db = db
        self.sync_interval = sync_interval
        
        # Collections MongoDB
        self.nodes_collection = db["network_nodes"] if db else None
        self.channels_collection = db["network_channels"] if db else None
        self.graph_metadata = db["graph_metadata"] if db else None
        
        # Graph NetworkX en mémoire (cache)
        self.graph: Optional[nx.Graph] = None
        self.last_sync: Optional[datetime] = None
        
        # Statistiques
        self.stats = {
            "total_nodes": 0,
            "total_channels": 0,
            "avg_degree": 0.0,
            "diameter": 0,
            "avg_path_length": 0.0,
            "last_updated": None
        }
        
        logger.info(f"NetworkGraphSync initialisé (sync_interval={sync_interval}s)")
    
    async def full_sync(self) -> Dict[str, Any]:
        """
        Effectue une synchronisation complète du graphe.
        
        Returns:
            Statistiques de la synchronisation
        """
        logger.info("Démarrage synchronisation complète du graphe...")
        start_time = datetime.utcnow()
        
        sync_result = {
            "success": False,
            "started_at": start_time.isoformat(),
            "nodes_added": 0,
            "channels_added": 0,
            "errors": []
        }
        
        try:
            # 1. Récupérer le graphe complet via LNBits
            logger.info("Récupération du graphe via LNBits...")
            graph_data = await self.lnbits.describe_graph()
            
            if not graph_data:
                raise Exception("Pas de données de graphe reçues")
            
            # 2. Parser et stocker les nœuds
            nodes = graph_data.get("nodes", [])
            logger.info(f"Traitement de {len(nodes)} nœuds...")
            
            for node in nodes:
                try:
                    await self._store_node(node)
                    sync_result["nodes_added"] += 1
                except Exception as e:
                    logger.warning(f"Erreur stockage nœud: {e}")
                    sync_result["errors"].append(str(e))
            
            # 3. Parser et stocker les canaux
            channels = graph_data.get("edges", [])
            logger.info(f"Traitement de {len(channels)} canaux...")
            
            for channel in channels:
                try:
                    await self._store_channel(channel)
                    sync_result["channels_added"] += 1
                except Exception as e:
                    logger.warning(f"Erreur stockage canal: {e}")
                    sync_result["errors"].append(str(e))
            
            # 4. Construire le graphe NetworkX
            logger.info("Construction du graphe NetworkX...")
            await self._build_networkx_graph()
            
            # 5. Calculer les métriques topologiques
            logger.info("Calcul des métriques topologiques...")
            await self._calculate_topology_metrics()
            
            # 6. Mise à jour métadonnées
            self.last_sync = datetime.utcnow()
            sync_result["success"] = True
            sync_result["completed_at"] = self.last_sync.isoformat()
            sync_result["duration_seconds"] = (self.last_sync - start_time).total_seconds()
            
            await self._save_sync_metadata(sync_result)
            
            logger.info(
                f"✅ Synchronisation complète réussie: "
                f"{sync_result['nodes_added']} nœuds, "
                f"{sync_result['channels_added']} canaux en "
                f"{sync_result['duration_seconds']:.1f}s"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
            sync_result["error"] = str(e)
        
        return sync_result
    
    async def incremental_sync(self) -> Dict[str, Any]:
        """
        Effectue une synchronisation incrémentale (déltas uniquement).
        
        Returns:
            Statistiques de la synchronisation
        """
        logger.info("Synchronisation incrémentale...")
        
        # TODO: Implémenter sync incrémentale via getnetworkinfo + subscribeChannelGraph
        # Pour l'instant, fallback sur full sync
        
        logger.warning("Incremental sync not implemented, falling back to full sync")
        return await self.full_sync()
    
    async def _store_node(self, node_data: Dict[str, Any]):
        """Stocke un nœud dans MongoDB."""
        if not self.nodes_collection:
            return
        
        node_id = node_data.get("pub_key")
        if not node_id:
            return
        
        # Enrichir avec timestamp
        node_data["last_updated"] = datetime.utcnow()
        
        # Upsert
        await self.nodes_collection.update_one(
            {"pub_key": node_id},
            {"$set": node_data},
            upsert=True
        )
    
    async def _store_channel(self, channel_data: Dict[str, Any]):
        """Stocke un canal dans MongoDB."""
        if not self.channels_collection:
            return
        
        channel_id = channel_data.get("channel_id")
        if not channel_id:
            return
        
        # Enrichir avec timestamp
        channel_data["last_updated"] = datetime.utcnow()
        
        # Upsert
        await self.channels_collection.update_one(
            {"channel_id": channel_id},
            {"$set": channel_data},
            upsert=True
        )
    
    async def _build_networkx_graph(self):
        """Construit le graphe NetworkX à partir des données MongoDB."""
        if not self.nodes_collection or not self.channels_collection:
            logger.warning("MongoDB non disponible, graph non construit")
            return
        
        # Créer graph
        G = nx.Graph()
        
        # Ajouter nœuds
        async for node in self.nodes_collection.find({}):
            node_id = node.get("pub_key")
            G.add_node(node_id, **node)
        
        # Ajouter arêtes (canaux)
        async for channel in self.channels_collection.find({}):
            node1 = channel.get("node1_pub")
            node2 = channel.get("node2_pub")
            
            if node1 and node2 and G.has_node(node1) and G.has_node(node2):
                G.add_edge(
                    node1,
                    node2,
                    channel_id=channel.get("channel_id"),
                    capacity=channel.get("capacity", 0)
                )
        
        self.graph = G
        
        logger.info(
            f"Graph construit: {G.number_of_nodes()} nœuds, "
            f"{G.number_of_edges()} arêtes"
        )
    
    async def _calculate_topology_metrics(self):
        """Calcule les métriques topologiques du graphe."""
        if not self.graph:
            logger.warning("Pas de graphe disponible pour calcul métriques")
            return
        
        G = self.graph
        
        try:
            # Nombre de nœuds et canaux
            self.stats["total_nodes"] = G.number_of_nodes()
            self.stats["total_channels"] = G.number_of_edges()
            
            # Degré moyen
            degrees = [d for n, d in G.degree()]
            self.stats["avg_degree"] = sum(degrees) / len(degrees) if degrees else 0
            
            # Pour les métriques globales, utiliser composante connexe principale
            if nx.is_connected(G):
                largest_cc = G
            else:
                # Récupérer la plus grande composante connexe
                largest_cc = max(nx.connected_components(G), key=len)
                largest_cc = G.subgraph(largest_cc).copy()
            
            # Diamètre (coûteux, limiter la taille)
            if largest_cc.number_of_nodes() < 10000:
                try:
                    self.stats["diameter"] = nx.diameter(largest_cc)
                except:
                    self.stats["diameter"] = 0
            else:
                self.stats["diameter"] = 0  # Trop coûteux
            
            # Longueur moyenne des chemins (échantillon)
            if largest_cc.number_of_nodes() < 5000:
                try:
                    self.stats["avg_path_length"] = nx.average_shortest_path_length(largest_cc)
                except:
                    self.stats["avg_path_length"] = 0.0
            else:
                self.stats["avg_path_length"] = 0.0
            
            self.stats["last_updated"] = datetime.utcnow().isoformat()
            
            logger.info(f"Métriques calculées: {self.stats}")
            
        except Exception as e:
            logger.error(f"Erreur calcul métriques topologiques: {e}")
    
    async def _save_sync_metadata(self, sync_result: Dict[str, Any]):
        """Sauvegarde les métadonnées de synchronisation."""
        if not self.graph_metadata:
            return
        
        metadata = {
            "sync_result": sync_result,
            "stats": self.stats,
            "timestamp": datetime.utcnow()
        }
        
        await self.graph_metadata.insert_one(metadata)
    
    def get_node_centrality(self, node_id: str, centrality_type: str = "betweenness") -> Optional[float]:
        """
        Calcule la centralité d'un nœud.
        
        Args:
            node_id: ID du nœud
            centrality_type: Type de centralité (betweenness, closeness, degree, eigenvector)
        
        Returns:
            Score de centralité ou None
        """
        if not self.graph or not self.graph.has_node(node_id):
            return None
        
        try:
            if centrality_type == "betweenness":
                centrality = nx.betweenness_centrality(self.graph)
            elif centrality_type == "closeness":
                centrality = nx.closeness_centrality(self.graph)
            elif centrality_type == "degree":
                centrality = nx.degree_centrality(self.graph)
            elif centrality_type == "eigenvector":
                centrality = nx.eigenvector_centrality(self.graph, max_iter=100)
            else:
                logger.warning(f"Type de centralité inconnu: {centrality_type}")
                return None
            
            return centrality.get(node_id, 0.0)
            
        except Exception as e:
            logger.error(f"Erreur calcul centralité: {e}")
            return None
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Trouve le plus court chemin entre deux nœuds.
        
        Args:
            source: Nœud source
            target: Nœud cible
        
        Returns:
            Liste des nœuds du chemin ou None si pas de chemin
        """
        if not self.graph:
            return None
        
        try:
            path = nx.shortest_path(self.graph, source, target)
            return path
        except nx.NetworkXNoPath:
            logger.debug(f"Pas de chemin entre {source[:8]} et {target[:8]}")
            return None
        except Exception as e:
            logger.error(f"Erreur recherche chemin: {e}")
            return None
    
    def get_node_neighbors(self, node_id: str, hops: int = 1) -> Set[str]:
        """
        Récupère les voisins d'un nœud à N sauts.
        
        Args:
            node_id: ID du nœud
            hops: Nombre de sauts (1 = voisins directs)
        
        Returns:
            Set des IDs des voisins
        """
        if not self.graph or not self.graph.has_node(node_id):
            return set()
        
        neighbors = set()
        
        try:
            if hops == 1:
                neighbors = set(self.graph.neighbors(node_id))
            else:
                # BFS pour N sauts
                visited = {node_id}
                current_level = {node_id}
                
                for _ in range(hops):
                    next_level = set()
                    for node in current_level:
                        for neighbor in self.graph.neighbors(node):
                            if neighbor not in visited:
                                visited.add(neighbor)
                                next_level.add(neighbor)
                                neighbors.add(neighbor)
                    current_level = next_level
            
            return neighbors
            
        except Exception as e:
            logger.error(f"Erreur récupération voisins: {e}")
            return set()
    
    def get_graph_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Retourne un snapshot du graphe au format JSON-compatible.
        
        Returns:
            Dict avec nodes et edges
        """
        if not self.graph:
            return None
        
        try:
            # Utiliser node_link_data pour export JSON
            snapshot = nx.node_link_data(self.graph)
            
            # Ajouter métadonnées
            snapshot["metadata"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "nodes_count": self.graph.number_of_nodes(),
                "edges_count": self.graph.number_of_edges(),
                "stats": self.stats
            }
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Erreur création snapshot: {e}")
            return None
    
    async def cleanup_old_data(self, days: int = 30):
        """
        Nettoie les données obsolètes (nœuds/canaux inactifs).
        
        Args:
            days: Age maximum des données à conserver
        """
        if not self.nodes_collection or not self.channels_collection:
            return
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Supprimer nœuds inactifs
        nodes_result = await self.nodes_collection.delete_many({
            "last_updated": {"$lt": cutoff}
        })
        
        # Supprimer canaux inactifs
        channels_result = await self.channels_collection.delete_many({
            "last_updated": {"$lt": cutoff}
        })
        
        logger.info(
            f"Cleanup: {nodes_result.deleted_count} nœuds et "
            f"{channels_result.deleted_count} canaux supprimés (> {days} jours)"
        )
    
    async def start_periodic_sync(self):
        """Démarre la synchronisation périodique en background."""
        logger.info(f"Démarrage synchronisation périodique (intervalle: {self.sync_interval}s)")
        
        while True:
            try:
                # Première sync: complète
                if not self.last_sync:
                    await self.full_sync()
                else:
                    # Syncs suivantes: incrémentale
                    await self.incremental_sync()
                
                # Attendre avant prochaine sync
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans boucle de synchronisation: {e}")
                await asyncio.sleep(60)  # Attendre 1 min avant retry
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du graphe."""
        return {
            **self.stats,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "graph_loaded": self.graph is not None
        }

