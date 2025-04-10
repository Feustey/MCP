from typing import Dict, List, Optional
from datetime import datetime
import logging
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

class MetricsStorage:
    def __init__(self, mongo_uri: str, database_name: str = "mcp_metrics"):
        self.client = MongoClient(mongo_uri)
        self.db: Database = self.client[database_name]
        self.metrics_collection: Collection = self.db.model_metrics
        
    def save_metrics(self, run_id: str, model_version: str, 
                    metrics: Dict, hyperparameters: Dict) -> bool:
        """
        Sauvegarde les métriques d'évaluation dans MongoDB
        """
        try:
            document = {
                "run_id": run_id,
                "timestamp": datetime.utcnow(),
                "model_version": model_version,
                "metrics": metrics,
                "hyperparameters": hyperparameters
            }
            
            self.metrics_collection.insert_one(document)
            logger.info(f"Métriques sauvegardées pour le run {run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques: {str(e)}")
            return False
    
    def get_metrics_history(self, model_version: Optional[str] = None, 
                          limit: int = 100) -> List[Dict]:
        """
        Récupère l'historique des métriques
        """
        try:
            query = {}
            if model_version:
                query["model_version"] = model_version
                
            cursor = self.metrics_collection.find(query).sort(
                "timestamp", -1).limit(limit)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
            return []
    
    def get_latest_metrics(self, model_version: Optional[str] = None) -> Optional[Dict]:
        """
        Récupère les dernières métriques
        """
        try:
            query = {}
            if model_version:
                query["model_version"] = model_version
                
            return self.metrics_collection.find_one(
                query, sort=[("timestamp", -1)])
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des dernières métriques: {str(e)}")
            return None
    
    def delete_metrics(self, run_id: str) -> bool:
        """
        Supprime les métriques d'un run spécifique
        """
        try:
            result = self.metrics_collection.delete_one({"run_id": run_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des métriques: {str(e)}")
            return False 