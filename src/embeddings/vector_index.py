import numpy as np
import logging
import os
import pickle
from typing import List, Dict, Tuple, Optional, Any
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorIndex:
    """
    Classe pour la gestion d'index vectoriel utilisant FAISS.
    Permet une recherche de similarité rapide et efficace.
    """
    
    def __init__(self, dimension: int = 1536):
        """
        Initialise l'index vectoriel.
        
        Args:
            dimension: Dimension des vecteurs d'embedding
        """
        self.dimension = dimension
        self.document_map = {}  # Map des IDs vers documents
        self._index = None
        
        # Importer FAISS uniquement au besoin (package optionnel)
        try:
            try:
                import faiss
            except ImportError:
                import faiss_cpu as faiss
            self.faiss = faiss
            # Création de l'index de base - IndexFlatIP pour similarité cosinus
            self._index = faiss.IndexFlatIP(dimension)
            logger.info(f"Index FAISS initialisé avec dimension {dimension}")
        except ImportError:
            logger.warning("FAISS non disponible. Installation recommandée: pip install faiss-cpu")
            self._index = None
            self._fallback_vectors = np.zeros((0, dimension), dtype=np.float32)

    @property
    def is_faiss_available(self):
        """Vérifie si FAISS est disponible."""
        return self._index is not None

    @property
    def num_documents(self):
        """Retourne le nombre de documents dans l'index."""
        return len(self.document_map)
    
    def add_documents(self, documents: List[Dict], embeddings: List[List[float]]):
        """
        Ajoute des documents avec leurs embeddings à l'index.
        
        Args:
            documents: Liste de documents (dictionnaires)
            embeddings: Liste des embeddings correspondants
        """
        if len(documents) == 0:
            logger.warning("Aucun document à ajouter à l'index")
            return
        
        if len(documents) != len(embeddings):
            raise ValueError(f"Le nombre de documents ({len(documents)}) ne correspond pas " +
                           f"au nombre d'embeddings ({len(embeddings)})")
        
        # Conversion en tableau numpy
        vectors = np.array(embeddings).astype('float32')
        
        # ID de départ pour les nouveaux documents
        start_id = len(self.document_map)
        
        if self.is_faiss_available:
            # Normaliser les vecteurs (pour similarité cosinus)
            self.faiss.normalize_L2(vectors)
            
            # Ajouter à l'index FAISS
            self._index.add(vectors)
        else:
            # Fallback si FAISS n'est pas disponible
            self._fallback_vectors = np.vstack([self._fallback_vectors, vectors])
        
        # Mettre à jour la correspondance ID → document
        for i, doc in enumerate(documents):
            # Stocker une copie du document sans l'embedding (pour économiser de l'espace)
            doc_copy = doc.copy()
            if "embedding" in doc_copy:
                del doc_copy["embedding"]
                
            self.document_map[start_id + i] = doc_copy
            
        logger.info(f"Ajout de {len(documents)} documents à l'index, maintenant {self.num_documents} documents au total")
    
    def search(self, query_vector: List[float], k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Recherche les k documents les plus similaires à query_vector.
        
        Args:
            query_vector: Vecteur de requête (embedding)
            k: Nombre de résultats à retourner
            
        Returns:
            Liste de tuples (document, score) triés par similarité décroissante
        """
        # S'assurer que k est valide
        k = min(k, self.num_documents)
        if k == 0:
            return []
        
        query_np = np.array([query_vector]).astype('float32')
        
        if self.is_faiss_available:
            # Normaliser le vecteur de requête
            self.faiss.normalize_L2(query_np)
            
            # Effectuer la recherche avec FAISS
            scores, indices = self._index.search(query_np, k)
            
            # Récupérer les documents correspondants
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx in self.document_map:  # -1 indique aucune correspondance
                    results.append((self.document_map[idx], float(scores[0][i])))
        else:
            # Fallback: recherche avec numpy si FAISS n'est pas disponible
            if len(self._fallback_vectors) == 0:
                return []
                
            # Calculer les similarités cosinus
            norm_query = query_np / np.linalg.norm(query_np)
            norm_vectors = self._fallback_vectors / np.linalg.norm(self._fallback_vectors, axis=1, keepdims=True)
            similarities = np.dot(norm_vectors, norm_query.T).flatten()
            
            # Trouver les top-k
            top_indices = np.argsort(similarities)[-k:][::-1]
            
            # Récupérer les documents
            results = []
            for idx in top_indices:
                if idx in self.document_map:
                    results.append((self.document_map[idx], float(similarities[idx])))
                    
        return results
    
    def save(self, filepath: str):
        """
        Sauvegarde l'index et les métadonnées.
        
        Args:
            filepath: Chemin de base pour la sauvegarde (sans extension)
        """
        try:
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Sauvegarder la correspondance ID → document
            with open(f"{filepath}.documents", "wb") as f:
                pickle.dump(self.document_map, f)
            
            if self.is_faiss_available:
                # Sauvegarder l'index FAISS
                self.faiss.write_index(self._index, f"{filepath}.index")
                logger.info(f"Index FAISS sauvegardé: {filepath}.index")
            else:
                # Sauvegarder les vecteurs fallback
                with open(f"{filepath}.vectors", "wb") as f:
                    np.save(f, self._fallback_vectors)
                logger.info(f"Vecteurs fallback sauvegardés: {filepath}.vectors")
                
            # Sauvegarder les métadonnées
            with open(f"{filepath}.meta", "w") as f:
                json.dump({
                    "dimension": self.dimension,
                    "num_documents": self.num_documents,
                    "uses_faiss": self.is_faiss_available
                }, f)
                
            logger.info(f"Index vectoriel sauvegardé avec {self.num_documents} documents")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'index: {str(e)}")
            return False
    
    @classmethod
    def load(cls, filepath: str) -> Optional['VectorIndex']:
        """
        Charge un index précédemment sauvegardé.
        
        Args:
            filepath: Chemin de base de l'index (sans extension)
            
        Returns:
            Instance de VectorIndex chargée, ou None en cas d'erreur
        """
        try:
            # Charger les métadonnées
            with open(f"{filepath}.meta", "r") as f:
                meta = json.load(f)
            
            # Créer une nouvelle instance
            instance = cls(meta["dimension"])
            
            # Charger la correspondance ID → document
            with open(f"{filepath}.documents", "rb") as f:
                instance.document_map = pickle.load(f)
            
            # Déterminer si on doit charger avec FAISS ou le fallback
            uses_faiss = meta.get("uses_faiss", False)
            
            if uses_faiss and instance.is_faiss_available:
                # Charger l'index FAISS
                try:
                    import faiss
                except ImportError:
                    import faiss_cpu as faiss
                instance._index = faiss.read_index(f"{filepath}.index")
                logger.info(f"Index FAISS chargé depuis {filepath}.index")
            else:
                # Charger les vecteurs fallback
                with open(f"{filepath}.vectors", "rb") as f:
                    instance._fallback_vectors = np.load(f)
                logger.info(f"Vecteurs fallback chargés: {len(instance._fallback_vectors)} vecteurs")
            
            logger.info(f"Index vectoriel chargé avec {instance.num_documents} documents")
            return instance
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'index: {str(e)}")
            return None 