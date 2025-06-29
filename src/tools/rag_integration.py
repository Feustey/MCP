#!/usr/bin/env python3
"""
Intégration RAG avancée pour MCP - Analyse sémantique et apprentissage
Dernière mise à jour: 7 mai 2025
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import redis
from redis.exceptions import RedisError
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Document pour le système RAG"""
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    timestamp: datetime = datetime.now()

@dataclass
class SearchResult:
    """Résultat de recherche RAG"""
    doc_id: str
    content: str
    similarity: float
    metadata: Dict[str, Any]

class RAGIntegration:
    """
    Système d'intégration RAG avancé avec analyse sémantique
    et apprentissage continu.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        embedding_dim: int = 768,
        similarity_threshold: float = 0.7
    ):
        """
        Initialise le système RAG
        
        Args:
            redis_url: URL de connexion Redis
            model_name: Nom du modèle de transformers
            embedding_dim: Dimension des embeddings
            similarity_threshold: Seuil de similarité
        """
        self.redis = redis.from_url(redis_url)
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        
        # Configuration des index
        self.index_config = {
            "channel_metrics": {
                "prefix": "metrics:",
                "ttl": 30 * 24 * 3600  # 30 jours
            },
            "market_analysis": {
                "prefix": "market:",
                "ttl": 7 * 24 * 3600   # 7 jours
            },
            "optimization_history": {
                "prefix": "optim:",
                "ttl": 90 * 24 * 3600  # 90 jours
            }
        }
        
    def index_document(
        self,
        content: str,
        doc_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Indexe un nouveau document
        
        Args:
            content: Contenu du document
            doc_type: Type de document
            metadata: Métadonnées
            
        Returns:
            str: ID du document
        """
        try:
            # 1. Générer l'ID
            doc_id = f"{doc_type}_{int(datetime.now().timestamp())}"
            
            # 2. Calculer l'embedding
            embedding = self._compute_embedding(content)
            
            # 3. Créer le document
            doc = Document(
                doc_id=doc_id,
                content=content,
                metadata=metadata,
                embedding=embedding
            )
            
            # 4. Sauvegarder
            self._save_document(doc, doc_type)
            
            logger.info(f"Document indexé: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Erreur indexation document: {e}")
            raise
            
    def search(
        self,
        query: str,
        doc_type: Optional[str] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Recherche sémantique dans les documents
        
        Args:
            query: Requête de recherche
            doc_type: Type de document (optionnel)
            top_k: Nombre de résultats
            filters: Filtres sur métadonnées
            
        Returns:
            Liste de résultats de recherche
        """
        try:
            # 1. Calculer l'embedding de la requête
            query_embedding = self._compute_embedding(query)
            
            # 2. Récupérer les documents
            docs = self._get_documents(doc_type)
            
            # 3. Filtrer si nécessaire
            if filters:
                docs = self._apply_filters(docs, filters)
                
            # 4. Calculer les similarités
            similarities = []
            for doc in docs:
                if doc.embedding is not None:
                    sim = cosine_similarity(
                        query_embedding.reshape(1, -1),
                        doc.embedding.reshape(1, -1)
                    )[0][0]
                    similarities.append((doc, sim))
                    
            # 5. Trier et filtrer
            similarities.sort(key=lambda x: x[1], reverse=True)
            results = []
            
            for doc, sim in similarities[:top_k]:
                if sim >= self.similarity_threshold:
                    results.append(SearchResult(
                        doc_id=doc.doc_id,
                        content=doc.content,
                        similarity=sim,
                        metadata=doc.metadata
                    ))
                    
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche: {e}")
            return []
            
    def update_document(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Met à jour un document existant
        
        Args:
            doc_id: ID du document
            content: Nouveau contenu (optionnel)
            metadata: Nouvelles métadonnées (optionnel)
            
        Returns:
            bool: True si succès
        """
        try:
            # 1. Récupérer le document
            doc_type = doc_id.split("_")[0]
            key = f"{self.index_config[doc_type]['prefix']}{doc_id}"
            doc_data = self.redis.get(key)
            
            if not doc_data:
                return False
                
            doc = eval(doc_data)  # Pour demo uniquement
            
            # 2. Mettre à jour le contenu
            if content is not None:
                doc["content"] = content
                doc["embedding"] = self._compute_embedding(content).tolist()
                
            # 3. Mettre à jour les métadonnées
            if metadata is not None:
                doc["metadata"].update(metadata)
                
            # 4. Sauvegarder
            self.redis.setex(
                key,
                self.index_config[doc_type]["ttl"],
                str(doc)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour document: {e}")
            return False
            
    def delete_document(self, doc_id: str) -> bool:
        """
        Supprime un document
        
        Args:
            doc_id: ID du document
            
        Returns:
            bool: True si succès
        """
        try:
            doc_type = doc_id.split("_")[0]
            key = f"{self.index_config[doc_type]['prefix']}{doc_id}"
            return bool(self.redis.delete(key))
            
        except Exception as e:
            logger.error(f"Erreur suppression document: {e}")
            return False
            
    def analyze_trends(
        self,
        doc_type: str,
        metric: str,
        window: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """
        Analyse les tendances dans les documents
        
        Args:
            doc_type: Type de document
            metric: Métrique à analyser
            window: Fenêtre d'analyse
            
        Returns:
            Dict avec analyse des tendances
        """
        try:
            # 1. Récupérer les documents
            docs = self._get_documents(doc_type)
            
            # 2. Filtrer par fenêtre temporelle
            start_time = datetime.now() - window
            docs = [
                d for d in docs
                if d.timestamp >= start_time
            ]
            
            if not docs:
                return {}
                
            # 3. Extraire les valeurs
            values = []
            timestamps = []
            
            for doc in docs:
                if metric in doc.metadata:
                    values.append(doc.metadata[metric])
                    timestamps.append(doc.timestamp)
                    
            if not values:
                return {}
                
            # 4. Calculer les statistiques
            return {
                "mean": np.mean(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values),
                "trend": self._calculate_trend(values),
                "volatility": self._calculate_volatility(values),
                "sample_size": len(values)
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse tendances: {e}")
            return {}
            
    def generate_insights(
        self,
        doc_type: str,
        metrics: List[str],
        window: timedelta = timedelta(days=30)
    ) -> List[str]:
        """
        Génère des insights à partir des documents
        
        Args:
            doc_type: Type de document
            metrics: Liste de métriques
            window: Fenêtre d'analyse
            
        Returns:
            Liste d'insights
        """
        insights = []
        
        try:
            # 1. Analyser chaque métrique
            metric_trends = {}
            for metric in metrics:
                trends = self.analyze_trends(doc_type, metric, window)
                if trends:
                    metric_trends[metric] = trends
                    
            if not metric_trends:
                return ["Données insuffisantes pour générer des insights"]
                
            # 2. Analyser les tendances
            for metric, trends in metric_trends.items():
                # Tendance forte
                if abs(trends["trend"]) > 0.5:
                    direction = "positive" if trends["trend"] > 0 else "négative"
                    insights.append(
                        f"Tendance {direction} forte pour {metric}: "
                        f"{trends['trend']:.1%} sur {window.days} jours"
                    )
                    
                # Forte volatilité
                if trends["volatility"] > 0.3:
                    insights.append(
                        f"Forte volatilité pour {metric}: "
                        f"{trends['volatility']:.1%}"
                    )
                    
                # Valeurs extrêmes
                if trends["max"] > 2 * trends["mean"]:
                    insights.append(
                        f"Pics importants détectés pour {metric}"
                    )
                    
            # 3. Analyser les corrélations
            if len(metrics) > 1:
                correlations = self._analyze_correlations(
                    doc_type,
                    metrics,
                    window
                )
                
                for (m1, m2), corr in correlations.items():
                    if abs(corr) > 0.7:
                        direction = "positive" if corr > 0 else "négative"
                        insights.append(
                            f"Forte corrélation {direction} entre "
                            f"{m1} et {m2}: {corr:.1%}"
                        )
                        
            return insights
            
        except Exception as e:
            logger.error(f"Erreur génération insights: {e}")
            return ["Erreur lors de la génération des insights"]
            
    def _compute_embedding(self, text: str) -> np.ndarray:
        """
        Calcule l'embedding d'un texte
        
        Args:
            text: Texte à encoder
            
        Returns:
            np.ndarray: Embedding
        """
        # Utiliser sentence-transformers
        embedding = self.model.encode(text)
        return embedding
        
    def _save_document(self, doc: Document, doc_type: str) -> None:
        """
        Sauvegarde un document dans Redis
        
        Args:
            doc: Document à sauvegarder
            doc_type: Type de document
        """
        key = f"{self.index_config[doc_type]['prefix']}{doc.doc_id}"
        ttl = self.index_config[doc_type]["ttl"]
        
        # Convertir l'embedding en liste pour serialization
        doc_data = {
            "doc_id": doc.doc_id,
            "content": doc.content,
            "metadata": doc.metadata,
            "embedding": doc.embedding.tolist() if doc.embedding is not None else None,
            "timestamp": doc.timestamp.isoformat()
        }
        
        self.redis.setex(key, ttl, str(doc_data))
        
    def _get_documents(
        self,
        doc_type: Optional[str] = None
    ) -> List[Document]:
        """
        Récupère les documents de Redis
        
        Args:
            doc_type: Type de document (optionnel)
            
        Returns:
            Liste de documents
        """
        docs = []
        
        # Définir les préfixes à chercher
        if doc_type:
            prefixes = [self.index_config[doc_type]["prefix"]]
        else:
            prefixes = [cfg["prefix"] for cfg in self.index_config.values()]
            
        # Récupérer les documents
        for prefix in prefixes:
            keys = self.redis.keys(f"{prefix}*")
            for key in keys:
                doc_data = eval(self.redis.get(key))  # Pour demo uniquement
                
                # Convertir l'embedding en array
                if doc_data["embedding"]:
                    embedding = np.array(doc_data["embedding"])
                else:
                    embedding = None
                    
                doc = Document(
                    doc_id=doc_data["doc_id"],
                    content=doc_data["content"],
                    metadata=doc_data["metadata"],
                    embedding=embedding,
                    timestamp=datetime.fromisoformat(doc_data["timestamp"])
                )
                docs.append(doc)
                
        return docs
        
    def _apply_filters(
        self,
        docs: List[Document],
        filters: Dict[str, Any]
    ) -> List[Document]:
        """
        Applique des filtres sur les documents
        
        Args:
            docs: Liste de documents
            filters: Filtres à appliquer
            
        Returns:
            Liste filtrée
        """
        filtered = []
        
        for doc in docs:
            match = True
            for key, value in filters.items():
                if key not in doc.metadata or doc.metadata[key] != value:
                    match = False
                    break
            if match:
                filtered.append(doc)
                
        return filtered
        
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calcule la tendance d'une série
        
        Args:
            values: Liste de valeurs
            
        Returns:
            float: Coefficient de tendance
        """
        if not values:
            return 0.0
            
        x = np.arange(len(values))
        y = np.array(values)
        
        # Régression linéaire
        slope = np.polyfit(x, y, 1)[0]
        
        # Normaliser
        return max(-1.0, min(1.0, slope))
        
    def _calculate_volatility(self, values: List[float]) -> float:
        """
        Calcule la volatilité d'une série
        
        Args:
            values: Liste de valeurs
            
        Returns:
            float: Score de volatilité
        """
        if not values:
            return 0.0
            
        # Écart-type normalisé
        mean = np.mean(values)
        if mean == 0:
            return 0.0
            
        return np.std(values) / mean
        
    def _analyze_correlations(
        self,
        doc_type: str,
        metrics: List[str],
        window: timedelta
    ) -> Dict[Tuple[str, str], float]:
        """
        Analyse les corrélations entre métriques
        
        Args:
            doc_type: Type de document
            metrics: Liste de métriques
            window: Fenêtre d'analyse
            
        Returns:
            Dict avec corrélations
        """
        # 1. Récupérer les documents
        docs = self._get_documents(doc_type)
        
        # 2. Filtrer par fenêtre
        start_time = datetime.now() - window
        docs = [d for d in docs if d.timestamp >= start_time]
        
        if not docs:
            return {}
            
        # 3. Extraire les valeurs par métrique
        metric_values = {m: [] for m in metrics}
        for doc in docs:
            for metric in metrics:
                if metric in doc.metadata:
                    metric_values[metric].append(doc.metadata[metric])
                    
        # 4. Calculer les corrélations
        correlations = {}
        for i, m1 in enumerate(metrics):
            for m2 in metrics[i+1:]:
                values1 = metric_values[m1]
                values2 = metric_values[m2]
                
                if len(values1) == len(values2) > 1:
                    corr = np.corrcoef(values1, values2)[0, 1]
                    correlations[(m1, m2)] = corr
                    
        return correlations 