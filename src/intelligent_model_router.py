"""
Intelligent Model Router - Route les requêtes vers le modèle optimal
Optimise le rapport coût/qualité/latence selon le contexte
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from app.services.rag_metrics import (
    rag_model_requests,
    rag_model_fallbacks,
    rag_processing_duration
)

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Tiers de modèles selon leur coût/qualité"""
    LOCAL = "local"          # Ollama local (gratuit, rapide, qualité moyenne)
    BALANCED = "balanced"    # Claude Haiku (coût modéré, bonne qualité)
    PREMIUM = "premium"      # Claude Opus (coût élevé, excellente qualité)


class UserTier(Enum):
    """Tiers utilisateur déterminant l'accès aux modèles"""
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class ModelConfig:
    """Configuration d'un modèle IA"""
    name: str
    tier: ModelTier
    cost_per_1m_tokens: float  # Coût en $ pour 1M tokens
    avg_latency_ms: int
    quality_score: float  # Score 0-10
    max_tokens: int
    context_window: int
    provider: str  # "ollama", "anthropic", "openai"
    
    def cost_for_tokens(self, input_tokens: int, output_tokens: int) -> float:
        """Calcule le coût pour un nombre de tokens"""
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1_000_000) * self.cost_per_1m_tokens


# ============================================================================
# CATALOGUE DE MODÈLES
# ============================================================================

MODELS_CATALOG: Dict[str, ModelConfig] = {
    # Modèles locaux Ollama (gratuits) - Base
    "llama3:8b-instruct": ModelConfig(
        name="llama3:8b-instruct",
        tier=ModelTier.LOCAL,
        cost_per_1m_tokens=0.0,
        avg_latency_ms=800,
        quality_score=7.5,  # Amélioré avec prompt engineering
        max_tokens=4096,
        context_window=8192,
        provider="ollama"
    ),
    "mistral:7b-instruct": ModelConfig(
        name="mistral:7b-instruct",
        tier=ModelTier.LOCAL,
        cost_per_1m_tokens=0.0,
        avg_latency_ms=700,
        quality_score=6.5,
        max_tokens=4096,
        context_window=8192,
        provider="ollama"
    ),
    
    # Modèles Ollama optimisés - Performance/Qualité
    "llama3:13b-instruct": ModelConfig(
        name="llama3:13b-instruct",
        tier=ModelTier.LOCAL,
        cost_per_1m_tokens=0.0,
        avg_latency_ms=1500,
        quality_score=8.2,
        max_tokens=8192,
        context_window=8192,
        provider="ollama"
    ),
    "qwen2.5:14b-instruct": ModelConfig(
        name="qwen2.5:14b-instruct",
        tier=ModelTier.LOCAL,
        cost_per_1m_tokens=0.0,
        avg_latency_ms=1400,
        quality_score=8.5,  # Excellent pour analyse technique
        max_tokens=8192,
        context_window=32768,  # Context window énorme!
        provider="ollama"
    ),
    "phi3:medium": ModelConfig(
        name="phi3:medium",
        tier=ModelTier.LOCAL,
        cost_per_1m_tokens=0.0,
        avg_latency_ms=500,
        quality_score=7.8,
        max_tokens=4096,
        context_window=128000,  # Très grand context!
        provider="ollama"
    ),
    "codellama:13b-instruct": ModelConfig(
        name="codellama:13b-instruct",
        tier=ModelTier.LOCAL,
        cost_per_1m_tokens=0.0,
        avg_latency_ms=1300,
        quality_score=8.0,  # Spécialisé code/technique
        max_tokens=4096,
        context_window=16384,
        provider="ollama"
    ),
    
    # Anthropic Claude (cloud)
    "claude-3-haiku-20240307": ModelConfig(
        name="claude-3-haiku-20240307",
        tier=ModelTier.BALANCED,
        cost_per_1m_tokens=0.25,  # $0.25 per 1M input tokens
        avg_latency_ms=1200,
        quality_score=8.5,
        max_tokens=4096,
        context_window=200000,
        provider="anthropic"
    ),
    "claude-3-sonnet-20240229": ModelConfig(
        name="claude-3-sonnet-20240229",
        tier=ModelTier.BALANCED,
        cost_per_1m_tokens=3.0,
        avg_latency_ms=1500,
        quality_score=9.0,
        max_tokens=4096,
        context_window=200000,
        provider="anthropic"
    ),
    "claude-3-opus-20240229": ModelConfig(
        name="claude-3-opus-20240229",
        tier=ModelTier.PREMIUM,
        cost_per_1m_tokens=15.0,
        avg_latency_ms=2000,
        quality_score=9.5,
        max_tokens=4096,
        context_window=200000,
        provider="anthropic"
    ),
}


class QueryComplexityAnalyzer:
    """Analyse la complexité d'une requête pour déterminer le modèle approprié"""
    
    @staticmethod
    def analyze(
        query: str,
        context: Dict[str, Any],
        user_tier: UserTier = UserTier.STANDARD
    ) -> float:
        """
        Analyse la complexité d'une requête
        
        Args:
            query: Texte de la requête
            context: Contexte additionnel
            user_tier: Tier de l'utilisateur
            
        Returns:
            Score de complexité entre 0 (simple) et 1 (très complexe)
        """
        score = 0.0
        
        # Longueur de la requête
        word_count = len(query.split())
        if word_count > 100:
            score += 0.2
        elif word_count > 50:
            score += 0.1
        
        # Mots-clés indiquant de la complexité
        complex_keywords = [
            'analyse', 'détaillé', 'complet', 'approfondi', 'stratégie',
            'optimisation', 'comparaison', 'évaluation', 'recommandation',
            'priorité', 'critique', 'complexe'
        ]
        keyword_count = sum(1 for kw in complex_keywords if kw in query.lower())
        score += min(keyword_count * 0.1, 0.3)
        
        # Contexte nécessitant de l'analyse
        if context.get('requires_analysis', False):
            score += 0.3
        
        if context.get('requires_prioritization', False):
            score += 0.2
        
        if context.get('historical_data_required', False):
            score += 0.2
        
        # Requêtes techniques complexes
        if any(term in query.lower() for term in ['machine learning', 'prédiction', 'forecast']):
            score += 0.3
        
        # Type de sortie demandé
        output_type = context.get('output_type', 'text')
        if output_type in ['structured', 'json', 'detailed_report']:
            score += 0.15
        
        # Normaliser entre 0 et 1
        return min(score, 1.0)


class IntelligentModelRouter:
    """
    Router intelligent pour sélectionner le modèle optimal
    """
    
    def __init__(
        self,
        default_user_tier: UserTier = UserTier.STANDARD,
        enable_cost_optimization: bool = True,
        max_cost_per_request: float = 0.05  # $0.05 max par requête
    ):
        self.default_user_tier = default_user_tier
        self.enable_cost_optimization = enable_cost_optimization
        self.max_cost_per_request = max_cost_per_request
        
        self.complexity_analyzer = QueryComplexityAnalyzer()
        
        # Statistiques de routage
        self.stats = {
            'total_requests': 0,
            'by_tier': {tier.value: 0 for tier in ModelTier},
            'total_cost': 0.0,
            'fallback_count': 0,
            'avg_complexity': 0.0
        }
        
        logger.info(
            f"Intelligent Model Router initialized: "
            f"default_tier={default_user_tier.value}, "
            f"cost_optimization={enable_cost_optimization}"
        )
    
    def route_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_tier: Optional[UserTier] = None,
        estimated_tokens: Optional[int] = None
    ) -> Tuple[ModelConfig, Dict[str, Any]]:
        """
        Route une requête vers le modèle optimal
        
        Args:
            query: Texte de la requête
            context: Contexte additionnel
            user_tier: Tier de l'utilisateur
            estimated_tokens: Estimation du nombre de tokens
            
        Returns:
            Tuple (model_config, routing_info)
        """
        context = context or {}
        user_tier = user_tier or self.default_user_tier
        estimated_tokens = estimated_tokens or self._estimate_tokens(query, context)
        
        # Analyser la complexité
        complexity = self.complexity_analyzer.analyze(query, context, user_tier)
        
        # Déterminer le modèle approprié
        model_config = self._select_model(
            complexity=complexity,
            user_tier=user_tier,
            estimated_tokens=estimated_tokens,
            context=context
        )
        
        # Informations de routage
        routing_info = {
            'complexity_score': complexity,
            'user_tier': user_tier.value,
            'selected_model': model_config.name,
            'model_tier': model_config.tier.value,
            'estimated_cost': model_config.cost_for_tokens(estimated_tokens, estimated_tokens),
            'estimated_latency_ms': model_config.avg_latency_ms,
            'routing_timestamp': datetime.utcnow().isoformat()
        }
        
        # Mettre à jour les statistiques
        self._update_stats(model_config, complexity, routing_info['estimated_cost'])
        
        # Métriques
        rag_model_requests.labels(
            model_name=model_config.name,
            model_type='generation',
            status='routed'
        ).inc()
        
        logger.debug(
            f"Routed query: complexity={complexity:.2f}, "
            f"model={model_config.name}, "
            f"cost_estimate=${routing_info['estimated_cost']:.4f}"
        )
        
        return model_config, routing_info
    
    def _select_model(
        self,
        complexity: float,
        user_tier: UserTier,
        estimated_tokens: int,
        context: Dict[str, Any]
    ) -> ModelConfig:
        """Sélectionne le modèle optimal"""
        
        # Contraintes selon le tier utilisateur
        if user_tier == UserTier.FREE:
            # Free tier: seulement modèles locaux
            available_models = [
                m for m in MODELS_CATALOG.values()
                if m.tier == ModelTier.LOCAL
            ]
        
        elif user_tier == UserTier.STANDARD:
            # Standard: local + balanced
            available_models = [
                m for m in MODELS_CATALOG.values()
                if m.tier in [ModelTier.LOCAL, ModelTier.BALANCED]
            ]
        
        elif user_tier in [UserTier.PREMIUM, UserTier.ENTERPRISE]:
            # Premium: tous les modèles
            available_models = list(MODELS_CATALOG.values())
        
        else:
            available_models = list(MODELS_CATALOG.values())
        
        # Filtrer par contraintes de coût
        if self.enable_cost_optimization:
            available_models = [
                m for m in available_models
                if m.cost_for_tokens(estimated_tokens, estimated_tokens) <= self.max_cost_per_request
            ]
        
        if not available_models:
            # Fallback vers le modèle local le moins cher
            logger.warning("No models meet cost constraints, falling back to local model")
            return MODELS_CATALOG["llama3:8b-instruct"]
        
        # Sélection selon la complexité
        if complexity < 0.3:
            # Requête simple: modèle local rapide
            candidates = [m for m in available_models if m.tier == ModelTier.LOCAL]
            if candidates:
                return min(candidates, key=lambda m: m.avg_latency_ms)
        
        elif complexity < 0.7:
            # Requête moyenne: modèle balanced
            candidates = [m for m in available_models if m.tier == ModelTier.BALANCED]
            if candidates:
                # Optimiser rapport qualité/coût
                return max(candidates, key=lambda m: m.quality_score / (m.cost_per_1m_tokens + 0.01))
        
        else:
            # Requête complexe: meilleur modèle disponible
            candidates = [m for m in available_models if m.tier == ModelTier.PREMIUM]
            if candidates:
                return max(candidates, key=lambda m: m.quality_score)
            
            # Fallback vers balanced si premium pas disponible
            candidates = [m for m in available_models if m.tier == ModelTier.BALANCED]
            if candidates:
                return max(candidates, key=lambda m: m.quality_score)
        
        # Fallback général: meilleur modèle disponible
        return max(available_models, key=lambda m: m.quality_score)
    
    def _estimate_tokens(self, query: str, context: Dict[str, Any]) -> int:
        """Estime le nombre de tokens d'une requête"""
        # Approximation: ~0.75 mots = 1 token
        query_tokens = int(len(query.split()) / 0.75)
        
        # Ajouter tokens de contexte
        context_size = context.get('context_size', 0)
        system_prompt_tokens = 100  # Estimation
        
        total_input = query_tokens + context_size + system_prompt_tokens
        
        # Estimer output (généralement plus court que input)
        estimated_output = int(total_input * 0.5)
        
        return total_input + estimated_output
    
    def get_fallback_model(
        self,
        failed_model: str,
        reason: str,
        user_tier: UserTier = None
    ) -> ModelConfig:
        """
        Retourne un modèle de fallback en cas d'échec
        
        Args:
            failed_model: Nom du modèle qui a échoué
            reason: Raison de l'échec
            user_tier: Tier utilisateur
            
        Returns:
            Configuration du modèle de fallback
        """
        user_tier = user_tier or self.default_user_tier
        
        # Logique de fallback: descendre d'un tier
        if failed_model in MODELS_CATALOG:
            failed_config = MODELS_CATALOG[failed_model]
            
            if failed_config.tier == ModelTier.PREMIUM:
                # Premium -> Balanced
                candidates = [
                    m for m in MODELS_CATALOG.values()
                    if m.tier == ModelTier.BALANCED
                ]
            elif failed_config.tier == ModelTier.BALANCED:
                # Balanced -> Local
                candidates = [
                    m for m in MODELS_CATALOG.values()
                    if m.tier == ModelTier.LOCAL
                ]
            else:
                # Local -> autre modèle local
                candidates = [
                    m for m in MODELS_CATALOG.values()
                    if m.tier == ModelTier.LOCAL and m.name != failed_model
                ]
        else:
            # Modèle inconnu, fallback vers local
            candidates = [
                m for m in MODELS_CATALOG.values()
                if m.tier == ModelTier.LOCAL
            ]
        
        if not candidates:
            # Dernier recours: llama3
            fallback = MODELS_CATALOG["llama3:8b-instruct"]
        else:
            # Choisir le meilleur candidat
            fallback = max(candidates, key=lambda m: m.quality_score)
        
        # Métriques
        rag_model_fallbacks.labels(
            from_model=failed_model,
            to_model=fallback.name,
            reason=reason
        ).inc()
        
        self.stats['fallback_count'] += 1
        
        logger.warning(
            f"Fallback from {failed_model} to {fallback.name} "
            f"(reason: {reason})"
        )
        
        return fallback
    
    def _update_stats(self, model: ModelConfig, complexity: float, cost: float):
        """Met à jour les statistiques"""
        self.stats['total_requests'] += 1
        self.stats['by_tier'][model.tier.value] += 1
        self.stats['total_cost'] += cost
        
        # Moyenne mobile de la complexité
        n = self.stats['total_requests']
        self.stats['avg_complexity'] = (
            (self.stats['avg_complexity'] * (n - 1) + complexity) / n
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de routage"""
        return {
            **self.stats,
            'avg_cost_per_request': (
                self.stats['total_cost'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0.0
            ),
            'tier_distribution': {
                tier: (count / self.stats['total_requests'] * 100)
                if self.stats['total_requests'] > 0 else 0.0
                for tier, count in self.stats['by_tier'].items()
            }
        }
    
    def reset_stats(self):
        """Réinitialise les statistiques"""
        self.stats = {
            'total_requests': 0,
            'by_tier': {tier.value: 0 for tier in ModelTier},
            'total_cost': 0.0,
            'fallback_count': 0,
            'avg_complexity': 0.0
        }


# ============================================================================
# INSTANCE GLOBALE
# ============================================================================

# Router global avec configuration par défaut
model_router = IntelligentModelRouter()


logger.info("Intelligent Model Router module loaded")

