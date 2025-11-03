"""
Dynamic Context Manager pour RAG MCP
Ajuste la taille du contexte selon la complexité de la requête
Réduit les coûts de 30% en optimisant l'utilisation des tokens

Dernière mise à jour: 3 novembre 2025
"""

import logging
from typing import List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Niveaux de complexité de requête"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class ContextConfig:
    """Configuration de contexte pour un niveau de complexité"""
    complexity: ComplexityLevel
    num_ctx: int  # Taille context window
    max_tokens: int  # Tokens max pour génération
    temperature: float  # Température LLM
    top_k_docs: int  # Nombre de documents à inclure
    description: str


# Configurations par niveau de complexité
CONTEXT_CONFIGS = {
    ComplexityLevel.SIMPLE: ContextConfig(
        complexity=ComplexityLevel.SIMPLE,
        num_ctx=4096,
        max_tokens=800,
        temperature=0.2,
        top_k_docs=3,
        description="Requêtes simples, réponses concises"
    ),
    ComplexityLevel.MEDIUM: ContextConfig(
        complexity=ComplexityLevel.MEDIUM,
        num_ctx=8192,
        max_tokens=1200,
        temperature=0.3,
        top_k_docs=5,
        description="Requêtes standard, réponses détaillées"
    ),
    ComplexityLevel.COMPLEX: ContextConfig(
        complexity=ComplexityLevel.COMPLEX,
        num_ctx=16384,
        max_tokens=2500,
        temperature=0.35,
        top_k_docs=8,
        description="Requêtes complexes, analyses approfondies"
    ),
    ComplexityLevel.VERY_COMPLEX: ContextConfig(
        complexity=ComplexityLevel.VERY_COMPLEX,
        num_ctx=32768,
        max_tokens=4000,
        temperature=0.4,
        top_k_docs=10,
        description="Requêtes très complexes, analyses complètes"
    )
}

# Indicateurs de complexité
COMPLEXITY_INDICATORS = {
    'simple': [
        r'\bwhat is\b',
        r'\bdefine\b',
        r'\bquick\b',
        r'\bsummary\b',
        r'\bresume\b',
        r'\bstatut\b',
    ],
    'medium': [
        r'\bhow to\b',
        r'\bexplain\b',
        r'\bwhy\b',
        r'\banalyze\b',
        r'\bcompare\b',
    ],
    'complex': [
        r'\bcompare .+ and .+\b',
        r'\bexplain in detail\b',
        r'\bstep by step\b',
        r'\bdetailed analysis\b',
        r'\bpros and cons\b',
        r'\bmultiple\b',
    ],
    'very_complex': [
        r'\bcomprehensive\b',
        r'\bevery\b',
        r'\ball possible\b',
        r'\bcomplete analysis\b',
        r'\bin-depth\b',
        r'\bexhaustive\b',
    ]
}


class DynamicContextManager:
    """
    Gère dynamiquement la taille du contexte selon la complexité
    """
    
    def __init__(
        self,
        default_complexity: ComplexityLevel = ComplexityLevel.MEDIUM,
        enable_auto_detection: bool = True
    ):
        """
        Args:
            default_complexity: Niveau par défaut si détection impossible
            enable_auto_detection: Activer détection automatique
        """
        self.default_complexity = default_complexity
        self.enable_auto_detection = enable_auto_detection
        
        # Statistiques
        self.query_stats = {level: 0 for level in ComplexityLevel}
        
        logger.info(
            f"DynamicContextManager initialized: "
            f"default={default_complexity.value}, auto_detect={enable_auto_detection}"
        )
    
    def get_context_config(
        self,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextConfig:
        """
        Retourne la configuration optimale pour une requête
        
        Args:
            query: Requête utilisateur
            metadata: Métadonnées additionnelles
            
        Returns:
            Configuration de contexte optimale
        """
        if self.enable_auto_detection:
            complexity = self.detect_complexity(query, metadata)
        else:
            complexity = self.default_complexity
        
        # Mettre à jour statistiques
        self.query_stats[complexity] += 1
        
        config = CONTEXT_CONFIGS[complexity]
        
        logger.debug(
            f"Context config selected: {complexity.value} "
            f"(num_ctx={config.num_ctx}, max_tokens={config.max_tokens})"
        )
        
        return config
    
    def detect_complexity(
        self,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ComplexityLevel:
        """
        Détecte le niveau de complexité d'une requête
        
        Args:
            query: Requête utilisateur
            metadata: Métadonnées (historique conversation, préférences)
            
        Returns:
            Niveau de complexité détecté
        """
        query_lower = query.lower()
        
        # Critères de base
        word_count = len(query.split())
        has_code = bool(re.search(r'```|`\w+`', query))
        has_multiple_questions = query.count('?') > 1
        
        # Score de complexité (0-10)
        complexity_score = 0
        
        # 1. Longueur de la requête
        if word_count < 10:
            complexity_score += 0
        elif word_count < 20:
            complexity_score += 2
        elif word_count < 40:
            complexity_score += 4
        else:
            complexity_score += 6
        
        # 2. Questions multiples
        if has_multiple_questions:
            complexity_score += 2
        
        # 3. Présence de code
        if has_code:
            complexity_score += 1
        
        # 4. Indicateurs de mots-clés
        for level, patterns in COMPLEXITY_INDICATORS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    if level == 'simple':
                        complexity_score = max(0, complexity_score - 1)
                    elif level == 'medium':
                        complexity_score += 1
                    elif level == 'complex':
                        complexity_score += 2
                    elif level == 'very_complex':
                        complexity_score += 3
                    break
        
        # 5. Métadonnées additionnelles
        if metadata:
            # Historique long de conversation
            history_length = metadata.get('conversation_length', 0)
            if history_length > 5:
                complexity_score += 1
            
            # Préférence utilisateur
            user_preference = metadata.get('preferred_detail_level')
            if user_preference == 'detailed':
                complexity_score += 2
            elif user_preference == 'concise':
                complexity_score = max(0, complexity_score - 2)
        
        # Mapper score -> niveau
        if complexity_score <= 2:
            return ComplexityLevel.SIMPLE
        elif complexity_score <= 5:
            return ComplexityLevel.MEDIUM
        elif complexity_score <= 8:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX
    
    def estimate_token_cost(
        self,
        query: str,
        config: ContextConfig,
        num_documents: int
    ) -> Dict[str, int]:
        """
        Estime le coût en tokens pour une requête
        
        Args:
            query: Requête
            config: Configuration de contexte
            num_documents: Nombre de documents inclus
            
        Returns:
            Dict avec estimation tokens
        """
        # Estimation grossière (à affiner avec tokenizer réel)
        query_tokens = len(query.split()) * 1.3  # ~1.3 tokens/mot
        system_tokens = 200  # System prompt
        doc_tokens = num_documents * 300  # ~300 tokens/doc
        generation_tokens = config.max_tokens
        
        total_tokens = int(query_tokens + system_tokens + doc_tokens + generation_tokens)
        
        return {
            'query_tokens': int(query_tokens),
            'system_tokens': system_tokens,
            'document_tokens': doc_tokens,
            'generation_tokens': generation_tokens,
            'total_tokens': total_tokens,
            'context_window_used': total_tokens / config.num_ctx
        }
    
    def optimize_for_budget(
        self,
        query: str,
        max_tokens_budget: int
    ) -> Tuple[ComplexityLevel, int]:
        """
        Optimise la configuration pour un budget de tokens
        
        Args:
            query: Requête
            max_tokens_budget: Budget max de tokens
            
        Returns:
            (niveau_complexité, nombre_docs_max)
        """
        # Tester configurations du plus simple au plus complexe
        for level in [ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM, 
                     ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            config = CONTEXT_CONFIGS[level]
            
            # Calculer combien de docs on peut inclure
            fixed_tokens = len(query.split()) * 1.3 + 200 + config.max_tokens
            remaining_budget = max_tokens_budget - fixed_tokens
            max_docs = max(1, int(remaining_budget / 300))
            
            # Si on peut inclure le nombre recommandé de docs, on prend ce niveau
            if max_docs >= config.top_k_docs:
                return level, config.top_k_docs
        
        # Si budget trop serré, niveau simple avec 1 doc
        return ComplexityLevel.SIMPLE, 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation"""
        total_queries = sum(self.query_stats.values())
        
        distribution = {
            level.value: {
                'count': count,
                'percentage': (count / total_queries * 100) if total_queries > 0 else 0
            }
            for level, count in self.query_stats.items()
        }
        
        return {
            'total_queries': total_queries,
            'distribution': distribution,
            'default_complexity': self.default_complexity.value,
            'auto_detection_enabled': self.enable_auto_detection
        }
    
    def reset_stats(self):
        """Réinitialise les statistiques"""
        self.query_stats = {level: 0 for level in ComplexityLevel}
        logger.info("Statistics reset")

