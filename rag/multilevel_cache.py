import json
import logging
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Union, Set
from datetime import datetime, timedelta
import redis.asyncio as redis

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiLevelCache:
    """
    Système de cache intelligent à plusieurs niveaux:
    - Niveau 1: Cache mémoire (le plus rapide, mais volatile)
    - Niveau 2: Cache Redis (persistant, partagé entre instances)
    
    Chaque type de donnée a sa propre configuration de TTL et politique de cache.
    """
    
    def __init__(self, redis_client: redis.Redis = None, redis_url: str = None):
        """
        Initialise le cache multi-niveaux avec Redis facultatif.
        
        Args:
            redis_client: Client Redis optionnel
            redis_url: URL Redis pour créer un client si aucun n'est fourni
        """
        # Cache en mémoire avec timestamp d'expiration
        self.memory_cache = {}
        self.expiry_times = {}
        
        # Capacité maximale du cache mémoire par type
        self.memory_capacity = {
            "embeddings": 500,        # 500 embeddings maximum
            "retrieval_results": 100,  # 100 résultats de récupération
            "generation_results": 50,  # 50 résultats de génération
            "query_expansions": 100,   # 100 expansions de requêtes
        }
        
        # TTL par niveau et type de donnée
        self.ttl_config = {
            "embeddings": 86400 * 7,        # 7 jours
            "retrieval_results": 3600 * 24,  # 24 heures
            "generation_results": 3600 * 2,  # 2 heures
            "query_expansions": 3600 * 12,   # 12 heures
        }
        
        # Client Redis
        self.redis_client = redis_client
        self.redis_url = redis_url
        self.redis_available = False
        
        # Statistiques du cache
        self.stats = {
            "memory_hits": 0,
            "redis_hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0
        }
        
        # Liste des types de données valides
        self.valid_data_types = set(self.ttl_config.keys())
        
        # Initialisation asynchrone de Redis (sera effectuée lors du premier appel)
        self._redis_initialized = False
        self._init_lock = asyncio.Lock()
    
    async def _init_redis(self):
        """Initialise la connexion Redis avec gestion d'erreur."""
        if self._redis_initialized:
            return
            
        async with self._init_lock:
            if self._redis_initialized:  # Double check après l'acquisition du verrou
                return
                
            try:
                if not self.redis_client and self.redis_url:
                    self.redis_client = redis.from_url(self.redis_url)
                
                if self.redis_client:
                    # Test de la connexion
                    await self.redis_client.ping()
                    self.redis_available = True
                    logger.info("Connexion Redis établie avec succès pour le cache multi-niveaux")
            except (redis.ConnectionError, redis.RedisError) as e:
                logger.error(f"Erreur de connexion Redis pour le cache: {str(e)}")
                self.redis_available = False
                self.redis_client = None
            except Exception as e:
                logger.error(f"Erreur inattendue lors de l'initialisation Redis: {str(e)}")
                self.redis_available = False
                self.redis_client = None
            finally:
                self._redis_initialized = True
    
    def _generate_key(self, key: str, data_type: str) -> str:
        """
        Génère une clé normalisée pour le cache.
        
        Args:
            key: Clé originale
            data_type: Type de données
            
        Returns:
            Clé formatée
        """
        # Convertir la clé en chaîne si ce n'est pas déjà le cas
        str_key = str(key)
        
        # Pour les longues clés, utiliser un hachage SHA256
        if len(str_key) > 100:
            hash_obj = hashlib.sha256(str_key.encode())
            str_key = hash_obj.hexdigest()
            
        return f"{data_type}:{str_key}"
    
    def _clean_memory_cache(self, data_type: str = None):
        """
        Nettoie le cache mémoire en supprimant les entrées expirées.
        Si un data_type est fourni, ne nettoie que les entrées de ce type.
        """
        now = datetime.now().timestamp()
        keys_to_delete = []
        
        # Identifier les clés expirées
        for key, expiry_time in self.expiry_times.items():
            if expiry_time <= now:
                if data_type is None or key.startswith(f"{data_type}:"):
                    keys_to_delete.append(key)
        
        # Supprimer les clés expirées
        for key in keys_to_delete:
            if key in self.memory_cache:
                del self.memory_cache[key]
                del self.expiry_times[key]
    
    def _enforce_capacity(self, data_type: str):
        """
        Assure que le cache mémoire ne dépasse pas sa capacité maximale pour un type de données.
        Supprime les entrées les moins récemment utilisées si nécessaire.
        
        Args:
            data_type: Type de données à vérifier
        """
        # Récupérer la capacité maximale pour ce type
        max_capacity = self.memory_capacity.get(data_type, 100)
        
        # Compter les entrées de ce type
        type_entries = [k for k in self.memory_cache.keys() if k.startswith(f"{data_type}:")]
        
        if len(type_entries) <= max_capacity:
            return
        
        # Trier par temps d'expiration (les plus proches de l'expiration d'abord)
        sorted_entries = sorted(
            type_entries, 
            key=lambda k: self.expiry_times.get(k, 0)
        )
        
        # Supprimer les entrées en excès
        entries_to_remove = len(type_entries) - max_capacity
        for key in sorted_entries[:entries_to_remove]:
            del self.memory_cache[key]
            del self.expiry_times[key]
    
    async def get(self, key: str, data_type: str) -> Optional[Any]:
        """
        Récupère une valeur depuis le cache (mémoire ou Redis).
        
        Args:
            key: Clé à récupérer
            data_type: Type de données (embeddings, retrieval_results, etc.)
            
        Returns:
            Valeur en cache ou None si non trouvée
        """
        if data_type not in self.valid_data_types:
            logger.warning(f"Type de données non valide: {data_type}")
            return None
            
        # Générer la clé formatée
        formatted_key = self._generate_key(key, data_type)
        
        # Nettoyer le cache mémoire des entrées expirées
        self._clean_memory_cache()
        
        # Vérifier le cache mémoire d'abord (le plus rapide)
        if formatted_key in self.memory_cache:
            self.stats["memory_hits"] += 1
            return self.memory_cache[formatted_key]
        
        # Sinon, vérifier Redis si disponible
        if not self._redis_initialized:
            await self._init_redis()
            
        if self.redis_available and self.redis_client:
            try:
                value = await self.redis_client.get(formatted_key)
                if value:
                    # Déserialiser
                    deserialized = json.loads(value)
                    
                    # Mettre en cache mémoire pour les prochains accès
                    self.memory_cache[formatted_key] = deserialized
                    ttl = self.ttl_config.get(data_type, 3600)
                    self.expiry_times[formatted_key] = (datetime.now() + timedelta(seconds=ttl)).timestamp()
                    self._enforce_capacity(data_type)
                    
                    self.stats["redis_hits"] += 1
                    return deserialized
            except Exception as e:
                logger.error(f"Erreur lors de la récupération depuis Redis: {str(e)}")
        
        # Aucune correspondance trouvée
        self.stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, data_type: str) -> bool:
        """
        Stocke une valeur dans le cache (mémoire et Redis).
        
        Args:
            key: Clé à stocker
            value: Valeur à stocker
            data_type: Type de données
            
        Returns:
            True si l'opération a réussi, False sinon
        """
        if data_type not in self.valid_data_types:
            logger.warning(f"Type de données non valide: {data_type}")
            return False
            
        # Générer la clé formatée
        formatted_key = self._generate_key(key, data_type)
        
        # Déterminer TTL selon le type de donnée
        ttl = self.ttl_config.get(data_type, 3600)  # 1h par défaut
        
        # Stockage dans le cache mémoire
        self.memory_cache[formatted_key] = value
        self.expiry_times[formatted_key] = (datetime.now() + timedelta(seconds=ttl)).timestamp()
        self._enforce_capacity(data_type)
        
        # Stockage dans Redis si disponible
        if not self._redis_initialized:
            await self._init_redis()
            
        if self.redis_available and self.redis_client:
            try:
                # Sérialiser
                serialized = json.dumps(value)
                
                # Stocker avec TTL
                await self.redis_client.setex(
                    formatted_key, 
                    ttl,
                    serialized
                )
            except Exception as e:
                logger.error(f"Erreur lors du stockage dans Redis: {str(e)}")
                # Continuer même si Redis échoue
        
        self.stats["sets"] += 1
        return True
    
    async def invalidate(self, pattern: str, data_type: Optional[str] = None) -> int:
        """
        Invalide toutes les entrées de cache correspondant au modèle.
        
        Args:
            pattern: Motif à invalider
            data_type: Type de données à invalider (ou tous si None)
            
        Returns:
            Nombre d'entrées invalidées
        """
        count = 0
        
        # Invalidation du cache mémoire
        keys_to_delete = []
        
        for key in self.memory_cache.keys():
            # Si un data_type est spécifié, ne vérifier que ces clés
            if data_type and not key.startswith(f"{data_type}:"):
                continue
                
            if pattern in key:
                keys_to_delete.append(key)
        
        # Supprimer les clés identifiées
        for key in keys_to_delete:
            del self.memory_cache[key]
            if key in self.expiry_times:
                del self.expiry_times[key]
            count += 1
        
        # Invalidation Redis si disponible
        if not self._redis_initialized:
            await self._init_redis()
            
        if self.redis_available and self.redis_client:
            try:
                # Construire le bon modèle de recherche
                if data_type:
                    redis_pattern = f"{data_type}:*{pattern}*"
                else:
                    redis_pattern = f"*{pattern}*"
                
                # Trouver et supprimer toutes les clés correspondantes
                cursor = b'0'
                while cursor:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor, 
                        match=redis_pattern,
                        count=100
                    )
                    
                    if keys:
                        await self.redis_client.delete(*keys)
                        count += len(keys)
                    
                    if cursor == b'0':
                        break
            except Exception as e:
                logger.error(f"Erreur lors de l'invalidation Redis: {str(e)}")
        
        self.stats["invalidations"] += 1
        return count
    
    async def clear_all(self, data_type: Optional[str] = None) -> int:
        """
        Efface tout le cache ou uniquement un type spécifique.
        
        Args:
            data_type: Type de données à effacer (ou tous si None)
            
        Returns:
            Nombre d'entrées effacées
        """
        count = 0
        
        # Effacement du cache mémoire
        if data_type:
            # Effacer uniquement les entrées du type spécifié
            keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(f"{data_type}:")]
            for key in keys_to_delete:
                del self.memory_cache[key]
                if key in self.expiry_times:
                    del self.expiry_times[key]
            count += len(keys_to_delete)
        else:
            # Effacer toutes les entrées
            count += len(self.memory_cache)
            self.memory_cache.clear()
            self.expiry_times.clear()
        
        # Effacement Redis si disponible
        if not self._redis_initialized:
            await self._init_redis()
            
        if self.redis_available and self.redis_client:
            try:
                if data_type:
                    # Effacer uniquement les clés du type spécifié
                    cursor = b'0'
                    while cursor:
                        cursor, keys = await self.redis_client.scan(
                            cursor=cursor, 
                            match=f"{data_type}:*",
                            count=100
                        )
                        
                        if keys:
                            await self.redis_client.delete(*keys)
                            count += len(keys)
                        
                        if cursor == b'0':
                            break
                else:
                    # Effacer toutes les clés du cache
                    for data_type in self.valid_data_types:
                        cursor = b'0'
                        while cursor:
                            cursor, keys = await self.redis_client.scan(
                                cursor=cursor, 
                                match=f"{data_type}:*",
                                count=100
                            )
                            
                            if keys:
                                await self.redis_client.delete(*keys)
                                count += len(keys)
                            
                            if cursor == b'0':
                                break
            except Exception as e:
                logger.error(f"Erreur lors de l'effacement Redis: {str(e)}")
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du cache.
        
        Returns:
            Dictionnaire des statistiques
        """
        total_hits = self.stats["memory_hits"] + self.stats["redis_hits"]
        total_requests = total_hits + self.stats["misses"]
        
        # Calculer les taux de succès
        hit_rate = (total_hits / total_requests) * 100 if total_requests > 0 else 0
        memory_hit_rate = (self.stats["memory_hits"] / total_requests) * 100 if total_requests > 0 else 0
        redis_hit_rate = (self.stats["redis_hits"] / total_requests) * 100 if total_requests > 0 else 0
        
        # Taille actuelle du cache mémoire par type
        memory_size_by_type = {}
        for data_type in self.valid_data_types:
            prefix = f"{data_type}:"
            count = len([k for k in self.memory_cache.keys() if k.startswith(prefix)])
            max_capacity = self.memory_capacity.get(data_type, 100)
            memory_size_by_type[data_type] = {
                "count": count,
                "capacity": max_capacity,
                "usage_percent": (count / max_capacity) * 100 if max_capacity > 0 else 0
            }
        
        return {
            "hits": {
                "total": total_hits,
                "memory": self.stats["memory_hits"],
                "redis": self.stats["redis_hits"]
            },
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "memory_hit_rate": memory_hit_rate,
            "redis_hit_rate": redis_hit_rate,
            "sets": self.stats["sets"],
            "invalidations": self.stats["invalidations"],
            "memory_size": len(self.memory_cache),
            "memory_by_type": memory_size_by_type,
            "redis_available": self.redis_available
        }
    
    async def close(self):
        """Ferme proprement les connexions."""
        if self.redis_available and self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Connexion Redis du cache fermée avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture de la connexion Redis du cache: {str(e)}") 