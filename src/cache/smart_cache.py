import json
import hashlib
import logging
import time
from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime, timedelta
import asyncio

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartCache:
    """
    Cache intelligent à plusieurs niveaux avec invalidation sélective basée sur le contexte.
    Utilise Redis comme backend de stockage.
    """
    
    def __init__(self, redis_client):
        """
        Initialise le cache intelligent.
        
        Args:
            redis_client: Client Redis asyncio
        """
        self.redis = redis_client
        
        # TTL par défaut pour différents types de données (en secondes)
        self.ttl_config = {
            "embeddings": 86400 * 30,  # 30 jours (rarement modifiés)
            "documents": 86400 * 7,     # 7 jours
            "responses": 3600 * 6,      # 6 heures
            "node_data": 3600,          # 1 heure
            "recommendations": 3600 * 2, # 2 heures
            "metrics": 600,             # 10 minutes
            "user_data": 3600 * 24      # 24 heures
        }
        
        # Tags pour l'invalidation groupée
        self.dependency_map = {
            "responses": ["documents", "embeddings"],
            "recommendations": ["node_data"],
            "metrics": ["node_data", "recommendations"]
        }
        
        # Niveau de compression pour différents types (0-9, 0=aucune, 9=max)
        self.compression_level = {
            "embeddings": 1,  # Compression légère pour les embeddings (déjà denses)
            "documents": 6,   # Compression moyenne pour les documents texte
            "responses": 6,   # Compression moyenne pour les réponses texte
            "node_data": 4,   # Compression légère pour les données structurées
            "metrics": 0      # Pas de compression pour les petites métriques
        }
    
    def _make_key(self, cache_type: str, key_data: Any) -> str:
        """
        Crée une clé de cache standardisée.
        
        Args:
            cache_type: Type de données à mettre en cache
            key_data: Données pour générer la clé (chaîne ou objet JSON-serializable)
            
        Returns:
            Clé de cache formatée
        """
        if isinstance(key_data, str):
            hash_input = key_data
        else:
            try:
                hash_input = json.dumps(key_data, sort_keys=True)
            except (TypeError, ValueError):
                # Fallback pour les objets non-JSON
                hash_input = str(hash(key_data))
            
        key_hash = hashlib.md5(hash_input.encode()).hexdigest()
        return f"cache:{cache_type}:{key_hash}"
    
    async def get(self, cache_type: str, key_data: Any) -> Optional[Any]:
        """
        Récupère des données du cache.
        
        Args:
            cache_type: Type de données à récupérer
            key_data: Données pour générer la clé
            
        Returns:
            Données mises en cache, ou None si non trouvées
        """
        key = self._make_key(cache_type, key_data)
        
        try:
            # Récupérer les données
            data = await self.redis.get(key)
            
            if data:
                try:
                    # Décompresser si nécessaire
                    if self.compression_level.get(cache_type, 0) > 0:
                        import zlib
                        data = zlib.decompress(data)
                    
                    # Désérialiser les données
                    cached_data = json.loads(data)
                    
                    # Rafraîchir automatiquement le TTL pour les accès fréquents
                    await self.redis.expire(key, self.ttl_config.get(cache_type, 3600))
                    
                    # Incrémenter le compteur d'accès
                    await self.redis.hincrby("cache:stats", key, 1)
                    await self.redis.hincrby("cache:type:hits", cache_type, 1)
                    
                    logger.debug(f"Cache hit pour {cache_type}:{key_hash}")
                    return cached_data["data"]
                    
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    logger.warning(f"Erreur de décodage du cache pour {key}: {str(e)}")
                    # Supprimer l'entrée invalide
                    await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {str(e)}")
            
        # Incrémenter le compteur de miss
        await self.redis.hincrby("cache:type:misses", cache_type, 1)
        logger.debug(f"Cache miss pour {cache_type}:{key_hash}")
                
        return None
    
    async def set(self, cache_type: str, key_data: Any, value: Any, 
                 tags: List[str] = None, ttl: int = None) -> bool:
        """
        Met en cache des données avec TTL et tags pour l'invalidation.
        
        Args:
            cache_type: Type de données à mettre en cache
            key_data: Données pour générer la clé
            value: Valeur à mettre en cache
            tags: Liste de tags pour l'invalidation groupée
            ttl: Durée de vie en secondes (utilise la config par défaut si None)
            
        Returns:
            True si succès, False sinon
        """
        try:
            key = self._make_key(cache_type, key_data)
            ttl_value = ttl if ttl is not None else self.ttl_config.get(cache_type, 3600)
            
            # Préparer les données avec metadata
            cache_data = {
                "data": value,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl_value,
                "type": cache_type,
                "tags": tags or []
            }
            
            # Sérialiser les données
            data_json = json.dumps(cache_data)
            
            # Compresser si configuré
            if self.compression_level.get(cache_type, 0) > 0:
                import zlib
                data_to_store = zlib.compress(
                    data_json.encode(), 
                    self.compression_level.get(cache_type, 0)
                )
            else:
                data_to_store = data_json.encode()
            
            # Utiliser une pipeline pour les opérations atomiques
            async with self.redis.pipeline() as pipe:
                # Stocker les données
                await pipe.setex(key, ttl_value, data_to_store)
                
                # Enregistrer les tags pour l'invalidation groupée
                if tags:
                    for tag in tags:
                        await pipe.sadd(f"cache:tag:{tag}", key)
                        # TTL sur les ensembles de tags pour éviter l'accumulation
                        await pipe.expire(f"cache:tag:{tag}", ttl_value * 2)
                
                # Enregistrer le type pour l'invalidation par type
                await pipe.sadd(f"cache:type:{cache_type}", key)
                await pipe.expire(f"cache:type:{cache_type}", ttl_value * 2)
                
                # Exécuter toutes les commandes
                await pipe.execute()
            
            logger.debug(f"Mise en cache réussie pour {cache_type}:{key}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {str(e)}")
            return False
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalide toutes les entrées de cache avec un tag spécifique.
        
        Args:
            tag: Tag pour l'invalidation
            
        Returns:
            Nombre d'entrées invalidées
        """
        try:
            # Récupérer les clés associées au tag
            keys = await self.redis.smembers(f"cache:tag:{tag}")
            count = 0
            
            if keys:
                # Conversion des bytes en str si nécessaire
                str_keys = [k.decode() if isinstance(k, bytes) else k for k in keys]
                
                # Supprimer les entrées
                await self.redis.delete(*str_keys)
                count = len(str_keys)
                
                # Supprimer l'ensemble de tags
                await self.redis.delete(f"cache:tag:{tag}")
                
                logger.info(f"Invalidation de {count} entrées avec tag '{tag}'")
            
            return count
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation par tag: {str(e)}")
            return 0
    
    async def invalidate_by_type(self, cache_type: str) -> int:
        """
        Invalide toutes les entrées d'un type spécifique et ses dépendances.
        
        Args:
            cache_type: Type de cache à invalider
            
        Returns:
            Nombre d'entrées invalidées
        """
        try:
            all_keys = set()
            
            # Récupérer les clés du type principal
            type_keys = await self.redis.smembers(f"cache:type:{cache_type}")
            if type_keys:
                all_keys.update(type_keys)
            
            # Invalider aussi les dépendances
            dependency_types = self.dependency_map.get(cache_type, [])
            for dep_type in dependency_types:
                dep_keys = await self.redis.smembers(f"cache:type:{dep_type}")
                if dep_keys:
                    all_keys.update(dep_keys)
            
            count = 0
            if all_keys:
                # Conversion des bytes en str si nécessaire
                str_keys = [k.decode() if isinstance(k, bytes) else k for k in all_keys]
                
                # Supprimer les entrées
                await self.redis.delete(*str_keys)
                count = len(str_keys)
                
                # Supprimer les ensembles de types
                await self.redis.delete(f"cache:type:{cache_type}")
                for dep_type in dependency_types:
                    await self.redis.delete(f"cache:type:{dep_type}")
                
                logger.info(f"Invalidation de {count} entrées pour le type '{cache_type}' et ses dépendances")
            
            return count
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation par type: {str(e)}")
            return 0
    
    async def invalidate_by_pattern(self, pattern: str) -> int:
        """
        Invalide les entrées de cache correspondant à un motif.
        
        Args:
            pattern: Motif glob Redis (ex: "cache:responses:*")
            
        Returns:
            Nombre d'entrées invalidées
        """
        try:
            # Utiliser SCAN pour les grandes BDs
            keys = []
            cursor = "0"
            
            while True:
                cursor, partial_keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
                keys.extend(partial_keys)
                
                if cursor == "0" or cursor == 0:
                    break
            
            # Supprimer les clés trouvées
            count = 0
            if keys:
                await self.redis.delete(*keys)
                count = len(keys)
                logger.info(f"Invalidation de {count} entrées avec motif '{pattern}'")
                
            return count
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation par motif: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache.
        
        Returns:
            Dictionnaire de statistiques
        """
        stats = {}
        try:
            # Taille par type
            for cache_type in self.ttl_config.keys():
                key_count = await self.redis.scard(f"cache:type:{cache_type}")
                stats[f"{cache_type}_count"] = key_count
            
            # Hits et misses par type
            hits = await self.redis.hgetall("cache:type:hits")
            misses = await self.redis.hgetall("cache:type:misses")
            
            # Convertir bytes en str si nécessaire
            hits_dict = {k.decode() if isinstance(k, bytes) else k: 
                      int(v.decode() if isinstance(v, bytes) else v) 
                      for k, v in hits.items()}
            
            misses_dict = {k.decode() if isinstance(k, bytes) else k: 
                        int(v.decode() if isinstance(v, bytes) else v) 
                        for k, v in misses.items()}
            
            # Calculer les ratios de hits
            hit_ratios = {}
            for cache_type in self.ttl_config.keys():
                hit_count = hits_dict.get(cache_type, 0)
                miss_count = misses_dict.get(cache_type, 0)
                total = hit_count + miss_count
                
                if total > 0:
                    hit_ratios[f"{cache_type}_hit_ratio"] = hit_count / total
                else:
                    hit_ratios[f"{cache_type}_hit_ratio"] = 0
            
            stats.update(hit_ratios)
            stats.update({f"{k}_hits": v for k, v in hits_dict.items()})
            stats.update({f"{k}_misses": v for k, v in misses_dict.items()})
            
            # Consommation mémoire
            memory_info = await self.redis.info("memory")
            if isinstance(memory_info, dict):
                stats["memory_used"] = memory_info.get("used_memory", 0)
            elif isinstance(memory_info, bytes):
                # Parsing simplifié si le format est différent
                mem_str = memory_info.decode()
                for line in mem_str.split("\n"):
                    if "used_memory:" in line:
                        stats["memory_used"] = int(line.split(":")[1].strip())
                        break
            
            # Expiration et éviction
            keyspace_info = await self.redis.info("stats")
            if isinstance(keyspace_info, dict):
                stats["expired_keys"] = keyspace_info.get("expired_keys", 0)
                stats["evicted_keys"] = keyspace_info.get("evicted_keys", 0)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        
        return stats
    
    async def clear_all(self) -> int:
        """
        Efface toutes les entrées de cache.
        Utilisez avec prudence!
        
        Returns:
            Nombre d'entrées supprimées
        """
        try:
            # Compter avant la suppression
            count = await self.redis.keys("cache:*")
            count = len(count)
            
            # Supprimer toutes les clés du cache
            await self.redis.eval("""
                local keys = redis.call('keys', 'cache:*')
                if #keys > 0 then
                    return redis.call('del', unpack(keys))
                end
                return 0
            """, 0)
            
            logger.warning(f"Cache entièrement vidé: {count} entrées supprimées")
            return count
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache: {str(e)}")
            return 0
    
    async def maintenance(self):
        """
        Effectue une maintenance du cache:
        - Supprime les entrées orphelines
        - Met à jour les statistiques
        - Nettoie les tags sans références
        
        Returns:
            Nombre d'entrées nettoyées
        """
        try:
            cleaned = 0
            
            # Nettoyer les tags orphelins
            tag_keys = await self.redis.keys("cache:tag:*")
            for tag_key in tag_keys:
                tag_key_str = tag_key.decode() if isinstance(tag_key, bytes) else tag_key
                members = await self.redis.smembers(tag_key_str)
                
                # Vérifier si des membres existent encore
                valid_members = []
                for member in members:
                    member_str = member.decode() if isinstance(member, bytes) else member
                    exists = await self.redis.exists(member_str)
                    if exists:
                        valid_members.append(member_str)
                
                # Mettre à jour l'ensemble ou le supprimer
                if not valid_members:
                    await self.redis.delete(tag_key_str)
                    cleaned += 1
                elif len(valid_members) != len(members):
                    # Recréer l'ensemble avec uniquement les membres valides
                    await self.redis.delete(tag_key_str)
                    if valid_members:
                        await self.redis.sadd(tag_key_str, *valid_members)
                    cleaned += len(members) - len(valid_members)
            
            # Nettoyer les types orphelins de la même manière
            type_keys = await self.redis.keys("cache:type:*")
            for type_key in type_keys:
                if type_key.endswith(b":hits") or type_key.endswith(b":misses"):
                    continue
                    
                type_key_str = type_key.decode() if isinstance(type_key, bytes) else type_key
                members = await self.redis.smembers(type_key_str)
                
                valid_members = []
                for member in members:
                    member_str = member.decode() if isinstance(member, bytes) else member
                    exists = await self.redis.exists(member_str)
                    if exists:
                        valid_members.append(member_str)
                
                if not valid_members:
                    await self.redis.delete(type_key_str)
                    cleaned += 1
                elif len(valid_members) != len(members):
                    await self.redis.delete(type_key_str)
                    if valid_members:
                        await self.redis.sadd(type_key_str, *valid_members)
                    cleaned += len(members) - len(valid_members)
            
            logger.info(f"Maintenance du cache terminée: {cleaned} entrées nettoyées")
            return cleaned
            
        except Exception as e:
            logger.error(f"Erreur lors de la maintenance du cache: {str(e)}")
            return 0 