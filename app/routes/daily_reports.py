"""
Endpoints API pour les rapports quotidiens
Gestion des workflows automatisés et consultation des rapports

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 5 novembre 2025
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from config.database.mongodb import get_database
from config.models.daily_reports import (
    DailyReport,
    DailyReportResponse,
    DailyReportListResponse,
    WorkflowStatusResponse,
    UserProfile
)
from app.auth import verify_jwt_and_get_tenant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Daily Reports"])


# ============================================================================
# GESTION DU WORKFLOW UTILISATEUR
# ============================================================================

@router.post("/user/profile/daily-report/enable")
async def enable_daily_report(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Active le workflow de rapport quotidien pour l'utilisateur"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    try:
        # Vérifier que l'utilisateur a un profil avec pubkey
        profile = await db.user_profiles.find_one({"tenant_id": tenant_id})
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="User profile not found. Please create your profile first."
            )
        
        if not profile.get("lightning_pubkey"):
            raise HTTPException(
                status_code=400,
                detail="Lightning pubkey required. Please add your node pubkey to your profile."
            )
        
        # Activer le workflow
        result = await db.user_profiles.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "daily_report_enabled": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to enable daily report workflow"
            )
        
        logger.info(f"Daily report enabled for tenant {tenant_id}")
        
        # Calculer la prochaine exécution (demain 06:00 UTC)
        tomorrow_6am = (datetime.utcnow() + timedelta(days=1)).replace(
            hour=6, minute=0, second=0, microsecond=0
        )
        
        return {
            "status": "success",
            "message": "Rapport quotidien activé avec succès",
            "next_report": tomorrow_6am.isoformat(),
            "schedule": "Every day at 06:00 UTC"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling daily report for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/profile/daily-report/disable")
async def disable_daily_report(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Désactive le workflow de rapport quotidien"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    try:
        result = await db.user_profiles.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "daily_report_enabled": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            # Vérifier si le profil existe
            profile = await db.user_profiles.find_one({"tenant_id": tenant_id})
            if not profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # Profil existe mais déjà désactivé
            logger.info(f"Daily report already disabled for tenant {tenant_id}")
        
        logger.info(f"Daily report disabled for tenant {tenant_id}")
        
        return {
            "status": "success",
            "message": "Rapport quotidien désactivé"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling daily report for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/profile/daily-report/status", response_model=WorkflowStatusResponse)
async def get_daily_report_status(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Récupère le statut du workflow pour l'utilisateur"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    try:
        profile = await db.user_profiles.find_one({"tenant_id": tenant_id})
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        enabled = profile.get("daily_report_enabled", False)
        
        # Calculer la prochaine exécution si activé
        next_report = None
        if enabled:
            now = datetime.utcnow()
            next_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now.hour >= 6:
                next_6am += timedelta(days=1)
            next_report = next_6am.isoformat()
        
        return WorkflowStatusResponse(
            enabled=enabled,
            schedule=profile.get("daily_report_schedule", "0 6 * * *"),
            last_report=profile.get("last_report_generated"),
            total_reports=profile.get("total_reports_generated", 0),
            next_report=next_report
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily report status for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONSULTATION DES RAPPORTS
# ============================================================================

@router.get("/reports/daily/latest", response_model=DailyReportResponse)
async def get_latest_daily_report(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Récupère le dernier rapport quotidien de l'utilisateur"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    try:
        report = await db.daily_reports.find_one(
            {
                "tenant_id": tenant_id,
                "generation_status": "completed"
            },
            sort=[("report_date", -1)]
        )
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Aucun rapport disponible. Activez les rapports quotidiens dans votre profil."
            )
        
        # Convertir le _id MongoDB
        if "_id" in report:
            report["id"] = str(report["_id"])
            del report["_id"]
        
        return DailyReportResponse(
            status="success",
            report=DailyReport(**report)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest report for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/daily/history", response_model=DailyReportListResponse)
async def get_daily_reports_history(
    days: int = Query(default=30, ge=1, le=90, description="Nombre de jours d'historique"),
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    limit: int = Query(default=10, ge=1, le=100, description="Résultats par page"),
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Récupère l'historique des rapports quotidiens (paginé)"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    try:
        date_threshold = datetime.utcnow() - timedelta(days=days)
        
        # Compter le total
        total = await db.daily_reports.count_documents({
            "tenant_id": tenant_id,
            "report_date": {"$gte": date_threshold},
            "generation_status": "completed"
        })
        
        # Récupérer les rapports paginés
        cursor = db.daily_reports.find(
            {
                "tenant_id": tenant_id,
                "report_date": {"$gte": date_threshold},
                "generation_status": "completed"
            },
            sort=[("report_date", -1)],
            skip=(page - 1) * limit,
            limit=limit
        )
        
        reports = await cursor.to_list(length=limit)
        
        # Convertir les _id MongoDB
        for report in reports:
            if "_id" in report:
                report["id"] = str(report["_id"])
                del report["_id"]
        
        return DailyReportListResponse(
            status="success",
            reports=[DailyReport(**r) for r in reports],
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if total > 0 else 0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report history for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/daily/{report_id}", response_model=DailyReportResponse)
async def get_daily_report_by_id(
    report_id: str,
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Récupère un rapport spécifique par son ID"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    try:
        report = await db.daily_reports.find_one({
            "report_id": report_id,
            "tenant_id": tenant_id
        })
        
        if not report:
            raise HTTPException(status_code=404, detail="Rapport introuvable")
        
        # Convertir le _id MongoDB
        if "_id" in report:
            report["id"] = str(report["_id"])
            del report["_id"]
        
        return DailyReportResponse(
            status="success",
            report=DailyReport(**report)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report {report_id} for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS ADMIN
# ============================================================================

@router.post("/admin/reports/daily/trigger")
async def admin_trigger_daily_reports(
    user_ids: Optional[List[str]] = None,
    authorization: str = Header(..., alias="Authorization"),
    background_tasks: BackgroundTasks = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """[ADMIN] Déclenche manuellement la génération des rapports quotidiens"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    # TODO: Vérifier permissions admin
    # Pour l'instant, on assume que l'utilisateur est admin
    
    try:
        from app.services.daily_report_generator import get_daily_report_generator
        
        task_id = f"daily_reports_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        async def generate_reports_task():
            try:
                generator = await get_daily_report_generator()
                await generator.run(user_ids=user_ids)
                logger.info(f"Manual daily reports generation completed: {task_id}")
            except Exception as e:
                logger.error(f"Error in manual daily reports generation {task_id}: {e}")
        
        if background_tasks:
            background_tasks.add_task(generate_reports_task)
            
            return {
                "status": "started",
                "task_id": task_id,
                "message": "Génération des rapports démarrée en arrière-plan",
                "user_ids": user_ids if user_ids else "all"
            }
        else:
            # Exécution synchrone si pas de background tasks
            await generate_reports_task()
            return {
                "status": "completed",
                "task_id": task_id,
                "message": "Génération des rapports terminée"
            }
        
    except Exception as e:
        logger.error(f"Error triggering daily reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/reports/daily/stats")
async def admin_get_daily_reports_stats(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """[ADMIN] Statistiques globales sur les rapports quotidiens"""
    tenant_id = verify_jwt_and_get_tenant(authorization)
    
    # TODO: Vérifier permissions admin
    
    try:
        # Total users avec workflow activé
        users_enabled = await db.user_profiles.count_documents({
            "daily_report_enabled": True
        })
        
        # Total rapports générés
        total_reports = await db.daily_reports.count_documents({})
        
        # Rapports générés aujourd'hui
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        reports_today = await db.daily_reports.count_documents({
            "generation_timestamp": {"$gte": today_start}
        })
        
        # Rapports en échec aujourd'hui
        reports_failed_today = await db.daily_reports.count_documents({
            "generation_timestamp": {"$gte": today_start},
            "generation_status": "failed"
        })
        
        # Taux de succès
        success_rate = 0
        if reports_today > 0:
            success_rate = ((reports_today - reports_failed_today) / reports_today) * 100
        
        return {
            "status": "success",
            "stats": {
                "users_with_workflow_enabled": users_enabled,
                "total_reports_generated": total_reports,
                "reports_generated_today": reports_today,
                "reports_failed_today": reports_failed_today,
                "success_rate_today": round(success_rate, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting daily reports stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

