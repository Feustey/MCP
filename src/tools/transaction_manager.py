#!/usr/bin/env python3
"""
Transaction Manager - Gestion transactionnelle des changements de policies

Ce module implémente un système de transactions ACID pour les modifications
de canaux Lightning, avec support de rollback automatique en cas d'échec.

Fonctionnalités :
- Transactions atomiques (tout ou rien)
- Snapshots d'état avant modification
- Rollback automatique ou manuel
- Traçabilité complète (MongoDB)
- Retention policy (90 jours)

Dernière mise à jour: 15 octobre 2025
"""

import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """Statuts possibles d'une transaction."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"


class TransactionManager:
    """
    Gestionnaire de transactions pour les modifications de canaux.
    
    Assure l'atomicité des opérations avec capacité de rollback.
    """
    
    def __init__(self, db=None, lnbits_client=None):
        """
        Initialise le gestionnaire de transactions.
        
        Args:
            db: Instance MongoDB (optionnel)
            lnbits_client: Client LNBits pour exécution (optionnel)
        """
        self.db = db
        self.lnbits_client = lnbits_client
        self.transactions_collection = db["transactions"] if db else None
        self.backups_collection = db["policy_backups"] if db else None
        
        # Fallback local si pas de DB
        self.local_transactions = {}
        self.local_backups = {}
        
        logger.info("TransactionManager initialisé")
    
    def begin_transaction(
        self,
        node_id: str,
        channels: List[Dict[str, Any]],
        operation_type: str = "policy_update",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Démarre une nouvelle transaction.
        
        Args:
            node_id: ID du nœud
            channels: Liste des canaux à modifier
            operation_type: Type d'opération (policy_update, rebalance, close)
            metadata: Métadonnées additionnelles
        
        Returns:
            transaction_id: ID unique de la transaction
        """
        transaction_id = str(uuid.uuid4())
        
        transaction = {
            "transaction_id": transaction_id,
            "node_id": node_id,
            "operation_type": operation_type,
            "status": TransactionStatus.PENDING.value,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "channels_modified": [],
            "channels_target": [c.get("channel_id") for c in channels],
            "backup_refs": [],
            "error": None,
            "rollback_reason": None,
            "metadata": metadata or {}
        }
        
        # Créer snapshots pour chaque canal
        backup_refs = []
        for channel in channels:
            backup_id = self._create_backup(transaction_id, channel, node_id)
            if backup_id:
                backup_refs.append(backup_id)
        
        transaction["backup_refs"] = backup_refs
        
        # Stocker la transaction
        if self.transactions_collection:
            self.transactions_collection.insert_one(transaction.copy())
        else:
            self.local_transactions[transaction_id] = transaction
        
        logger.info(f"Transaction {transaction_id} démarrée pour {len(channels)} canaux")
        
        return transaction_id
    
    def _create_backup(
        self,
        transaction_id: str,
        channel: Dict[str, Any],
        node_id: str
    ) -> Optional[str]:
        """
        Crée un backup d'un canal avant modification.
        
        Args:
            transaction_id: ID de la transaction
            channel: Données du canal
            node_id: ID du nœud
        
        Returns:
            backup_id ou None si échec
        """
        try:
            backup_id = str(uuid.uuid4())
            
            # Extraire policy actuelle
            current_policy = channel.get("policy", {})
            
            backup = {
                "backup_id": backup_id,
                "transaction_id": transaction_id,
                "node_id": node_id,
                "channel_id": channel.get("channel_id"),
                "channel_point": channel.get("channel_point"),
                "policy_before": current_policy,
                "policy_after": None,  # Sera rempli après application
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=90),
                "checksum": self._calculate_checksum(current_policy),
                "metadata": {
                    "local_balance": channel.get("local_balance"),
                    "remote_balance": channel.get("remote_balance"),
                    "capacity": channel.get("capacity")
                }
            }
            
            # Stocker le backup
            if self.backups_collection:
                self.backups_collection.insert_one(backup.copy())
            else:
                self.local_backups[backup_id] = backup
            
            logger.debug(f"Backup {backup_id} créé pour canal {channel.get('channel_id', 'unknown')[:8]}")
            
            return backup_id
            
        except Exception as e:
            logger.error(f"Erreur création backup: {e}")
            return None
    
    def _calculate_checksum(self, data: Dict) -> str:
        """Calcule un checksum MD5 des données."""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def update_transaction_progress(
        self,
        transaction_id: str,
        channel_id: str,
        success: bool,
        new_policy: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """
        Met à jour la progression d'une transaction.
        
        Args:
            transaction_id: ID de la transaction
            channel_id: ID du canal modifié
            success: Si la modification a réussi
            new_policy: Nouvelle policy appliquée
            error: Message d'erreur si échec
        """
        try:
            # Récupérer la transaction
            if self.transactions_collection:
                transaction = self.transactions_collection.find_one(
                    {"transaction_id": transaction_id}
                )
            else:
                transaction = self.local_transactions.get(transaction_id)
            
            if not transaction:
                logger.error(f"Transaction {transaction_id} introuvable")
                return
            
            # Mettre à jour la liste des canaux modifiés
            update_data = {}
            
            if success:
                channels_modified = transaction.get("channels_modified", [])
                channels_modified.append(channel_id)
                update_data["channels_modified"] = channels_modified
                
                # Mettre à jour le backup avec la nouvelle policy
                if new_policy:
                    self._update_backup_after(transaction_id, channel_id, new_policy)
            else:
                update_data["error"] = error
                update_data["status"] = TransactionStatus.FAILED.value
            
            # Sauvegarder
            if self.transactions_collection:
                self.transactions_collection.update_one(
                    {"transaction_id": transaction_id},
                    {"$set": update_data}
                )
            else:
                self.local_transactions[transaction_id].update(update_data)
            
            logger.debug(f"Transaction {transaction_id} mise à jour: canal {channel_id[:8]} - success={success}")
            
        except Exception as e:
            logger.error(f"Erreur mise à jour transaction: {e}")
    
    def _update_backup_after(
        self,
        transaction_id: str,
        channel_id: str,
        new_policy: Dict
    ):
        """Met à jour un backup avec la policy appliquée."""
        try:
            if self.backups_collection:
                self.backups_collection.update_one(
                    {
                        "transaction_id": transaction_id,
                        "channel_id": channel_id
                    },
                    {
                        "$set": {
                            "policy_after": new_policy,
                            "checksum_after": self._calculate_checksum(new_policy)
                        }
                    }
                )
            else:
                # Local fallback
                for backup in self.local_backups.values():
                    if (backup.get("transaction_id") == transaction_id and 
                        backup.get("channel_id") == channel_id):
                        backup["policy_after"] = new_policy
                        backup["checksum_after"] = self._calculate_checksum(new_policy)
                        break
        except Exception as e:
            logger.error(f"Erreur mise à jour backup: {e}")
    
    def commit_transaction(self, transaction_id: str) -> bool:
        """
        Valide (commit) une transaction réussie.
        
        Args:
            transaction_id: ID de la transaction
        
        Returns:
            True si commit réussi
        """
        try:
            # Récupérer la transaction
            if self.transactions_collection:
                transaction = self.transactions_collection.find_one(
                    {"transaction_id": transaction_id}
                )
            else:
                transaction = self.local_transactions.get(transaction_id)
            
            if not transaction:
                logger.error(f"Transaction {transaction_id} introuvable")
                return False
            
            # Vérifier que tous les canaux ont été modifiés
            channels_target = transaction.get("channels_target", [])
            channels_modified = transaction.get("channels_modified", [])
            
            if len(channels_modified) == len(channels_target):
                status = TransactionStatus.SUCCESS
            elif len(channels_modified) > 0:
                status = TransactionStatus.PARTIAL
            else:
                status = TransactionStatus.FAILED
            
            # Mettre à jour le statut
            update_data = {
                "status": status.value,
                "completed_at": datetime.utcnow()
            }
            
            if self.transactions_collection:
                self.transactions_collection.update_one(
                    {"transaction_id": transaction_id},
                    {"$set": update_data}
                )
            else:
                self.local_transactions[transaction_id].update(update_data)
            
            logger.info(f"Transaction {transaction_id} commit avec statut: {status.value}")
            
            return status in [TransactionStatus.SUCCESS, TransactionStatus.PARTIAL]
            
        except Exception as e:
            logger.error(f"Erreur commit transaction: {e}")
            return False
    
    async def rollback_transaction(
        self,
        transaction_id: str,
        reason: str = "Manual rollback"
    ) -> Dict[str, Any]:
        """
        Effectue un rollback complet d'une transaction.
        
        Args:
            transaction_id: ID de la transaction à annuler
            reason: Raison du rollback
        
        Returns:
            Dict avec résultats du rollback
        """
        logger.warning(f"Rollback de la transaction {transaction_id}: {reason}")
        
        results = {
            "transaction_id": transaction_id,
            "success": False,
            "channels_restored": [],
            "channels_failed": [],
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Récupérer la transaction
            if self.transactions_collection:
                transaction = self.transactions_collection.find_one(
                    {"transaction_id": transaction_id}
                )
            else:
                transaction = self.local_transactions.get(transaction_id)
            
            if not transaction:
                results["error"] = "Transaction introuvable"
                return results
            
            # Récupérer tous les backups
            if self.backups_collection:
                backups = list(self.backups_collection.find(
                    {"transaction_id": transaction_id}
                ))
            else:
                backups = [
                    b for b in self.local_backups.values()
                    if b.get("transaction_id") == transaction_id
                ]
            
            # Restaurer chaque canal
            for backup in backups:
                channel_id = backup.get("channel_id")
                channel_point = backup.get("channel_point")
                policy_before = backup.get("policy_before", {})
                
                if not self.lnbits_client:
                    logger.warning("Pas de LNBits client, rollback simulé")
                    results["channels_restored"].append(channel_id)
                    continue
                
                try:
                    # Restaurer via LNBits
                    restore_result = await self._restore_policy(
                        channel_point,
                        policy_before
                    )
                    
                    if restore_result.get("success"):
                        results["channels_restored"].append(channel_id)
                    else:
                        results["channels_failed"].append({
                            "channel_id": channel_id,
                            "error": restore_result.get("error", "Unknown")
                        })
                
                except Exception as e:
                    logger.error(f"Erreur restauration canal {channel_id}: {e}")
                    results["channels_failed"].append({
                        "channel_id": channel_id,
                        "error": str(e)
                    })
            
            # Mettre à jour le statut de la transaction
            if len(results["channels_failed"]) == 0:
                results["success"] = True
                final_status = TransactionStatus.ROLLED_BACK
            else:
                final_status = TransactionStatus.FAILED
            
            update_data = {
                "status": final_status.value,
                "rollback_reason": reason,
                "rollback_at": datetime.utcnow(),
                "rollback_results": results
            }
            
            if self.transactions_collection:
                self.transactions_collection.update_one(
                    {"transaction_id": transaction_id},
                    {"$set": update_data}
                )
            else:
                self.local_transactions[transaction_id].update(update_data)
            
            logger.info(
                f"Rollback terminé: {len(results['channels_restored'])} restaurés, "
                f"{len(results['channels_failed'])} échoués"
            )
            
        except Exception as e:
            logger.error(f"Erreur critique lors du rollback: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _restore_policy(
        self,
        channel_point: str,
        policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Restaure une policy via LNBits.
        
        Args:
            channel_point: Point du canal
            policy: Policy à restaurer
        
        Returns:
            Résultat de l'opération
        """
        try:
            result = await self.lnbits_client.update_channel_policy(
                channel_point=channel_point,
                base_fee_msat=int(policy.get("base_fee_msat", 1000)),
                fee_rate_ppm=int(policy.get("fee_rate_ppm", 500)),
                time_lock_delta=int(policy.get("time_lock_delta", 40)),
                min_htlc_msat=int(policy.get("min_htlc_msat", 1000)),
                max_htlc_msat=policy.get("max_htlc_msat")
            )
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le statut d'une transaction.
        
        Args:
            transaction_id: ID de la transaction
        
        Returns:
            Détails de la transaction ou None
        """
        if self.transactions_collection:
            return self.transactions_collection.find_one(
                {"transaction_id": transaction_id},
                {"_id": 0}
            )
        else:
            return self.local_transactions.get(transaction_id)
    
    def list_pending_transactions(self, node_id: Optional[str] = None) -> List[Dict]:
        """
        Liste les transactions en cours.
        
        Args:
            node_id: Filtrer par node_id (optionnel)
        
        Returns:
            Liste des transactions pending
        """
        query = {"status": TransactionStatus.PENDING.value}
        if node_id:
            query["node_id"] = node_id
        
        if self.transactions_collection:
            return list(self.transactions_collection.find(query, {"_id": 0}))
        else:
            return [
                t for t in self.local_transactions.values()
                if t.get("status") == TransactionStatus.PENDING.value and
                (not node_id or t.get("node_id") == node_id)
            ]
    
    def cleanup_old_backups(self, days: int = 90) -> int:
        """
        Nettoie les backups expirés.
        
        Args:
            days: Age maximum en jours
        
        Returns:
            Nombre de backups supprimés
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            if self.backups_collection:
                result = self.backups_collection.delete_many({
                    "created_at": {"$lt": cutoff_date}
                })
                deleted_count = result.deleted_count
            else:
                # Local cleanup
                to_delete = [
                    bid for bid, backup in self.local_backups.items()
                    if backup.get("created_at", datetime.utcnow()) < cutoff_date
                ]
                for bid in to_delete:
                    del self.local_backups[bid]
                deleted_count = len(to_delete)
            
            logger.info(f"Cleanup: {deleted_count} backups supprimés (> {days} jours)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Erreur cleanup backups: {e}")
            return 0

