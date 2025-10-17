"""
Système de scoring multi-facteurs pour les recommandations
Permet de prioriser les recommandations selon plusieurs critères pondérés
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RecommendationPriority(Enum):
    """Niveaux de priorité"""
    CRITICAL = "critical"    # Action immédiate requise
    HIGH = "high"           # Action dans les 24h
    MEDIUM = "medium"       # Action dans la semaine
    LOW = "low"             # Action quand possible
    INFO = "info"           # Information uniquement


@dataclass
class ScoredRecommendation:
    """Recommandation avec score et métadonnées"""
    action: str
    category: str
    priority: RecommendationPriority
    score: float  # 0-100
    confidence: float  # 0-1
    impact_factors: Dict[str, float]
    reasoning: str = ""
    estimated_cost: Optional[float] = None
    estimated_time_hours: Optional[float] = None
    estimated_revenue_increase: Optional[float] = None
    risk_level: str = "medium"  # low, medium, high
    command: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'action': self.action,
            'category': self.category,
            'priority': self.priority.value,
            'score': round(self.score, 2),
            'confidence': round(self.confidence, 3),
            'impact_factors': {k: round(v, 3) for k, v in self.impact_factors.items()},
            'reasoning': self.reasoning,
            'estimated_cost': self.estimated_cost,
            'estimated_time_hours': self.estimated_time_hours,
            'estimated_revenue_increase': self.estimated_revenue_increase,
            'risk_level': self.risk_level,
            'command': self.command,
            'metadata': self.metadata
        }


class RecommendationScorer:
    """
    Système de scoring multi-facteurs pour prioriser les recommandations
    
    Facteurs pris en compte:
    - Impact sur les revenus (revenue_impact)
    - Facilité d'implémentation (ease_of_implementation)
    - Niveau de risque (risk_level, inversé)
    - Temps avant résultats (time_to_value)
    - Confiance dans les données (data_confidence)
    - Conditions réseau actuelles (network_conditions)
    """
    
    # Poids des facteurs (total = 1.0)
    DEFAULT_WEIGHTS = {
        'revenue_impact': 0.30,             # Impact sur les revenus
        'ease_of_implementation': 0.20,     # Facilité d'implémentation
        'risk_level': 0.15,                 # Niveau de risque (inverse)
        'time_to_value': 0.15,              # Temps avant résultats
        'data_confidence': 0.10,            # Confiance dans les données
        'network_conditions': 0.10          # Conditions réseau actuelles
    }
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        enable_dynamic_weights: bool = True
    ):
        """
        Args:
            weights: Poids personnalisés des facteurs
            enable_dynamic_weights: Ajuster les poids selon le contexte
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.enable_dynamic_weights = enable_dynamic_weights
        
        # Vérifier que les poids somment à 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing...")
            self.weights = {
                k: v / total_weight for k, v in self.weights.items()
            }
        
        # Statistiques
        self.stats = {
            'total_scored': 0,
            'by_category': {},
            'avg_score': 0.0,
            'avg_confidence': 0.0
        }
        
        logger.info(f"RecommendationScorer initialized with weights: {self.weights}")
    
    async def score_recommendation(
        self,
        recommendation: Dict[str, Any],
        node_metrics: Dict[str, Any],
        network_state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ScoredRecommendation:
        """
        Calcule un score composite pour une recommandation
        
        Args:
            recommendation: Dictionnaire de la recommandation
            node_metrics: Métriques du nœud
            network_state: État du réseau Lightning
            context: Contexte additionnel
            
        Returns:
            ScoredRecommendation avec score et détails
        """
        network_state = network_state or {}
        context = context or {}
        
        # Ajuster les poids si mode dynamique
        weights = self._adjust_weights(context) if self.enable_dynamic_weights else self.weights
        
        # Calculer chaque facteur
        factors = {
            'revenue_impact': self._score_revenue_impact(recommendation, node_metrics),
            'ease_of_implementation': self._score_ease(recommendation),
            'risk_level': 1.0 - self._score_risk(recommendation, node_metrics),  # Inverse
            'time_to_value': self._score_time_to_value(recommendation),
            'data_confidence': self._score_confidence(recommendation, node_metrics),
            'network_conditions': self._score_network_conditions(network_state, recommendation)
        }
        
        # Score pondéré final (0-100)
        total_score = sum(
            factors[key] * weights[key]
            for key in factors
        ) * 100
        
        # Confiance globale
        confidence = factors['data_confidence']
        
        # Déterminer la priorité selon le score
        priority = self._priority_from_score(total_score, confidence)
        
        # Générer le raisonnement
        reasoning = self._generate_reasoning(
            recommendation,
            factors,
            weights,
            total_score
        )
        
        # Créer la recommandation scorée
        scored = ScoredRecommendation(
            action=recommendation.get('action', ''),
            category=recommendation.get('category', 'unknown'),
            priority=priority,
            score=total_score,
            confidence=confidence,
            impact_factors=factors,
            reasoning=reasoning,
            estimated_cost=recommendation.get('estimated_cost'),
            estimated_time_hours=recommendation.get('estimated_time_hours'),
            estimated_revenue_increase=recommendation.get('estimated_revenue_increase'),
            risk_level=recommendation.get('risk_level', 'medium'),
            command=recommendation.get('command'),
            metadata={
                'weights_used': weights,
                'scored_at': datetime.utcnow().isoformat(),
                'node_uptime': node_metrics.get('uptime_percentage'),
                'network_congestion': network_state.get('congestion_level', 'unknown')
            }
        )
        
        # Mettre à jour les stats
        self._update_stats(scored)
        
        return scored
    
    async def score_batch(
        self,
        recommendations: List[Dict[str, Any]],
        node_metrics: Dict[str, Any],
        network_state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ScoredRecommendation]:
        """Score un batch de recommandations"""
        scored = []
        
        for rec in recommendations:
            try:
                scored_rec = await self.score_recommendation(
                    rec,
                    node_metrics,
                    network_state,
                    context
                )
                scored.append(scored_rec)
            except Exception as e:
                logger.error(f"Failed to score recommendation: {str(e)}")
        
        # Trier par score décroissant
        scored.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(
            f"Scored {len(scored)} recommendations "
            f"(avg score: {sum(r.score for r in scored)/len(scored):.1f})"
        )
        
        return scored
    
    def _score_revenue_impact(
        self,
        rec: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> float:
        """Score basé sur l'impact estimé sur les revenus (0-1)"""
        # Essayer de parser l'augmentation estimée
        revenue_increase_str = rec.get('estimated_revenue_increase', '0%')
        if isinstance(revenue_increase_str, str):
            try:
                percentage = float(revenue_increase_str.strip('%+'))
            except:
                percentage = 0.0
        else:
            percentage = float(revenue_increase_str)
        
        # Normaliser: 50% d'augmentation = score 1.0
        score = min(percentage / 50.0, 1.0)
        
        # Ajuster selon les revenus actuels
        current_revenue = metrics.get('monthly_routing_revenue', 0)
        if current_revenue > 0:
            # Plus les revenus sont élevés, plus l'impact est important
            revenue_factor = min(current_revenue / 100000, 1.2)  # Cap à 120%
            score *= revenue_factor
        
        return max(0.0, min(score, 1.0))
    
    def _score_ease(self, rec: Dict[str, Any]) -> float:
        """Score basé sur la facilité d'implémentation (0-1)"""
        difficulty = rec.get('difficulty', 'medium').lower()
        
        ease_map = {
            'easy': 1.0,
            'low': 1.0,
            'medium': 0.6,
            'moderate': 0.6,
            'hard': 0.3,
            'difficult': 0.3,
            'very hard': 0.1
        }
        
        score = ease_map.get(difficulty, 0.5)
        
        # Ajuster selon temps estimé
        estimated_hours = rec.get('estimated_time_hours', 1.0)
        if estimated_hours < 1:
            score *= 1.2
        elif estimated_hours > 8:
            score *= 0.7
        
        # Ajuster selon coût
        estimated_cost = rec.get('estimated_cost', 0)
        if estimated_cost == 0:
            score *= 1.1  # Gratuit, plus facile
        elif estimated_cost > 1000:
            score *= 0.8  # Coût élevé, moins "facile"
        
        return max(0.0, min(score, 1.0))
    
    def _score_risk(
        self,
        rec: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> float:
        """Score le niveau de risque (0-1, plus haut = plus risqué)"""
        risk_level = rec.get('risk_level', 'medium').lower()
        
        risk_map = {
            'low': 0.2,
            'minimal': 0.1,
            'medium': 0.5,
            'moderate': 0.5,
            'high': 0.8,
            'critical': 0.9
        }
        
        base_risk = risk_map.get(risk_level, 0.5)
        
        # Ajuster selon la catégorie
        category = rec.get('category', '').lower()
        if category in ['channel_closure', 'force_close']:
            base_risk *= 1.5  # Plus risqué
        elif category in ['monitoring', 'analysis']:
            base_risk *= 0.5  # Moins risqué
        
        # Ajuster selon l'uptime du nœud
        uptime = metrics.get('uptime_percentage', 95)
        if uptime < 90:
            base_risk *= 1.3  # Nœud instable, plus risqué
        elif uptime > 99:
            base_risk *= 0.8  # Nœud stable, moins risqué
        
        return max(0.0, min(base_risk, 1.0))
    
    def _score_time_to_value(self, rec: Dict[str, Any]) -> float:
        """Score le délai avant résultats (0-1, plus haut = plus rapide)"""
        timeframe = rec.get('timeframe', '1 week').lower()
        
        # Mapper les timeframes
        if 'immediate' in timeframe or 'instant' in timeframe:
            score = 1.0
        elif 'hour' in timeframe or 'day' in timeframe:
            score = 0.9
        elif 'week' in timeframe or '7 day' in timeframe:
            score = 0.6
        elif 'month' in timeframe or '30 day' in timeframe:
            score = 0.3
        else:
            score = 0.5
        
        return score
    
    def _score_confidence(
        self,
        rec: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> float:
        """Score la confiance dans les données (0-1)"""
        # Confidence de base de la recommandation
        base_confidence = rec.get('confidence', 0.7)
        
        # Ajuster selon la qualité des métriques
        metrics_quality = 1.0
        
        # Vérifier la fraîcheur des données
        last_update = metrics.get('last_updated')
        if last_update:
            # Dégrader si données anciennes
            # TODO: Implémenter vérification temporelle
            pass
        
        # Vérifier la complétude des données
        required_fields = ['channel_count', 'total_capacity', 'uptime_percentage']
        available_fields = sum(1 for field in required_fields if field in metrics)
        completeness = available_fields / len(required_fields)
        
        metrics_quality *= completeness
        
        final_confidence = base_confidence * metrics_quality
        
        return max(0.0, min(final_confidence, 1.0))
    
    def _score_network_conditions(
        self,
        network_state: Dict[str, Any],
        rec: Dict[str, Any]
    ) -> float:
        """Score selon les conditions réseau actuelles (0-1)"""
        if not network_state:
            return 0.5  # Neutral si pas de données
        
        score = 0.5
        
        # Congestion réseau
        congestion = network_state.get('congestion_level', 'normal').lower()
        if congestion == 'low':
            score += 0.2
        elif congestion == 'high':
            score -= 0.2
        
        # Frais réseau moyens
        avg_fee_rate = network_state.get('average_fee_rate_ppm', 100)
        if rec.get('category') == 'fees':
            # Ajuster les recommandations de frais selon conditions
            if avg_fee_rate > 200:
                score += 0.2  # Bon moment pour ajuster frais
            elif avg_fee_rate < 50:
                score -= 0.1
        
        # Nombre de nœuds actifs
        active_nodes = network_state.get('active_nodes_count', 15000)
        if active_nodes > 20000:
            score += 0.1  # Réseau sain
        
        return max(0.0, min(score, 1.0))
    
    def _adjust_weights(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Ajuste les poids selon le contexte"""
        weights = self.weights.copy()
        
        # Ajuster selon l'objectif principal
        primary_goal = context.get('primary_goal', 'balanced')
        
        if primary_goal == 'revenue':
            # Priorité aux revenus
            weights['revenue_impact'] = 0.50
            weights['ease_of_implementation'] = 0.15
        
        elif primary_goal == 'stability':
            # Priorité à la stabilité/sécurité
            weights['risk_level'] = 0.30
            weights['revenue_impact'] = 0.20
        
        elif primary_goal == 'quick_wins':
            # Priorité aux gains rapides
            weights['ease_of_implementation'] = 0.35
            weights['time_to_value'] = 0.25
        
        # Normaliser
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
        
        return weights
    
    def _priority_from_score(
        self,
        score: float,
        confidence: float
    ) -> RecommendationPriority:
        """Détermine la priorité selon le score et la confiance"""
        # Ajuster le seuil selon la confiance
        adjusted_score = score * confidence
        
        if adjusted_score >= 85:
            return RecommendationPriority.CRITICAL
        elif adjusted_score >= 70:
            return RecommendationPriority.HIGH
        elif adjusted_score >= 50:
            return RecommendationPriority.MEDIUM
        elif adjusted_score >= 30:
            return RecommendationPriority.LOW
        else:
            return RecommendationPriority.INFO
    
    def _generate_reasoning(
        self,
        rec: Dict[str, Any],
        factors: Dict[str, float],
        weights: Dict[str, float],
        total_score: float
    ) -> str:
        """Génère un raisonnement textuel pour la recommandation"""
        # Identifier les facteurs dominants
        sorted_factors = sorted(
            factors.items(),
            key=lambda x: x[1] * weights[x[0]],
            reverse=True
        )
        
        top_factors = sorted_factors[:2]
        
        reasoning_parts = []
        
        # Score global
        reasoning_parts.append(
            f"Score global de {total_score:.1f}/100"
        )
        
        # Facteurs principaux
        factor_names = {
            'revenue_impact': 'impact sur les revenus',
            'ease_of_implementation': 'facilité d\'implémentation',
            'risk_level': 'niveau de risque acceptable',
            'time_to_value': 'rapidité des résultats',
            'data_confidence': 'qualité des données',
            'network_conditions': 'conditions réseau favorables'
        }
        
        for factor, value in top_factors:
            if value > 0.7:
                reasoning_parts.append(
                    f"{factor_names.get(factor, factor)} élevé ({value:.1%})"
                )
        
        return " - ".join(reasoning_parts) + "."
    
    def _update_stats(self, scored: ScoredRecommendation):
        """Met à jour les statistiques"""
        self.stats['total_scored'] += 1
        
        # Par catégorie
        cat = scored.category
        if cat not in self.stats['by_category']:
            self.stats['by_category'][cat] = {
                'count': 0,
                'avg_score': 0.0
            }
        
        cat_stats = self.stats['by_category'][cat]
        cat_stats['count'] += 1
        cat_stats['avg_score'] = (
            (cat_stats['avg_score'] * (cat_stats['count'] - 1) + scored.score)
            / cat_stats['count']
        )
        
        # Moyennes globales
        n = self.stats['total_scored']
        self.stats['avg_score'] = (
            (self.stats['avg_score'] * (n - 1) + scored.score) / n
        )
        self.stats['avg_confidence'] = (
            (self.stats['avg_confidence'] * (n - 1) + scored.confidence) / n
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        return self.stats.copy()


logger.info("Recommendation Scorer module loaded")

