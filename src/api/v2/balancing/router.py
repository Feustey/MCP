from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging
from .models import (
    BalancingConfig, BalancingConfigCreate, BalancingConfigUpdate,
    BalancingOperation, BalancingOperationCreate, BalancingOperationUpdate,
    BalancingStats, BalancingStatsFilter, BalancingOperationFilter,
    BalancingStrategy, BalancingStatus, BalancingOperationType
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du router
router = APIRouter(
    prefix="/balancing",
    tags=["équilibrage"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit"},
        404: {"description": "Ressource non trouvée"},
        500: {"description": "Erreur interne du serveur"}
    }
)

# Base de données temporaire en mémoire (à remplacer par une vraie base de données)
class BalancingDB:
    def __init__(self):
        self.configs: Dict[str, BalancingConfig] = {}
        self.operations: Dict[str, BalancingOperation] = {}

# Instance de la base de données
db = BalancingDB()

# Routes pour la gestion des configurations
@router.post("/configs", response_model=BalancingConfig, status_code=status.HTTP_201_CREATED)
async def create_config(config: BalancingConfigCreate):
    """Créer une nouvelle configuration d'équilibrage"""
    config_id = f"config-{uuid.uuid4().hex[:8]}"
    new_config = BalancingConfig(
        id=config_id,
        **config.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.configs[config_id] = new_config
    return new_config

@router.get("/configs", response_model=List[BalancingConfig])
async def list_configs(
    is_active: Optional[bool] = None,
    strategy: Optional[BalancingStrategy] = None
):
    """Lister les configurations d'équilibrage avec filtrage"""
    configs = list(db.configs.values())
    
    if is_active is not None:
        configs = [c for c in configs if c.is_active == is_active]
    if strategy:
        configs = [c for c in configs if c.strategy == strategy]
    
    return configs

@router.get("/configs/{config_id}", response_model=BalancingConfig)
async def get_config(config_id: str = Path(..., description="ID de la configuration")):
    """Obtenir les détails d'une configuration"""
    if config_id not in db.configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    return db.configs[config_id]

@router.put("/configs/{config_id}", response_model=BalancingConfig)
async def update_config(
    config_id: str = Path(..., description="ID de la configuration"),
    config_update: BalancingConfigUpdate = None
):
    """Mettre à jour une configuration"""
    if config_id not in db.configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    
    config = db.configs[config_id]
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_at = datetime.utcnow()
    
    return config

@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(config_id: str = Path(..., description="ID de la configuration")):
    """Supprimer une configuration"""
    if config_id not in db.configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    del db.configs[config_id]

# Routes pour la gestion des opérations
@router.post("/operations", response_model=BalancingOperation, status_code=status.HTTP_201_CREATED)
async def create_operation(operation: BalancingOperationCreate):
    """Créer une nouvelle opération d'équilibrage"""
    if operation.config_id not in db.configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    
    operation_id = f"op-{uuid.uuid4().hex[:8]}"
    new_operation = BalancingOperation(
        id=operation_id,
        **operation.dict(),
        status=BalancingStatus.PENDING,
        start_time=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db.operations[operation_id] = new_operation
    
    # Déclencher l'opération d'équilibrage de manière asynchrone
    # await execute_balancing_operation(new_operation)
    
    return new_operation

@router.get("/operations", response_model=List[BalancingOperation])
async def list_operations(
    filter: BalancingOperationFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister les opérations d'équilibrage avec filtrage"""
    operations = list(db.operations.values())
    
    if filter.config_id:
        operations = [o for o in operations if o.config_id == filter.config_id]
    if filter.type:
        operations = [o for o in operations if o.type == filter.type]
    if filter.status:
        operations = [o for o in operations if o.status == filter.status]
    if filter.source_channel:
        operations = [o for o in operations if o.source_channel == filter.source_channel]
    if filter.target_channel:
        operations = [o for o in operations if o.target_channel == filter.target_channel]
    if filter.start_time:
        operations = [o for o in operations if o.start_time >= filter.start_time]
    if filter.end_time:
        operations = [o for o in operations if o.end_time <= filter.end_time]
    
    return operations[skip:skip + limit]

@router.get("/operations/{operation_id}", response_model=BalancingOperation)
async def get_operation(operation_id: str = Path(..., description="ID de l'opération")):
    """Obtenir les détails d'une opération"""
    if operation_id not in db.operations:
        raise HTTPException(status_code=404, detail="Opération non trouvée")
    return db.operations[operation_id]

@router.put("/operations/{operation_id}", response_model=BalancingOperation)
async def update_operation(
    operation_id: str = Path(..., description="ID de l'opération"),
    operation_update: BalancingOperationUpdate = None
):
    """Mettre à jour une opération"""
    if operation_id not in db.operations:
        raise HTTPException(status_code=404, detail="Opération non trouvée")
    
    operation = db.operations[operation_id]
    update_data = operation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(operation, field, value)
    
    return operation

@router.post("/operations/{operation_id}/cancel", response_model=BalancingOperation)
async def cancel_operation(operation_id: str = Path(..., description="ID de l'opération")):
    """Annuler une opération en cours"""
    if operation_id not in db.operations:
        raise HTTPException(status_code=404, detail="Opération non trouvée")
    
    operation = db.operations[operation_id]
    if operation.status != BalancingStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Seules les opérations en cours peuvent être annulées")
    
    operation.status = BalancingStatus.CANCELLED
    operation.end_time = datetime.utcnow()
    
    return operation

# Routes pour les statistiques
@router.get("/stats", response_model=BalancingStats)
async def get_stats(filter: BalancingStatsFilter = Depends()):
    """Obtenir les statistiques d'équilibrage"""
    operations = list(db.operations.values())
    
    if filter.start_date:
        operations = [o for o in operations if o.start_time >= filter.start_date]
    if filter.end_date:
        operations = [o for o in operations if o.end_time <= filter.end_date]
    if filter.config_id:
        operations = [o for o in operations if o.config_id == filter.config_id]
    if filter.channel_id:
        operations = [o for o in operations if o.source_channel == filter.channel_id or o.target_channel == filter.channel_id]
    if filter.status:
        operations = [o for o in operations if o.status == filter.status]
    
    total_operations = len(operations)
    successful_operations = len([o for o in operations if o.status == BalancingStatus.COMPLETED])
    failed_operations = len([o for o in operations if o.status == BalancingStatus.FAILED])
    
    total_amount = sum(o.amount for o in operations if o.status == BalancingStatus.COMPLETED)
    total_fees = sum(o.actual_fee for o in operations if o.status == BalancingStatus.COMPLETED and o.actual_fee is not None)
    
    completed_operations = [o for o in operations if o.status == BalancingStatus.COMPLETED and o.actual_fee is not None]
    average_fee_rate = sum(o.fee_rate for o in completed_operations) / len(completed_operations) if completed_operations else 0
    
    start_date = min(o.start_time for o in operations) if operations else datetime.utcnow()
    end_date = max(o.end_time for o in operations if o.end_time) if operations else datetime.utcnow()
    
    return BalancingStats(
        total_operations=total_operations,
        successful_operations=successful_operations,
        failed_operations=failed_operations,
        total_amount=total_amount,
        total_fees=total_fees,
        average_fee_rate=average_fee_rate,
        start_date=start_date,
        end_date=end_date
    )

# Fonctions utilitaires
async def execute_balancing_operation(operation: BalancingOperation):
    """Exécuter une opération d'équilibrage"""
    try:
        # Mettre à jour le statut
        operation.status = BalancingStatus.RUNNING
        db.operations[operation.id] = operation
        
        # Simuler l'exécution de l'opération
        # Dans un environnement réel, cette fonction interagirait avec le nœud Lightning
        await simulate_lightning_operation(operation)
        
        # Mettre à jour le statut en cas de succès
        operation.status = BalancingStatus.COMPLETED
        operation.end_time = datetime.utcnow()
        db.operations[operation.id] = operation
        
    except Exception as e:
        # Gérer les erreurs
        operation.status = BalancingStatus.FAILED
        operation.error_message = str(e)
        operation.end_time = datetime.utcnow()
        db.operations[operation.id] = operation
        logger.error(f"Erreur lors de l'exécution de l'opération {operation.id}: {e}")

async def simulate_lightning_operation(operation: BalancingOperation):
    """Simuler une opération Lightning (à remplacer par l'intégration réelle)"""
    # Simuler un délai d'exécution
    import asyncio
    await asyncio.sleep(2)
    
    # Simuler des frais réels
    operation.actual_fee = int(operation.amount * operation.fee_rate / 1000000)
    
    # Simuler un taux de succès de 95%
    import random
    if random.random() > 0.95:
        raise Exception("Échec simulé de l'opération Lightning") 