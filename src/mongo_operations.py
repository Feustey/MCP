from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from .database import get_database, close_mongo_connection
from .models import Document, QueryHistory, SystemStats, NodeData, ChannelData, NetworkMetrics, NodePerformance, ChannelRecommendation, DataValidationError, LightningMetricsHistory, ArchiveSettings, FeeChangeHypothesis, ChannelConfigHypothesis
import logging

logger = logging.getLogger(__name__)

class MongoOperations:
    def __init__(self):
        self.client = None
        self.db = None
        self.collections = {
            'nodes': None,
            'channels': None,
            'metrics': None,
            'documents': None,
            'query_history': None,
            'system_stats': None,
            'error_logs': None,
            'metrics_history': None,
            'archives': None,
            'fee_hypotheses': None,
            'channel_hypotheses': None
        }
        self.indexes = {
            'nodes': [
                [('pubkey', 1), ('last_updated', -1)],
                [('alias', 'text')],
                [('capacity', -1)],
                [('channels', -1)]
            ],
            'channels': [
                [('channel_id', 1), ('last_updated', -1)],
                [('node1_pubkey', 1), ('node2_pubkey', 1)],
                [('capacity', -1)],
                [('fee_rate.base_fee', 1), ('fee_rate.fee_rate', 1)]
            ],
            'metrics': [
                [('last_update', -1)],
                [('total_capacity', -1)],
                [('total_channels', -1)]
            ],
            'documents': [
                [('metadata.type', 1), ('metadata.timestamp', -1)],
                [('content', 'text')]
            ],
            'query_history': [
                [('timestamp', -1)],
                [('query', 'text')]
            ],
            'error_logs': [
                [('timestamp', -1)],
                [('error_type', 1)],
                [('context.node_id', 1)]
            ],
            'metrics_history': [
                [('node_id', 1), ('timestamp', -1)],
                [('timestamp', -1)],
                [('base_fee_rate', 1)],
                [('fee_rate_ppm', 1)],
                [('local_balance_ratio', 1)]
            ],
            'archives': [
                [('collection_name', 1), ('timestamp', -1)],
                [('timestamp', -1)]
            ],
            'fee_hypotheses': [
                [('hypothesis_id', 1)],
                [('node_id', 1), ('created_at', -1)],
                [('channel_id', 1), ('created_at', -1)],
                [('is_validated', 1), ('created_at', -1)]
            ],
            'channel_hypotheses': [
                [('hypothesis_id', 1)],
                [('node_id', 1), ('created_at', -1)],
                [('is_validated', 1), ('created_at', -1)]
            ]
        }
        self.db_name = os.getenv("MONGODB_DB_NAME", "dazlng")

    async def connect(self):
        """Établit la connexion à MongoDB et configure les index"""
        try:
            self.client = AsyncIOMotorClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))
            self.db = self.client.lightning_network
            
            # Initialisation des collections
            for collection_name in self.collections:
                self.collections[collection_name] = self.db[collection_name]
            
            # Configuration des index
            await self._setup_indexes()
            
            logger.info("Connexion MongoDB établie et index configurés")
        except Exception as e:
            logger.error(f"Erreur lors de la connexion à MongoDB: {e}")
            raise

    async def _setup_indexes(self):
        """Configure les index pour toutes les collections"""
        for collection_name, indexes in self.indexes.items():
            collection = self.collections[collection_name]
            for index in indexes:
                try:
                    await collection.create_index(index)
                    logger.info(f"Index créé pour {collection_name}: {index}")
                except Exception as e:
                    logger.error(f"Erreur lors de la création de l'index {index} pour {collection_name}: {e}")

    async def initialize(self):
        """Initialise la connexion à la base de données"""
        return await self.connect()

    async def close(self):
        """Ferme la connexion à la base de données"""
        if self.client:
            self.client.close()
            logger.info("Connexion MongoDB fermée")

    async def ensure_connection(self):
        """S'assure qu'une connexion est établie"""
        if not self.client:
            await self.connect()

    async def save_document(self, document: Document) -> str:
        """Sauvegarde un document dans MongoDB"""
        await self.ensure_connection()
        doc_dict = document.model_dump()
        result = await self.collections['documents'].insert_one(doc_dict)
        return str(result.inserted_id)

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Récupère un document par son ID"""
        await self.ensure_connection()
        doc_dict = await self.collections['documents'].find_one({"_id": doc_id})
        if doc_dict:
            return Document(**doc_dict)
        return None

    async def save_query_history(self, query_history: QueryHistory) -> str:
        """Sauvegarde l'historique d'une requête"""
        await self.ensure_connection()
        history_dict = query_history.model_dump()
        result = await self.collections['query_history'].insert_one(history_dict)
        return str(result.inserted_id)

    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        """Récupère les requêtes récentes"""
        if not self.client:
            await self.connect()
        cursor = self.collections['query_history'].find().sort("created_at", -1).limit(limit)
        queries = await cursor.to_list(length=limit)
        return [QueryHistory(**q) for q in queries]

    async def update_system_stats(self, stats: SystemStats):
        """Met à jour les statistiques du système"""
        await self.ensure_connection()
        stats_dict = stats.model_dump()
        await self.collections['system_stats'].replace_one({}, stats_dict, upsert=True)

    async def get_system_stats(self) -> Optional[SystemStats]:
        """Récupère les statistiques du système"""
        if not self.client:
            await self.connect()
        stats_dict = await self.collections['system_stats'].find_one()
        if stats_dict:
            return SystemStats(**stats_dict)
        return None

    async def get_documents_by_source(self, source: str) -> List[Document]:
        """Récupère tous les documents d'une source donnée"""
        await self.ensure_connection()
        cursor = self.collections['documents'].find({"source": source})
        documents = []
        async for doc in cursor:
            documents.append(Document(**doc))
        return documents

    # Nouvelles méthodes pour la gestion des nœuds et canaux
    async def save_node(self, node: NodeData) -> str:
        """Sauvegarde ou met à jour un nœud"""
        if not self.client:
            await self.connect()
        node_dict = node.model_dump()
        result = await self.collections['nodes'].update_one(
            {"node_id": node.node_id},
            {"$set": node_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else node.node_id

    async def save_channel(self, channel: ChannelData) -> str:
        """Sauvegarde ou met à jour un canal"""
        if not self.client:
            await self.connect()
        channel_dict = channel.model_dump()
        result = await self.collections['channels'].update_one(
            {"channel_id": channel.channel_id},
            {"$set": channel_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else channel.channel_id

    async def save_network_metrics(self, metrics: NetworkMetrics) -> None:
        """Sauvegarde ou met à jour les métriques réseau"""
        if not self.client:
            await self.connect()
        metrics_dict = metrics.model_dump()
        await self.collections['metrics'].update_one(
            {},
            {"$set": metrics_dict},
            upsert=True
        )

    async def save_node_performance(self, performance: NodePerformance) -> str:
        """Sauvegarde ou met à jour les performances d'un nœud"""
        if not self.client:
            await self.connect()
        perf_dict = performance.model_dump()
        result = await self.collections['node_performance'].update_one(
            {"node_id": performance.node_id},
            {"$set": perf_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else performance.node_id

    async def save_channel_recommendation(self, recommendation: ChannelRecommendation) -> str:
        """Sauvegarde ou met à jour une recommandation de canal"""
        if not self.client:
            await self.connect()
        rec_dict = recommendation.model_dump()
        result = await self.collections['channel_recommendations'].update_one(
            {
                "source_node_id": recommendation.source_node_id,
                "target_node_id": recommendation.target_node_id
            },
            {"$set": rec_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else f"{recommendation.source_node_id}_{recommendation.target_node_id}"

    async def save_node_data(self, node_data: NodeData):
        """Sauvegarde les données d'un nœud avec validation"""
        try:
            # Validation des données
            validated_data = await DataValidator.validate_node_data(node_data.dict())
            
            # Mise à jour avec upsert
            await self.collections['nodes'].update_one(
                {'pubkey': validated_data.pubkey},
                {'$set': validated_data.dict()},
                upsert=True
            )
            
            # Mise à jour des statistiques
            await self._update_node_stats(validated_data)
            
        except DataValidationError as e:
            logger.error(f"Erreur de validation des données du nœud: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données du nœud: {e}")
            raise

    async def get_node_history(self, node_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Récupère l'historique d'un nœud avec optimisation"""
        try:
            # Utilisation de l'index composé (pubkey, last_updated)
            pipeline = [
                {
                    '$match': {
                        'pubkey': node_id,
                        'last_updated': {
                            '$gte': start_date,
                            '$lte': end_date
                        }
                    }
                },
                {
                    '$sort': {'last_updated': 1}
                },
                {
                    '$group': {
                        '_id': '$pubkey',
                        'history': {
                            '$push': {
                                'capacity': '$capacity',
                                'channels': '$channels',
                                'timestamp': '$last_updated'
                            }
                        }
                    }
                }
            ]
            
            result = await self.collections['nodes'].aggregate(pipeline).to_list(length=None)
            return result[0]['history'] if result else []
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique du nœud: {e}")
            return []

    async def get_network_metrics_history(self, days: int = 30) -> List[Dict]:
        """Récupère l'historique des métriques réseau avec optimisation"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'last_update': {
                            '$gte': start_date,
                            '$lte': end_date
                        }
                    }
                },
                {
                    '$sort': {'last_update': 1}
                },
                {
                    '$group': {
                        '_id': None,
                        'metrics': {
                            '$push': {
                                'total_capacity': '$total_capacity',
                                'total_channels': '$total_channels',
                                'total_nodes': '$total_nodes',
                                'average_fee_rate': '$average_fee_rate',
                                'timestamp': '$last_update'
                            }
                        }
                    }
                }
            ]
            
            result = await self.collections['metrics'].aggregate(pipeline).to_list(length=None)
            return result[0]['metrics'] if result else []
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique des métriques: {e}")
            return []

    async def _update_node_stats(self, node_data: NodeData):
        """Met à jour les statistiques globales du nœud"""
        try:
            # Calcul des statistiques
            stats = {
                'total_capacity': node_data.capacity,
                'channel_count': node_data.channels,
                'last_updated': node_data.last_updated
            }
            
            # Mise à jour avec upsert
            await self.collections['system_stats'].update_one(
                {'node_id': node_data.pubkey},
                {'$set': stats},
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques du nœud: {e}") 

    async def save_lightning_metrics_history(self, metrics: LightningMetricsHistory) -> str:
        """
        Sauvegarde les métriques historiques d'un nœud Lightning
        
        Args:
            metrics: Instance de LightningMetricsHistory
            
        Returns:
            ID du document inséré
        """
        await self.ensure_connection()
        metrics_dict = metrics.model_dump()
        result = await self.collections['metrics_history'].insert_one(metrics_dict)
        return str(result.inserted_id)
    
    async def get_lightning_metrics_history(
        self, 
        node_id: str, 
        start_date: datetime = None, 
        end_date: datetime = None,
        limit: int = 100
    ) -> List[LightningMetricsHistory]:
        """
        Récupère l'historique des métriques d'un nœud Lightning
        
        Args:
            node_id: ID du nœud
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des métriques historiques
        """
        await self.ensure_connection()
        
        # Construction du filtre
        filter_query = {"node_id": node_id}
        if start_date or end_date:
            timestamp_filter = {}
            if start_date:
                timestamp_filter["$gte"] = start_date
            if end_date:
                timestamp_filter["$lte"] = end_date
            if timestamp_filter:
                filter_query["timestamp"] = timestamp_filter
        
        # Exécution de la requête
        cursor = self.collections['metrics_history'].find(filter_query).sort("timestamp", -1).limit(limit)
        metrics_list = []
        async for doc in cursor:
            metrics_list.append(LightningMetricsHistory(**doc))
        
        return metrics_list
    
    async def save_archive_settings(self, settings: ArchiveSettings) -> None:
        """
        Sauvegarde les paramètres d'archivage pour une collection
        
        Args:
            settings: Instance de ArchiveSettings
        """
        await self.ensure_connection()
        settings_dict = settings.model_dump()
        
        # Mise à jour ou création des paramètres
        await self.db.archive_settings.update_one(
            {"collection_name": settings.collection_name},
            {"$set": settings_dict},
            upsert=True
        )
    
    async def get_archive_settings(self, collection_name: str) -> Optional[ArchiveSettings]:
        """
        Récupère les paramètres d'archivage pour une collection
        
        Args:
            collection_name: Nom de la collection
            
        Returns:
            Instance de ArchiveSettings ou None
        """
        await self.ensure_connection()
        settings_dict = await self.db.archive_settings.find_one({"collection_name": collection_name})
        
        if settings_dict:
            return ArchiveSettings(**settings_dict)
        return None
    
    async def archive_old_data(self, collection_name: str) -> Dict[str, Any]:
        """
        Archive les anciennes données d'une collection
        
        Args:
            collection_name: Nom de la collection à archiver
            
        Returns:
            Statistiques de l'opération d'archivage
        """
        await self.ensure_connection()
        
        # Récupération des paramètres d'archivage
        settings = await self.get_archive_settings(collection_name)
        if not settings:
            raise ValueError(f"Paramètres d'archivage non trouvés pour la collection {collection_name}")
        
        # Calcul des dates limites
        now = datetime.now()
        retention_date = now - timedelta(days=settings.retention_days)
        deletion_date = now - timedelta(days=settings.archive_after_days)
        
        # Archives à archiver (plus vieilles que la période de rétention)
        archive_filter = {
            "timestamp": {"$lt": retention_date}
        }
        
        # Archives à supprimer définitivement (plus vieilles que la période d'archivage)
        delete_filter = {
            "timestamp": {"$lt": deletion_date}
        }
        
        # Collection source et destination
        source_collection = self.collections[collection_name]
        archive_collection = self.db[f"{collection_name}_archive"]
        
        # 1. Récupération des documents à archiver
        cursor = source_collection.find(archive_filter)
        docs_to_archive = []
        async for doc in cursor:
            # Ajout d'un timestamp d'archivage
            doc["archived_at"] = now
            docs_to_archive.append(doc)
        
        stats = {
            "collection": collection_name,
            "archived_count": len(docs_to_archive),
            "deleted_count": 0,
            "timestamp": now
        }
        
        # 2. Insertion dans la collection d'archives si des documents sont trouvés
        if docs_to_archive:
            await archive_collection.insert_many(docs_to_archive)
            
            # 3. Suppression des documents archivés de la collection source
            result = await source_collection.delete_many(archive_filter)
            stats["deleted_from_source"] = result.deleted_count
        
        # 4. Suppression définitive des archives trop anciennes
        result = await archive_collection.delete_many(delete_filter)
        stats["deleted_count"] = result.deleted_count
        
        # 5. Enregistrement des statistiques d'archivage
        await self.collections["archives"].insert_one(stats)
        
        return stats

    async def get_archiving_statistics(self, collection_name: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Récupère les statistiques des opérations d'archivage
        
        Args:
            collection_name: Nom de la collection (optionnel)
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des statistiques d'archivage
        """
        await self.ensure_connection()
        
        # Construction du filtre
        filter_query = {}
        if collection_name:
            filter_query["collection"] = collection_name
        
        # Exécution de la requête
        cursor = self.collections["archives"].find(filter_query).sort("timestamp", -1).limit(limit)
        stats_list = []
        async for doc in cursor:
            stats_list.append(doc)
        
        return stats_list

    async def save_fee_hypothesis(self, hypothesis: FeeChangeHypothesis) -> str:
        """
        Sauvegarde une hypothèse de changement de frais
        
        Args:
            hypothesis: Instance de FeeChangeHypothesis
            
        Returns:
            ID de l'hypothèse
        """
        await self.ensure_connection()
        
        # Création d'un ID si nécessaire
        if not hypothesis.hypothesis_id:
            import uuid
            hypothesis.hypothesis_id = str(uuid.uuid4())
        
        hypothesis_dict = hypothesis.model_dump()
        
        # Mise à jour ou création de l'hypothèse
        await self.collections['fee_hypotheses'].update_one(
            {"hypothesis_id": hypothesis.hypothesis_id},
            {"$set": hypothesis_dict},
            upsert=True
        )
        
        return hypothesis.hypothesis_id
    
    async def get_fee_hypothesis(self, hypothesis_id: str) -> Optional[FeeChangeHypothesis]:
        """
        Récupère une hypothèse de changement de frais par son ID
        
        Args:
            hypothesis_id: ID de l'hypothèse
            
        Returns:
            Instance de FeeChangeHypothesis ou None
        """
        await self.ensure_connection()
        
        hypothesis_dict = await self.collections['fee_hypotheses'].find_one(
            {"hypothesis_id": hypothesis_id}
        )
        
        if hypothesis_dict:
            return FeeChangeHypothesis(**hypothesis_dict)
        return None
    
    async def update_fee_hypothesis_results(
        self, 
        hypothesis_id: str, 
        after_stats: Dict[str, Any],
        is_validated: bool,
        conclusion: str,
        impact_metrics: Dict[str, float]
    ) -> bool:
        """
        Met à jour les résultats d'une hypothèse de changement de frais
        
        Args:
            hypothesis_id: ID de l'hypothèse
            after_stats: Statistiques après le changement
            is_validated: L'hypothèse est-elle validée?
            conclusion: Conclusion de l'hypothèse
            impact_metrics: Métriques d'impact
            
        Returns:
            Succès de la mise à jour
        """
        await self.ensure_connection()
        
        result = await self.collections['fee_hypotheses'].update_one(
            {"hypothesis_id": hypothesis_id},
            {"$set": {
                "after_stats": after_stats,
                "is_validated": is_validated,
                "conclusion": conclusion,
                "impact_metrics": impact_metrics,
                "evaluation_completed_at": datetime.now()
            }}
        )
        
        return result.modified_count > 0
    
    async def get_fee_hypotheses_for_node(
        self, 
        node_id: str, 
        limit: int = 10,
        only_validated: bool = False
    ) -> List[FeeChangeHypothesis]:
        """
        Récupère les hypothèses de changement de frais pour un nœud
        
        Args:
            node_id: ID du nœud
            limit: Nombre maximum de résultats
            only_validated: Ne récupérer que les hypothèses validées
            
        Returns:
            Liste des hypothèses
        """
        await self.ensure_connection()
        
        # Construction du filtre
        filter_query = {"node_id": node_id}
        if only_validated:
            filter_query["is_validated"] = {"$ne": None}
        
        # Exécution de la requête
        cursor = self.collections['fee_hypotheses'].find(filter_query).sort("created_at", -1).limit(limit)
        
        hypotheses = []
        async for doc in cursor:
            hypotheses.append(FeeChangeHypothesis(**doc))
        
        return hypotheses
    
    async def save_channel_hypothesis(self, hypothesis: ChannelConfigHypothesis) -> str:
        """
        Sauvegarde une hypothèse de configuration de canaux
        
        Args:
            hypothesis: Instance de ChannelConfigHypothesis
            
        Returns:
            ID de l'hypothèse
        """
        await self.ensure_connection()
        
        # Création d'un ID si nécessaire
        if not hypothesis.hypothesis_id:
            import uuid
            hypothesis.hypothesis_id = str(uuid.uuid4())
        
        hypothesis_dict = hypothesis.model_dump()
        
        # Mise à jour ou création de l'hypothèse
        await self.collections['channel_hypotheses'].update_one(
            {"hypothesis_id": hypothesis.hypothesis_id},
            {"$set": hypothesis_dict},
            upsert=True
        )
        
        return hypothesis.hypothesis_id
    
    async def get_channel_hypothesis(self, hypothesis_id: str) -> Optional[ChannelConfigHypothesis]:
        """
        Récupère une hypothèse de configuration de canaux par son ID
        
        Args:
            hypothesis_id: ID de l'hypothèse
            
        Returns:
            Instance de ChannelConfigHypothesis ou None
        """
        await self.ensure_connection()
        
        hypothesis_dict = await self.collections['channel_hypotheses'].find_one(
            {"hypothesis_id": hypothesis_id}
        )
        
        if hypothesis_dict:
            return ChannelConfigHypothesis(**hypothesis_dict)
        return None
    
    async def update_channel_hypothesis_results(
        self, 
        hypothesis_id: str, 
        after_config: Dict[str, Any],
        after_performance: Dict[str, Any],
        is_validated: bool,
        conclusion: str,
        impact_metrics: Dict[str, float]
    ) -> bool:
        """
        Met à jour les résultats d'une hypothèse de configuration de canaux
        
        Args:
            hypothesis_id: ID de l'hypothèse
            after_config: Configuration après les changements
            after_performance: Performance après les changements
            is_validated: L'hypothèse est-elle validée?
            conclusion: Conclusion de l'hypothèse
            impact_metrics: Métriques d'impact
            
        Returns:
            Succès de la mise à jour
        """
        await self.ensure_connection()
        
        result = await self.collections['channel_hypotheses'].update_one(
            {"hypothesis_id": hypothesis_id},
            {"$set": {
                "after_config": after_config,
                "after_performance": after_performance,
                "is_validated": is_validated,
                "conclusion": conclusion,
                "impact_metrics": impact_metrics,
                "evaluation_completed_at": datetime.now()
            }}
        )
        
        return result.modified_count > 0
    
    async def get_channel_hypotheses_for_node(
        self, 
        node_id: str, 
        limit: int = 10,
        only_validated: bool = False
    ) -> List[ChannelConfigHypothesis]:
        """
        Récupère les hypothèses de configuration de canaux pour un nœud
        
        Args:
            node_id: ID du nœud
            limit: Nombre maximum de résultats
            only_validated: Ne récupérer que les hypothèses validées
            
        Returns:
            Liste des hypothèses
        """
        await self.ensure_connection()
        
        # Construction du filtre
        filter_query = {"node_id": node_id}
        if only_validated:
            filter_query["is_validated"] = {"$ne": None}
        
        # Exécution de la requête
        cursor = self.collections['channel_hypotheses'].find(filter_query).sort("created_at", -1).limit(limit)
        
        hypotheses = []
        async for doc in cursor:
            hypotheses.append(ChannelConfigHypothesis(**doc))
        
        return hypotheses 