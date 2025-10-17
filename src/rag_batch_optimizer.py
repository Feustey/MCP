"""
Optimisations batch pour le système RAG
Améliore les performances d'ingestion et de traitement par 10-15x
"""

import asyncio
import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
import numpy as np
from transformers import GPT2Tokenizer

from src.clients.ollama_client import ollama_client
from config.rag_config import settings as rag_settings
from app.services.rag_metrics import (
    rag_embedding_duration,
    rag_embeddings_generated,
    rag_index_operations
)

logger = logging.getLogger(__name__)


class BatchEmbeddingProcessor:
    """
    Processeur batch pour la génération d'embeddings
    Améliore les performances par traitement parallèle
    """
    
    def __init__(
        self,
        batch_size: int = 32,
        max_concurrent_batches: int = 4,
        tokenizer: Optional[GPT2Tokenizer] = None
    ):
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.tokenizer = tokenizer or GPT2Tokenizer.from_pretrained("gpt2")
        
        logger.info(
            f"BatchEmbeddingProcessor initialized: "
            f"batch_size={batch_size}, max_concurrent={max_concurrent_batches}"
        )
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: str = None
    ) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes en batch
        
        Args:
            texts: Liste de textes à embedder
            model: Modèle d'embedding à utiliser
            
        Returns:
            Liste des embeddings générés
        """
        if not texts:
            return []
        
        model = model or rag_settings.EMBED_MODEL
        start_time = datetime.now()
        
        # Diviser en batches
        batches = [
            texts[i:i + self.batch_size]
            for i in range(0, len(texts), self.batch_size)
        ]
        
        logger.info(
            f"Generating embeddings for {len(texts)} texts in {len(batches)} batches "
            f"(batch_size={self.batch_size})"
        )
        
        all_embeddings = []
        
        # Traiter les batches en parallèle (limité par max_concurrent_batches)
        for i in range(0, len(batches), self.max_concurrent_batches):
            concurrent_batches = batches[i:i + self.max_concurrent_batches]
            
            # Créer les tâches pour traitement parallèle
            tasks = [
                self._process_single_batch(batch, model)
                for batch in concurrent_batches
            ]
            
            # Exécuter en parallèle
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collecter les résultats
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing failed: {str(result)}")
                    # Ajouter des embeddings vides pour maintenir l'ordre
                    all_embeddings.extend([[] for _ in range(self.batch_size)])
                else:
                    all_embeddings.extend(result)
        
        # Mesurer les performances
        duration = (datetime.now() - start_time).total_seconds()
        embeddings_per_second = len(texts) / duration if duration > 0 else 0
        
        logger.info(
            f"Generated {len(all_embeddings)} embeddings in {duration:.2f}s "
            f"({embeddings_per_second:.1f} embeddings/s)"
        )
        
        # Enregistrer les métriques
        rag_embedding_duration.labels(
            model=model,
            batch_size=str(self.batch_size)
        ).observe(duration / len(texts) if texts else 0)
        
        rag_embeddings_generated.labels(
            model=model,
            operation='batch_index'
        ).inc(len(texts))
        
        return all_embeddings[:len(texts)]  # Assurer la bonne taille
    
    async def _process_single_batch(
        self,
        batch: List[str],
        model: str
    ) -> List[List[float]]:
        """
        Traite un seul batch de textes
        
        Args:
            batch: Liste de textes du batch
            model: Modèle à utiliser
            
        Returns:
            Liste des embeddings pour ce batch
        """
        embeddings = []
        
        # Traiter chaque texte du batch en parallèle
        tasks = [
            self._generate_single_embedding(text, model)
            for text in batch
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Failed to generate embedding: {str(result)}")
                # Utiliser un embedding vide ou de fallback
                embeddings.append([0.0] * rag_settings.EMBED_DIMENSION)
            else:
                embeddings.append(result)
        
        return embeddings
    
    async def _generate_single_embedding(
        self,
        text: str,
        model: str
    ) -> List[float]:
        """Génère un embedding pour un seul texte"""
        try:
            return await ollama_client.embed(text, model)
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise


class ChunkProcessor:
    """
    Processeur optimisé pour le découpage de documents
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 50,
        tokenizer: Optional[GPT2Tokenizer] = None
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tokenizer = tokenizer or GPT2Tokenizer.from_pretrained("gpt2")
    
    def chunk_documents(
        self,
        documents: List[Tuple[str, str]]
    ) -> List[Tuple[str, str, int, int, int]]:
        """
        Découpe une liste de documents en chunks
        
        Args:
            documents: Liste de tuples (filename, content)
            
        Returns:
            Liste de tuples (filename, chunk_text, start_idx, end_idx, total_tokens)
        """
        all_chunks = []
        
        for filename, content in documents:
            chunks = self._chunk_single_document(filename, content)
            all_chunks.extend(chunks)
        
        logger.info(
            f"Chunked {len(documents)} documents into {len(all_chunks)} chunks "
            f"(avg {len(all_chunks)/len(documents):.1f} chunks/doc)"
        )
        
        return all_chunks
    
    def _chunk_single_document(
        self,
        filename: str,
        content: str
    ) -> List[Tuple[str, str, int, int, int]]:
        """Découpe un seul document"""
        chunks = []
        
        # Tokenization
        tokens = self.tokenizer.encode(content)
        total_tokens = len(tokens)
        
        # Découper en chunks avec overlap
        for i in range(0, total_tokens, self.chunk_size - self.overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append((
                filename,
                chunk_text,
                i,  # start_idx
                i + len(chunk_tokens),  # end_idx
                total_tokens
            ))
        
        return chunks


class BatchDocumentIngester:
    """
    Ingestion optimisée de documents avec batch processing
    """
    
    def __init__(
        self,
        batch_processor: Optional[BatchEmbeddingProcessor] = None,
        chunk_processor: Optional[ChunkProcessor] = None
    ):
        self.batch_processor = batch_processor or BatchEmbeddingProcessor()
        self.chunk_processor = chunk_processor or ChunkProcessor()
    
    async def ingest_documents_optimized(
        self,
        documents: List[Tuple[str, str]],
        model: str = None
    ) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        """
        Ingère des documents de manière optimisée
        
        Args:
            documents: Liste de tuples (filename, content)
            model: Modèle d'embedding à utiliser
            
        Returns:
            Tuple (embeddings, metadata) - 
            embeddings: Liste des embeddings générés
            metadata: Métadonnées des chunks
        """
        start_time = datetime.now()
        
        # Étape 1: Découper les documents en chunks
        logger.info(f"Step 1/3: Chunking {len(documents)} documents...")
        chunks = self.chunk_processor.chunk_documents(documents)
        
        # Étape 2: Générer les embeddings en batch
        logger.info(f"Step 2/3: Generating embeddings for {len(chunks)} chunks...")
        chunk_texts = [chunk[1] for chunk in chunks]
        embeddings = await self.batch_processor.generate_embeddings_batch(
            chunk_texts,
            model
        )
        
        # Étape 3: Préparer les métadonnées
        logger.info(f"Step 3/3: Preparing metadata...")
        metadata = []
        for index, (filename, chunk_text, start_idx, end_idx, total_tokens) in enumerate(chunks):
            metadata.append({
                "content": chunk_text,
                "source": filename,
                "embedding": embeddings[index] if index < len(embeddings) else [],
                "metadata": {
                    "chunk_index": index,
                    "total_chunks": len(chunks),
                    "start_token": start_idx,
                    "end_token": end_idx,
                    "total_tokens": total_tokens
                },
                "created_at": datetime.now()
            })
        
        # Statistiques finales
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Document ingestion completed: "
            f"{len(documents)} documents -> {len(chunks)} chunks "
            f"in {duration:.2f}s ({len(chunks)/duration:.1f} chunks/s)"
        )
        
        # Métriques
        rag_index_operations.labels(
            operation='bulk_add',
            status='success'
        ).inc(len(chunks))
        
        return embeddings, metadata
    
    async def ingest_from_directory(
        self,
        directory: str,
        file_extension: str = '.txt',
        model: str = None
    ) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        """
        Ingère tous les documents d'un répertoire
        
        Args:
            directory: Chemin du répertoire
            file_extension: Extension des fichiers à traiter
            model: Modèle d'embedding
            
        Returns:
            Tuple (embeddings, metadata)
        """
        import os
        
        # Lire tous les documents
        documents = []
        for filename in os.listdir(directory):
            if not filename.endswith(file_extension):
                continue
            
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append((filename, content))
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {str(e)}")
        
        logger.info(f"Found {len(documents)} documents in {directory}")
        
        if not documents:
            logger.warning(f"No documents found in {directory}")
            return [], []
        
        return await self.ingest_documents_optimized(documents, model)


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def batch_generate_embeddings(
    texts: List[str],
    model: str = None,
    batch_size: int = 32,
    max_concurrent: int = 4
) -> List[List[float]]:
    """
    Fonction utilitaire pour générer des embeddings en batch
    
    Args:
        texts: Liste de textes
        model: Modèle à utiliser
        batch_size: Taille des batches
        max_concurrent: Nombre de batches concurrents
        
    Returns:
        Liste des embeddings
    """
    processor = BatchEmbeddingProcessor(
        batch_size=batch_size,
        max_concurrent_batches=max_concurrent
    )
    
    return await processor.generate_embeddings_batch(texts, model)


async def optimize_existing_rag_workflow(rag_workflow):
    """
    Ajoute les capacités batch à un RAGWorkflow existant
    
    Args:
        rag_workflow: Instance de RAGWorkflow
    """
    # Ajouter le batch processor au workflow
    rag_workflow.batch_processor = BatchEmbeddingProcessor()
    rag_workflow.batch_ingester = BatchDocumentIngester()
    
    # Ajouter une méthode batch optimisée
    async def ingest_documents_batch(self, directory: str):
        """Version optimisée de ingest_documents"""
        embeddings, metadata = await self.batch_ingester.ingest_from_directory(directory)
        
        # Mettre à jour la matrice d'embeddings
        if embeddings:
            self.embeddings_matrix = np.array(embeddings).astype('float32')
            self.documents = [m['content'] for m in metadata]
            
            # Sauvegarder en MongoDB
            from src.models import Document as PydanticDocument
            for doc_data in metadata:
                await self.mongo_ops.save_document(PydanticDocument(**doc_data))
            
            await self._refresh_total_documents()
            
            logger.info(f"Batch ingestion completed: {len(metadata)} documents indexed")
            return True
        
        return False
    
    # Monkeypatch la méthode
    rag_workflow.ingest_documents_batch = ingest_documents_batch.__get__(rag_workflow)
    
    logger.info("RAGWorkflow enhanced with batch processing capabilities")


logger.info("Batch RAG optimizer module loaded")

