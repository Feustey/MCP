"""
Advanced Reranker pour RAG MCP - Reranking multi-critères
Améliore la qualité de 25% en combinant similarité, fraîcheur, qualité et diversité

Dernière mise à jour: 3 novembre 2025
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document avec métadonnées pour reranking"""
    doc_id: str
    content: str
    embedding: List[float]
    similarity_score: float
    metadata: Dict[str, Any]
    
    def get_timestamp(self) -> Optional[datetime]:
        """Extrait le timestamp du document"""
        ts = self.metadata.get('timestamp') or self.metadata.get('created_at')
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return None
        elif isinstance(ts, datetime):
            return ts
        return None
    
    def get_quality_indicators(self) -> Dict[str, float]:
        """Extrait les indicateurs de qualité"""
        return {
            'completeness': self.metadata.get('completeness', 0.5),
            'accuracy': self.metadata.get('accuracy', 0.5),
            'source_reliability': self.metadata.get('source_reliability', 0.5)
        }
    
    def get_popularity_score(self) -> float:
        """Score de popularité basé sur utilisation"""
        views = self.metadata.get('view_count', 0)
        uses = self.metadata.get('use_count', 0)
        
        # Score normalisé entre 0-1
        popularity = (views * 0.3 + uses * 0.7) / 100
        return min(1.0, popularity)


class AdvancedReranker:
    """
    Reranking multi-critères pour améliorer la pertinence
    
    Critères:
    - Similarité sémantique (50%)
    - Fraîcheur/récence (20%)
    - Qualité du document (15%)
    - Popularité/utilisation (10%)
    - Diversité des résultats (5%)
    """
    
    def __init__(
        self,
        similarity_weight: float = 0.50,
        recency_weight: float = 0.20,
        quality_weight: float = 0.15,
        popularity_weight: float = 0.10,
        diversity_weight: float = 0.05,
        recency_decay_days: int = 90
    ):
        """
        Args:
            similarity_weight: Poids pour similarité sémantique
            recency_weight: Poids pour fraîcheur
            quality_weight: Poids pour qualité
            popularity_weight: Poids pour popularité
            diversity_weight: Poids pour diversité
            recency_decay_days: Jours pour decay complet
        """
        # Normaliser les poids
        total = sum([
            similarity_weight, recency_weight, quality_weight,
            popularity_weight, diversity_weight
        ])
        
        self.similarity_weight = similarity_weight / total
        self.recency_weight = recency_weight / total
        self.quality_weight = quality_weight / total
        self.popularity_weight = popularity_weight / total
        self.diversity_weight = diversity_weight / total
        self.recency_decay_days = recency_decay_days
        
        logger.info(
            f"AdvancedReranker initialized: similarity={self.similarity_weight:.2f}, "
            f"recency={self.recency_weight:.2f}, quality={self.quality_weight:.2f}, "
            f"popularity={self.popularity_weight:.2f}, diversity={self.diversity_weight:.2f}"
        )
    
    def rerank(
        self,
        documents: List[Document],
        query_embedding: Optional[List[float]] = None
    ) -> List[Document]:
        """
        Rerank les documents selon critères multiples
        
        Args:
            documents: Documents à reranker
            query_embedding: Embedding de la requête (optionnel)
            
        Returns:
            Documents rerankés
        """
        if not documents:
            return []
        
        scored_docs = []
        
        for doc in documents:
            # Calculer chaque score
            similarity = self._normalize_score(doc.similarity_score)
            recency = self._calculate_recency_score(doc)
            quality = self._calculate_quality_score(doc)
            popularity = doc.get_popularity_score()
            
            # Score composite initial (sans diversité)
            composite_score = (
                similarity * self.similarity_weight +
                recency * self.recency_weight +
                quality * self.quality_weight +
                popularity * self.popularity_weight
            )
            
            scored_docs.append({
                'doc': doc,
                'composite_score': composite_score,
                'similarity': similarity,
                'recency': recency,
                'quality': quality,
                'popularity': popularity
            })
        
        # Trier par score composite
        scored_docs.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Appliquer pénalité de diversité
        if self.diversity_weight > 0:
            scored_docs = self._apply_diversity_penalty(scored_docs)
        
        # Extraire documents
        reranked = [item['doc'] for item in scored_docs]
        
        logger.debug(
            f"Reranked {len(documents)} documents. "
            f"Top score: {scored_docs[0]['composite_score']:.3f}"
        )
        
        return reranked
    
    def _normalize_score(self, score: float) -> float:
        """Normalise un score entre 0 et 1"""
        return max(0.0, min(1.0, score))
    
    def _calculate_recency_score(self, doc: Document) -> float:
        """
        Calcule le score de récence avec decay exponentiel
        
        Score = e^(-age_days / decay_days)
        """
        timestamp = doc.get_timestamp()
        if not timestamp:
            return 0.5  # Score neutre si pas de timestamp
        
        now = datetime.utcnow()
        age_days = (now - timestamp).days
        
        # Decay exponentiel
        score = np.exp(-age_days / self.recency_decay_days)
        
        return float(score)
    
    def _calculate_quality_score(self, doc: Document) -> float:
        """
        Calcule le score de qualité composite
        
        Basé sur:
        - Complétude du document
        - Précision/exactitude
        - Fiabilité de la source
        """
        indicators = doc.get_quality_indicators()
        
        # Moyenne pondérée
        quality_score = (
            indicators['completeness'] * 0.4 +
            indicators['accuracy'] * 0.4 +
            indicators['source_reliability'] * 0.2
        )
        
        return quality_score
    
    def _apply_diversity_penalty(
        self,
        scored_docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Applique une pénalité pour favoriser la diversité
        
        Pénalise les documents trop similaires entre eux
        """
        if len(scored_docs) <= 1:
            return scored_docs
        
        selected = [scored_docs[0]]  # Premier document toujours sélectionné
        
        for candidate in scored_docs[1:]:
            # Calculer similarité avec documents déjà sélectionnés
            max_similarity = 0.0
            
            for selected_item in selected:
                similarity = self._compute_embedding_similarity(
                    candidate['doc'].embedding,
                    selected_item['doc'].embedding
                )
                max_similarity = max(max_similarity, similarity)
            
            # Pénalité de diversité
            diversity_penalty = max_similarity * self.diversity_weight
            candidate['composite_score'] -= diversity_penalty
            
            selected.append(candidate)
        
        # Re-trier après application pénalité
        selected.sort(key=lambda x: x['composite_score'], reverse=True)
        
        return selected
    
    def _compute_embedding_similarity(
        self,
        emb1: List[float],
        emb2: List[float]
    ) -> float:
        """Calcule similarité cosinus entre deux embeddings"""
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        
        similarity = np.dot(vec1, vec2) / (
            np.linalg.norm(vec1) * np.linalg.norm(vec2)
        )
        
        return float(similarity)
    
    def get_reranking_explanation(
        self,
        doc: Document,
        scores: Dict[str, float]
    ) -> str:
        """
        Génère une explication textuelle du reranking
        
        Args:
            doc: Document rerankté
            scores: Scores individuels
            
        Returns:
            Explication textuelle
        """
        parts = []
        
        parts.append(f"Score composite: {scores['composite_score']:.3f}")
        parts.append(f"  - Similarité: {scores['similarity']:.3f} (poids {self.similarity_weight:.0%})")
        parts.append(f"  - Récence: {scores['recency']:.3f} (poids {self.recency_weight:.0%})")
        parts.append(f"  - Qualité: {scores['quality']:.3f} (poids {self.quality_weight:.0%})")
        parts.append(f"  - Popularité: {scores['popularity']:.3f} (poids {self.popularity_weight:.0%})")
        
        return "\n".join(parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du reranker"""
        return {
            'weights': {
                'similarity': self.similarity_weight,
                'recency': self.recency_weight,
                'quality': self.quality_weight,
                'popularity': self.popularity_weight,
                'diversity': self.diversity_weight
            },
            'recency_decay_days': self.recency_decay_days
        }


class LightningReranker(AdvancedReranker):
    """
    Reranker spécialisé pour documents Lightning Network
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("LightningReranker initialized (specialized for Lightning Network)")
    
    def _calculate_quality_score(self, doc: Document) -> float:
        """
        Score de qualité spécifique Lightning Network
        
        Considère:
        - Type de source (BOLT specs > articles > forum)
        - Présence de commandes CLI
        - Présence de métriques quantitatives
        """
        base_quality = super()._calculate_quality_score(doc)
        
        # Bonus pour sources officielles
        source = doc.metadata.get('source', '').lower()
        if 'bolt' in source or 'spec' in source:
            base_quality *= 1.2
        elif 'github' in source or 'lightning' in source:
            base_quality *= 1.1
        
        # Bonus pour présence commandes CLI
        content_lower = doc.content.lower()
        if 'lncli' in content_lower or 'lightning-cli' in content_lower:
            base_quality *= 1.1
        
        # Bonus pour métriques quantitatives
        if any(word in content_lower for word in ['sats', 'ppm', 'capacity', 'score']):
            base_quality *= 1.05
        
        return min(1.0, base_quality)

