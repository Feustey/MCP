#!/usr/bin/env python3
"""
Backup Manager - Gestion avancée des backups de policies

Ce module gère les backups de policies avec :
- Versioning
- Compression (gzip pour anciens backups)
- Retention policy automatique (hot/warm/cold)
- Vérification d'intégrité (checksums)
- Export/Import pour disaster recovery

Dernière mise à jour: 15 octobre 2025
"""

import logging
import gzip
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# Directories
BACKUP_DIR = Path("data/rollbacks")
HOT_DIR = BACKUP_DIR / "hot"    # < 7 jours
WARM_DIR = BACKUP_DIR / "warm"  # 7-30 jours
COLD_DIR = BACKUP_DIR / "cold"  # 30-90 jours

# Créer les répertoires
for dir_path in [HOT_DIR, WARM_DIR, COLD_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)


class BackupTier(Enum):
    """Niveaux de stockage des backups."""
    HOT = "hot"      # Accès rapide
    WARM = "warm"    # Compressé
    COLD = "cold"    # Archivé


class BackupManager:
    """
    Gestionnaire avancé de backups avec retention policy.
    """
    
    def __init__(self, db=None):
        """
        Initialise le gestionnaire de backups.
        
        Args:
            db: Instance MongoDB (optionnel)
        """
        self.db = db
        self.backups_collection = db["policy_backups"] if db else None
        
        logger.info("BackupManager initialisé")
    
    def create_backup(
        self,
        channel_id: str,
        channel_point: str,
        policy: Dict[str, Any],
        node_id: str,
        transaction_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Crée un nouveau backup.
        
        Args:
            channel_id: ID du canal
            channel_point: Point du canal
            policy: Policy à sauvegarder
            node_id: ID du nœud
            transaction_id: ID de transaction (optionnel)
            metadata: Métadonnées (optionnel)
        
        Returns:
            backup_id
        """
        backup_id = f"{node_id[:8]}_{channel_id[:8]}_{int(datetime.utcnow().timestamp())}"
        
        backup_data = {
            "backup_id": backup_id,
            "transaction_id": transaction_id,
            "node_id": node_id,
            "channel_id": channel_id,
            "channel_point": channel_point,
            "policy": policy,
            "created_at": datetime.utcnow(),
            "tier": BackupTier.HOT.value,
            "compressed": False,
            "checksum": self._calculate_checksum(policy),
            "metadata": metadata or {}
        }
        
        # Sauvegarder en HOT (non compressé)
        hot_file = HOT_DIR / f"{backup_id}.json"
        self._save_to_file(hot_file, backup_data, compress=False)
        
        # Sauvegarder aussi dans MongoDB si disponible
        if self.backups_collection:
            self.backups_collection.insert_one(backup_data.copy())
        
        logger.info(f"Backup {backup_id} créé (HOT)")
        
        return backup_id
    
    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un backup par son ID.
        
        Args:
            backup_id: ID du backup
        
        Returns:
            Données du backup ou None
        """
        # Chercher dans MongoDB d'abord
        if self.backups_collection:
            backup = self.backups_collection.find_one(
                {"backup_id": backup_id},
                {"_id": 0}
            )
            if backup:
                return backup
        
        # Chercher dans les fichiers (HOT → WARM → COLD)
        for tier_dir in [HOT_DIR, WARM_DIR, COLD_DIR]:
            # Non compressé
            file_path = tier_dir / f"{backup_id}.json"
            if file_path.exists():
                return self._load_from_file(file_path, compressed=False)
            
            # Compressé
            gz_path = tier_dir / f"{backup_id}.json.gz"
            if gz_path.exists():
                return self._load_from_file(gz_path, compressed=True)
        
        logger.warning(f"Backup {backup_id} introuvable")
        return None
    
    def get_latest_backup(
        self,
        channel_id: str,
        node_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère le backup le plus récent pour un canal.
        
        Args:
            channel_id: ID du canal
            node_id: ID du nœud (optionnel, pour filtrage)
        
        Returns:
            Backup le plus récent ou None
        """
        query = {"channel_id": channel_id}
        if node_id:
            query["node_id"] = node_id
        
        if self.backups_collection:
            backup = self.backups_collection.find_one(
                query,
                {"_id": 0},
                sort=[("created_at", -1)]
            )
            return backup
        
        # Fallback fichiers
        all_backups = []
        for tier_dir in [HOT_DIR, WARM_DIR, COLD_DIR]:
            for file_path in tier_dir.glob(f"*{channel_id[:8]}*.json*"):
                backup = self._load_from_file(
                    file_path,
                    compressed=str(file_path).endswith('.gz')
                )
                if backup and backup.get("channel_id") == channel_id:
                    if not node_id or backup.get("node_id") == node_id:
                        all_backups.append(backup)
        
        if all_backups:
            all_backups.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            return all_backups[0]
        
        return None
    
    def verify_integrity(self, backup_id: str) -> bool:
        """
        Vérifie l'intégrité d'un backup via checksum.
        
        Args:
            backup_id: ID du backup
        
        Returns:
            True si intégrité OK
        """
        backup = self.get_backup(backup_id)
        if not backup:
            return False
        
        stored_checksum = backup.get("checksum")
        policy = backup.get("policy", {})
        calculated_checksum = self._calculate_checksum(policy)
        
        is_valid = stored_checksum == calculated_checksum
        
        if not is_valid:
            logger.error(f"Backup {backup_id} corrompu! Checksum mismatch.")
        
        return is_valid
    
    def apply_retention_policy(self) -> Dict[str, int]:
        """
        Applique la retention policy (HOT → WARM → COLD → DELETE).
        
        Returns:
            Stats: moved_to_warm, moved_to_cold, deleted
        """
        stats = {
            "moved_to_warm": 0,
            "moved_to_cold": 0,
            "deleted": 0
        }
        
        now = datetime.utcnow()
        
        # 1. HOT → WARM (> 7 jours)
        for file_path in HOT_DIR.glob("*.json"):
            backup = self._load_from_file(file_path, compressed=False)
            if not backup:
                continue
            
            created_at = backup.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            age_days = (now - created_at).days
            
            if age_days > 7:
                # Déplacer vers WARM avec compression
                backup_id = backup.get("backup_id")
                warm_path = WARM_DIR / f"{backup_id}.json.gz"
                backup["tier"] = BackupTier.WARM.value
                backup["compressed"] = True
                
                self._save_to_file(warm_path, backup, compress=True)
                file_path.unlink()  # Supprimer de HOT
                
                stats["moved_to_warm"] += 1
                logger.debug(f"Backup {backup_id} déplacé vers WARM")
        
        # 2. WARM → COLD (> 30 jours)
        for file_path in WARM_DIR.glob("*.json.gz"):
            backup = self._load_from_file(file_path, compressed=True)
            if not backup:
                continue
            
            created_at = backup.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            age_days = (now - created_at).days
            
            if age_days > 30:
                # Déplacer vers COLD
                backup_id = backup.get("backup_id")
                cold_path = COLD_DIR / f"{backup_id}.json.gz"
                backup["tier"] = BackupTier.COLD.value
                
                self._save_to_file(cold_path, backup, compress=True)
                file_path.unlink()  # Supprimer de WARM
                
                stats["moved_to_cold"] += 1
                logger.debug(f"Backup {backup_id} déplacé vers COLD")
        
        # 3. COLD → DELETE (> 90 jours)
        for file_path in COLD_DIR.glob("*.json.gz"):
            backup = self._load_from_file(file_path, compressed=True)
            if not backup:
                continue
            
            created_at = backup.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            age_days = (now - created_at).days
            
            if age_days > 90:
                backup_id = backup.get("backup_id")
                file_path.unlink()  # Supprimer
                
                # Supprimer aussi de MongoDB
                if self.backups_collection:
                    self.backups_collection.delete_one({"backup_id": backup_id})
                
                stats["deleted"] += 1
                logger.debug(f"Backup {backup_id} supprimé (> 90j)")
        
        logger.info(
            f"Retention policy appliquée: {stats['moved_to_warm']} → WARM, "
            f"{stats['moved_to_cold']} → COLD, {stats['deleted']} supprimés"
        )
        
        return stats
    
    def export_backup(
        self,
        backup_id: str,
        export_path: str
    ) -> bool:
        """
        Exporte un backup vers un fichier pour disaster recovery.
        
        Args:
            backup_id: ID du backup
            export_path: Chemin de destination
        
        Returns:
            True si export réussi
        """
        backup = self.get_backup(backup_id)
        if not backup:
            logger.error(f"Backup {backup_id} introuvable pour export")
            return False
        
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(exist_ok=True, parents=True)
            
            with open(export_file, 'w') as f:
                json.dump(backup, f, indent=2, default=str)
            
            logger.info(f"Backup {backup_id} exporté vers {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur export backup: {e}")
            return False
    
    def import_backup(self, import_path: str) -> Optional[str]:
        """
        Importe un backup depuis un fichier externe.
        
        Args:
            import_path: Chemin du fichier à importer
        
        Returns:
            backup_id ou None si échec
        """
        try:
            with open(import_path, 'r') as f:
                backup = json.load(f)
            
            # Générer nouveau backup_id si nécessaire
            if "backup_id" not in backup:
                backup["backup_id"] = f"imported_{int(datetime.utcnow().timestamp())}"
            
            backup_id = backup["backup_id"]
            
            # Recréer le backup
            hot_file = HOT_DIR / f"{backup_id}.json"
            self._save_to_file(hot_file, backup, compress=False)
            
            # Sauvegarder dans MongoDB
            if self.backups_collection:
                self.backups_collection.insert_one(backup.copy())
            
            logger.info(f"Backup importé avec ID: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Erreur import backup: {e}")
            return None
    
    def _calculate_checksum(self, data: Dict) -> str:
        """Calcule checksum MD5."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _save_to_file(
        self,
        file_path: Path,
        data: Dict,
        compress: bool = False
    ):
        """Sauvegarde données dans un fichier (avec compression optionnelle)."""
        try:
            json_str = json.dumps(data, indent=2, default=str)
            
            if compress:
                with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                    f.write(json_str)
            else:
                with open(file_path, 'w') as f:
                    f.write(json_str)
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde fichier {file_path}: {e}")
            raise
    
    def _load_from_file(
        self,
        file_path: Path,
        compressed: bool = False
    ) -> Optional[Dict]:
        """Charge données depuis un fichier."""
        try:
            if compressed:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement fichier {file_path}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les backups.
        
        Returns:
            Dict avec stats par tier
        """
        stats = {
            "hot": {
                "count": len(list(HOT_DIR.glob("*.json"))),
                "size_mb": sum(f.stat().st_size for f in HOT_DIR.glob("*.json")) / 1024 / 1024
            },
            "warm": {
                "count": len(list(WARM_DIR.glob("*.json.gz"))),
                "size_mb": sum(f.stat().st_size for f in WARM_DIR.glob("*.json.gz")) / 1024 / 1024
            },
            "cold": {
                "count": len(list(COLD_DIR.glob("*.json.gz"))),
                "size_mb": sum(f.stat().st_size for f in COLD_DIR.glob("*.json.gz")) / 1024 / 1024
            }
        }
        
        stats["total"] = {
            "count": sum(t["count"] for t in stats.values() if isinstance(t, dict)),
            "size_mb": sum(t["size_mb"] for t in stats.values() if isinstance(t, dict))
        }
        
        return stats

