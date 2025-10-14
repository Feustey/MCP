"""
Rollback Manager - Gestion des backups et rollbacks de policies
Dernière mise à jour: 12 octobre 2025
Version: 1.0.0

Système transactionnel pour policies Lightning:
- Backup automatique avant chaque changement
- Rollback automatique ou manuel
- Historique complet
- Rétention configurable
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib

import structlog

logger = structlog.get_logger(__name__)


class BackupStatus(Enum):
    """Status d'un backup"""
    ACTIVE = "active"
    RESTORED = "restored"
    EXPIRED = "expired"
    DELETED = "deleted"


@dataclass
class BackupEntry:
    """Entrée de backup de policy"""
    backup_id: str
    channel_id: str
    node_id: str
    policy: Dict[str, Any]
    created_at: datetime
    reason: str
    status: BackupStatus = BackupStatus.ACTIVE
    restored_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["restored_at"] = self.restored_at.isoformat() if self.restored_at else None
        data["expires_at"] = self.expires_at.isoformat() if self.expires_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupEntry":
        """Crée depuis un dictionnaire"""
        data["status"] = BackupStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["restored_at"] = datetime.fromisoformat(data["restored_at"]) if data.get("restored_at") else None
        data["expires_at"] = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
        return cls(**data)


class RollbackManager:
    """
    Gestionnaire de rollback pour policies Lightning
    
    Fonctionnalités:
    - Création de backups avant chaque changement
    - Rollback automatique en cas d'échec
    - Rollback manuel via API
    - Historique complet des backups
    - Expiration automatique des vieux backups
    - Statistiques et métriques
    """
    
    def __init__(
        self,
        storage_backend: Optional[Any] = None,
        retention_days: int = 90,
        max_backups_per_channel: int = 100
    ):
        """
        Initialise le gestionnaire de rollback
        
        Args:
            storage_backend: Backend MongoDB pour persistance
            retention_days: Nombre de jours de rétention des backups
            max_backups_per_channel: Nombre max de backups par canal
        """
        self.storage = storage_backend
        self.retention_days = retention_days
        self.max_backups_per_channel = max_backups_per_channel
        
        # Cache en mémoire
        self._cache: Dict[str, BackupEntry] = {}
        
        # Stats
        self._stats = {
            "total_backups": 0,
            "total_restores": 0,
            "successful_restores": 0,
            "failed_restores": 0
        }
        
        logger.info(
            "rollback_manager_initialized",
            retention_days=retention_days,
            max_backups_per_channel=max_backups_per_channel
        )
    
    def _generate_backup_id(self, channel_id: str) -> str:
        """Génère un ID unique pour le backup"""
        timestamp = datetime.now().isoformat()
        data = f"{channel_id}{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def create_backup(
        self,
        channel_id: str,
        current_policy: Dict[str, Any],
        node_id: Optional[str] = None,
        reason: str = "Pre-optimization",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crée un backup de la policy actuelle
        
        Args:
            channel_id: ID du canal
            current_policy: Policy actuelle à sauvegarder
            node_id: ID du nœud (optionnel)
            reason: Raison du backup
            metadata: Métadonnées additionnelles
            
        Returns:
            ID du backup créé
        """
        backup_id = self._generate_backup_id(channel_id)
        
        # Calculer expiration
        expires_at = datetime.now() + timedelta(days=self.retention_days)
        
        # Créer l'entrée
        backup = BackupEntry(
            backup_id=backup_id,
            channel_id=channel_id,
            node_id=node_id or "unknown",
            policy=current_policy,
            created_at=datetime.now(),
            reason=reason,
            expires_at=expires_at,
            metadata=metadata
        )
        
        # Stocker en cache
        self._cache[backup_id] = backup
        
        # Stocker dans MongoDB
        if self.storage:
            await self._store_backup(backup)
        
        # Nettoyer les vieux backups du canal
        await self._cleanup_old_backups(channel_id)
        
        self._stats["total_backups"] += 1
        
        logger.info(
            "backup_created",
            backup_id=backup_id,
            channel_id=channel_id,
            reason=reason,
            expires_at=expires_at.isoformat()
        )
        
        return backup_id
    
    async def restore_backup(
        self,
        backup_id: str,
        lnbits_client: Optional[Any] = None,
        dry_run: bool = False
    ) -> bool:
        """
        Restaure un backup
        
        Args:
            backup_id: ID du backup à restaurer
            lnbits_client: Client LNBits pour application
            dry_run: Mode simulation
            
        Returns:
            True si restauré avec succès
        """
        self._stats["total_restores"] += 1
        
        # Récupérer le backup
        backup = await self.get_backup(backup_id)
        if not backup:
            logger.error("backup_not_found", backup_id=backup_id)
            self._stats["failed_restores"] += 1
            return False
        
        # Vérifier le status
        if backup.status != BackupStatus.ACTIVE:
            logger.warning(
                "backup_not_active",
                backup_id=backup_id,
                status=backup.status.value
            )
            self._stats["failed_restores"] += 1
            return False
        
        logger.info(
            "restoring_backup",
            backup_id=backup_id,
            channel_id=backup.channel_id,
            dry_run=dry_run
        )
        
        if dry_run:
            logger.info(
                "backup_restore_simulated",
                backup_id=backup_id,
                policy=backup.policy
            )
            return True
        
        # Application réelle de la policy
        if lnbits_client:
            try:
                result = await lnbits_client.update_channel_policy(
                    channel_id=backup.channel_id,
                    base_fee_msat=backup.policy.get("base_fee_msat"),
                    fee_rate_ppm=backup.policy.get("fee_rate_ppm"),
                    time_lock_delta=backup.policy.get("time_lock_delta"),
                    min_htlc_msat=backup.policy.get("min_htlc_msat"),
                    max_htlc_msat=backup.policy.get("max_htlc_msat")
                )
                
                # Marquer comme restauré
                backup.status = BackupStatus.RESTORED
                backup.restored_at = datetime.now()
                
                # Mettre à jour dans le storage
                if self.storage:
                    await self._update_backup(backup)
                
                self._stats["successful_restores"] += 1
                
                logger.info(
                    "backup_restored",
                    backup_id=backup_id,
                    channel_id=backup.channel_id
                )
                
                return True
                
            except Exception as e:
                logger.error(
                    "backup_restore_failed",
                    backup_id=backup_id,
                    error=str(e)
                )
                self._stats["failed_restores"] += 1
                return False
        else:
            logger.warning(
                "no_lnbits_client_provided",
                backup_id=backup_id
            )
            self._stats["failed_restores"] += 1
            return False
    
    async def get_backup(self, backup_id: str) -> Optional[BackupEntry]:
        """
        Récupère un backup
        
        Args:
            backup_id: ID du backup
            
        Returns:
            BackupEntry ou None si non trouvé
        """
        # Chercher dans le cache
        if backup_id in self._cache:
            return self._cache[backup_id]
        
        # Chercher dans le storage
        if self.storage:
            backup = await self._load_backup(backup_id)
            if backup:
                self._cache[backup_id] = backup
            return backup
        
        return None
    
    async def list_backups(
        self,
        channel_id: Optional[str] = None,
        status: Optional[BackupStatus] = None,
        limit: int = 100
    ) -> List[BackupEntry]:
        """
        Liste les backups
        
        Args:
            channel_id: Filtrer par canal (None = tous)
            status: Filtrer par status (None = tous)
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des backups
        """
        if self.storage:
            return await self._list_from_storage(channel_id, status, limit)
        else:
            # Depuis le cache
            result = []
            for backup in self._cache.values():
                if channel_id and backup.channel_id != channel_id:
                    continue
                if status and backup.status != status:
                    continue
                result.append(backup)
            
            # Trier par date décroissante
            result.sort(key=lambda b: b.created_at, reverse=True)
            return result[:limit]
    
    async def cleanup_expired_backups(self) -> int:
        """
        Nettoie les backups expirés
        
        Returns:
            Nombre de backups supprimés
        """
        now = datetime.now()
        deleted_count = 0
        
        # Chercher les backups expirés
        backups = await self.list_backups()
        
        for backup in backups:
            if backup.expires_at and backup.expires_at < now:
                # Marquer comme expiré
                backup.status = BackupStatus.EXPIRED
                
                # Mettre à jour dans le storage
                if self.storage:
                    await self._update_backup(backup)
                
                # Retirer du cache
                if backup.backup_id in self._cache:
                    del self._cache[backup.backup_id]
                
                deleted_count += 1
        
        logger.info(
            "expired_backups_cleaned",
            count=deleted_count
        )
        
        return deleted_count
    
    async def _cleanup_old_backups(self, channel_id: str):
        """Nettoie les vieux backups d'un canal (garde max_backups_per_channel)"""
        backups = await self.list_backups(
            channel_id=channel_id,
            status=BackupStatus.ACTIVE
        )
        
        if len(backups) > self.max_backups_per_channel:
            # Garder les plus récents
            to_delete = backups[self.max_backups_per_channel:]
            
            for backup in to_delete:
                backup.status = BackupStatus.DELETED
                
                if self.storage:
                    await self._update_backup(backup)
                
                if backup.backup_id in self._cache:
                    del self._cache[backup.backup_id]
            
            logger.info(
                "old_backups_cleaned",
                channel_id=channel_id,
                deleted=len(to_delete)
            )
    
    # ═══════════════════════════════════════════════════════════
    # MÉTHODES DE STORAGE (MONGODB)
    # ═══════════════════════════════════════════════════════════
    
    async def _store_backup(self, backup: BackupEntry):
        """Stocke un backup dans MongoDB"""
        if not self.storage:
            return
        
        await self.storage.insert_one({
            "type": "policy_backup",
            **backup.to_dict()
        })
    
    async def _load_backup(self, backup_id: str) -> Optional[BackupEntry]:
        """Charge un backup depuis MongoDB"""
        if not self.storage:
            return None
        
        doc = await self.storage.find_one({"backup_id": backup_id})
        if not doc:
            return None
        
        # Retirer les champs MongoDB
        doc.pop("_id", None)
        doc.pop("type", None)
        
        return BackupEntry.from_dict(doc)
    
    async def _update_backup(self, backup: BackupEntry):
        """Met à jour un backup dans MongoDB"""
        if not self.storage:
            return
        
        await self.storage.update_one(
            {"backup_id": backup.backup_id},
            {"$set": backup.to_dict()}
        )
    
    async def _list_from_storage(
        self,
        channel_id: Optional[str],
        status: Optional[BackupStatus],
        limit: int
    ) -> List[BackupEntry]:
        """Liste les backups depuis MongoDB"""
        if not self.storage:
            return []
        
        query = {"type": "policy_backup"}
        if channel_id:
            query["channel_id"] = channel_id
        if status:
            query["status"] = status.value
        
        cursor = self.storage.find(query).sort("created_at", -1).limit(limit)
        
        result = []
        async for doc in cursor:
            doc.pop("_id", None)
            doc.pop("type", None)
            result.append(BackupEntry.from_dict(doc))
        
        return result

