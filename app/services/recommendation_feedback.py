"""
Système de feedback pour mesurer l'efficacité des recommandations
Permet d'apprendre et d'améliorer les recommandations au fil du temps
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.mongo_operations import MongoOperations

logger = logging.getLogger(__name__)


class RecommendationStatus(Enum):
    """Status d'une recommandation"""
    GENERATED = "generated"       # Générée
    VIEWED = "viewed"             # Vue par l'utilisateur
    APPLIED = "applied"           # Appliquée
    REJECTED = "rejected"         # Rejetée explicitement
    EXPIRED = "expired"           # Expirée sans action


@dataclass
class RecommendationTracking:
    """Suivi d'une recommandation"""
    recommendation_id: str
    pubkey: str
    action: str
    category: str
    generated_at: datetime
    status: RecommendationStatus
    applied_at: Optional[datetime] = None
    baseline_metrics: Optional[Dict[str, Any]] = None
    post_metrics: Optional[Dict[str, Any]] = None
    effectiveness_score: Optional[float] = None
    user_feedback: Optional[Dict[str, Any]] = None


class RecommendationFeedbackSystem:
    """
    Système de feedback pour tracker et apprendre des recommandations
    """
    
    def __init__(self):
        self.mongo_ops = MongoOperations()
        self.stats = {
            'total_tracked': 0,
            'applied_count': 0,
            'rejected_count': 0,
            'avg_effectiveness': 0.0
        }
        
        logger.info("RecommendationFeedbackSystem initialized")
    
    async def track_recommendation_generated(
        self,
        recommendation_id: str,
        pubkey: str,
        recommendation: Dict[str, Any]
    ) -> bool:
        """Enregistre qu'une recommandation a été générée"""
        try:
            tracking_data = {
                'recommendation_id': recommendation_id,
                'pubkey': pubkey,
                'action': recommendation.get('action', ''),
                'category': recommendation.get('category', 'unknown'),
                'priority': recommendation.get('priority', 'medium'),
                'score': recommendation.get('score', 0.0),
                'generated_at': datetime.utcnow(),
                'status': RecommendationStatus.GENERATED.value,
                'baseline_metrics': await self._capture_baseline_metrics(pubkey),
                'metadata': recommendation.get('metadata', {})
            }
            
            # Sauvegarder dans MongoDB
            await self.mongo_ops.db['recommendation_tracking'].insert_one(tracking_data)
            
            self.stats['total_tracked'] += 1
            
            logger.debug(f"Tracked recommendation {recommendation_id} for {pubkey[:16]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track recommendation: {str(e)}")
            return False
    
    async def track_recommendation_applied(
        self,
        recommendation_id: str,
        applied_at: Optional[datetime] = None,
        user_notes: Optional[str] = None
    ) -> bool:
        """Enregistre qu'une recommandation a été appliquée"""
        try:
            update_data = {
                'status': RecommendationStatus.APPLIED.value,
                'applied_at': applied_at or datetime.utcnow(),
                'user_notes': user_notes
            }
            
            result = await self.mongo_ops.db['recommendation_tracking'].update_one(
                {'recommendation_id': recommendation_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                self.stats['applied_count'] += 1
                logger.info(f"Recommendation {recommendation_id} marked as applied")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to track application: {str(e)}")
            return False
    
    async def measure_recommendation_impact(
        self,
        recommendation_id: str,
        days_after: int = 7
    ) -> Optional[Dict[str, Any]]:
        """Mesure l'impact réel d'une recommandation après X jours"""
        try:
            # Récupérer le tracking
            tracking = await self.mongo_ops.db['recommendation_tracking'].find_one(
                {'recommendation_id': recommendation_id}
            )
            
            if not tracking or tracking['status'] != RecommendationStatus.APPLIED.value:
                return None
            
            # Vérifier que suffisamment de temps s'est écoulé
            applied_at = tracking['applied_at']
            if datetime.utcnow() - applied_at < timedelta(days=days_after):
                return {'status': 'too_early', 'days_since_applied': (datetime.utcnow() - applied_at).days}
            
            # Récupérer les métriques actuelles
            current_metrics = await self._get_current_metrics(tracking['pubkey'])
            baseline_metrics = tracking['baseline_metrics']
            
            # Calculer l'impact
            impact = self._calculate_impact(
                baseline_metrics,
                current_metrics,
                tracking['category']
            )
            
            # Calculer le score d'efficacité (0-1)
            effectiveness_score = self._calculate_effectiveness_score(impact)
            
            # Mettre à jour le tracking
            await self.mongo_ops.db['recommendation_tracking'].update_one(
                {'recommendation_id': recommendation_id},
                {
                    '$set': {
                        'post_metrics': current_metrics,
                        'impact': impact,
                        'effectiveness_score': effectiveness_score,
                        'measured_at': datetime.utcnow()
                    }
                }
            )
            
            # Mettre à jour les stats
            self._update_effectiveness_stats(effectiveness_score)
            
            logger.info(
                f"Measured impact for {recommendation_id}: "
                f"effectiveness={effectiveness_score:.2f}"
            )
            
            return {
                'recommendation_id': recommendation_id,
                'effectiveness_score': effectiveness_score,
                'impact': impact,
                'days_measured_after': days_after
            }
            
        except Exception as e:
            logger.error(f"Failed to measure impact: {str(e)}")
            return None
    
    async def get_recommendation_success_rate(
        self,
        category: Optional[str] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """Retourne le taux de succès des recommandations"""
        try:
            query = {
                'generated_at': {
                    '$gte': datetime.utcnow() - timedelta(days=time_range_days)
                }
            }
            
            if category:
                query['category'] = category
            
            # Compter par status
            pipeline = [
                {'$match': query},
                {
                    '$group': {
                        '_id': '$status',
                        'count': {'$sum': 1},
                        'avg_effectiveness': {'$avg': '$effectiveness_score'}
                    }
                }
            ]
            
            results = await self.mongo_ops.db['recommendation_tracking'].aggregate(pipeline).to_list(None)
            
            total = sum(r['count'] for r in results)
            applied = next((r['count'] for r in results if r['_id'] == RecommendationStatus.APPLIED.value), 0)
            
            return {
                'category': category or 'all',
                'time_range_days': time_range_days,
                'total_recommendations': total,
                'applied_count': applied,
                'application_rate': applied / total if total > 0 else 0.0,
                'by_status': {r['_id']: r['count'] for r in results},
                'avg_effectiveness': next((r['avg_effectiveness'] for r in results if r['_id'] == RecommendationStatus.APPLIED.value), None)
            }
            
        except Exception as e:
            logger.error(f"Failed to get success rate: {str(e)}")
            return {}
    
    async def get_top_effective_recommendations(
        self,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retourne les recommandations les plus efficaces"""
        try:
            query = {
                'status': RecommendationStatus.APPLIED.value,
                'effectiveness_score': {'$exists': True, '$ne': None}
            }
            
            if category:
                query['category'] = category
            
            cursor = self.mongo_ops.db['recommendation_tracking'].find(query).sort('effectiveness_score', -1).limit(limit)
            results = await cursor.to_list(None)
            
            return [
                {
                    'action': r['action'],
                    'category': r['category'],
                    'effectiveness_score': r['effectiveness_score'],
                    'applied_at': r['applied_at'],
                    'impact': r.get('impact', {})
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to get top recommendations: {str(e)}")
            return []
    
    async def _capture_baseline_metrics(self, pubkey: str) -> Dict[str, Any]:
        """Capture les métriques de base avant application"""
        # TODO: Implémenter capture réelle depuis Sparkseer/LNBits
        return {
            'captured_at': datetime.utcnow().isoformat(),
            'routing_revenue': 0,
            'success_rate': 0.0,
            'channel_balance_ratio': 0.5
        }
    
    async def _get_current_metrics(self, pubkey: str) -> Dict[str, Any]:
        """Récupère les métriques actuelles"""
        # TODO: Implémenter récupération réelle
        return {
            'measured_at': datetime.utcnow().isoformat(),
            'routing_revenue': 0,
            'success_rate': 0.0,
            'channel_balance_ratio': 0.5
        }
    
    def _calculate_impact(
        self,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """Calcule l'impact d'une recommandation"""
        impact = {}
        
        # Calculer les changements pour chaque métrique
        for metric in ['routing_revenue', 'success_rate', 'channel_balance_ratio']:
            if metric in baseline and metric in current:
                baseline_val = baseline[metric]
                current_val = current[metric]
                
                if baseline_val != 0:
                    change_pct = ((current_val - baseline_val) / baseline_val) * 100
                else:
                    change_pct = 0.0
                
                impact[f'{metric}_change_pct'] = change_pct
        
        return impact
    
    def _calculate_effectiveness_score(self, impact: Dict[str, Any]) -> float:
        """Calcule un score d'efficacité global (0-1)"""
        # Pondérer les impacts
        weights = {
            'routing_revenue_change_pct': 0.5,
            'success_rate_change_pct': 0.3,
            'channel_balance_ratio_change_pct': 0.2
        }
        
        score = 0.0
        for metric, weight in weights.items():
            change = impact.get(metric, 0.0)
            # Normaliser: +20% = score 1.0
            normalized = min(change / 20.0, 1.0)
            score += normalized * weight
        
        return max(0.0, min(score, 1.0))
    
    def _update_effectiveness_stats(self, effectiveness_score: float):
        """Met à jour les statistiques d'efficacité"""
        n = self.stats['applied_count']
        if n > 0:
            self.stats['avg_effectiveness'] = (
                (self.stats['avg_effectiveness'] * (n - 1) + effectiveness_score) / n
            )


logger.info("Recommendation Feedback System loaded")

