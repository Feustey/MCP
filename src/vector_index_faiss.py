"""
Index vectoriel optimisé avec FAISS pour recherche ultra-rapide
Améliore les performances de recherche de similarité par 100-1000x
"""

import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import faiss
from datetime import datetime
import pickle
import os

from app.services.rag_metrics import (
    rag_similarity_search_duration,
    rag_index_operations,
    rag_index_size_bytes
)

logger = logging.getLogger(__name__)


class FAISSVectorIndex:
    """
    Index vectoriel basé sur FAISS pour recherche de similarité ultra-rapide
    
    Supporte plusieurs types d'index:
    - Flat: Recherche exacte (small datasets < 10k)
    - IVF: Recherche approximative rapide (medium datasets 10k-1M)
    - HNSW: Recherche graphe rapide (large datasets > 1M)
    """
    
    def __init__(
        self,
        dimension: int = 768,
        index_type: str = "flat",
        nlist: int = 100,
        nprobe: int = 10,
        use_gpu: bool = False
    ):
        """
        Args:
            dimension: Dimension des vecteurs d'embedding
            index_type: Type d'index ('flat', 'ivf', 'hnsw')
            nlist: Nombre de clusters pour IVF
            nprobe: Nombre de clusters à rechercher pour IVF
            use_gpu: Utiliser GPU si disponible
        """
        self.dimension = dimension
        self.index_type = index_type
        self.nlist = nlist
        self.nprobe = nprobe
        self.use_gpu = use_gpu
        
        # Créer l'index FAISS
        self.index = self._create_index()
        
        # Métadonnées des documents
        self.documents: List[str] = []
        self.metadata: List[Dict[str, Any]] = []
        
        # Statistiques
        self.stats = {
            'total_vectors': 0,
            'total_searches': 0,
            'average_search_time_ms': 0.0,
            'index_size_bytes': 0,
            'last_updated': None
        }
        
        logger.info(
            f"FAISS index initialized: "
            f"type={index_type}, dimension={dimension}, "
            f"gpu={use_gpu}"
        )
    
    def _create_index(self) -> faiss.Index:
        """Crée l'index FAISS selon le type configuré"""
        
        if self.index_type == "flat":
            # Index exact - Inner Product (équivalent cosine avec vecteurs normalisés)
            index = faiss.IndexFlatIP(self.dimension)
            logger.info("Created FAISS Flat index (exact search)")
            
        elif self.index_type == "ivf":
            # Index IVF (Inverted File) - Recherche approximative
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
            logger.info(f"Created FAISS IVF index (nlist={self.nlist})")
            
        elif self.index_type == "hnsw":
            # Index HNSW (Hierarchical Navigable Small World) - Très rapide
            index = faiss.IndexHNSWFlat(self.dimension, 32)  # M=32 connections
            logger.info("Created FAISS HNSW index")
            
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")
        
        # Configurer pour GPU si demandé
        if self.use_gpu and faiss.get_num_gpus() > 0:
            try:
                res = faiss.StandardGpuResources()
                index = faiss.index_cpu_to_gpu(res, 0, index)
                logger.info("FAISS index moved to GPU")
            except Exception as e:
                logger.warning(f"Failed to use GPU, falling back to CPU: {str(e)}")
        
        return index
    
    def add_vectors(
        self,
        vectors: np.ndarray,
        documents: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Ajoute des vecteurs à l'index
        
        Args:
            vectors: Array numpy de shape (n_vectors, dimension)
            documents: Liste des documents correspondants
            metadata: Métadonnées optionnelles
        """
        start_time = datetime.now()
        
        # Valider les dimensions
        if len(vectors.shape) != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Invalid vector shape: {vectors.shape}. "
                f"Expected (n, {self.dimension})"
            )
        
        if len(documents) != vectors.shape[0]:
            raise ValueError(
                f"Number of documents ({len(documents)}) must match "
                f"number of vectors ({vectors.shape[0]})"
            )
        
        # Normaliser les vecteurs pour similarité cosinus
        vectors_normalized = vectors / np.linalg.norm(vectors, axis=1)[:, np.newaxis]
        vectors_normalized = vectors_normalized.astype('float32')
        
        # Entraîner l'index IVF si nécessaire
        if self.index_type == "ivf" and not self.index.is_trained:
            logger.info(f"Training IVF index with {len(vectors_normalized)} vectors...")
            self.index.train(vectors_normalized)
        
        # Ajouter les vecteurs
        self.index.add(vectors_normalized)
        
        # Stocker les documents et métadonnées
        self.documents.extend(documents)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{} for _ in documents])
        
        # Mettre à jour les statistiques
        self.stats['total_vectors'] = len(self.documents)
        self.stats['last_updated'] = datetime.now().isoformat()
        self.stats['index_size_bytes'] = self._estimate_index_size()
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Added {len(vectors)} vectors to FAISS index in {duration_ms:.1f}ms "
            f"(total: {self.stats['total_vectors']} vectors)"
        )
        
        # Métriques
        rag_index_operations.labels(
            operation='add',
            status='success'
        ).inc(len(vectors))
        
        rag_index_size_bytes.labels(
            index_type=self.index_type
        ).set(self.stats['index_size_bytes'])
    
    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        return_metadata: bool = False
    ) -> List[Tuple[str, float]]:
        """
        Recherche les k documents les plus similaires
        
        Args:
            query_vector: Vecteur de requête
            k: Nombre de résultats à retourner
            return_metadata: Inclure les métadonnées dans les résultats
            
        Returns:
            Liste de tuples (document, score) ou (document, score, metadata)
        """
        start_time = datetime.now()
        
        if len(self.documents) == 0:
            logger.warning("FAISS index is empty, returning no results")
            return []
        
        # Valider et normaliser le vecteur de requête
        if query_vector.shape[0] != self.dimension:
            raise ValueError(
                f"Query vector dimension ({query_vector.shape[0]}) "
                f"doesn't match index dimension ({self.dimension})"
            )
        
        query_normalized = query_vector / np.linalg.norm(query_vector)
        query_normalized = query_normalized.reshape(1, -1).astype('float32')
        
        # Configurer nprobe pour IVF
        if self.index_type == "ivf":
            self.index.nprobe = self.nprobe
        
        # Effectuer la recherche
        k_actual = min(k, len(self.documents))
        distances, indices = self.index.search(query_normalized, k_actual)
        
        # Construire les résultats
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.documents):
                doc = self.documents[idx]
                score = float(distances[0][i])
                
                if return_metadata:
                    meta = self.metadata[idx] if idx < len(self.metadata) else {}
                    results.append((doc, score, meta))
                else:
                    results.append((doc, score))
        
        # Mettre à jour les statistiques
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.stats['total_searches'] += 1
        self.stats['average_search_time_ms'] = (
            (self.stats['average_search_time_ms'] * (self.stats['total_searches'] - 1) + duration_ms)
            / self.stats['total_searches']
        )
        
        # Déterminer la bucket de taille pour les métriques
        size_bucket = self._get_size_bucket(len(self.documents))
        
        # Métriques
        rag_similarity_search_duration.labels(
            index_size_bucket=size_bucket
        ).observe(duration_ms / 1000)
        
        rag_index_operations.labels(
            operation='search',
            status='success'
        ).inc()
        
        logger.debug(
            f"FAISS search completed in {duration_ms:.2f}ms "
            f"(k={k_actual}, index_size={len(self.documents)})"
        )
        
        return results
    
    def batch_search(
        self,
        query_vectors: np.ndarray,
        k: int = 5,
        return_metadata: bool = False
    ) -> List[List[Tuple[str, float]]]:
        """
        Recherche batch pour plusieurs vecteurs de requête
        
        Args:
            query_vectors: Array de vecteurs (n_queries, dimension)
            k: Nombre de résultats par requête
            return_metadata: Inclure les métadonnées
            
        Returns:
            Liste de listes de résultats
        """
        start_time = datetime.now()
        
        if len(self.documents) == 0:
            return [[] for _ in range(len(query_vectors))]
        
        # Normaliser les vecteurs
        query_normalized = query_vectors / np.linalg.norm(query_vectors, axis=1)[:, np.newaxis]
        query_normalized = query_normalized.astype('float32')
        
        # Recherche batch
        k_actual = min(k, len(self.documents))
        distances, indices = self.index.search(query_normalized, k_actual)
        
        # Construire les résultats
        all_results = []
        for query_idx in range(len(query_vectors)):
            results = []
            for i, idx in enumerate(indices[query_idx]):
                if idx >= 0 and idx < len(self.documents):
                    doc = self.documents[idx]
                    score = float(distances[query_idx][i])
                    
                    if return_metadata:
                        meta = self.metadata[idx] if idx < len(self.metadata) else {}
                        results.append((doc, score, meta))
                    else:
                        results.append((doc, score))
            
            all_results.append(results)
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"FAISS batch search completed: {len(query_vectors)} queries "
            f"in {duration_ms:.1f}ms ({duration_ms/len(query_vectors):.2f}ms per query)"
        )
        
        return all_results
    
    def save(self, filepath: str):
        """Sauvegarde l'index et les métadonnées"""
        try:
            # Sauvegarder l'index FAISS
            if self.use_gpu:
                # Transférer vers CPU avant sauvegarde
                index_cpu = faiss.index_gpu_to_cpu(self.index)
                faiss.write_index(index_cpu, f"{filepath}.index")
            else:
                faiss.write_index(self.index, f"{filepath}.index")
            
            # Sauvegarder les métadonnées
            metadata = {
                'documents': self.documents,
                'metadata': self.metadata,
                'stats': self.stats,
                'config': {
                    'dimension': self.dimension,
                    'index_type': self.index_type,
                    'nlist': self.nlist,
                    'nprobe': self.nprobe
                }
            }
            
            with open(f"{filepath}.meta", 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"FAISS index saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {str(e)}")
            raise
    
    def load(self, filepath: str):
        """Charge l'index et les métadonnées"""
        try:
            # Charger l'index FAISS
            index = faiss.read_index(f"{filepath}.index")
            
            if self.use_gpu and faiss.get_num_gpus() > 0:
                res = faiss.StandardGpuResources()
                index = faiss.index_cpu_to_gpu(res, 0, index)
            
            self.index = index
            
            # Charger les métadonnées
            with open(f"{filepath}.meta", 'rb') as f:
                metadata = pickle.load(f)
            
            self.documents = metadata['documents']
            self.metadata = metadata['metadata']
            self.stats = metadata['stats']
            
            logger.info(
                f"FAISS index loaded from {filepath}: "
                f"{len(self.documents)} vectors"
            )
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {str(e)}")
            raise
    
    def _estimate_index_size(self) -> int:
        """Estime la taille de l'index en bytes"""
        # Taille approximative: nb_vectors * dimension * 4 bytes (float32)
        # + overhead FAISS (~10%)
        base_size = len(self.documents) * self.dimension * 4
        return int(base_size * 1.1)
    
    def _get_size_bucket(self, size: int) -> str:
        """Retourne la bucket de taille pour les métriques"""
        if size < 1000:
            return "< 1k"
        elif size < 10000:
            return "1k-10k"
        elif size < 100000:
            return "10k-100k"
        elif size < 1000000:
            return "100k-1M"
        else:
            return "> 1M"
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'index"""
        return {
            **self.stats,
            'index_type': self.index_type,
            'dimension': self.dimension,
            'use_gpu': self.use_gpu,
            'is_trained': self.index.is_trained if hasattr(self.index, 'is_trained') else True
        }
    
    def clear(self):
        """Vide l'index"""
        self.index = self._create_index()
        self.documents = []
        self.metadata = []
        self.stats['total_vectors'] = 0
        logger.info("FAISS index cleared")


# ============================================================================
# FACTORY POUR CRÉER L'INDEX OPTIMAL
# ============================================================================

def create_optimal_index(
    dimension: int,
    expected_size: int,
    use_gpu: bool = False
) -> FAISSVectorIndex:
    """
    Crée l'index FAISS optimal selon la taille attendue
    
    Args:
        dimension: Dimension des vecteurs
        expected_size: Nombre de vecteurs attendu
        use_gpu: Utiliser GPU si disponible
        
    Returns:
        Instance de FAISSVectorIndex optimisée
    """
    if expected_size < 10000:
        # Petit dataset: index exact
        index_type = "flat"
        logger.info("Creating Flat index for small dataset (< 10k)")
    elif expected_size < 1000000:
        # Dataset moyen: IVF
        index_type = "ivf"
        nlist = int(np.sqrt(expected_size))  # Heuristique
        logger.info(f"Creating IVF index for medium dataset (< 1M), nlist={nlist}")
    else:
        # Large dataset: HNSW
        index_type = "hnsw"
        logger.info("Creating HNSW index for large dataset (> 1M)")
    
    return FAISSVectorIndex(
        dimension=dimension,
        index_type=index_type,
        nlist=int(np.sqrt(expected_size)) if index_type == "ivf" else 100,
        use_gpu=use_gpu
    )


logger.info("FAISS vector index module loaded")

