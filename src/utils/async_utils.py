import asyncio
import logging
import time
from typing import List, Callable, Any, TypeVar, Dict, Set, Tuple
from functools import wraps

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type générique pour les fonctions
T = TypeVar('T')

async def execute_with_concurrency(
    max_workers: int,
    func: Callable,
    items: List[Any],
    *args,
    **kwargs
) -> List[Any]:
    """
    Exécute une fonction asynchrone sur une liste d'items avec concurrence limitée.
    
    Args:
        max_workers: Nombre maximal de tâches concurrentes
        func: Fonction asynchrone à appeler
        items: Liste d'items à traiter
        *args, **kwargs: Arguments supplémentaires à passer à la fonction
        
    Returns:
        Liste des résultats dans le même ordre que les items
    """
    # Créer un sémaphore pour limiter la concurrence
    semaphore = asyncio.Semaphore(max_workers)
    
    async def worker(item):
        async with semaphore:
            try:
                return await func(item, *args, **kwargs)
            except Exception as e:
                logger.error(f"Erreur dans execute_with_concurrency: {str(e)}")
                return e
    
    # Exécuter les tâches en parallèle avec limite de concurrence
    return await asyncio.gather(*[worker(item) for item in items], return_exceptions=True)

def async_timed():
    """
    Décorateur pour mesurer le temps d'exécution d'une coroutine.
    
    Exemple:
        @async_timed()
        async def ma_fonction():
            await asyncio.sleep(1)
    """
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"{func.__name__} terminé en {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"{func.__name__} échoué après {elapsed:.2f}s: {str(e)}")
                raise
        return wrapped
    return wrapper

class AsyncBatchProcessor:
    """
    Classe utilitaire pour le traitement par lots asynchrone avec suivi de progression.
    """
    
    def __init__(self, batch_size: int = 20, max_workers: int = 5):
        """
        Initialise le processeur de lots asynchrone.
        
        Args:
            batch_size: Taille de chaque lot
            max_workers: Nombre maximal de travailleurs concurrents
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable[[int, int, float], None]):
        """
        Définit une fonction de rappel pour suivre la progression.
        
        Args:
            callback: Fonction appelée avec (traités, total, pourcentage)
        """
        self.progress_callback = callback
        
    async def process_batches(self, items: List[Any], process_func: Callable) -> List[Any]:
        """
        Traite une liste d'items par lots avec parallélisme limité.
        
        Args:
            items: Liste d'items à traiter
            process_func: Fonction asynchrone pour traiter un lot
            
        Returns:
            Liste des résultats combinés
        """
        results = []
        total_items = len(items)
        processed_items = 0
        
        # Diviser en lots
        batches = [items[i:i+self.batch_size] for i in range(0, total_items, self.batch_size)]
        total_batches = len(batches)
        
        for i, batch in enumerate(batches):
            # Traiter le lot actuel
            try:
                logger.info(f"Traitement du lot {i+1}/{total_batches} ({len(batch)} items)")
                batch_result = await process_func(batch)
                
                # Prendre en compte des réponses sous forme de liste ou singleton
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
                    
                # Mise à jour de la progression
                processed_items += len(batch)
                if self.progress_callback:
                    progress_pct = (processed_items / total_items) * 100
                    self.progress_callback(processed_items, total_items, progress_pct)
                    
            except Exception as e:
                logger.error(f"Erreur lors du traitement du lot {i+1}: {str(e)}")
                
        return results
    
    async def process_batches_parallel(self, items: List[Any], process_func: Callable) -> List[Any]:
        """
        Traite une liste d'items par lots en parallèle avec concurrence limitée.
        
        Args:
            items: Liste d'items à traiter
            process_func: Fonction asynchrone pour traiter un lot
            
        Returns:
            Liste des résultats combinés
        """
        results = []
        
        # Diviser en lots
        batches = [items[i:i+self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        # Fonction pour reporter la progression
        async def process_and_report(i, batch):
            try:
                result = await process_func(batch)
                
                # Mise à jour de la progression
                if self.progress_callback:
                    processed = min((i + 1) * self.batch_size, len(items))
                    progress_pct = (processed / len(items)) * 100
                    self.progress_callback(processed, len(items), progress_pct)
                    
                return result
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement du lot {i+1}: {str(e)}")
                return []
        
        # Traiter les lots en parallèle avec concurrence limitée
        batch_results = await execute_with_concurrency(
            self.max_workers,
            process_and_report,
            [(i, batch) for i, batch in enumerate(batches)]
        )
        
        # Combiner les résultats
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Erreur de traitement par lot: {str(result)}")
            elif isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
                
        return results

class RetryWithBackoff:
    """
    Classe utilitaire pour ré-essayer des opérations asynchrones avec backoff exponentiel.
    """
    
    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0,
                factor: float = 2.0, jitter: float = 0.1):
        """
        Initialise la stratégie de retry.
        
        Args:
            max_retries: Nombre maximal de tentatives
            initial_delay: Délai initial avant le premier retry (secondes)
            factor: Facteur multiplicatif pour le backoff exponentiel
            jitter: Variation aléatoire pour éviter les tempêtes de connexions
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.factor = factor
        self.jitter = jitter
        
    async def execute(self, coro_func: Callable, *args, **kwargs):
        """
        Exécute une coroutine avec retry en cas d'échec.
        
        Args:
            coro_func: Fonction coroutine à exécuter
            *args, **kwargs: Arguments à passer à la fonction
            
        Returns:
            Résultat de la coroutine si succès
            
        Raises:
            Exception: La dernière exception si toutes les tentatives échouent
        """
        import random
        
        last_exception = None
        delay = self.initial_delay
        
        # Tentatives avec backoff exponentiel
        for attempt in range(self.max_retries + 1):  # +1 pour inclure la première tentative
            try:
                if attempt > 0:
                    logger.warning(f"Tentative {attempt}/{self.max_retries} après {delay:.2f}s...")
                
                return await coro_func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # Calculer le délai avec jitter pour éviter les effets de synchronisation
                    jitter_value = random.uniform(-self.jitter, self.jitter)
                    delay = delay * self.factor * (1 + jitter_value)
                    
                    logger.warning(f"Échec de l'opération: {str(e)}. Nouvelle tentative dans {delay:.2f}s.")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Échec de toutes les tentatives ({self.max_retries + 1}). "
                               f"Dernière erreur: {str(e)}")
        
        # Si on arrive ici, c'est que toutes les tentatives ont échoué
        raise last_exception 