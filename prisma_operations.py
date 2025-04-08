import motor.motor_asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
from bson import ObjectId # Nécessaire pour les requêtes par ID MongoDB
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

class MongoOperations:
    def __init__(self):
        self.mongo_url = os.getenv("DATABASE_URL")
        if not self.mongo_url or not (self.mongo_url.startswith("mongodb://") or self.mongo_url.startswith("mongodb+srv://")):
            raise ValueError("DATABASE_URL n'est pas définie correctement pour MongoDB dans .env")
            
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        self.connected = False
        
    async def connect(self):
        """Établit la connexion à la base de données MongoDB"""
        if not self.connected:
            try:
                self.client = motor.motor_asyncio.AsyncIOMotorClient(self.mongo_url)
                # Utiliser le nom de base de données spécifié "Dazlng"
                db_name = "Dazlng"
                self.db = self.client.get_database(db_name)
                # Tester la connexion
                await self.client.admin.command('ping') 
                self.connected = True
                logger.info(f"Connexion à MongoDB établie (DB: {self.db.name})")
            except ConnectionFailure as e:
                logger.error(f"Échec de la connexion à MongoDB: {e}")
                self.client = None
                self.db = None
                raise
            except Exception as e:
                 logger.error(f"Erreur inattendue lors de la connexion à MongoDB: {e}")
                 self.client = None
                 self.db = None
                 raise
        
    async def disconnect(self):
        """Ferme la connexion à la base de données MongoDB"""
        if self.connected and self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.connected = False
            logger.info("Connexion à MongoDB fermée")
            
    async def ensure_connected(self):
        """S'assure que la connexion est établie avant une opération"""
        if not self.connected:
            await self.connect()
        if not self.db:
             raise ConnectionFailure("Non connecté à la base de données MongoDB")
             
    # --- Méthodes CRUD adaptées pour Motor --- 
    # Note: Les noms des collections correspondent aux noms des modèles Prisma par défaut (commençant par une majuscule)

    async def save_node(self, node_data: Dict[str, Any]) -> None:
        """Sauvegarde ou met à jour un nœud dans la collection 'Node'"""
        await self.ensure_connected()
        try:
            pubkey = node_data['pubkey']
            update_data = {
                '$set': {
                    'alias': node_data.get('alias', ''),
                    'capacity': float(node_data.get('capacity', 0.0)), # Assurer float
                    'channels': int(node_data.get('channels', 0)), # Assurer int
                    'last_updated': datetime.now()
                },
                '$setOnInsert': {
                    'pubkey': pubkey,
                    # Convertir timestamp si nécessaire (ex: Amboss first_seen est déjà datetime?)
                    'first_seen': node_data.get('first_seen', datetime.now()) 
                }
            }
            result = await self.db.Node.update_one({'pubkey': pubkey}, update_data, upsert=True)
            if result.upserted_id:
                logger.info(f"Nœud {pubkey} inséré avec succès")
            elif result.modified_count > 0:
                 logger.info(f"Nœud {pubkey} mis à jour avec succès")
            # else:
            #      logger.debug(f"Nœud {pubkey} déjà à jour.") # Moins verbeux en INFO
                 
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du nœud {node_data.get('pubkey', 'N/A')}: {str(e)}")
            raise
            
    async def save_channel(self, channel_data: Dict[str, Any]) -> None:
        """Sauvegarde ou met à jour un canal dans la collection 'Channel'"""
        await self.ensure_connected()
        try:
            channel_id_str = channel_data['channel_id'] # Utiliser l'ID de canal unique
            update_data = {
                '$set': {
                    'node1_pubkey': channel_data['node1_pubkey'],
                    'node2_pubkey': channel_data['node2_pubkey'],
                    'capacity': float(channel_data.get('capacity', 0.0)), # Assurer float
                    # Fee rate peut être imbriqué, s'assurer de prendre la bonne valeur
                    'fee_rate': float(channel_data.get('fee_rate', 0.0) if isinstance(channel_data.get('fee_rate'), (int, float)) else channel_data.get('fee_rate', {}).get('rate', 0.0)),
                    'last_updated': datetime.now()
                },
                 '$setOnInsert': {
                    'channel_id': channel_id_str
                }
            }
            result = await self.db.Channel.update_one({'channel_id': channel_id_str}, update_data, upsert=True)
            if result.upserted_id:
                logger.info(f"Canal {channel_id_str} inséré avec succès")
            elif result.modified_count > 0:
                 logger.info(f"Canal {channel_id_str} mis à jour avec succès")
            # else:
            #      logger.debug(f"Canal {channel_id_str} déjà à jour.")
                 
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du canal {channel_data.get('channel_id', 'N/A')}: {str(e)}")
            raise
            
    async def save_network_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """Sauvegarde les métriques du réseau dans la collection 'NetworkMetrics'"""
        await self.ensure_connected()
        try:
            # NetworkMetrics est généralement une série temporelle, donc on insère toujours
            insert_data = {
                'total_capacity': float(metrics_data.get('total_capacity', 0.0)),
                'total_channels': int(metrics_data.get('total_channels', 0)),
                'total_nodes': int(metrics_data.get('total_nodes', 0)),
                'average_fee_rate': float(metrics_data.get('average_fee_rate', 0.0)),
                'timestamp': datetime.now()
            }
            await self.db.NetworkMetrics.insert_one(insert_data)
            logger.info("Métriques réseau insérées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques réseau: {str(e)}")
            raise
            
    async def save_node_performance(self, performance_data: Dict[str, Any]) -> None:
        """Sauvegarde les performances d'un nœud dans la collection 'NodePerformance'"""
        await self.ensure_connected()
        try:
            # Les performances sont aussi une série temporelle par noeud
            insert_data = {
                'node_pubkey': performance_data['node_pubkey'],
                'uptime': float(performance_data.get('uptime', 0.0)),
                'fee_earned': float(performance_data.get('fee_earned', 0.0)),
                'timestamp': datetime.now()
            }
            await self.db.NodePerformance.insert_one(insert_data)
            logger.info(f"Performances du nœud {performance_data['node_pubkey']} sauvegardées")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des performances du nœud: {str(e)}")
            raise
            
    async def save_channel_recommendation(self, recommendation_data: Dict[str, Any]) -> None:
        """Sauvegarde une recommandation de canal dans la collection 'ChannelRecommendation'"""
        await self.ensure_connected()
        try:
            # Insérer chaque nouvelle recommandation
            insert_data = {
                'source_node': recommendation_data['source_node'],
                'target_node': recommendation_data['target_node'],
                'recommended_capacity': float(recommendation_data.get('recommended_capacity', 0.0)),
                'reason': recommendation_data.get('reason', ''),
                'timestamp': datetime.now()
            }
            await self.db.ChannelRecommendation.insert_one(insert_data)
            logger.info(f"Recommandation de canal sauvegardée pour {recommendation_data['source_node']} -> {recommendation_data['target_node']}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la recommandation de canal: {str(e)}")
            raise
            
    # --- Méthodes pour RAG et Stats adaptées --- 

    async def save_document(self, document_data: Dict[str, Any]) -> bool:
        """Sauvegarde un document RAG dans la collection 'Document'"""
        await self.ensure_connected()
        try:
            # Convertir metadata en dict si ce n'est pas déjà le cas (Prisma stockait en Json)
            metadata = document_data.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                     logger.warning(f"Metadata invalide pour document {document_data.get('source')}, utilisation de dict vide.")
                     metadata = {}
                     
            insert_data = {
                'content': document_data['content'],
                'source': document_data['source'],
                'embedding': document_data.get('embedding', []),
                'metadata': metadata,
                'created_at': document_data.get('created_at', datetime.now())
            }
            await self.db.Document.insert_one(insert_data)
            logger.info(f"Document source '{document_data['source']}' sauvegardé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du document: {str(e)}")
            return False
            
    async def save_query_history(self, history_data: Dict[str, Any]) -> bool:
        """Sauvegarde une entrée de l'historique des requêtes dans 'QueryHistory'"""
        await self.ensure_connected()
        try:
            # Convertir metadata en dict si nécessaire
            metadata = history_data.get('metadata', {})
            if isinstance(metadata, str):
                 try:
                    metadata = json.loads(metadata)
                 except json.JSONDecodeError:
                     logger.warning(f"Metadata invalide pour requête '{history_data.get('query')}', utilisation de dict vide.")
                     metadata = {}
                     
            insert_data = {
                'query': history_data['query'],
                'response': history_data['response'],
                'context_docs': history_data.get('context_docs', []), # Doit être une liste de str
                'processing_time': float(history_data.get('processing_time', 0.0)),
                'cache_hit': bool(history_data.get('cache_hit', False)),
                'metadata': metadata,
                'timestamp': history_data.get('timestamp', datetime.now())
            }
            await self.db.QueryHistory.insert_one(insert_data)
            logger.info(f"Entrée d'historique pour la requête '{history_data['query'][:50]}...' sauvegardée")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'historique des requêtes: {str(e)}")
            return False
            
    async def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """Récupère les dernières statistiques système depuis 'SystemStats'"""
        await self.ensure_connected()
        try:
            # Récupérer le document le plus récent
            stats = await self.db.SystemStats.find_one({}, sort=[('last_update', -1)])
            if stats:
                # Convertir ObjectId en str pour éviter les problèmes de sérialisation JSON si nécessaire
                if '_id' in stats and isinstance(stats['_id'], ObjectId):
                    stats['_id'] = str(stats['_id'])
                logger.info("Statistiques système récupérées")
                return stats
            else:
                logger.info("Aucune statistique système trouvée.")
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques système: {str(e)}")
            return None
            
    async def update_system_stats(self, stats_data: Dict[str, Any]) -> bool:
        """Met à jour (ou crée) les statistiques système dans 'SystemStats'"""
        # Cette fonction remplace toutes les stats par les nouvelles. 
        # Prisma mettait à jour un seul doc, ici on en insère un nouveau ou on remplace le dernier.
        # Pour simplifier, on insère toujours un nouveau document de stats.
        await self.ensure_connected()
        try:
            insert_data = {
                'total_documents': int(stats_data.get('total_documents', 0)),
                'total_queries': int(stats_data.get('total_queries', 0)),
                'average_processing_time': float(stats_data.get('average_processing_time', 0.0)),
                'cache_hit_rate': float(stats_data.get('cache_hit_rate', 0.0)),
                'last_update': datetime.now() 
            }
            # Option 1: Insérer un nouveau document à chaque fois (série temporelle)
            await self.db.SystemStats.insert_one(insert_data)
            logger.info("Nouvelles statistiques système insérées")
            
            # Option 2: Remplacer le seul document de stats (si on ne veut pas d'historique)
            # await self.db.SystemStats.replace_one({}, insert_data, upsert=True)
            # logger.info("Statistiques système mises à jour (remplacées)")
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques système: {str(e)}")
            return False

    # --- Méthodes GET (Adaptation simplifiée ou à faire plus tard si besoin) ---
    # Note: Ces méthodes nécessiteraient une logique plus complexe (agrégation, etc.)
    # pour répliquer exactement le `include` de Prisma.

    async def get_node_data(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Récupère les données d'un nœud par pubkey (simplifié)."""
        await self.ensure_connected()
        try:
            node = await self.db.Node.find_one({'pubkey': pubkey})
            if node and '_id' in node and isinstance(node['_id'], ObjectId):
                 node['_id'] = str(node['_id']) # Convertir ObjectId
            return node
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données du nœud {pubkey}: {str(e)}")
            return None
            
    async def get_network_metrics(self, limit: int = 1) -> List[Dict[str, Any]]:
        """Récupère les dernières métriques globales du réseau."""
        await self.ensure_connected()
        try:
            cursor = self.db.NetworkMetrics.find({}, sort=[('timestamp', -1)], limit=limit)
            metrics = await cursor.to_list(length=limit)
            for m in metrics:
                if '_id' in m and isinstance(m['_id'], ObjectId):
                    m['_id'] = str(m['_id']) # Convertir ObjectId
            return metrics
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques réseau: {str(e)}")
            return []
            
    async def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère l'historique des requêtes récentes."""
        await self.ensure_connected()
        try:
            cursor = self.db.QueryHistory.find({}, sort=[('timestamp', -1)], limit=limit)
            queries = await cursor.to_list(length=limit)
            for q in queries:
                if '_id' in q and isinstance(q['_id'], ObjectId):
                    q['_id'] = str(q['_id'])
                # Assurer que metadata est un dict (Prisma le stockait en JSON string)
                if 'metadata' in q and isinstance(q['metadata'], str):
                     try:
                         q['metadata'] = json.loads(q['metadata'])
                     except json.JSONDecodeError:
                         logger.warning(f"Impossible de décoder les métadonnées JSON pour la requête ID {q.get('_id')}")
                         q['metadata'] = {}
            logger.info(f"Récupération de {len(queries)} requêtes récentes")
            return queries
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des requêtes récentes: {str(e)}")
            return []
            
    # Les méthodes get_channel_recommendations, get_node_performance 
    # nécessiteraient une adaptation plus spécifique de la logique de requête (find, sort, limit)
    # et potentiellement des agrégations pour répliquer les `include` Prisma. 
    # Laissées comme placeholder ou à implémenter selon les besoins exacts. 