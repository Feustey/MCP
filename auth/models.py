from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    API = "api"

class User(BaseModel):
    username: str
    role: UserRole = UserRole.USER
    lightning_pubkey: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None
    exp: Optional[datetime] = None

class Permission(BaseModel):
    resource: str
    action: str
    description: str

class RolePermissions:
    ADMIN = [
        Permission(resource="*", action="*", description="Accès complet"),
        Permission(resource="system", action="manage", description="Gestion du système"),
    ]
    
    USER = [
        Permission(resource="node", action="read", description="Lecture des données de nœud"),
        Permission(resource="node", action="optimize", description="Optimisation de nœud"),
        Permission(resource="network", action="read", description="Lecture des données réseau"),
    ]
    
    API = [
        Permission(resource="node", action="read", description="Lecture des données de nœud"),
        Permission(resource="network", action="read", description="Lecture des données réseau"),
    ]

    @classmethod
    def get_permissions(cls, role: UserRole) -> List[Permission]:
        return getattr(cls, role.upper(), []) 