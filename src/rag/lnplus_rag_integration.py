from typing import Dict, Any, List
from datetime import datetime
import json
from src.lnplus_integration import (
    LNPlusClient,
    SwapService,
    NodeMetricsService,
    RatingService
)

class LNPlusRAGIntegration:
    def __init__(self, lnplus_client: LNPlusClient, mongo_ops):
        self.client = lnplus_client
        self.mongo_ops = mongo_ops
        self.swap_service = SwapService(lnplus_client)
        self.node_metrics_service = NodeMetricsService(lnplus_client)
        self.rating_service = RatingService(lnplus_client)

    async def analyze_lnplus_data(self) -> Dict[str, Any]:
        """Analyse les données LN+ et génère un rapport"""
        try:
            # Récupération des données
            swaps = await self.swap_service.get_available_swaps()
            node_metrics = await self.node_metrics_service.get_enhanced_metrics("YOUR_NODE_ID")
            ratings = await self.rating_service.get_node_ratings("YOUR_NODE_ID")
            
            # Analyse des données
            total_swaps = len(swaps)
            active_swaps = len([s for s in swaps if s.status == "active"])
            total_capacity = sum(s.capacity_sats for s in swaps)
            
            # Calcul des statistiques de réputation
            reputation_score = (
                ratings.get("positive_ratings", 0) /
                (ratings.get("positive_ratings", 0) + ratings.get("negative_ratings", 0) + 1)
            )
            
            # Génération du rapport
            report = {
                "total_swaps": total_swaps,
                "active_swaps": active_swaps,
                "total_capacity": total_capacity,
                "node_metrics": {
                    "open_channels": node_metrics.open_channels,
                    "capacity": node_metrics.capacity,
                    "hubness_rank": node_metrics.hubness_rank,
                    "reputation_score": reputation_score
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Création d'un document RAG
            await self.create_lnplus_document(report, "lnplus_analysis")
            
            return report
            
        except Exception as e:
            print(f"Erreur lors de l'analyse des données LN+: {str(e)}")
            return {}

    async def create_lnplus_document(self, data: Dict[str, Any], doc_type: str):
        """Crée un document RAG à partir des données LN+"""
        try:
            # Formatage du document
            document = {
                "content": json.dumps(data),
                "metadata": {
                    "type": doc_type,
                    "source": "lnplus",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Sauvegarde dans MongoDB
            await self.mongo_ops.save_document(document)
            
        except Exception as e:
            print(f"Erreur lors de la création du document RAG: {str(e)}")

    async def get_lnplus_context(self, query: str) -> List[Dict[str, Any]]:
        """Récupère le contexte LN+ pour une requête"""
        try:
            # Recherche dans les documents RAG
            context_docs = await self.mongo_ops.search_documents(
                query,
                filters={"metadata.source": "lnplus"}
            )
            
            return context_docs
            
        except Exception as e:
            print(f"Erreur lors de la récupération du contexte LN+: {str(e)}")
            return [] 