from fastapi import Depends, HTTPException, status
from typing import List
from .models import User, UserRole, Permission
from .jwt import get_current_user, check_permissions
from .models import RolePermissions

def require_permissions(required_permissions: List[Permission]):
    """Décorateur pour vérifier des permissions spécifiques."""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = RolePermissions.get_permissions(current_user.role)
        
        # Les administrateurs ont toujours accès
        if current_user.role == UserRole.ADMIN:
            return current_user
            
        # Vérification des permissions requises
        for required in required_permissions:
            has_permission = False
            for user_perm in user_permissions:
                if (user_perm.resource == required.resource or user_perm.resource == "*") and \
                   (user_perm.action == required.action or user_perm.action == "*"):
                    has_permission = True
                    break
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission requise : {required.resource}:{required.action}"
                )
        return current_user
    return permission_checker

def require_lightning_node():
    """Décorateur pour vérifier que l'utilisateur a une clé Lightning associée."""
    async def node_checker(current_user: User = Depends(get_current_user)):
        if not current_user.lightning_pubkey:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Une clé Lightning est requise pour cette opération"
            )
        return current_user
    return node_checker

# Dépendances prédéfinies pour les rôles courants
require_admin = check_permissions(UserRole.ADMIN)
require_user = check_permissions(UserRole.USER)
require_api = check_permissions(UserRole.API)

# Dépendances prédéfinies pour les permissions courantes
require_node_read = require_permissions([
    Permission(resource="node", action="read", description="Lecture des données de nœud")
])

require_node_optimize = require_permissions([
    Permission(resource="node", action="optimize", description="Optimisation de nœud")
])

require_network_read = require_permissions([
    Permission(resource="network", action="read", description="Lecture des données réseau")
]) 