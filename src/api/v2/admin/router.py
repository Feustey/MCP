from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging
from .models import (
    User, UserCreate, UserUpdate,
    Role, RoleCreate, RoleUpdate,
    Permission, PermissionCreate, PermissionUpdate,
    SystemConfig, SystemConfigCreate, SystemConfigUpdate,
    SystemLog, SystemLogFilter,
    AuditLog, AuditLogFilter,
    SystemHealth,
    BackupConfig, BackupConfigCreate, BackupConfigUpdate,
    BackupStatus
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du router
router = APIRouter(
    prefix="/admin",
    tags=["administration"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit"},
        404: {"description": "Ressource non trouvée"},
        500: {"description": "Erreur interne du serveur"}
    }
)

# Base de données temporaire en mémoire (à remplacer par une vraie base de données)
class AdminDB:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}
        self.system_configs: Dict[str, SystemConfig] = {}
        self.system_logs: List[SystemLog] = []
        self.audit_logs: List[AuditLog] = []
        self.backup_configs: Dict[str, BackupConfig] = {}
        self.backup_statuses: List[BackupStatus] = []

# Instance de la base de données
db = AdminDB()

# Routes pour la gestion des utilisateurs
@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Créer un nouvel utilisateur"""
    user_id = f"usr-{uuid.uuid4().hex[:8]}"
    new_user = User(
        id=user_id,
        **user.dict(exclude={'password'}),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.users[user_id] = new_user
    return new_user

@router.get("/users", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None
):
    """Lister les utilisateurs avec pagination et filtrage"""
    users = list(db.users.values())
    if status:
        users = [u for u in users if u.status == status]
    return users[skip:skip + limit]

@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str = Path(..., description="ID de l'utilisateur")):
    """Obtenir les détails d'un utilisateur"""
    if user_id not in db.users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return db.users[user_id]

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str = Path(..., description="ID de l'utilisateur"),
    user_update: UserUpdate = None
):
    """Mettre à jour un utilisateur"""
    if user_id not in db.users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    user = db.users[user_id]
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str = Path(..., description="ID de l'utilisateur")):
    """Supprimer un utilisateur"""
    if user_id not in db.users:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    del db.users[user_id]

# Routes pour la gestion des rôles
@router.post("/roles", response_model=Role, status_code=status.HTTP_201_CREATED)
async def create_role(role: RoleCreate):
    """Créer un nouveau rôle"""
    role_id = f"role-{uuid.uuid4().hex[:8]}"
    new_role = Role(
        id=role_id,
        **role.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.roles[role_id] = new_role
    return new_role

@router.get("/roles", response_model=List[Role])
async def list_roles():
    """Lister tous les rôles"""
    return list(db.roles.values())

@router.get("/roles/{role_id}", response_model=Role)
async def get_role(role_id: str = Path(..., description="ID du rôle")):
    """Obtenir les détails d'un rôle"""
    if role_id not in db.roles:
        raise HTTPException(status_code=404, detail="Rôle non trouvé")
    return db.roles[role_id]

@router.put("/roles/{role_id}", response_model=Role)
async def update_role(
    role_id: str = Path(..., description="ID du rôle"),
    role_update: RoleUpdate = None
):
    """Mettre à jour un rôle"""
    if role_id not in db.roles:
        raise HTTPException(status_code=404, detail="Rôle non trouvé")
    
    role = db.roles[role_id]
    update_data = role_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    role.updated_at = datetime.utcnow()
    
    return role

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: str = Path(..., description="ID du rôle")):
    """Supprimer un rôle"""
    if role_id not in db.roles:
        raise HTTPException(status_code=404, detail="Rôle non trouvé")
    del db.roles[role_id]

# Routes pour la gestion des permissions
@router.post("/permissions", response_model=Permission, status_code=status.HTTP_201_CREATED)
async def create_permission(permission: PermissionCreate):
    """Créer une nouvelle permission"""
    permission_id = f"perm-{uuid.uuid4().hex[:8]}"
    new_permission = Permission(
        id=permission_id,
        **permission.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.permissions[permission_id] = new_permission
    return new_permission

@router.get("/permissions", response_model=List[Permission])
async def list_permissions():
    """Lister toutes les permissions"""
    return list(db.permissions.values())

@router.get("/permissions/{permission_id}", response_model=Permission)
async def get_permission(permission_id: str = Path(..., description="ID de la permission")):
    """Obtenir les détails d'une permission"""
    if permission_id not in db.permissions:
        raise HTTPException(status_code=404, detail="Permission non trouvée")
    return db.permissions[permission_id]

@router.put("/permissions/{permission_id}", response_model=Permission)
async def update_permission(
    permission_id: str = Path(..., description="ID de la permission"),
    permission_update: PermissionUpdate = None
):
    """Mettre à jour une permission"""
    if permission_id not in db.permissions:
        raise HTTPException(status_code=404, detail="Permission non trouvée")
    
    permission = db.permissions[permission_id]
    update_data = permission_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)
    permission.updated_at = datetime.utcnow()
    
    return permission

@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(permission_id: str = Path(..., description="ID de la permission")):
    """Supprimer une permission"""
    if permission_id not in db.permissions:
        raise HTTPException(status_code=404, detail="Permission non trouvée")
    del db.permissions[permission_id]

# Routes pour la gestion de la configuration système
@router.post("/config", response_model=SystemConfig, status_code=status.HTTP_201_CREATED)
async def create_system_config(config: SystemConfigCreate):
    """Créer une nouvelle configuration système"""
    config_id = f"config-{uuid.uuid4().hex[:8]}"
    new_config = SystemConfig(
        id=config_id,
        **config.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.system_configs[config_id] = new_config
    return new_config

@router.get("/config", response_model=List[SystemConfig])
async def list_system_configs():
    """Lister toutes les configurations système"""
    return list(db.system_configs.values())

@router.get("/config/{config_id}", response_model=SystemConfig)
async def get_system_config(config_id: str = Path(..., description="ID de la configuration")):
    """Obtenir les détails d'une configuration système"""
    if config_id not in db.system_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    return db.system_configs[config_id]

@router.put("/config/{config_id}", response_model=SystemConfig)
async def update_system_config(
    config_id: str = Path(..., description="ID de la configuration"),
    config_update: SystemConfigUpdate = None
):
    """Mettre à jour une configuration système"""
    if config_id not in db.system_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    
    config = db.system_configs[config_id]
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_at = datetime.utcnow()
    
    return config

@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system_config(config_id: str = Path(..., description="ID de la configuration")):
    """Supprimer une configuration système"""
    if config_id not in db.system_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    del db.system_configs[config_id]

# Routes pour la gestion des logs système
@router.get("/logs/system", response_model=List[SystemLog])
async def list_system_logs(
    filter: SystemLogFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister les logs système avec filtrage"""
    logs = db.system_logs
    
    if filter.level:
        logs = [log for log in logs if log.level == filter.level]
    if filter.source:
        logs = [log for log in logs if log.source == filter.source]
    if filter.start_time:
        logs = [log for log in logs if log.timestamp >= filter.start_time]
    if filter.end_time:
        logs = [log for log in logs if log.timestamp <= filter.end_time]
    if filter.user_id:
        logs = [log for log in logs if log.user_id == filter.user_id]
    
    return logs[skip:skip + limit]

# Routes pour la gestion des logs d'audit
@router.get("/logs/audit", response_model=List[AuditLog])
async def list_audit_logs(
    filter: AuditLogFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister les logs d'audit avec filtrage"""
    logs = db.audit_logs
    
    if filter.user_id:
        logs = [log for log in logs if log.user_id == filter.user_id]
    if filter.action:
        logs = [log for log in logs if log.action == filter.action]
    if filter.resource_type:
        logs = [log for log in logs if log.resource_type == filter.resource_type]
    if filter.resource_id:
        logs = [log for log in logs if log.resource_id == filter.resource_id]
    if filter.start_time:
        logs = [log for log in logs if log.timestamp >= filter.start_time]
    if filter.end_time:
        logs = [log for log in logs if log.timestamp <= filter.end_time]
    
    return logs[skip:skip + limit]

# Routes pour la surveillance du système
@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """Obtenir l'état de santé du système"""
    # Simulation des métriques système
    return SystemHealth(
        status="healthy",
        version="1.0.0",
        uptime=86400,
        memory_usage=45.2,
        cpu_usage=12.8,
        disk_usage=62.5,
        active_users=len(db.users),
        api_requests=1000,
        last_check=datetime.utcnow()
    )

# Routes pour la gestion des sauvegardes
@router.post("/backups", response_model=BackupConfig, status_code=status.HTTP_201_CREATED)
async def create_backup_config(config: BackupConfigCreate):
    """Créer une nouvelle configuration de sauvegarde"""
    config_id = f"backup-{uuid.uuid4().hex[:8]}"
    new_config = BackupConfig(
        id=config_id,
        **config.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.backup_configs[config_id] = new_config
    return new_config

@router.get("/backups", response_model=List[BackupConfig])
async def list_backup_configs():
    """Lister toutes les configurations de sauvegarde"""
    return list(db.backup_configs.values())

@router.get("/backups/{config_id}", response_model=BackupConfig)
async def get_backup_config(config_id: str = Path(..., description="ID de la configuration")):
    """Obtenir les détails d'une configuration de sauvegarde"""
    if config_id not in db.backup_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    return db.backup_configs[config_id]

@router.put("/backups/{config_id}", response_model=BackupConfig)
async def update_backup_config(
    config_id: str = Path(..., description="ID de la configuration"),
    config_update: BackupConfigUpdate = None
):
    """Mettre à jour une configuration de sauvegarde"""
    if config_id not in db.backup_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    
    config = db.backup_configs[config_id]
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    config.updated_at = datetime.utcnow()
    
    return config

@router.delete("/backups/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup_config(config_id: str = Path(..., description="ID de la configuration")):
    """Supprimer une configuration de sauvegarde"""
    if config_id not in db.backup_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    del db.backup_configs[config_id]

@router.get("/backups/{config_id}/status", response_model=List[BackupStatus])
async def list_backup_statuses(
    config_id: str = Path(..., description="ID de la configuration"),
    limit: int = Query(10, ge=1, le=100)
):
    """Lister les statuts de sauvegarde pour une configuration donnée"""
    if config_id not in db.backup_configs:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    
    statuses = [status for status in db.backup_statuses if status.config_id == config_id]
    return sorted(statuses, key=lambda x: x.start_time, reverse=True)[:limit] 