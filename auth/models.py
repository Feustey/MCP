from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    API = "api"

class UserBase(BaseModel):
    username: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    lightning_pubkey: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    lightning_pubkey: Optional[str] = None

class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User

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
        Permission(resource="users", action="manage", description="Gestion des utilisateurs"),
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