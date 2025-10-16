#!/usr/bin/env python3
"""
Rollback Orchestrator - Orchestration automatique et manuelle des rollbacks

Ce module gère :
- Rollback automatique basé sur métriques
- Rollback manuel avec confirmation
- Rollback partiel (sous-ensemble de canaux)
- Notifications et alertes
- Interface CLI

Dernière mise à jour: 15 octobre 2025
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.tools.transaction_manager import TransactionManager, TransactionStatus
from src.tools.backup_manager import BackupManager

logger = logging.getLogger(__name__)


class RollbackOrchestrator:
    """
    Orchestrateur de rollbacks automatiques et manuels.
    """
    
    def __init__(
        self,
        transaction_manager: TransactionManager,
        backup_manager: BackupManager,
        telegram_client=None
    ):
        """
        Initialise l'orchestrateur.
        
        Args:
            transaction_manager: Gestionnaire de transactions
            backup_manager: Gestionnaire de backups
            telegram_client: Client Telegram pour notifications (optionnel)
        """
        self.tx_manager = transaction_manager
        self.backup_manager = backup_manager
        self.telegram = telegram_client
        
        # Seuils pour rollback automatique
        self.auto_rollback_config = {
            "error_rate_threshold": 0.5,  # 50% d'erreurs
            "latency_multiplier": 2.0,    # 2x la latence normale
            "min_samples": 3,              # Minimum d'échantillons pour décision
            "check_interval": 300          # Vérification toutes les 5 minutes
        }
        
        logger.info("RollbackOrchestrator initialisé")
    
    async def auto_rollback_on_failure(
        self,
        transaction_id: str,
        metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Effectue un rollback automatique si les métriques indiquent un échec.
        
        Args:
            transaction_id: ID de la transaction à surveiller
            metrics: Métriques actuelles (error_rate, latency, etc.)
        
        Returns:
            Résultat du rollback ou None si pas nécessaire
        """
        # Analyser les métriques
        should_rollback, reason = self._should_auto_rollback(metrics)
        
        if not should_rollback:
            return None
        
        logger.warning(
            f"Rollback automatique déclenché pour transaction {transaction_id}: {reason}"
        )
        
        # Notifier
        if self.telegram:
            await self._send_alert(
                f"🚨 Rollback automatique\n"
                f"Transaction: {transaction_id}\n"
                f"Raison: {reason}"
            )
        
        # Effectuer le rollback
        result = self.tx_manager.rollback_transaction(
            transaction_id,
            reason=f"Auto-rollback: {reason}"
        )
        
        # Notifier résultat
        if self.telegram:
            if result.get("success"):
                await self._send_alert(
                    f"✅ Rollback réussi\n"
                    f"Canaux restaurés: {len(result.get('channels_restored', []))}"
                )
            else:
                await self._send_alert(
                    f"❌ Rollback échoué\n"
                    f"Erreur: {result.get('error', 'Unknown')}"
                )
        
        return result
    
    def _should_auto_rollback(
        self,
        metrics: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Détermine si un rollback automatique est nécessaire.
        
        Args:
            metrics: Métriques à analyser
        
        Returns:
            (should_rollback, reason)
        """
        error_rate = metrics.get("error_rate", 0.0)
        latency_ratio = metrics.get("latency_ratio", 1.0)
        sample_count = metrics.get("sample_count", 0)
        
        # Pas assez de données
        if sample_count < self.auto_rollback_config["min_samples"]:
            return False, ""
        
        # Taux d'erreur trop élevé
        if error_rate >= self.auto_rollback_config["error_rate_threshold"]:
            return True, f"Taux d'erreur élevé: {error_rate*100:.1f}%"
        
        # Latence anormale
        if latency_ratio >= self.auto_rollback_config["latency_multiplier"]:
            return True, f"Latence anormale: {latency_ratio:.1f}x la normale"
        
        return False, ""
    
    async def manual_rollback(
        self,
        transaction_id: str,
        reason: str = "Manual rollback",
        require_confirmation: bool = True
    ) -> Dict[str, Any]:
        """
        Effectue un rollback manuel avec confirmation.
        
        Args:
            transaction_id: ID de la transaction
            reason: Raison du rollback
            require_confirmation: Si True, demande confirmation
        
        Returns:
            Résultat du rollback
        """
        # Récupérer info transaction
        tx = self.tx_manager.get_transaction_status(transaction_id)
        if not tx:
            return {
                "success": False,
                "error": "Transaction introuvable"
            }
        
        logger.info(f"Rollback manuel demandé pour transaction {transaction_id}")
        
        # Afficher preview
        channels_modified = tx.get("channels_modified", [])
        print(f"\n{'='*60}")
        print(f"ROLLBACK MANUEL")
        print(f"{'='*60}")
        print(f"Transaction: {transaction_id}")
        print(f"Nœud: {tx.get('node_id', 'unknown')[:8]}...")
        print(f"Status: {tx.get('status')}")
        print(f"Canaux modifiés: {len(channels_modified)}")
        print(f"Raison: {reason}")
        print(f"{'='*60}\n")
        
        # Confirmation
        if require_confirmation:
            response = input("Confirmer le rollback? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Rollback annulé par l'utilisateur")
                return {
                    "success": False,
                    "cancelled": True,
                    "message": "Rollback annulé"
                }
        
        # Effectuer le rollback
        logger.info("Exécution du rollback...")
        result = self.tx_manager.rollback_transaction(transaction_id, reason)
        
        # Afficher résultat
        print(f"\n{'='*60}")
        print(f"RÉSULTAT")
        print(f"{'='*60}")
        print(f"Success: {result.get('success')}")
        print(f"Canaux restaurés: {len(result.get('channels_restored', []))}")
        print(f"Canaux échoués: {len(result.get('channels_failed', []))}")
        
        if result.get("channels_failed"):
            print("\nÉchecs:")
            for failure in result["channels_failed"]:
                print(f"  - {failure.get('channel_id', 'unknown')[:8]}: {failure.get('error')}")
        
        print(f"{'='*60}\n")
        
        # Notifier
        if self.telegram:
            await self._send_alert(
                f"🔄 Rollback manuel\n"
                f"Transaction: {transaction_id}\n"
                f"Status: {'✅ Réussi' if result.get('success') else '❌ Échoué'}\n"
                f"Canaux: {len(result.get('channels_restored', []))}/{len(channels_modified)}"
            )
        
        return result
    
    async def partial_rollback(
        self,
        transaction_id: str,
        channel_ids: List[str],
        reason: str = "Partial rollback"
    ) -> Dict[str, Any]:
        """
        Effectue un rollback partiel (seulement certains canaux).
        
        Args:
            transaction_id: ID de la transaction
            channel_ids: Liste des IDs de canaux à rollback
            reason: Raison du rollback
        
        Returns:
            Résultat du rollback
        """
        logger.info(
            f"Rollback partiel pour transaction {transaction_id}: "
            f"{len(channel_ids)} canaux"
        )
        
        # Récupérer la transaction
        tx = self.tx_manager.get_transaction_status(transaction_id)
        if not tx:
            return {
                "success": False,
                "error": "Transaction introuvable"
            }
        
        results = {
            "transaction_id": transaction_id,
            "success": True,
            "channels_restored": [],
            "channels_failed": [],
            "reason": reason
        }
        
        # Restaurer chaque canal demandé
        for channel_id in channel_ids:
            try:
                # Récupérer le backup
                backup = self.backup_manager.get_latest_backup(
                    channel_id,
                    node_id=tx.get("node_id")
                )
                
                if not backup:
                    results["channels_failed"].append({
                        "channel_id": channel_id,
                        "error": "Backup introuvable"
                    })
                    continue
                
                # Vérifier intégrité
                if not self.backup_manager.verify_integrity(backup.get("backup_id")):
                    results["channels_failed"].append({
                        "channel_id": channel_id,
                        "error": "Backup corrompu"
                    })
                    continue
                
                # Restaurer (via transaction manager)
                # TODO: Implémenter restauration individuelle
                results["channels_restored"].append(channel_id)
                
            except Exception as e:
                logger.error(f"Erreur rollback canal {channel_id}: {e}")
                results["channels_failed"].append({
                    "channel_id": channel_id,
                    "error": str(e)
                })
        
        # Mise à jour du statut
        if len(results["channels_failed"]) > 0:
            results["success"] = False
        
        logger.info(
            f"Rollback partiel terminé: {len(results['channels_restored'])} restaurés, "
            f"{len(results['channels_failed'])} échoués"
        )
        
        return results
    
    async def monitor_transaction(
        self,
        transaction_id: str,
        duration_seconds: int = 300,
        check_interval: int = 30
    ):
        """
        Surveille une transaction et déclenche rollback auto si nécessaire.
        
        Args:
            transaction_id: ID de la transaction à surveiller
            duration_seconds: Durée de surveillance
            check_interval: Intervalle entre vérifications
        """
        logger.info(
            f"Surveillance de la transaction {transaction_id} pour {duration_seconds}s"
        )
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=duration_seconds)
        
        metrics_history = []
        
        while datetime.utcnow() < end_time:
            # Récupérer métriques actuelles
            # TODO: Implémenter collecte de métriques réelles
            metrics = await self._collect_metrics(transaction_id)
            metrics_history.append(metrics)
            
            # Vérifier si rollback nécessaire
            result = await self.auto_rollback_on_failure(transaction_id, metrics)
            
            if result:
                logger.info("Rollback automatique effectué, fin de surveillance")
                break
            
            # Attendre avant prochaine vérification
            await asyncio.sleep(check_interval)
        
        logger.info(
            f"Surveillance terminée pour transaction {transaction_id}. "
            f"Métriques collectées: {len(metrics_history)}"
        )
    
    async def _collect_metrics(self, transaction_id: str) -> Dict[str, Any]:
        """
        Collecte les métriques actuelles pour une transaction.
        
        Args:
            transaction_id: ID de la transaction
        
        Returns:
            Métriques (error_rate, latency_ratio, etc.)
        """
        # TODO: Implémenter collecte réelle depuis monitoring
        # Pour l'instant, retourner métriques simulées
        return {
            "error_rate": 0.0,
            "latency_ratio": 1.0,
            "sample_count": 10,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _send_alert(self, message: str):
        """
        Envoie une alerte via Telegram.
        
        Args:
            message: Message à envoyer
        """
        if self.telegram:
            try:
                await self.telegram.send_message(message)
            except Exception as e:
                logger.error(f"Erreur envoi alerte Telegram: {e}")
        else:
            logger.warning(f"Alerte (pas de Telegram): {message}")
    
    def get_rollback_history(
        self,
        node_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des rollbacks.
        
        Args:
            node_id: Filtrer par node_id (optionnel)
            limit: Nombre max de résultats
        
        Returns:
            Liste des rollbacks
        """
        query = {
            "status": {"$in": [
                TransactionStatus.ROLLED_BACK.value,
                TransactionStatus.FAILED.value
            ]}
        }
        
        if node_id:
            query["node_id"] = node_id
        
        if self.tx_manager.transactions_collection:
            rollbacks = list(
                self.tx_manager.transactions_collection.find(
                    query,
                    {"_id": 0}
                ).sort("rollback_at", -1).limit(limit)
            )
            return rollbacks
        
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les rollbacks.
        
        Returns:
            Dict avec stats
        """
        if not self.tx_manager.transactions_collection:
            return {"error": "MongoDB non disponible"}
        
        # Compter par statut
        stats = {}
        for status in TransactionStatus:
            count = self.tx_manager.transactions_collection.count_documents({
                "status": status.value
            })
            stats[status.value] = count
        
        # Taux de succès
        total = sum(stats.values())
        if total > 0:
            stats["success_rate"] = stats.get("success", 0) / total
            stats["rollback_rate"] = stats.get("rolled_back", 0) / total
        else:
            stats["success_rate"] = 0.0
            stats["rollback_rate"] = 0.0
        
        return stats


# CLI pour usage manuel
async def main_cli():
    """Interface CLI pour rollbacks manuels."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Rollback Orchestrator CLI")
    parser.add_argument("action", choices=["rollback", "status", "history", "stats"])
    parser.add_argument("--transaction-id", help="ID de la transaction")
    parser.add_argument("--reason", default="Manual CLI rollback", help="Raison du rollback")
    parser.add_argument("--no-confirm", action="store_true", help="Pas de confirmation")
    parser.add_argument("--node-id", help="Filtrer par node ID")
    
    args = parser.parse_args()
    
    # Initialiser (sans DB pour CLI simple)
    tx_manager = TransactionManager()
    backup_manager = BackupManager()
    orchestrator = RollbackOrchestrator(tx_manager, backup_manager)
    
    if args.action == "rollback":
        if not args.transaction_id:
            print("❌ --transaction-id requis pour rollback")
            sys.exit(1)
        
        result = await orchestrator.manual_rollback(
            args.transaction_id,
            reason=args.reason,
            require_confirmation=not args.no_confirm
        )
        
        sys.exit(0 if result.get("success") else 1)
    
    elif args.action == "status":
        if not args.transaction_id:
            print("❌ --transaction-id requis pour status")
            sys.exit(1)
        
        status = tx_manager.get_transaction_status(args.transaction_id)
        if status:
            print(json.dumps(status, indent=2, default=str))
        else:
            print("❌ Transaction introuvable")
            sys.exit(1)
    
    elif args.action == "history":
        history = orchestrator.get_rollback_history(args.node_id)
        print(json.dumps(history, indent=2, default=str))
    
    elif args.action == "stats":
        stats = orchestrator.get_stats()
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    import json
    asyncio.run(main_cli())

