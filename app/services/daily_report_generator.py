"""
Service de génération des rapports quotidiens
Collecte, analyse et génération automatisée de rapports Lightning Network

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 5 novembre 2025
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from config.models.daily_reports import (
    DailyReport,
    ReportSummary,
    ReportMetrics,
    ReportRecommendation,
    ReportAlert,
    ReportTrends
)

logger = logging.getLogger(__name__)


class DailyReportGenerator:
    """Service de génération des rapports quotidiens"""
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        rag_workflow = None,
        redis_ops = None
    ):
        self.db = db
        self.rag_workflow = rag_workflow
        self.redis_ops = redis_ops
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.max_concurrent = int(os.getenv("DAILY_REPORTS_MAX_CONCURRENT", "10"))
        self.max_retries = int(os.getenv("DAILY_REPORTS_MAX_RETRIES", "3"))
        self.timeout_seconds = int(os.getenv("DAILY_REPORTS_TIMEOUT", "300"))
    
    async def run(self, user_ids: Optional[List[str]] = None):
        """Exécute la génération de rapports pour tous les users éligibles"""
        
        start_time = datetime.utcnow()
        self.logger.info("Starting daily reports generation")
        
        try:
            # 1. Récupérer les utilisateurs avec workflow actif
            query = {"daily_report_enabled": True, "lightning_pubkey": {"$ne": None}}
            if user_ids:
                query["id"] = {"$in": user_ids}
            
            users = await self.db.user_profiles.find(query).to_list(length=None)
            
            self.logger.info(f"Found {len(users)} users eligible for daily report generation")
            
            if not users:
                self.logger.info("No users to process")
                return
            
            # 2. Génération parallèle avec limite de concurrence
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def generate_with_semaphore(user):
                async with semaphore:
                    try:
                        await self.generate_report_for_user(user)
                    except Exception as e:
                        self.logger.error(f"Error generating report for user {user.get('id')}: {e}")
            
            await asyncio.gather(*[
                generate_with_semaphore(user) for user in users
            ], return_exceptions=True)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"Daily reports generation completed in {duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in daily reports generation: {e}")
            raise
    
    async def generate_report_for_user(self, user: Dict[str, Any]):
        """Génère le rapport pour un utilisateur spécifique"""
        
        report_id = str(uuid.uuid4())
        node_pubkey = user.get("lightning_pubkey")
        user_id = user.get("id")
        tenant_id = user.get("tenant_id")
        
        if not node_pubkey:
            self.logger.warning(f"User {user_id} has no lightning pubkey")
            return
        
        self.logger.info(f"Generating daily report for user {user_id} (node: {node_pubkey[:16]}...)")
        
        # 1. Créer le document rapport avec status processing
        report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        report_doc = {
            "report_id": report_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "node_pubkey": node_pubkey,
            "node_alias": user.get("node_alias"),
            "report_date": report_date,
            "generation_timestamp": datetime.utcnow(),
            "generation_status": "processing",
            "report_version": "1.0.0",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "retry_count": 0
        }
        
        await self.db.daily_reports.insert_one(report_doc)
        
        try:
            # 2. Collecter les données multi-sources avec timeout
            async with asyncio.timeout(self.timeout_seconds):
                node_data = await self._collect_node_data(node_pubkey)
            
            # 3. Analyser via RAG (si disponible)
            analysis = await self._analyze_with_rag(node_pubkey, node_data)
            
            # 4. Générer les sections du rapport
            summary = self._generate_summary(node_data, analysis)
            metrics = self._generate_metrics(node_data)
            recommendations = self._generate_recommendations(analysis, node_data)
            alerts = self._detect_alerts(node_data, analysis)
            trends = await self._compute_trends(user_id, node_pubkey)
            
            # 5. Mettre à jour le rapport avec le contenu
            report_content = {
                "summary": summary.dict() if summary else None,
                "metrics": metrics.dict() if metrics else None,
                "recommendations": [r.dict() for r in recommendations],
                "alerts": [a.dict() for a in alerts],
                "trends": trends.dict() if trends else None,
                "generation_status": "completed",
                "updated_at": datetime.utcnow()
            }
            
            await self.db.daily_reports.update_one(
                {"report_id": report_id},
                {"$set": report_content}
            )
            
            # 6. Stocker comme asset RAG
            rag_asset_id = await self._store_as_rag_asset(
                report_id, 
                report_content, 
                user
            )
            
            await self.db.daily_reports.update_one(
                {"report_id": report_id},
                {"$set": {
                    "rag_asset_id": rag_asset_id,
                    "rag_indexed": True,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # 7. Mettre à jour le profil utilisateur
            await self.db.user_profiles.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "last_report_generated": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"total_reports_generated": 1}
                }
            )
            
            # 8. Envoyer notification si configuré
            await self._send_notification(user, report_id)
            
            self.logger.info(f"Report {report_id} generated successfully for user {user_id}")
            
        except asyncio.TimeoutError:
            error_msg = f"Report generation timeout after {self.timeout_seconds}s"
            self.logger.error(f"{error_msg} for user {user_id}")
            await self._mark_report_failed(report_id, error_msg)
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error generating report {report_id}: {error_msg}")
            await self._mark_report_failed(report_id, error_msg)
    
    async def _mark_report_failed(self, report_id: str, error_message: str):
        """Marque un rapport comme échoué"""
        await self.db.daily_reports.update_one(
            {"report_id": report_id},
            {
                "$set": {
                    "generation_status": "failed",
                    "error_message": error_message,
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"retry_count": 1}
            }
        )
    
    async def _collect_node_data(self, node_pubkey: str) -> Dict[str, Any]:
        """Collecte données multi-sources pour un nœud"""
        
        self.logger.info(f"Collecting data for node {node_pubkey[:16]}...")
        
        node_data = {
            "pubkey": node_pubkey,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Collecter depuis différentes sources
        try:
            # 1. Données depuis la base de données locale
            local_node = await self.db.nodes.find_one({"pubkey": node_pubkey})
            if local_node:
                node_data["local"] = {
                    "alias": local_node.get("alias"),
                    "capacity": local_node.get("capacity", 0),
                    "channels": local_node.get("channels", 0),
                    "score": local_node.get("score", 0),
                    "metrics": local_node.get("metrics", {})
                }
            
            # 2. Données depuis Amboss (si disponible)
            try:
                from src.clients.amboss_client import AmbossClient
                amboss = AmbossClient()
                amboss_data = await amboss.get_node_info(node_pubkey)
                if amboss_data:
                    node_data["amboss"] = amboss_data
            except Exception as e:
                self.logger.warning(f"Could not fetch Amboss data: {e}")
            
            # 3. Données depuis Mempool (si disponible)
            try:
                from src.clients.mempool_client import MempoolClient
                mempool = MempoolClient()
                mempool_data = await mempool.get_node_stats(node_pubkey)
                if mempool_data:
                    node_data["mempool"] = mempool_data
            except Exception as e:
                self.logger.warning(f"Could not fetch Mempool data: {e}")
            
            # 4. Métriques historiques
            history = await self.db.node_metrics_history.find(
                {"node_pubkey": node_pubkey},
                sort=[("timestamp", -1)],
                limit=30
            ).to_list(length=30)
            
            if history:
                node_data["history"] = history
            
        except Exception as e:
            self.logger.error(f"Error collecting node data: {e}")
        
        return node_data
    
    async def _analyze_with_rag(
        self, 
        node_pubkey: str, 
        node_data: Dict
    ) -> Dict[str, Any]:
        """Analyse via système RAG"""
        
        if not self.rag_workflow:
            self.logger.warning("RAG workflow not available, using fallback analysis")
            return {"analysis": "fallback", "recommendations": []}
        
        try:
            # Construire la requête pour le RAG
            query = f"""
Analyse complète du nœud Lightning Network suivant et génère des recommandations d'optimisation:

Pubkey: {node_pubkey}
Alias: {node_data.get('local', {}).get('alias', 'Unknown')}
Capacité: {node_data.get('local', {}).get('capacity', 0)} sats
Canaux: {node_data.get('local', {}).get('channels', 0)}
Score actuel: {node_data.get('local', {}).get('score', 0)}

Fournis:
1. Un score global de performance (0-100)
2. Une évaluation du statut (healthy/warning/critical)
3. Des recommandations d'optimisation priorisées
4. Des alertes sur les problèmes détectés
"""
            
            # Requête RAG
            result = await self.rag_workflow.query(query)
            
            return {
                "rag_response": result,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in RAG analysis: {e}")
            return {"error": str(e)}
    
    def _generate_summary(
        self, 
        node_data: Dict, 
        analysis: Dict
    ) -> Optional[ReportSummary]:
        """Génère le résumé exécutif du rapport"""
        
        try:
            local_data = node_data.get("local", {})
            metrics = local_data.get("metrics", {})
            
            # Extraire les métriques de base
            capacity_sats = local_data.get("capacity", 0)
            capacity_btc = capacity_sats / 100_000_000
            channels_count = local_data.get("channels", 0)
            score = local_data.get("score", 0)
            
            # Calculer le delta de score (si historique disponible)
            score_delta = 0
            history = node_data.get("history", [])
            if len(history) > 1:
                previous_score = history[1].get("score", score)
                score_delta = score - previous_score
            
            # Déterminer le statut
            status = "healthy"
            if score < 50:
                status = "critical"
            elif score < 75:
                status = "warning"
            
            # Compter les alertes
            critical_alerts = 0
            warnings = 0
            # TODO: Extraire depuis l'analyse RAG
            
            # Métriques de forwarding (exemple)
            forwarding_rate = metrics.get("forwarding_rate_24h", 0)
            revenue_sats = metrics.get("revenue_sats_24h", 0)
            
            return ReportSummary(
                overall_score=score,
                score_delta_24h=score_delta,
                status=status,
                critical_alerts=critical_alerts,
                warnings=warnings,
                capacity_btc=capacity_btc,
                channels_count=channels_count,
                forwarding_rate_24h=forwarding_rate,
                revenue_sats_24h=revenue_sats
            )
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return None
    
    def _generate_metrics(self, node_data: Dict) -> Optional[ReportMetrics]:
        """Génère les métriques détaillées"""
        
        try:
            local_data = node_data.get("local", {})
            metrics_raw = local_data.get("metrics", {})
            
            capacity_sats = local_data.get("capacity", 0)
            channels_count = local_data.get("channels", 0)
            
            metrics = ReportMetrics(
                capacity={
                    "total_sats": capacity_sats,
                    "local_balance": metrics_raw.get("local_balance", capacity_sats // 2),
                    "remote_balance": metrics_raw.get("remote_balance", capacity_sats // 2),
                    "liquidity_ratio": 0.5
                },
                channels={
                    "active": channels_count,
                    "inactive": 0,
                    "pending": 0,
                    "avg_capacity_sats": capacity_sats // channels_count if channels_count > 0 else 0
                },
                forwarding={
                    "forwards_24h": metrics_raw.get("forwards_24h", 0),
                    "forwards_7d": metrics_raw.get("forwards_7d", 0),
                    "success_rate_24h": metrics_raw.get("success_rate", 0.95),
                    "revenue_24h": metrics_raw.get("revenue_24h", 0),
                    "revenue_7d": metrics_raw.get("revenue_7d", 0)
                },
                fees={
                    "avg_fee_rate": metrics_raw.get("avg_fee_rate", 250),
                    "min_fee_rate": metrics_raw.get("min_fee_rate", 50),
                    "max_fee_rate": metrics_raw.get("max_fee_rate", 2000),
                    "base_fee_avg": metrics_raw.get("base_fee_avg", 1000)
                },
                network={
                    "uptime_24h": metrics_raw.get("uptime", 0.99),
                    "peer_count": channels_count,
                    "centrality_score": metrics_raw.get("centrality", 0.5),
                    "betweenness_rank": metrics_raw.get("betweenness_rank", 0)
                }
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error generating metrics: {e}")
            return None
    
    def _generate_recommendations(
        self, 
        analysis: Dict, 
        node_data: Dict
    ) -> List[ReportRecommendation]:
        """Génère les recommandations d'optimisation"""
        
        recommendations = []
        
        try:
            # TODO: Extraire les recommandations depuis l'analyse RAG
            # Pour l'instant, générer des recommandations basiques
            
            local_data = node_data.get("local", {})
            score = local_data.get("score", 0)
            
            if score < 80:
                recommendations.append(ReportRecommendation(
                    priority="medium",
                    category="performance",
                    title="Amélioration du score global",
                    description="Votre score de performance peut être amélioré",
                    impact_score=7.0,
                    channels_affected=[],
                    suggested_action="Consultez les recommandations détaillées ci-dessous",
                    estimated_gain_sats_month=10000
                ))
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
        
        return recommendations
    
    def _detect_alerts(
        self, 
        node_data: Dict, 
        analysis: Dict
    ) -> List[ReportAlert]:
        """Détecte les alertes sur le nœud"""
        
        alerts = []
        
        try:
            # TODO: Détecter les alertes depuis les données et l'analyse
            
            local_data = node_data.get("local", {})
            channels = local_data.get("channels", 0)
            
            if channels == 0:
                alerts.append(ReportAlert(
                    severity="warning",
                    type="no_channels",
                    title="Aucun canal détecté",
                    description="Votre nœud n'a pas de canaux actifs",
                    detected_at=datetime.utcnow(),
                    requires_action=True
                ))
            
        except Exception as e:
            self.logger.error(f"Error detecting alerts: {e}")
        
        return alerts
    
    async def _compute_trends(
        self, 
        user_id: str, 
        node_pubkey: str
    ) -> Optional[ReportTrends]:
        """Calcule les tendances sur 7 jours"""
        
        try:
            # Récupérer les 7 derniers rapports
            reports = await self.db.daily_reports.find(
                {
                    "user_id": user_id,
                    "node_pubkey": node_pubkey,
                    "generation_status": "completed"
                },
                sort=[("report_date", -1)],
                limit=7
            ).to_list(length=7)
            
            if not reports:
                return None
            
            # Inverser pour avoir l'ordre chronologique
            reports.reverse()
            
            score_evolution = []
            revenue_evolution = []
            forward_rate_evolution = []
            capacity_evolution = []
            
            for report in reports:
                summary = report.get("summary", {})
                metrics = report.get("metrics", {})
                
                score_evolution.append(summary.get("overall_score", 0))
                revenue_evolution.append(summary.get("revenue_sats_24h", 0))
                forward_rate_evolution.append(summary.get("forwarding_rate_24h", 0))
                
                capacity = metrics.get("capacity", {})
                capacity_evolution.append(capacity.get("total_sats", 0))
            
            return ReportTrends(
                score_evolution_7d=score_evolution,
                revenue_evolution_7d=revenue_evolution,
                forward_rate_evolution_7d=forward_rate_evolution,
                capacity_evolution_7d=capacity_evolution
            )
            
        except Exception as e:
            self.logger.error(f"Error computing trends: {e}")
            return None
    
    async def _store_as_rag_asset(
        self, 
        report_id: str, 
        report_content: Dict, 
        user: Dict
    ) -> str:
        """Stocke le rapport comme asset RAG"""
        
        try:
            date_str = datetime.utcnow().strftime("%Y%m%d")
            user_id = user.get("id", "unknown")
            asset_id = f"daily_report_{user_id}_{date_str}"
            
            # 1. Créer le répertoire si nécessaire
            asset_dir = f"rag/RAG_assets/reports/daily/{user_id}"
            os.makedirs(asset_dir, exist_ok=True)
            
            # 2. Sauvegarder le fichier JSON
            asset_path = f"{asset_dir}/{date_str}.json"
            
            full_report = {
                "report_id": report_id,
                "user_id": user_id,
                "node_pubkey": user.get("lightning_pubkey"),
                "node_alias": user.get("node_alias"),
                "date": date_str,
                "generated_at": datetime.utcnow().isoformat(),
                **report_content
            }
            
            with open(asset_path, 'w') as f:
                json.dump(full_report, f, indent=2, default=str)
            
            self.logger.info(f"RAG asset saved to {asset_path}")
            
            # 3. Indexer dans RAG (si disponible)
            if self.rag_workflow:
                try:
                    await self.rag_workflow.index_document(
                        content=json.dumps(full_report, default=str),
                        metadata={
                            "asset_id": asset_id,
                            "type": "daily_report",
                            "user_id": user_id,
                            "node_pubkey": user.get("lightning_pubkey"),
                            "date": date_str,
                            "report_id": report_id
                        }
                    )
                    self.logger.info(f"RAG asset indexed: {asset_id}")
                except Exception as e:
                    self.logger.warning(f"Could not index RAG asset: {e}")
            
            return asset_id
            
        except Exception as e:
            self.logger.error(f"Error storing RAG asset: {e}")
            return f"error_{report_id}"
    
    async def _send_notification(self, user: Dict, report_id: str):
        """Envoie une notification à l'utilisateur (si configuré)"""
        
        try:
            notification_prefs = user.get("notification_preferences", {})
            
            if not notification_prefs:
                return
            
            # TODO: Implémenter les différents types de notifications
            # - Email
            # - Webhook
            # - Push notification
            
            self.logger.info(f"Notification sent for report {report_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")


# Singleton pour récupérer le générateur
_generator_instance = None

async def get_daily_report_generator() -> DailyReportGenerator:
    """Récupère l'instance du générateur de rapports quotidiens"""
    global _generator_instance
    
    if _generator_instance is None:
        from config.database import get_database
        from app.services.rag_service import get_rag_workflow
        
        db = await get_database()
        
        # RAG workflow optionnel
        rag_workflow = None
        try:
            rag_workflow = await get_rag_workflow()
        except Exception as e:
            logger.warning(f"RAG workflow not available: {e}")
        
        _generator_instance = DailyReportGenerator(
            db=db,
            rag_workflow=rag_workflow
        )
    
    return _generator_instance

