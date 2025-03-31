from typing import Optional, List
from datetime import datetime
from .models import User, UserInDB, UserRole
from .jwt import get_password_hash, verify_password

class UserDatabase:
    """Gestionnaire de base de données pour les utilisateurs."""
    
    def __init__(self):
        # En production, utilisez une vraie base de données
        self._users: dict[str, UserInDB] = {}
        
    async def get_user(self, username: str) -> Optional[UserInDB]:
        """Récupère un utilisateur par son nom d'utilisateur."""
        return self._users.get(username)
        
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Récupère un utilisateur par son ID."""
        for user in self._users.values():
            if user.id == user_id:
                return user
        return None
        
    async def create_user(self, username: str, password: str, role: UserRole = UserRole.USER) -> UserInDB:
        """Crée un nouvel utilisateur."""
        if username in self._users:
            raise ValueError("Un utilisateur avec ce nom d'utilisateur existe déjà")
            
        user = UserInDB(
            id=str(len(self._users) + 1),
            username=username,
            role=role,
            hashed_password=get_password_hash(password),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True
        )
        
        self._users[username] = user
        return user
        
    async def update_user(self, user_id: str, **kwargs) -> Optional[UserInDB]:
        """Met à jour un utilisateur."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        update_data = kwargs.copy()
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
            
        update_data["updated_at"] = datetime.utcnow()
        
        for key, value in update_data.items():
            setattr(user, key, value)
            
        return user
        
    async def delete_user(self, user_id: str) -> bool:
        """Supprime un utilisateur."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
            
        if user.username in self._users:
            del self._users[user.username]
            return True
        return False
        
    async def verify_user(self, username: str, password: str) -> Optional[UserInDB]:
        """Vérifie les identifiants d'un utilisateur."""
        user = await self.get_user(username)
        if not user:
            return None
            
        if not verify_password(password, user.hashed_password):
            return None
            
        return user
        
    async def list_users(self) -> List[UserInDB]:
        """Liste tous les utilisateurs."""
        return list(self._users.values())
        
    async def update_last_login(self, user_id: str) -> Optional[UserInDB]:
        """Met à jour la date de dernière connexion."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        user.last_login = datetime.utcnow()
        return user

# Instance globale de la base de données
db = UserDatabase() 