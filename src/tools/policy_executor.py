"""
Policy Executor - Exécution sécurisée des policies Lightning
Dernière mise à jour: 12 octobre 2025
Version: 1.0.0

Gère l'exécution sécurisée des policies avec:
- Validation pré-application
- Backup automatique
- Dry-run simulation
- Rollback en cas d'échec
- Notifications
- Audit complet
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import asyncio

import structlog

from src.clients.lnbits_client_v2 import LNBitsClientV2
from src.optimizers.policy_validator import PolicyValidator, ValidationResult, ValidationError
from src.tools.rollback_manager import RollbackManager, BackupEntry

logger = structlog.get_logger(__name__)


class ExecutionResult(Enum):
    """Résultats d'exécution possibles"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"
    DRY_RUN = "dry_run"


@dataclass
class ExecutionContext:
    """Contexte d'exécution d'une policy"""
    channel_id: str
    node_id: str
    new_policy: Dict[str, Any]
    current_policy: Optional[Dict[str, Any]]
    reason: str
    dry_run: bool
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ExecutionReport:
    """Rapport d'exécution d'une policy"""
    execution_id: str
    context: ExecutionContext
    validation_result: ValidationResult
    validation_errors: List[ValidationError]
    execution_result: ExecutionResult
    backup_id: Optional[str]
    execution_time_ms: float
    error_message: Optional[str] = None
    rollback_performed: bool = False
    notifications_sent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "execution_id": self.execution_id,
            "context": self.context.to_dict(),
            "validation": {
                "result": self.validation_result.value,
                "errors": [
                    {
                        "field": e.field,
                        "message": e.message,
                        "severity": e.severity.value
                    }
                    for e in self.validation_errors
                ]
            },
            "execution": {
                "result": self.execution_result.value,
                "time_ms": self.execution_time_ms,
                "error": self.error_message
            },
            "backup_id": self.backup_id,
            "rollback_performed": self.rollback_performed,
            "notifications_sent": self.notifications_sent
        }


class PolicyExecutor:
    """
    Exécuteur de policies Lightning
    
    Workflow:
    1. Validation de la policy
    2. Backup de la policy actuelle
    3. Simulation (si dry-run)
    4. Application de la nouvelle policy
    5. Vérification post-application
    6. Rollback si échec
    7. Notifications
    8. Audit log
    """
    
    def __init__(
        self,
        lnbits_client: LNBitsClientV2,
        validator: PolicyValidator,
        rollback_manager: RollbackManager,
        dry_run: bool = True,
        require_manual_approval: bool = True,
        storage_backend: Optional[Any] = None
    ):
        """
        Initialise l'exécuteur de policies
        
        Args:
            lnbits_client: Client LNBits pour exécution
            validator: Validateur de policies
            rollback_manager: Gestionnaire de rollback
            dry_run: Mode simulation (aucune action réelle)
            require_manual_approval: Requiert confirmation manuelle
            storage_backend: Backend MongoDB pour audit
        """
        self.client = lnbits_client
        self.validator = validator
        self.rollback = rollback_manager
        self.dry_run = dry_run
        self.require_manual_approval = require_manual_approval
        self.storage = storage_backend
        
        # Stats d'exécution
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "rolled_back": 0,
            "dry_run": 0
        }
        
        logger.info(
            "policy_executor_initialized",
            dry_run=dry_run,
            require_approval=require_manual_approval
        )
    
    async def execute_policy(
        self,
        channel_id: str,
        node_id: str,
        new_policy: Dict[str, Any],
        reason: str = "Optimization",
        force: bool = False,
        channel_info: Optional[Dict[str, Any]] = None
    ) -> ExecutionReport:
        """
        Exécute une policy sur un canal
        
        Args:
            channel_id: ID du canal
            node_id: ID du nœud
            new_policy: Nouvelle policy à appliquer
            reason: Raison du changement
            force: Forcer l'exécution (skip validation warnings)
            channel_info: Informations du canal (pour validation)
            
        Returns:
            Rapport d'exécution complet
        """
        start_time = datetime.now()
        execution_id = self._generate_execution_id(channel_id)
        
        # Créer le contexte
        context = ExecutionContext(
            channel_id=channel_id,
            node_id=node_id,
            new_policy=new_policy,
            current_policy=None,  # Sera récupérée
            reason=reason,
            dry_run=self.dry_run,
            timestamp=start_time
        )
        
        logger.info(
            "policy_execution_started",
            execution_id=execution_id,
            channel_id=channel_id,
            dry_run=self.dry_run
        )
        
        try:
            # 1. Récupérer la policy actuelle
            current_policy = await self.client.get_channel_policy(channel_id)
            context.current_policy = current_policy
            
            # 2. Validation
            validation_result, validation_errors = self.validator.validate_policy(
                channel_id=channel_id,
                new_policy=new_policy,
                current_policy=current_policy,
                node_pubkey=node_id,
                channel_info=channel_info
            )
            
            logger.info(
                "policy_validated",
                execution_id=execution_id,
                result=validation_result.value,
                error_count=len(validation_errors)
            )
            
            # Si bloqué ou invalide (et pas forcé), skip
            if validation_result in [ValidationResult.BLOCKED, ValidationResult.INVALID] and not force:
                report = self._create_report(
                    execution_id, context, validation_result, validation_errors,
                    ExecutionResult.SKIPPED, start_time,
                    error_message="Validation failed"
                )
                self._stats["skipped"] += 1
                return report
            
            # 3. Backup de la policy actuelle
            backup_id = None
            if not self.dry_run:
                backup_id = await self.rollback.create_backup(
                    channel_id=channel_id,
                    current_policy=current_policy,
                    reason=f"Before {reason}"
                )
                logger.info("policy_backed_up", backup_id=backup_id)
            
            # 4. Approval manuelle si requise
            if self.require_manual_approval and not self.dry_run:
                logger.info(
                    "manual_approval_required",
                    execution_id=execution_id,
                    channel_id=channel_id
                )
                # TODO: Implémenter système d'approval
                # Pour l'instant, on skip
                report = self._create_report(
                    execution_id, context, validation_result, validation_errors,
                    ExecutionResult.SKIPPED, start_time, backup_id=backup_id,
                    error_message="Manual approval required"
                )
                self._stats["skipped"] += 1
                return report
            
            # 5. Application de la policy
            if self.dry_run:
                # Mode simulation
                logger.info(
                    "policy_execution_simulated",
                    execution_id=execution_id,
                    channel_id=channel_id,
                    new_policy=new_policy
                )
                report = self._create_report(
                    execution_id, context, validation_result, validation_errors,
                    ExecutionResult.DRY_RUN, start_time, backup_id=backup_id
                )
                self._stats["dry_run"] += 1
                return report
            else:
                # Exécution réelle
                result = await self.client.update_channel_policy(
                    channel_id=channel_id,
                    base_fee_msat=new_policy.get("base_fee_msat"),
                    fee_rate_ppm=new_policy.get("fee_rate_ppm"),
                    time_lock_delta=new_policy.get("time_lock_delta"),
                    min_htlc_msat=new_policy.get("min_htlc_msat"),
                    max_htlc_msat=new_policy.get("max_htlc_msat")
                )
                
                logger.info(
                    "policy_applied",
                    execution_id=execution_id,
                    channel_id=channel_id,
                    result=result
                )
                
                # 6. Vérification post-application
                await asyncio.sleep(2)  # Attendre propagation
                new_policy_check = await self.client.get_channel_policy(channel_id)
                
                # Vérifier que la policy a bien été appliquée
                if not self._verify_policy_applied(new_policy, new_policy_check):
                    logger.error(
                        "policy_verification_failed",
                        execution_id=execution_id,
                        expected=new_policy,
                        actual=new_policy_check
                    )
                    
                    # Rollback
                    if backup_id:
                        await self.rollback.restore_backup(backup_id)
                        logger.info("policy_rolled_back", backup_id=backup_id)
                        
                        report = self._create_report(
                            execution_id, context, validation_result, validation_errors,
                            ExecutionResult.ROLLED_BACK, start_time, backup_id=backup_id,
                            error_message="Policy verification failed",
                            rollback_performed=True
                        )
                        self._stats["rolled_back"] += 1
                        return report
                
                # Enregistrer le changement
                self.validator.record_change(channel_id)
                
                # Rapport de succès
                report = self._create_report(
                    execution_id, context, validation_result, validation_errors,
                    ExecutionResult.SUCCESS, start_time, backup_id=backup_id
                )
                self._stats["successful"] += 1
                return report
                
        except Exception as e:
            logger.error(
                "policy_execution_failed",
                execution_id=execution_id,
                channel_id=channel_id,
                error=str(e)
            )
            
            # Tentative de rollback si backup existe
            rollback_performed = False
            if backup_id:
                try:
                    await self.rollback.restore_backup(backup_id)
                    rollback_performed = True
                    logger.info("policy_rolled_back_after_error", backup_id=backup_id)
                except Exception as rollback_error:
                    logger.error("rollback_failed", error=str(rollback_error))
            
            report = self._create_report(
                execution_id, context,
                ValidationResult.INVALID, [],
                ExecutionResult.FAILED, start_time,
                backup_id=backup_id,
                error_message=str(e),
                rollback_performed=rollback_performed
            )
            self._stats["failed"] += 1
            return report
        
        finally:
            # Sauvegarder le rapport dans MongoDB
            if self.storage:
                try:
                    await self._store_report(report)
                except Exception as e:
                    logger.error("failed_to_store_report", error=str(e))
    
    def _generate_execution_id(self, channel_id: str) -> str:
        """Génère un ID unique pour l'exécution"""
        import hashlib
        data = f"{channel_id}{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _verify_policy_applied(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> bool:
        """Vérifie que la policy a été correctement appliquée"""
        # Vérifier les champs critiques
        critical_fields = ["base_fee_msat", "fee_rate_ppm"]
        
        for field in critical_fields:
            if field in expected:
                if expected[field] != actual.get(field):
                    logger.warning(
                        "policy_field_mismatch",
                        field=field,
                        expected=expected[field],
                        actual=actual.get(field)
                    )
                    return False
        
        return True
    
    def _create_report(
        self,
        execution_id: str,
        context: ExecutionContext,
        validation_result: ValidationResult,
        validation_errors: List[ValidationError],
        execution_result: ExecutionResult,
        start_time: datetime,
        backup_id: Optional[str] = None,
        error_message: Optional[str] = None,
        rollback_performed: bool = False
    ) -> ExecutionReport:
        """Crée un rapport d'exécution"""
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return ExecutionReport(
            execution_id=execution_id,
            context=context,
            validation_result=validation_result,
            validation_errors=validation_errors,
            execution_result=execution_result,
            backup_id=backup_id,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            rollback_performed=rollback_performed,
            notifications_sent=False  # TODO: Implémenter notifications
        )
    
    async def _store_report(self, report: ExecutionReport):
        """Stocke le rapport dans MongoDB"""
        if not self.storage:
            return
        
        await self.storage.insert_one({
            "type": "policy_execution",
            **report.to_dict()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exécution"""
        total = self._stats["total_executions"]
        return {
            **self._stats,
            "success_rate": self._stats["successful"] / total if total > 0 else 0,
            "rollback_rate": self._stats["rolled_back"] / total if total > 0 else 0
        }
    
    async def batch_execute_policies(
        self,
        policies: List[Dict[str, Any]],
        max_concurrent: int = 3,
        stop_on_error: bool = False
    ) -> List[ExecutionReport]:
        """
        Exécute plusieurs policies en batch
        
        Args:
            policies: Liste de policies à appliquer
            max_concurrent: Nombre max d'exécutions simultanées
            stop_on_error: Arrêter si une exécution échoue
            
        Returns:
            Liste des rapports d'exécution
        """
        logger.info(
            "batch_execution_started",
            count=len(policies),
            max_concurrent=max_concurrent
        )
        
        reports = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(policy: Dict[str, Any]):
            async with semaphore:
                report = await self.execute_policy(
                    channel_id=policy["channel_id"],
                    node_id=policy["node_id"],
                    new_policy=policy["new_policy"],
                    reason=policy.get("reason", "Batch optimization"),
                    channel_info=policy.get("channel_info")
                )
                
                if stop_on_error and report.execution_result == ExecutionResult.FAILED:
                    raise Exception(f"Execution failed for channel {policy['channel_id']}")
                
                return report
        
        # Exécuter en parallèle avec limite de concurrence
        tasks = [execute_with_semaphore(policy) for policy in policies]
        reports = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrer les exceptions
        valid_reports = [r for r in reports if isinstance(r, ExecutionReport)]
        
        logger.info(
            "batch_execution_completed",
            total=len(policies),
            successful=len([r for r in valid_reports if r.execution_result == ExecutionResult.SUCCESS]),
            failed=len([r for r in valid_reports if r.execution_result == ExecutionResult.FAILED])
        )
        
        return valid_reports

