"""
API pour le contrôle et la supervision du pilotage des frais.
Fournit des endpoints REST pour déclencher des optimisations, consulter l'historique
et contrôler les rollbacks.

Dernière mise à jour: 10 mai 2025
"""

import logging
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter

# Ajouter le répertoire parent au path pour les imports relatifs
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent
sys.path.append(str(root_dir))

from scripts.fee_optimizer_scheduler import FeeOptimizerScheduler
from src.automation_manager import AutomationManager
from src.mongo_operations import MongoOperations
from src.redis_operations import RedisOperations
from src.auth.auth_utils import get_current_user
from app.auth import verify_jwt_and_get_tenant

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fee_optimizer_api")

# Créer le router FastAPI
router = APIRouter(
    prefix="/api/v1/fee-optimizer",
    tags=["Fee Optimizer"],
    responses={404: {"description": "Not found"}},
)

# Modèles Pydantic pour les requêtes et réponses
class FeeUpdateResponse(BaseModel):
    success: bool
    channel_id: str
    old_base_fee: int
    old_fee_rate: int
    new_base_fee: int
    new_fee_rate: int
    timestamp: str
    reason: Optional[str] = None
    status: Optional[str] = None
    node_id: Optional[str] = None

class FeeOptimizationRequest(BaseModel):
    node_ids: Optional[List[str]] = None
    channel_ids: Optional[List[str]] = None
    dry_run: bool = True
    max_updates: Optional[int] = None
    override_confidence: Optional[float] = None

class FeeOptimizationResponse(BaseModel):
    success: bool
    message: str
    updates: List[FeeUpdateResponse] = []
    timestamp: str
    job_id: Optional[str] = None

class RollbackRequest(BaseModel):
    updates_id: str
    reason: Optional[str] = None

class RollbackResponse(BaseModel):
    success: bool
    message: str
    rollback_count: int
    timestamp: str

# Injection de dépendances
async def get_mongo_ops():
    return MongoOperations()

async def get_redis_ops():
    return RedisOperations()

async def get_fee_optimizer():
    return FeeOptimizerScheduler(dry_run=True)

# Endpoints API
@router.post("/optimize", response_model=FeeOptimizationResponse)
async def trigger_fee_optimization(
    request: FeeOptimizationRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(..., alias="Authorization"),
    mongo_ops: MongoOperations = Depends(get_mongo_ops),
    fee_optimizer: FeeOptimizerScheduler = Depends(get_fee_optimizer)
):
    """Déclenche une optimisation des frais pour les nœuds ou canaux spécifiés"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Vérifier les autorisations
        if not current_user.get("permissions", {}).get("fee_optimization", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Autorisations insuffisantes pour cette opération"
            )
        
        # Définir le mode dry_run
        fee_optimizer.dry_run = request.dry_run
        
        # Générer un ID unique pour ce job
        job_id = f"fee-opt-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{current_user.get('username', 'unknown')}"
        
        # Définir une fonction de background pour exécuter l'optimisation
        async def run_optimization():
            try:
                # Collecter les données des nœuds
                if request.node_ids:
                    # Optimiser uniquement les nœuds spécifiés
                    node_data = await fee_optimizer._collect_node_data()
                    node_data = {node_id: data for node_id, data in node_data.items() if node_id in request.node_ids}
                else:
                    # Optimiser tous les nœuds
                    node_data = await fee_optimizer._collect_node_data()
                
                all_updates = []
                
                # Traiter chaque nœud
                for node_id, data in node_data.items():
                    # Filtrer les canaux spécifiques si demandé
                    if request.channel_ids:
                        data["channels"] = [ch for ch in data["channels"] if ch.get("channel_id") in request.channel_ids]
                    
                    # Évaluer et appliquer les mises à jour
                    evaluation = fee_optimizer.evaluate_node(data)
                    if evaluation["status"] != "success":
                        continue
                    
                    # Générer les mises à jour
                    fee_updates = []
                    for channel_score in evaluation["channel_scores"]:
                        # [...] Logique de génération des mises à jour (similaire à celle du scheduler)
                        # Cette partie serait très similaire au code existant dans le scheduler
                        
                        # Récupérer et ajouter les mises à jour pour ce nœud
                        # Code simplifié par souci de clarté
                        pass
                    
                    # Ajouter à la liste globale
                    all_updates.extend(fee_updates)
                
                # Limiter le nombre de mises à jour si spécifié
                if request.max_updates and len(all_updates) > request.max_updates:
                    all_updates = all_updates[:request.max_updates]
                
                # Appliquer les mises à jour
                if all_updates:
                    await fee_optimizer._apply_fee_updates(all_updates)
                
                # Sauvegarder les résultats dans MongoDB
                await mongo_ops.insert_document("fee_optimization_jobs", {
                    "job_id": job_id,
                    "status": "completed",
                    "user": current_user.get("username"),
                    "request": request.dict(),
                    "updates": all_updates,
                    "completed_at": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Erreur lors de l'optimisation en arrière-plan: {str(e)}")
                # Enregistrer l'erreur dans MongoDB
                await mongo_ops.insert_document("fee_optimization_jobs", {
                    "job_id": job_id,
                    "status": "failed",
                    "user": current_user.get("username"),
                    "request": request.dict(),
                    "error": str(e),
                    "completed_at": datetime.now().isoformat()
                })
        
        # Planifier la tâche en arrière-plan
        background_tasks.add_task(run_optimization)
        
        # Enregistrer le démarrage du job
        await mongo_ops.insert_document("fee_optimization_jobs", {
            "job_id": job_id,
            "status": "started",
            "user": current_user.get("username"),
            "request": request.dict(),
            "started_at": datetime.now().isoformat()
        })
        
        # Retourner une réponse immédiate
        return FeeOptimizationResponse(
            success=True,
            message=f"Optimisation des frais démarrée en arrière-plan (mode {'simulation' if request.dry_run else 'production'})",
            updates=[],
            timestamp=datetime.now().isoformat(),
            job_id=job_id
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement de l'optimisation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du déclenchement de l'optimisation: {str(e)}"
        )

@router.get("/updates", response_model=List[FeeUpdateResponse])
async def get_fee_updates(
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    node_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    authorization: str = Header(..., alias="Authorization"),
    mongo_ops: MongoOperations = Depends(get_mongo_ops)
):
    """Récupère l'historique des mises à jour de frais avec filtrage"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Construire le filtre MongoDB
        query = {}
        
        if node_id:
            query["node_id"] = node_id
            
        if channel_id:
            query["channel_id"] = channel_id
            
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
            
        if end_date:
            date_filter["$lte"] = end_date
            
        if date_filter:
            query["timestamp"] = date_filter
        
        # Récupérer les données
        updates = await mongo_ops.find_documents(
            "fee_updates",
            query=query,
            sort=[("timestamp", -1)],
            skip=offset,
            limit=limit
        )
        
        # Convertir en réponse Pydantic
        response = []
        for update in updates:
            try:
                response.append(FeeUpdateResponse(**update))
            except Exception as e:
                logger.warning(f"Erreur lors de la conversion d'une mise à jour: {str(e)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des mises à jour: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des mises à jour: {str(e)}"
        )

@router.post("/rollback", response_model=RollbackResponse)
async def rollback_updates(
    request: RollbackRequest,
    authorization: str = Header(..., alias="Authorization"),
    mongo_ops: MongoOperations = Depends(get_mongo_ops),
    fee_optimizer: FeeOptimizerScheduler = Depends(get_fee_optimizer)
):
    """Annule une série de mises à jour de frais"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Vérifier les autorisations
        if not current_user.get("permissions", {}).get("fee_rollback", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Autorisations insuffisantes pour cette opération"
            )
        
        # Récupérer les informations de mise à jour
        rollback_file = Path(fee_optimizer.config.get("rollback", {}).get("dir", "data/rollbacks")) / f"{request.updates_id}.json"
        
        if not rollback_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mise à jour {request.updates_id} non trouvée"
            )
        
        # Charger les données
        with open(rollback_file, 'r') as f:
            update_data = json.load(f)
        
        # Vérifier si déjà annulée
        if update_data.get("rolled_back", False):
            return RollbackResponse(
                success=True,
                message="Ces mises à jour ont déjà été annulées",
                rollback_count=0,
                timestamp=datetime.now().isoformat()
            )
        
        # Effectuer le rollback
        updates_to_rollback = update_data.get("updates", [])
        await fee_optimizer._rollback_fee_updates(updates_to_rollback)
        
        # Mettre à jour le statut
        update_data["rolled_back"] = True
        update_data["rollback_timestamp"] = datetime.now().isoformat()
        update_data["rollback_reason"] = request.reason
        update_data["rollback_user"] = current_user.get("username")
        
        with open(rollback_file, 'w') as f:
            json.dump(update_data, f, indent=2)
        
        # Enregistrer dans MongoDB
        await mongo_ops.insert_document("fee_rollbacks", {
            "updates_id": request.updates_id,
            "rolled_back_at": datetime.now().isoformat(),
            "user": current_user.get("username"),
            "reason": request.reason,
            "updates": updates_to_rollback
        })
        
        return RollbackResponse(
            success=True,
            message=f"Rollback de {len(updates_to_rollback)} mises à jour effectué avec succès",
            rollback_count=len(updates_to_rollback),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du rollback des mises à jour: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du rollback des mises à jour: {str(e)}"
        )

@router.get("/status")
async def get_optimizer_status(
    authorization: str = Header(..., alias="Authorization"),
    mongo_ops: MongoOperations = Depends(get_mongo_ops),
    redis_ops: RedisOperations = Depends(get_redis_ops)
):
    """Récupère le statut du service d'optimisation des frais"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        # Récupérer le nombre de mises à jour récentes (dernières 24h)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        recent_updates = await mongo_ops.count_documents(
            "fee_updates", 
            {"timestamp": {"$gte": yesterday}}
        )
        
        # Récupérer le nombre de rollbacks récents
        recent_rollbacks = await mongo_ops.count_documents(
            "fee_rollbacks", 
            {"rolled_back_at": {"$gte": yesterday}}
        )
        
        # Vérifier si un job est en cours
        running_jobs = await mongo_ops.count_documents(
            "fee_optimization_jobs",
            {"status": "started", "started_at": {"$gte": yesterday}}
        )
        
        # Récupérer les derniers jobs
        latest_jobs = await mongo_ops.find_documents(
            "fee_optimization_jobs",
            sort=[("started_at", -1)],
            limit=5
        )
        
        # Récupérer les statistiques d'optimisation
        # Ces valeurs seraient stockées dans Redis par le scheduler
        success_rate = await redis_ops.get("fee_optimizer:success_rate") or "N/A"
        total_optimizations = await redis_ops.get("fee_optimizer:total_optimizations") or 0
        total_rollbacks = await redis_ops.get("fee_optimizer:total_rollbacks") or 0
        
        return {
            "success": True,
            "service_status": "running",
            "last_24h": {
                "updates": recent_updates,
                "rollbacks": recent_rollbacks,
                "jobs": running_jobs
            },
            "stats": {
                "success_rate": success_rate,
                "total_optimizations": total_optimizations,
                "total_rollbacks": total_rollbacks
            },
            "latest_jobs": latest_jobs,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
        return {
            "success": False,
            "service_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

shadow_recommendations_total = Counter('shadow_recommendations_total', 'Nombre total de recommandations shadow mode')
@router.get("/recommendations", response_model=List[FeeUpdateResponse])
async def get_shadow_recommendations(
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    authorization: str = Header(..., alias="Authorization"),
    mongo_ops: MongoOperations = Depends(get_mongo_ops)
):
    """Retourne les recommandations générées en mode shadow (dry-run)"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    query = {"dry_run": True}
    docs = await mongo_ops.find_documents("fee_optimization_jobs", query, limit=limit, offset=offset)
    recos = []
    for doc in docs:
        recos.extend(doc.get("updates", []))
    shadow_recommendations_total.inc(len(recos))
    return recos 