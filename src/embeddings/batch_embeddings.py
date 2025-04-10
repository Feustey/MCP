import asyncio
import logging
from typing import List, Dict, Any, Optional
from src.embeddings.openai_embeddings import OpenAIEmbeddings

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchEmbeddings:
    """
    Classe pour générer des embeddings par lot afin d'optimiser les appels API.
    """
    
    def __init__(self, openai_embeddings: Optional[OpenAIEmbeddings] = None, batch_size: int = 20):
        """
        Initialise le gestionnaire d'embeddings par lot.
        
        Args:
            openai_embeddings: Instance de OpenAIEmbeddings, créée si non fournie
            batch_size: Taille maximale des lots pour les appels API
        """
        self.embeddings = openai_embeddings or OpenAIEmbeddings()
        self.batch_size = batch_size
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes en utilisant le traitement par lot.
        
        Args:
            texts: Liste de textes à encoder
            
        Returns:
            Liste d'embeddings correspondant aux textes
        """
        all_embeddings = []
        
        # Traiter les textes par lots
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i+self.batch_size]
            try:
                logger.info(f"Génération d'embeddings pour le lot {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1} " +
                          f"({len(batch)} textes)")
                
                # Appel API en un seul batch
                batch_embeddings = self.embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
                
                # Pause pour respecter les limites de l'API
                if i + self.batch_size < len(texts):
                    await asyncio.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"Erreur batch embeddings [{i}:{i+self.batch_size}]: {str(e)}")
                
                # Stratégie de repli: réduire la taille du lot en cas d'erreur
                if len(batch) > 5:
                    logger.info(f"Tentative avec des lots plus petits...")
                    # Diviser le lot en deux et réessayer récursivement
                    mid = len(batch) // 2
                    
                    # Traiter la première moitié
                    first_half = await self.get_embeddings_batch(batch[:mid])
                    all_embeddings.extend(first_half)
                    
                    # Traiter la seconde moitié
                    second_half = await self.get_embeddings_batch(batch[mid:])
                    all_embeddings.extend(second_half)
                else:
                    # Fallback: traitement individuel
                    logger.info(f"Traitement individuel des textes...")
                    for text in batch:
                        try:
                            single_emb = self.embeddings.embed_query(text)
                            all_embeddings.append(single_emb)
                            await asyncio.sleep(0.1)  # Pause entre chaque appel
                        except Exception as single_err:
                            logger.error(f"Erreur d'embedding individuel: {str(single_err)}")
                            # Embedding nul en cas d'échec
                            all_embeddings.append([0.0] * 1536)
        
        return all_embeddings
    
    async def get_embeddings_with_retry(self, texts: List[str], max_retries: int = 3) -> List[List[float]]:
        """
        Génère des embeddings avec mécanisme de retry en cas d'échec.
        
        Args:
            texts: Liste de textes à encoder
            max_retries: Nombre maximal de tentatives
            
        Returns:
            Liste d'embeddings correspondant aux textes
        """
        retries = 0
        while retries < max_retries:
            try:
                return await self.get_embeddings_batch(texts)
            except Exception as e:
                retries += 1
                wait_time = 2 ** retries  # Backoff exponentiel
                logger.warning(f"Échec de l'embedding (tentative {retries}/{max_retries}). " +
                             f"Nouvelle tentative dans {wait_time}s. Erreur: {str(e)}")
                await asyncio.sleep(wait_time)
        
        # Si toutes les tentatives échouent, renvoyer des embeddings nuls
        logger.error(f"Échec de toutes les tentatives d'embedding après {max_retries} essais.")
        return [[0.0] * 1536 for _ in range(len(texts))] 