"""
Gestionnaire de données pour les analyses graphiques Lightning Network
Interface unifiée pour l'accès aux données réseau, canaux et historique
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import json
from dataclasses import dataclass

logger = logging.getLogger("mcp.graph_data_manager")

@dataclass
class NetworkSnapshot:
    """Snapshot des données réseau"""
    nodes: List[Dict[str, Any]]
    channels: List[Dict[str, Any]]
    timestamp: datetime
    node_count: int
    channel_count: int

class GraphDataManager:
    """
    Gestionnaire centralisé des données pour analyses graphiques avancées
    """
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes de cache
        self.network_cache = {}
        self.node_cache = {}
        
        # URLs des APIs Lightning (à adapter selon implémentation)
        self.ln_apis = {
            "1ml": "https://1ml.com/node",
            "amboss": "https://amboss.space/api/v1",
            "mempool": "https://mempool.space/api/lightning"
        }
        
    async def get_network_data(self, force_refresh: bool = False) -> Tuple[List[Dict], List[Dict]]:
        """
        Obtient les données complètes du réseau (nœuds + canaux)
        """
        cache_key = "network_snapshot"
        
        # Vérifier le cache
        if not force_refresh and cache_key in self.network_cache:
            cached_data = self.network_cache[cache_key]
            if (datetime.utcnow() - cached_data['timestamp']).seconds < self.cache_duration:
                logger.debug("Utilisation des données réseau en cache")
                return cached_data['nodes'], cached_data['channels']
        
        try:
            logger.info("Récupération des données réseau Lightning...")
            
            # Tenter plusieurs sources de données
            nodes, channels = await self._fetch_from_multiple_sources()
            
            if not nodes or not channels:
                # Fallback vers données mock/test
                logger.warning("Utilisation des données de test")
                nodes, channels = self._get_mock_network_data()
            
            # Mettre en cache
            self.network_cache[cache_key] = {
                'nodes': nodes,
                'channels': channels,
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"Données réseau chargées: {len(nodes)} nœuds, {len(channels)} canaux")
            return nodes, channels
            
        except Exception as e:
            logger.error(f"Erreur chargement données réseau: {str(e)}")
            # Fallback vers cache expiré ou données mock
            return self._get_fallback_data()
    
    async def get_node_channels(self, node_pubkey: str) -> List[Dict[str, Any]]:
        """
        Obtient tous les canaux d'un nœud spécifique
        """
        try:
            # Charger les données réseau
            nodes, channels = await self.get_network_data()
            
            # Filtrer les canaux du nœud
            node_channels = [
                ch for ch in channels 
                if ch.get('node1_pub') == node_pubkey or ch.get('node2_pub') == node_pubkey
            ]
            
            # Enrichir avec les balances et métriques si disponibles
            enriched_channels = []
            for channel in node_channels:
                enriched = await self._enrich_channel_data(channel, node_pubkey)
                enriched_channels.append(enriched)
            
            return enriched_channels
            
        except Exception as e:
            logger.error(f"Erreur récupération canaux nœud {node_pubkey}: {str(e)}")
            return []
    
    async def get_payment_history(self, node_pubkey: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Obtient l'historique des paiements d'un nœud (si disponible)
        """
        try:
            # Dans une implémentation réelle, ceci connecterait à la DB des paiements
            # ou à l'API du nœud Lightning
            
            # Pour l'instant, génération de données simulées
            mock_payments = self._generate_mock_payment_history(node_pubkey, days)
            
            return mock_payments
            
        except Exception as e:
            logger.error(f"Erreur récupération historique paiements {node_pubkey}: {str(e)}")
            return []
    
    async def get_market_fee_data(self) -> List[Dict[str, Any]]:
        """
        Obtient les données de frais du marché pour analyse concurrentielle
        """
        try:
            # Récupérer les données de frais depuis plusieurs sources
            market_data = await self._fetch_market_fee_data()
            
            return market_data
            
        except Exception as e:
            logger.error(f"Erreur récupération données marché: {str(e)}")
            return []
    
    async def get_node_info(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Obtient les informations détaillées d'un nœud
        """
        cache_key = f"node_{node_pubkey}"
        
        # Vérifier le cache
        if cache_key in self.node_cache:
            cached = self.node_cache[cache_key]
            if (datetime.utcnow() - cached['timestamp']).seconds < self.cache_duration:
                return cached['data']
        
        try:
            # Charger depuis les APIs
            node_info = await self._fetch_node_info(node_pubkey)
            
            # Cache
            self.node_cache[cache_key] = {
                'data': node_info,
                'timestamp': datetime.utcnow()
            }
            
            return node_info
            
        except Exception as e:
            logger.error(f"Erreur récupération info nœud {node_pubkey}: {str(e)}")
            return {}
    
    async def _fetch_from_multiple_sources(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Tente de récupérer les données depuis plusieurs sources
        """
        # Essayer mempool.space en premier (gratuit et fiable)
        try:
            nodes, channels = await self._fetch_from_mempool()
            if nodes and channels:
                return nodes, channels
        except Exception as e:
            logger.warning(f"Échec récupération mempool.space: {str(e)}")
        
        # Fallback vers 1ML
        try:
            nodes, channels = await self._fetch_from_1ml()
            if nodes and channels:
                return nodes, channels
        except Exception as e:
            logger.warning(f"Échec récupération 1ML: {str(e)}")
        
        # Fallback vers données locales/mock
        return self._get_mock_network_data()
    
    async def _fetch_from_mempool(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Récupère les données depuis mempool.space
        """
        async with aiohttp.ClientSession() as session:
            # Récupérer les nœuds
            async with session.get(f"{self.ln_apis['mempool']}/nodes/rankings") as resp:
                if resp.status == 200:
                    nodes_data = await resp.json()
                else:
                    raise Exception(f"HTTP {resp.status} from mempool nodes API")
            
            # Récupérer les canaux (sample)
            async with session.get(f"{self.ln_apis['mempool']}/channels") as resp:
                if resp.status == 200:
                    channels_data = await resp.json()
                else:
                    raise Exception(f"HTTP {resp.status} from mempool channels API")
        
        # Transformer au format standard
        nodes = self._transform_mempool_nodes(nodes_data)
        channels = self._transform_mempool_channels(channels_data)
        
        return nodes, channels
    
    async def _fetch_from_1ml(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Récupère les données depuis 1ML (format alternatif)
        """
        # Implémentation similaire pour 1ML
        # Note: 1ML a des limites de rate et format différent
        nodes = []
        channels = []
        
        return nodes, channels
    
    def _get_mock_network_data(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Génère des données réseau simulées pour tests et développement
        """
        # Nœuds mock représentatifs
        mock_nodes = [
            {
                "pubkey": "029ef6567a4be22b0387d63f721808dce5c0a13682dbd0d6efce820d3ec3c73991",
                "alias": "ACINQ",
                "color": "#49daaa",
                "total_capacity": 50000000000,  # 500 BTC
                "num_channels": 1250,
                "last_update": int(datetime.utcnow().timestamp())
            },
            {
                "pubkey": "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
                "alias": "bitrefill.com",
                "color": "#3399ff",
                "total_capacity": 25000000000,  # 250 BTC
                "num_channels": 850,
                "last_update": int(datetime.utcnow().timestamp())
            },
            {
                "pubkey": "0331f80652fb840239df8dc99205792bba2e559a05469915804c08420230e23c7c",
                "alias": "River Financial 1",
                "color": "#00d4aa",
                "total_capacity": 30000000000,  # 300 BTC
                "num_channels": 920,
                "last_update": int(datetime.utcnow().timestamp())
            }
        ]
        
        # Canaux mock
        mock_channels = []
        for i in range(len(mock_nodes)):
            for j in range(i + 1, len(mock_nodes)):
                channel_id = f"channel_{i}_{j}_{datetime.utcnow().timestamp()}"
                capacity = 5000000 + (i * j * 1000000)  # Capacités variables
                
                mock_channels.append({
                    "channel_id": channel_id,
                    "node1_pub": mock_nodes[i]["pubkey"],
                    "node2_pub": mock_nodes[j]["pubkey"],
                    "capacity": capacity,
                    "node1_fee_rate": 100 + (i * 50),  # 100-200 ppm
                    "node2_fee_rate": 150 + (j * 30),  # 150-210 ppm
                    "node1_balance": capacity // 2 + (capacity // 10),  # Léger déséquilibre
                    "node2_balance": capacity // 2 - (capacity // 10),
                    "last_update": int(datetime.utcnow().timestamp())
                })
        
        return mock_nodes, mock_channels
    
    def _get_fallback_data(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Données de fallback en cas d'échec total
        """
        if 'network_snapshot' in self.network_cache:
            cached = self.network_cache['network_snapshot']
            logger.warning("Utilisation des données en cache expirées")
            return cached['nodes'], cached['channels']
        
        logger.warning("Aucune donnée disponible, utilisation de données mock minimales")
        return self._get_mock_network_data()
    
    async def _enrich_channel_data(self, channel: Dict[str, Any], node_pubkey: str) -> Dict[str, Any]:
        """
        Enrichit les données d'un canal avec métriques additionnelles
        """
        enriched = channel.copy()
        
        # Ajouter la perspective du nœud
        if channel.get('node1_pub') == node_pubkey:
            enriched['local_balance'] = channel.get('node1_balance', channel.get('capacity', 0) // 2)
            enriched['remote_balance'] = channel.get('node2_balance', channel.get('capacity', 0) // 2)
            enriched['fee_rate_ppm'] = channel.get('node1_fee_rate', 0)
            enriched['peer_pubkey'] = channel.get('node2_pub')
        else:
            enriched['local_balance'] = channel.get('node2_balance', channel.get('capacity', 0) // 2)
            enriched['remote_balance'] = channel.get('node1_balance', channel.get('capacity', 0) // 2)
            enriched['fee_rate_ppm'] = channel.get('node2_fee_rate', 0)
            enriched['peer_pubkey'] = channel.get('node1_pub')
        
        # Ajouter métriques simulées
        enriched['volume_30d'] = enriched.get('capacity', 0) * 0.1  # 10% de volume simulé
        enriched['success_rate'] = 0.95  # 95% de succès simulé
        
        return enriched
    
    def _generate_mock_payment_history(self, node_pubkey: str, days: int) -> List[Dict[str, Any]]:
        """
        Génère un historique de paiements simulé
        """
        import random
        
        payments = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Générer environ 10-50 paiements par jour
        for day in range(days):
            date = start_date + timedelta(days=day)
            daily_payments = random.randint(10, 50)
            
            for _ in range(daily_payments):
                payment_time = date + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                amount = random.randint(10000, 5000000)  # 10k-5M sats
                fee = max(1, amount // 1000000)  # ~1000 ppm moyen
                
                payments.append({
                    "timestamp": payment_time.isoformat(),
                    "channel_id": f"mock_channel_{random.randint(1, 10)}",
                    "amount_sats": amount,
                    "fee_sats": fee,
                    "status": "success" if random.random() > 0.05 else "failed",
                    "direction": "outgoing" if random.random() > 0.5 else "incoming"
                })
        
        return payments
    
    async def _fetch_market_fee_data(self) -> List[Dict[str, Any]]:
        """
        Récupère les données de frais du marché
        """
        # Dans une implémentation réelle, ceci agrègerait les données de frais
        # depuis plusieurs sources (1ML, Amboss, etc.)
        
        # Données simulées pour développement
        market_data = []
        for i in range(100):  # 100 nœuds de référence
            market_data.append({
                "node_pubkey": f"market_node_{i}",
                "avg_fee_rate_ppm": 50 + (i * 10),  # 50-1050 ppm
                "median_fee_rate_ppm": 45 + (i * 8),
                "total_capacity": 1000000 * (100 + i),  # Capacités variables
                "channel_count": 10 + (i // 10),
                "success_rate": 0.85 + (0.15 * random.random())
            })
        
        return market_data
    
    async def _fetch_node_info(self, node_pubkey: str) -> Dict[str, Any]:
        """
        Récupère les informations détaillées d'un nœud
        """
        # Tentative depuis mempool.space
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ln_apis['mempool']}/nodes/{node_pubkey}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"Échec récupération info nœud depuis mempool: {str(e)}")
        
        # Fallback vers données mock
        return {
            "pubkey": node_pubkey,
            "alias": f"Node {node_pubkey[:16]}",
            "color": "#000000",
            "capacity": 10000000,  # 0.1 BTC par défaut
            "num_channels": 5,
            "last_update": int(datetime.utcnow().timestamp())
        }
    
    def _transform_mempool_nodes(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Transforme les données de nœuds depuis mempool.space au format standard
        """
        transformed = []
        for node in raw_data:
            transformed.append({
                "pubkey": node.get("public_key", ""),
                "alias": node.get("alias", ""),
                "color": node.get("color", "#000000"),
                "total_capacity": node.get("capacity", 0),
                "num_channels": node.get("channels", 0),
                "last_update": node.get("updated_at", 0)
            })
        return transformed
    
    def _transform_mempool_channels(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Transforme les données de canaux depuis mempool.space au format standard
        """
        transformed = []
        for channel in raw_data:
            transformed.append({
                "channel_id": channel.get("short_channel_id", ""),
                "node1_pub": channel.get("node1_public_key", ""),
                "node2_pub": channel.get("node2_public_key", ""),
                "capacity": channel.get("capacity", 0),
                "node1_fee_rate": channel.get("node1_fee_rate", 0),
                "node2_fee_rate": channel.get("node2_fee_rate", 0),
                "last_update": channel.get("updated_at", 0)
            })
        return transformed