"""
Stratégie d'optimisation Ollama selon le type de requête
Permet de sélectionner le modèle et les paramètres optimaux pour chaque cas d'usage
"""

import logging
from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types de requêtes Lightning Network"""
    QUICK_ANALYSIS = "quick_analysis"          # Analyse rapide
    DETAILED_RECOMMENDATIONS = "detailed_recs"  # Recommandations détaillées
    TECHNICAL_EXPLANATION = "tech_explain"      # Explication technique
    SCORING = "scoring"                         # Scoring de recommandations
    STRATEGIC_PLANNING = "strategic"            # Planning stratégique
    TROUBLESHOOTING = "troubleshooting"         # Diagnostic de problèmes


@dataclass
class OllamaStrategy:
    """Stratégie de génération pour un type de requête"""
    model: str
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    num_ctx: int
    num_predict: int
    stop_sequences: List[str]
    system_prompt_template: str
    description: str


# Stratégies optimisées par type de requête
OLLAMA_STRATEGIES: Dict[QueryType, OllamaStrategy] = {
    QueryType.QUICK_ANALYSIS: OllamaStrategy(
        model="phi3:medium",
        temperature=0.2,
        top_p=0.85,
        top_k=30,
        repeat_penalty=1.15,
        num_ctx=8192,
        num_predict=800,
        stop_sequences=["###", "---"],
        system_prompt_template="Tu es un analyste Lightning Network expert. Fournis une analyse concise et factuelle en 3-5 points clés.",
        description="Analyse rapide pour vue d'ensemble"
    ),
    
    QueryType.DETAILED_RECOMMENDATIONS: OllamaStrategy(
        model="qwen2.5:14b-instruct",
        temperature=0.3,
        top_p=0.92,
        top_k=40,
        repeat_penalty=1.1,
        num_ctx=16384,
        num_predict=2500,
        stop_sequences=["### Input:", "---"],
        system_prompt_template="""Tu es un expert senior Lightning Network avec 5+ ans d'expérience.

Analyse les métriques fournies et génère des recommandations:
1. Priorisées par ROI (CRITIQUE → LOW)
2. Avec commandes CLI précises
3. Avec estimation d'impact quantifiée
4. Avec évaluation des risques

Format strict : Markdown structuré avec émojis de priorité.""",
        description="Recommandations détaillées avec CLI et ROI"
    ),
    
    QueryType.TECHNICAL_EXPLANATION: OllamaStrategy(
        model="codellama:13b-instruct",
        temperature=0.25,
        top_p=0.9,
        top_k=35,
        repeat_penalty=1.12,
        num_ctx=8192,
        num_predict=1500,
        stop_sequences=["```\n\n", "---"],
        system_prompt_template="Tu es un expert technique Lightning. Explique les concepts avec précision et clarté, en utilisant des exemples concrets et des commandes CLI quand pertinent.",
        description="Explications techniques approfondies"
    ),
    
    QueryType.SCORING: OllamaStrategy(
        model="phi3:medium",
        temperature=0.1,
        top_p=0.8,
        top_k=20,
        repeat_penalty=1.2,
        num_ctx=4096,
        num_predict=500,
        stop_sequences=["\n\n\n"],
        system_prompt_template="Tu es un système de scoring Lightning. Évalue objectivement selon les métriques fournies. Format : JSON ou liste structurée.",
        description="Scoring objectif de recommandations"
    ),
    
    QueryType.STRATEGIC_PLANNING: OllamaStrategy(
        model="llama3:13b-instruct",
        temperature=0.4,
        top_p=0.95,
        top_k=50,
        repeat_penalty=1.08,
        num_ctx=8192,
        num_predict=2000,
        stop_sequences=["### Conclusion"],
        system_prompt_template="""Tu es un conseiller stratégique Lightning Network.

Fournis une analyse stratégique à 3-6 mois incluant:
- Positionnement réseau optimal
- Stratégie de croissance
- Allocation de liquidité
- Gestion des risques
- ROI estimé par stratégie""",
        description="Planning stratégique long terme"
    ),
    
    QueryType.TROUBLESHOOTING: OllamaStrategy(
        model="codellama:13b-instruct",
        temperature=0.15,
        top_p=0.85,
        top_k=25,
        repeat_penalty=1.18,
        num_ctx=8192,
        num_predict=1200,
        stop_sequences=["### Résolu"],
        system_prompt_template="""Tu es un expert en diagnostic Lightning Network.

Analyse les erreurs/problèmes et fournis:
1. Cause racine probable
2. Solutions étape par étape
3. Commandes de diagnostic
4. Commandes de résolution
5. Prévention future""",
        description="Diagnostic et résolution de problèmes"
    ),
}


def get_strategy(query_type: QueryType, fallback_model: str = "llama3:8b-instruct") -> OllamaStrategy:
    """
    Retourne la stratégie optimale pour un type de requête
    
    Args:
        query_type: Type de requête
        fallback_model: Modèle de fallback si le modèle préféré n'est pas disponible
        
    Returns:
        OllamaStrategy configurée
    """
    strategy = OLLAMA_STRATEGIES.get(query_type, OLLAMA_STRATEGIES[QueryType.DETAILED_RECOMMENDATIONS])
    
    # Fallback vers modèle de base si modèle préféré non disponible
    # TODO: Implémenter vérification de disponibilité du modèle
    
    return strategy


def detect_query_type(query: str, context: Dict[str, Any]) -> QueryType:
    """
    Détecte automatiquement le type de requête
    
    Args:
        query: Texte de la requête
        context: Contexte additionnel
        
    Returns:
        QueryType détecté
    """
    query_lower = query.lower()
    
    # Troubleshooting
    if any(word in query_lower for word in ['erreur', 'error', 'problème', 'ne fonctionne pas', 'échec', 'fail', 'debug']):
        return QueryType.TROUBLESHOOTING
    
    # Quick analysis
    if any(word in query_lower for word in ['résumé', 'rapide', 'quick', 'overview', 'état', 'status']):
        return QueryType.QUICK_ANALYSIS
    
    # Scoring
    if any(word in query_lower for word in ['score', 'évalue', 'note', 'classe', 'priorité', 'compare']):
        return QueryType.SCORING
    
    # Technical explanation
    if any(word in query_lower for word in ['comment', 'pourquoi', 'expliquer', 'explain', 'fonctionnement', 'works']):
        return QueryType.TECHNICAL_EXPLANATION
    
    # Strategic
    if any(word in query_lower for word in ['stratégie', 'strategy', 'plan', 'roadmap', 'croissance', 'growth', 'long terme']):
        return QueryType.STRATEGIC_PLANNING
    
    # Contexte-based detection
    if context.get('requires_strategy', False):
        return QueryType.STRATEGIC_PLANNING
    
    if context.get('is_diagnostic', False):
        return QueryType.TROUBLESHOOTING
    
    # Detailed recommendations (default)
    return QueryType.DETAILED_RECOMMENDATIONS


def get_optimal_model_for_hardware(
    query_type: QueryType,
    available_ram_gb: int = 16,
    gpu_available: bool = False
) -> str:
    """
    Sélectionne le modèle optimal selon le hardware disponible
    
    Args:
        query_type: Type de requête
        available_ram_gb: RAM disponible en GB
        gpu_available: GPU CUDA disponible
        
    Returns:
        Nom du modèle Ollama optimal
    """
    strategy = get_strategy(query_type)
    preferred_model = strategy.model
    
    # Mapping de modèles selon RAM
    # 8GB RAM: Modèles 7B
    # 16GB RAM: Modèles 13-14B
    # 32GB+ RAM: Modèles 70B+
    
    if available_ram_gb < 8:
        # Fallback vers petit modèle
        logger.warning(f"RAM insuffisante ({available_ram_gb}GB), fallback vers modèle léger")
        return "phi3:medium"  # ~3.8GB
    
    elif available_ram_gb < 16:
        # Limiter aux modèles 7B-8B
        if "13b" in preferred_model or "14b" in preferred_model:
            logger.info(f"RAM limitée ({available_ram_gb}GB), fallback vers 8B model")
            return "llama3:8b-instruct"
        return preferred_model
    
    elif available_ram_gb >= 32 and gpu_available:
        # Possibilité d'utiliser modèles plus gros
        logger.info(f"Hardware puissant détecté ({available_ram_gb}GB RAM + GPU)")
        # Possibilité d'upgrader vers 70B+ si disponible
        return preferred_model
    
    # Configuration standard (16-32GB RAM)
    return preferred_model


def list_available_strategies() -> List[Dict[str, Any]]:
    """Liste toutes les stratégies disponibles avec leurs caractéristiques"""
    strategies = []
    
    for query_type, strategy in OLLAMA_STRATEGIES.items():
        strategies.append({
            'query_type': query_type.value,
            'model': strategy.model,
            'description': strategy.description,
            'temperature': strategy.temperature,
            'max_tokens': strategy.num_predict,
            'context_window': strategy.num_ctx,
            'characteristics': {
                'speed': 'fast' if 'phi3' in strategy.model else 'medium',
                'quality': 'high' if '14b' in strategy.model or '13b' in strategy.model else 'medium',
                'specialization': query_type.value
            }
        })
    
    return strategies


def get_strategy_stats() -> Dict[str, Any]:
    """Retourne des statistiques sur les stratégies disponibles"""
    return {
        'total_strategies': len(OLLAMA_STRATEGIES),
        'models_used': list(set(s.model for s in OLLAMA_STRATEGIES.values())),
        'avg_temperature': sum(s.temperature for s in OLLAMA_STRATEGIES.values()) / len(OLLAMA_STRATEGIES),
        'avg_context_window': sum(s.num_ctx for s in OLLAMA_STRATEGIES.values()) / len(OLLAMA_STRATEGIES),
        'strategies_by_type': {qt.value: OLLAMA_STRATEGIES[qt].model for qt in QueryType}
    }


# Validation au chargement
def validate_strategies():
    """Valide la cohérence des stratégies"""
    issues = []
    
    for query_type, strategy in OLLAMA_STRATEGIES.items():
        # Vérifier températures valides
        if not 0 <= strategy.temperature <= 2:
            issues.append(f"{query_type.value}: température invalide ({strategy.temperature})")
        
        # Vérifier top_p valide
        if not 0 <= strategy.top_p <= 1:
            issues.append(f"{query_type.value}: top_p invalide ({strategy.top_p})")
        
        # Vérifier num_predict raisonnable
        if strategy.num_predict > 4096:
            issues.append(f"{query_type.value}: num_predict très élevé ({strategy.num_predict})")
    
    if issues:
        logger.warning(f"Problèmes détectés dans les stratégies: {issues}")
    else:
        logger.info(f"Toutes les {len(OLLAMA_STRATEGIES)} stratégies sont valides")
    
    return len(issues) == 0


# Valider au chargement du module
validate_strategies()

logger.info(f"Ollama Strategy Optimizer loaded: {len(OLLAMA_STRATEGIES)} strategies available")

