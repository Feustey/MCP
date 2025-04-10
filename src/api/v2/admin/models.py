from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union, Set
from enum import Enum
from datetime import datetime, timedelta
import uuid

class UserStatus(str, Enum):
    """Statut d'un utilisateur"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class UserRole(str, Enum):
    """Rôles utilisateur"""
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    USER = "user"
    GUEST = "guest"

class PermissionCategory(str, Enum):
    """Catégories de permissions"""
    USER_MANAGEMENT = "user_management"
    SYSTEM_CONFIG = "system_config"
    MONITORING = "monitoring"
    NETWORK_MANAGEMENT = "network_management"
    PAYMENT_MANAGEMENT = "payment_management"
    REPORTING = "reporting"
    API_ACCESS = "api_access"

class PermissionAction(str, Enum):
    """Actions possibles sur les permissions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"

class SystemLogLevel(str, Enum):
    """Niveaux de log système"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class User(BaseModel):
    """Modèle d'utilisateur"""
    id: Optional[str] = None
    username: str
    email: str
    full_name: Optional[str] = None
    password_hash: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    roles: List[UserRole] = [UserRole.USER]
    permissions: List[str] = []
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "usr-12345",
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "status": "active",
                "roles": ["user"],
                "permissions": ["monitoring:read"],
                "last_login": "2023-07-01T12:34:56Z",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class UserCreate(BaseModel):
    """Modèle pour la création d'un utilisateur"""
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    roles: List[UserRole] = [UserRole.USER]
    permissions: List[str] = []

class UserUpdate(BaseModel):
    """Modèle pour la mise à jour d'un utilisateur"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    status: Optional[UserStatus] = None
    roles: Optional[List[UserRole]] = None
    permissions: Optional[List[str]] = None

class Role(BaseModel):
    """Modèle de rôle"""
    id: Optional[str] = None
    name: UserRole
    description: str
    permissions: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "role-12345",
                "name": "manager",
                "description": "Gestionnaire avec accès étendu",
                "permissions": [
                    "user_management:read",
                    "monitoring:read",
                    "monitoring:update",
                    "network_management:read"
                ],
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class RoleCreate(BaseModel):
    """Modèle pour la création d'un rôle"""
    name: UserRole
    description: str
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    """Modèle pour la mise à jour d'un rôle"""
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class Permission(BaseModel):
    """Modèle de permission"""
    id: Optional[str] = None
    name: str
    category: PermissionCategory
    action: PermissionAction
    description: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "perm-12345",
                "name": "user_management:create",
                "category": "user_management",
                "action": "create",
                "description": "Permet de créer de nouveaux utilisateurs",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class PermissionCreate(BaseModel):
    """Modèle pour la création d'une permission"""
    name: str
    category: PermissionCategory
    action: PermissionAction
    description: str

class PermissionUpdate(BaseModel):
    """Modèle pour la mise à jour d'une permission"""
    description: Optional[str] = None

class SystemConfig(BaseModel):
    """Modèle de configuration système"""
    id: Optional[str] = None
    key: str
    value: Any
    description: str
    is_encrypted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "config-12345",
                "key": "api.rate_limit",
                "value": 100,
                "description": "Limite de requêtes API par minute",
                "is_encrypted": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class SystemConfigCreate(BaseModel):
    """Modèle pour la création d'une configuration système"""
    key: str
    value: Any
    description: str
    is_encrypted: bool = False

class SystemConfigUpdate(BaseModel):
    """Modèle pour la mise à jour d'une configuration système"""
    value: Optional[Any] = None
    description: Optional[str] = None
    is_encrypted: Optional[bool] = None

class SystemLog(BaseModel):
    """Modèle de log système"""
    id: Optional[str] = None
    timestamp: datetime
    level: SystemLogLevel
    source: str
    message: str
    details: Dict[str, Any] = {}
    user_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "log-12345",
                "timestamp": "2023-07-01T12:34:56Z",
                "level": "info",
                "source": "user_management",
                "message": "Utilisateur créé avec succès",
                "details": {
                    "user_id": "usr-12345",
                    "username": "johndoe"
                },
                "user_id": "usr-67890"
            }
        }

class SystemLogFilter(BaseModel):
    """Filtres pour les logs système"""
    level: Optional[SystemLogLevel] = None
    source: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[str] = None
    limit: int = 100
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être entre 1 et 1000')
        return v

class AuditLog(BaseModel):
    """Modèle de log d'audit"""
    id: Optional[str] = None
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "audit-12345",
                "timestamp": "2023-07-01T12:34:56Z",
                "user_id": "usr-12345",
                "action": "update",
                "resource_type": "user",
                "resource_id": "usr-67890",
                "details": {
                    "field": "status",
                    "old_value": "active",
                    "new_value": "suspended"
                },
                "ip_address": "192.168.1.1"
            }
        }

class AuditLogFilter(BaseModel):
    """Filtres pour les logs d'audit"""
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('La limite doit être entre 1 et 1000')
        return v

class SystemHealth(BaseModel):
    """Modèle de santé du système"""
    status: str
    version: str
    uptime: int
    memory_usage: float
    cpu_usage: float
    disk_usage: float
    active_users: int
    api_requests: int
    last_check: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 86400,
                "memory_usage": 45.2,
                "cpu_usage": 12.8,
                "disk_usage": 62.5,
                "active_users": 42,
                "api_requests": 1234,
                "last_check": "2023-07-01T12:34:56Z"
            }
        }

class BackupConfig(BaseModel):
    """Modèle de configuration de sauvegarde"""
    id: Optional[str] = None
    name: str
    schedule: str
    retention_days: int
    include_databases: bool = True
    include_files: bool = True
    destination: str
    is_enabled: bool = True
    last_backup: Optional[datetime] = None
    next_backup: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "backup-12345",
                "name": "Sauvegarde quotidienne",
                "schedule": "0 0 * * *",
                "retention_days": 30,
                "include_databases": True,
                "include_files": True,
                "destination": "/backups",
                "is_enabled": True,
                "last_backup": "2023-07-01T00:00:00Z",
                "next_backup": "2023-07-02T00:00:00Z",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-07-01T12:34:56Z"
            }
        }

class BackupConfigCreate(BaseModel):
    """Modèle pour la création d'une configuration de sauvegarde"""
    name: str
    schedule: str
    retention_days: int
    include_databases: bool = True
    include_files: bool = True
    destination: str
    is_enabled: bool = True

class BackupConfigUpdate(BaseModel):
    """Modèle pour la mise à jour d'une configuration de sauvegarde"""
    name: Optional[str] = None
    schedule: Optional[str] = None
    retention_days: Optional[int] = None
    include_databases: Optional[bool] = None
    include_files: Optional[bool] = None
    destination: Optional[str] = None
    is_enabled: Optional[bool] = None

class BackupStatus(BaseModel):
    """Modèle de statut de sauvegarde"""
    id: str
    config_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "backup-status-12345",
                "config_id": "backup-12345",
                "start_time": "2023-07-01T00:00:00Z",
                "end_time": "2023-07-01T00:05:23Z",
                "status": "completed",
                "size_bytes": 1048576,
                "error_message": None
            }
        } 