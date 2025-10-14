"""
Fallback Manager - Mode Dégradé pour Services Externes

Ce module gère le mode dégradé gracieux lorsque les services externes 
(MongoDB, Redis, APIs) sont indisponibles.

Auteur: MCP Team
Date: 13 octobre 2025
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ServiceStatus(Enum):
    """Statuts possibles d'un service"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class FallbackMode(Enum):
    """Modes de fallback disponibles"""
    FULL = "full"  # Tous services OK
    PARTIAL = "partial"  # Certains services down, fonctionnalité réduite
    EMERGENCY = "emergency"  # Services critiques down, mode minimal
    MAINTENANCE = "maintenance"  # Mode maintenance planifié


class FallbackManager:
    """
    Gère les fallbacks gracieux pour tous les services externes.
    
    Implémente:
    - Circuit breaker pattern
    - Fallback vers fichiers locaux si DB down
    - Mode read-only si services d'écriture down
    - Alertes automatiques si dégradation
    """
    
    def __init__(self, fallback_dir: Optional[str] = None):
        """
        Initialise le fallback manager.
        
        Args:
            fallback_dir: Répertoire pour stocker les données de fallback
        """
        self.fallback_dir = Path(fallback_dir or "data/fallback")
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        
        self.service_status: Dict[str, ServiceStatus] = {}
        self.last_check: Dict[str, datetime] = {}
        self.failure_count: Dict[str, int] = {}
        self.mode = FallbackMode.FULL
        
        # Configuration
        self.max_failures = 5
        self.check_interval = timedelta(seconds=30)
        self.recovery_threshold = 3  # Succès consécutifs pour récupération
        
        logger.info("fallback_manager_initialized", 
                   fallback_dir=str(self.fallback_dir))
    
    def check_service_health(self, service_name: str, 
                            health_check_fn) -> ServiceStatus:
        """
        Vérifie la santé d'un service.
        
        Args:
            service_name: Nom du service (mongodb, redis, lnbits, etc.)
            health_check_fn: Fonction de healthcheck qui retourne True si OK
            
        Returns:
            ServiceStatus du service
        """
        now = datetime.utcnow()
        
        # Rate limiting des checks
        if service_name in self.last_check:
            if now - self.last_check[service_name] < self.check_interval:
                return self.service_status.get(service_name, ServiceStatus.UNKNOWN)
        
        try:
            is_healthy = health_check_fn()
            
            if is_healthy:
                # Service OK, réinitialiser compteur échecs
                self.failure_count[service_name] = 0
                self.service_status[service_name] = ServiceStatus.HEALTHY
                logger.info("service_healthy", service=service_name)
            else:
                self._handle_service_failure(service_name)
                
        except Exception as e:
            logger.error("service_check_error", 
                        service=service_name, 
                        error=str(e))
            self._handle_service_failure(service_name)
        
        self.last_check[service_name] = now
        return self.service_status.get(service_name, ServiceStatus.UNKNOWN)
    
    def _handle_service_failure(self, service_name: str):
        """Gère l'échec d'un service."""
        self.failure_count[service_name] = self.failure_count.get(service_name, 0) + 1
        
        if self.failure_count[service_name] >= self.max_failures:
            self.service_status[service_name] = ServiceStatus.DOWN
            logger.error("service_down", 
                        service=service_name,
                        failures=self.failure_count[service_name])
        else:
            self.service_status[service_name] = ServiceStatus.DEGRADED
            logger.warning("service_degraded",
                          service=service_name,
                          failures=self.failure_count[service_name])
        
        self._update_global_mode()
    
    def _update_global_mode(self):
        """Met à jour le mode global basé sur l'état des services."""
        down_services = [s for s, status in self.service_status.items() 
                        if status == ServiceStatus.DOWN]
        degraded_services = [s for s, status in self.service_status.items()
                            if status == ServiceStatus.DEGRADED]
        
        if not down_services and not degraded_services:
            new_mode = FallbackMode.FULL
        elif "mongodb" in down_services or "redis" in down_services:
            new_mode = FallbackMode.EMERGENCY
        elif len(degraded_services) > 0:
            new_mode = FallbackMode.PARTIAL
        else:
            new_mode = FallbackMode.FULL
        
        if new_mode != self.mode:
            logger.warning("mode_changed",
                          old_mode=self.mode.value,
                          new_mode=new_mode.value,
                          down=down_services,
                          degraded=degraded_services)
            self.mode = new_mode
    
    # MongoDB Fallbacks
    
    def save_to_local_fallback(self, collection: str, 
                               document: Dict[str, Any]) -> bool:
        """
        Sauvegarde un document localement si MongoDB est down.
        
        Args:
            collection: Nom de la collection
            document: Document à sauvegarder
            
        Returns:
            True si succès
        """
        try:
            filepath = self.fallback_dir / f"{collection}.jsonl"
            
            # Ajouter timestamp et ID si manquant
            if "_id" not in document:
                document["_id"] = f"fallback_{datetime.utcnow().isoformat()}"
            if "fallback_timestamp" not in document:
                document["fallback_timestamp"] = datetime.utcnow().isoformat()
            
            # Append au fichier JSONL
            with open(filepath, "a") as f:
                f.write(json.dumps(document) + "\n")
            
            logger.info("document_saved_to_fallback",
                       collection=collection,
                       doc_id=document.get("_id"))
            return True
            
        except Exception as e:
            logger.error("fallback_save_failed",
                        collection=collection,
                        error=str(e))
            return False
    
    def read_from_local_fallback(self, collection: str, 
                                 query: Optional[Dict] = None) -> List[Dict]:
        """
        Lit des documents depuis le fallback local.
        
        Args:
            collection: Nom de la collection
            query: Filtre simple (égalité uniquement)
            
        Returns:
            Liste de documents matchant
        """
        try:
            filepath = self.fallback_dir / f"{collection}.jsonl"
            
            if not filepath.exists():
                return []
            
            documents = []
            with open(filepath, "r") as f:
                for line in f:
                    doc = json.loads(line.strip())
                    
                    # Filtre simple
                    if query:
                        match = all(doc.get(k) == v for k, v in query.items())
                        if match:
                            documents.append(doc)
                    else:
                        documents.append(doc)
            
            logger.info("documents_read_from_fallback",
                       collection=collection,
                       count=len(documents))
            return documents
            
        except Exception as e:
            logger.error("fallback_read_failed",
                        collection=collection,
                        error=str(e))
            return []
    
    def sync_fallback_to_mongodb(self, mongodb_client) -> int:
        """
        Synchronise les données du fallback vers MongoDB quand il revient.
        
        Args:
            mongodb_client: Client MongoDB
            
        Returns:
            Nombre de documents synchronisés
        """
        synced = 0
        
        try:
            for filepath in self.fallback_dir.glob("*.jsonl"):
                collection_name = filepath.stem
                
                documents = []
                with open(filepath, "r") as f:
                    for line in f:
                        documents.append(json.loads(line.strip()))
                
                if documents:
                    collection = mongodb_client[collection_name]
                    result = collection.insert_many(documents, ordered=False)
                    synced += len(result.inserted_ids)
                    
                    # Archiver le fichier synchro
                    archive_path = filepath.with_suffix(".synced.jsonl")
                    filepath.rename(archive_path)
                    
                    logger.info("fallback_synced",
                               collection=collection_name,
                               count=len(documents))
            
            return synced
            
        except Exception as e:
            logger.error("fallback_sync_failed", error=str(e))
            return synced
    
    # Redis Fallbacks
    
    def get_from_memory_cache(self, key: str, 
                             memory_cache: Dict) -> Optional[Any]:
        """
        Fallback vers un cache mémoire si Redis est down.
        
        Args:
            key: Clé du cache
            memory_cache: Dictionnaire servant de cache mémoire
            
        Returns:
            Valeur du cache ou None
        """
        value = memory_cache.get(key)
        if value:
            logger.debug("cache_hit_memory", key=key)
        return value
    
    def set_in_memory_cache(self, key: str, value: Any,
                           memory_cache: Dict, ttl: int = 300):
        """
        Fallback pour stocker en mémoire si Redis est down.
        
        Args:
            key: Clé du cache
            value: Valeur à stocker
            memory_cache: Dictionnaire servant de cache mémoire
            ttl: TTL en secondes (ignoré pour mémoire)
        """
        memory_cache[key] = value
        logger.debug("cache_set_memory", key=key)
    
    # API External Fallbacks
    
    def use_cached_response(self, api_name: str, 
                           endpoint: str) -> Optional[Dict]:
        """
        Utilise une réponse en cache si l'API externe est down.
        
        Args:
            api_name: Nom de l'API (amboss, mempool, etc.)
            endpoint: Endpoint appelé
            
        Returns:
            Réponse en cache ou None
        """
        try:
            cache_file = self.fallback_dir / f"{api_name}_{endpoint.replace('/', '_')}.json"
            
            if cache_file.exists():
                # Vérifier âge du cache
                age = datetime.utcnow() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                
                if age < timedelta(hours=24):  # Cache valide 24h
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    
                    logger.info("api_fallback_cache_used",
                               api=api_name,
                               endpoint=endpoint,
                               age_hours=age.total_seconds() / 3600)
                    return data
            
            return None
            
        except Exception as e:
            logger.error("api_fallback_failed",
                        api=api_name,
                        endpoint=endpoint,
                        error=str(e))
            return None
    
    def cache_api_response(self, api_name: str, 
                          endpoint: str, 
                          response: Dict):
        """
        Cache une réponse API pour fallback futur.
        
        Args:
            api_name: Nom de l'API
            endpoint: Endpoint appelé
            response: Réponse de l'API
        """
        try:
            cache_file = self.fallback_dir / f"{api_name}_{endpoint.replace('/', '_')}.json"
            
            with open(cache_file, "w") as f:
                json.dump(response, f, indent=2)
            
            logger.debug("api_response_cached",
                        api=api_name,
                        endpoint=endpoint)
            
        except Exception as e:
            logger.error("api_cache_failed",
                        api=api_name,
                        error=str(e))
    
    # Status & Reporting
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Retourne le statut complet du système.
        
        Returns:
            Dict avec status de tous les services
        """
        return {
            "mode": self.mode.value,
            "services": {
                name: {
                    "status": status.value,
                    "failures": self.failure_count.get(name, 0),
                    "last_check": self.last_check.get(name, datetime.min).isoformat()
                }
                for name, status in self.service_status.items()
            },
            "healthy_count": sum(1 for s in self.service_status.values() 
                                if s == ServiceStatus.HEALTHY),
            "degraded_count": sum(1 for s in self.service_status.values()
                                 if s == ServiceStatus.DEGRADED),
            "down_count": sum(1 for s in self.service_status.values()
                             if s == ServiceStatus.DOWN),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def is_service_available(self, service_name: str) -> bool:
        """
        Vérifie si un service est disponible.
        
        Args:
            service_name: Nom du service
            
        Returns:
            True si service est HEALTHY ou DEGRADED
        """
        status = self.service_status.get(service_name, ServiceStatus.UNKNOWN)
        return status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)
    
    def get_mode(self) -> FallbackMode:
        """Retourne le mode actuel."""
        return self.mode
    
    def is_read_only(self) -> bool:
        """
        Vérifie si le système est en mode read-only.
        
        Returns:
            True si mode EMERGENCY ou services d'écriture down
        """
        return self.mode == FallbackMode.EMERGENCY
    
    def should_skip_optimization(self) -> bool:
        """
        Détermine si les optimisations doivent être skippées.
        
        Returns:
            True si mode EMERGENCY ou LNBits down
        """
        return (self.mode == FallbackMode.EMERGENCY or 
                not self.is_service_available("lnbits"))


# Instance globale (singleton)
_fallback_manager: Optional[FallbackManager] = None


def get_fallback_manager() -> FallbackManager:
    """
    Retourne l'instance globale du fallback manager.
    
    Returns:
        FallbackManager instance
    """
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = FallbackManager()
    return _fallback_manager


def init_fallback_manager(fallback_dir: Optional[str] = None) -> FallbackManager:
    """
    Initialise le fallback manager global.
    
    Args:
        fallback_dir: Répertoire pour les données de fallback
        
    Returns:
        FallbackManager instance
    """
    global _fallback_manager
    _fallback_manager = FallbackManager(fallback_dir)
    return _fallback_manager

