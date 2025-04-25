"""
Module de Récupération Augmentée pour le système MCP.

Ce module étend les capacités de l'EnhancedContextManager avec:
- Requêtes hybrides avancées
- Pondération dynamique des sources
- Extraction automatique de contraintes
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional, Set
from datetime import datetime, timedelta
import asyncio
import time
import numpy as np
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

from src.context_enrichment import EnhancedContextManager

logger = logging.getLogger(__name__)

class AugmentedRetrievalManager(EnhancedContextManager):
    """
    Extension de l'EnhancedContextManager avec des capacités de récupération augmentée.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialise le gestionnaire de récupération augmentée."""
        super().__init__(*args, **kwargs)
        self.source_weights = {
            "metrics_history": 1.0,
            "hypothesis": 0.8,
            "documentation": 0.7,
            "logs": 0.6
        }
        # Facteurs d'apprentissage pour ajustement dynamique
        self.source_learning_rate = 0.1
        self.recency_weight = 0.8
        self.query_history = []
        
    async def retrieve_enhanced_context(
        self, 
        query: str,
        limit: int = 10,
        dynamic_weighting: bool = True,
        *args, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Version améliorée de la récupération avec pondération dynamique.
        
        Args:
            query: Texte de la requête
            limit: Nombre maximum de résultats
            dynamic_weighting: Activer la pondération dynamique
            *args, **kwargs: Paramètres additionnels pour la méthode parent
            
        Returns:
            Liste des résultats enrichis
        """
        # Extraction avancée des contraintes
        constraints = self._advanced_constraint_extraction(query)
        
        # Ajustement dynamique des poids des sources en fonction du contexte de la requête
        if dynamic_weighting:
            self._adjust_source_weights(query, constraints)
        
        # Appel à la méthode parent avec les contraintes extraites
        results = await super().retrieve_enhanced_context(
            query=query,
            limit=limit,
            time_range=constraints.get("time_range"),
            node_ids=constraints.get("node_ids"),
            collection_filters=constraints.get("collection_filters"),
            *args,
            **kwargs
        )
        
        # Enregistrement de la requête pour l'apprentissage
        self._record_query(query, constraints, len(results))
        
        return results
    
    def _advanced_constraint_extraction(self, query: str) -> Dict[str, Any]:
        """
        Extraction avancée des contraintes à partir de la requête.
        
        Args:
            query: Texte de la requête
            
        Returns:
            Dictionnaire des contraintes extraites
        """
        # Récupérer les contraintes de base
        constraints = self._extract_constraints_from_query(query)
        
        # Patterns pour extraire des sources spécifiques
        source_patterns = {
            r'\b(?:info|données|information)s?\s+(?:sur|de|concernant)\s+(?:les\s+)?métriques\b': 'metrics_history',
            r'\b(?:hypothèses|hypothèse)\b': 'hypothesis',
            r'\b(?:documentation|doc|manuel|guide)\b': 'documentation',
            r'\b(?:logs|journaux|traces)\b': 'logs'
        }
        
        # Détecter les sources mentionnées dans la requête
        collection_filters = constraints.get('collection_filters', {})
        for pattern, source in source_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                collection_filters[source] = True
        
        # Si des sources sont explicitement mentionnées, désactiver les autres
        if collection_filters and all(v is True for v in collection_filters.values()):
            for source in self.source_weights.keys():
                if source not in collection_filters:
                    collection_filters[source] = False
        
        # Mise à jour des contraintes
        constraints['collection_filters'] = collection_filters
        
        # Détection avancée de plages temporelles
        time_expressions = {
            r'\b(?:aujourd\'hui|ce jour)\b': (datetime.now().replace(hour=0, minute=0, second=0), 
                                            datetime.now().replace(hour=23, minute=59, second=59)),
            r'\b(?:hier|la veille)\b': ((datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0),
                                      (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59)),
            r'\b(?:cette semaine|semaine en cours)\b': ((datetime.now() - timedelta(days=datetime.now().weekday())).replace(hour=0, minute=0, second=0),
                                                     datetime.now()),
            r'\b(?:ce mois|mois en cours)\b': (datetime.now().replace(day=1, hour=0, minute=0, second=0),
                                             datetime.now()),
            r'\b(?:dernière semaine|semaine dernière)\b': ((datetime.now() - timedelta(days=datetime.now().weekday() + 7)).replace(hour=0, minute=0, second=0),
                                                        (datetime.now() - timedelta(days=datetime.now().weekday() + 1)).replace(hour=23, minute=59, second=59)),
            r'\b(?:dernier mois|mois dernier)\b': ((datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0),
                                                (datetime.now().replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59))
        }
        
        # Vérifier si une expression temporelle est présente
        if 'time_range' not in constraints:
            for pattern, time_range in time_expressions.items():
                if re.search(pattern, query, re.IGNORECASE):
                    constraints['time_range'] = time_range
                    break
        
        return constraints
    
    def _adjust_source_weights(self, query: str, constraints: Dict[str, Any]) -> None:
        """
        Ajuste dynamiquement les poids des sources en fonction de la requête.
        
        Args:
            query: Texte de la requête
            constraints: Contraintes extraites
        """
        # Mots-clés associés à chaque source
        source_keywords = {
            "metrics_history": ["métrique", "performance", "statistique", "chiffre", "mesure", "tendance"],
            "hypothesis": ["hypothèse", "validation", "test", "expérience", "résultat", "conclusion"],
            "documentation": ["guide", "documentation", "explication", "procédure", "fonctionnement"],
            "logs": ["erreur", "incident", "journal", "log", "événement", "alerte"]
        }
        
        # Calcul de la pertinence de chaque source pour cette requête
        query_lower = query.lower()
        source_relevance = {}
        
        for source, keywords in source_keywords.items():
            relevance = 0.0
            for keyword in keywords:
                if keyword in query_lower:
                    relevance += 1.0
            
            # Normalisation et mise à jour du poids
            if keywords:
                relevance = relevance / len(keywords)
                
                # Intégrer la contrainte de collection si présente
                collection_filters = constraints.get('collection_filters', {})
                if collection_filters.get(source, True) is False:
                    relevance = 0.0
                elif collection_filters.get(source, False) is True:
                    relevance = max(relevance, 0.7)  # Boost minimum si explicitement demandé
                
                # Mettre à jour le poids avec un facteur d'apprentissage
                current_weight = self.source_weights.get(source, 0.5)
                updated_weight = current_weight * (1 - self.source_learning_rate) + relevance * self.source_learning_rate
                self.source_weights[source] = updated_weight
        
        logger.debug(f"Poids des sources ajustés: {self.source_weights}")
    
    async def _hybrid_retrieval(self, *args, **kwargs):
        """
        Version améliorée de la récupération hybride avec pondération dynamique des sources.
        """
        # Appel à l'implémentation de base
        results = await super()._hybrid_retrieval(*args, **kwargs)
        
        # Application des poids des sources mis à jour
        for doc in results:
            source = doc.get("metadata", {}).get("source", "unknown")
            source_weight = self.source_weights.get(source, 0.5)
            
            # Appliquer le facteur de récence si une date est disponible
            recency_factor = 1.0
            if "timestamp" in doc:
                time_diff = datetime.now() - doc["timestamp"]
                days_old = time_diff.days
                # Fonction de décroissance exponentielle pour la récence
                recency_factor = np.exp(-0.01 * days_old)
            
            # Mise à jour du score avec pondération dynamique
            doc["source_weight"] = source_weight
            doc["recency_factor"] = recency_factor
            doc["final_score"] = (doc["final_score"] * 0.7) + (source_weight * 0.2) + (recency_factor * 0.1 * self.recency_weight)
        
        # Retrier les résultats après ajustement des scores
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        return results
    
    def _record_query(self, query: str, constraints: Dict[str, Any], result_count: int) -> None:
        """
        Enregistre la requête et son contexte pour l'apprentissage.
        
        Args:
            query: Texte de la requête
            constraints: Contraintes utilisées
            result_count: Nombre de résultats obtenus
        """
        self.query_history.append({
            "query": query,
            "constraints": constraints,
            "result_count": result_count,
            "timestamp": datetime.now(),
            "source_weights": self.source_weights.copy()
        })
        
        # Limiter la taille de l'historique
        if len(self.query_history) > 100:
            self.query_history = self.query_history[-100:] 