"""
Modèles de sécurité
Définition des modèles de sécurité pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import jwt
import hashlib
import secrets

class SecurityConfig:
    """Configuration de sécurité"""
    
    # Configuration JWT
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24
    JWT_REFRESH_EXPIRATION_DAYS = 30
    
    # Configuration des mots de passe
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPER = True
    PASSWORD_REQUIRE_LOWER = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Configuration de la limitation de débit
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60  # secondes
    RATE_LIMIT_BURST = 10
    
    # Configuration des tentatives de connexion
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    
    # Configuration des sessions
    SESSION_EXPIRATION_HOURS = 2
    MAX_SESSIONS_PER_USER = 5
    
    # Configuration des IPs autorisées
    ALLOWED_IPS: Set[str] = set()
    BLOCKED_IPS: Set[str] = set()
    
    # Configuration des origines CORS
    ALLOWED_ORIGINS: Set[str] = {
        "https://app.dazno.de",
        "https://api.dazno.de"
    }
    
    # Configuration des en-têtes de sécurité
    SECURITY_HEADERS = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }

class Token(BaseModel):
    """Modèle de token JWT"""
    
    access_token: str = Field(..., description="Token d'accès")
    refresh_token: str = Field(..., description="Token de rafraîchissement")
    token_type: str = Field(default="bearer", description="Type de token")
    expires_at: datetime = Field(..., description="Date d'expiration")
    
    @classmethod
    def create(
        cls,
        user_id: str,
        permissions: List[str],
        secret: str,
        expires_delta: Optional[timedelta] = None
    ) -> "Token":
        """Crée un nouveau token"""
        
        if expires_delta is None:
            expires_delta = timedelta(hours=SecurityConfig.JWT_EXPIRATION_HOURS)
        
        expires_at = datetime.utcnow() + expires_delta
        
        # Création du token d'accès
        access_token_data = {
            "sub": user_id,
            "permissions": permissions,
            "exp": expires_at.timestamp(),
            "type": "access"
        }
        access_token = jwt.encode(
            access_token_data,
            secret,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )
        
        # Création du token de rafraîchissement
        refresh_token_data = {
            "sub": user_id,
            "exp": (datetime.utcnow() + timedelta(days=SecurityConfig.JWT_REFRESH_EXPIRATION_DAYS)).timestamp(),
            "type": "refresh"
        }
        refresh_token = jwt.encode(
            refresh_token_data,
            secret,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )
        
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

class PasswordHash:
    """Gestion des hachages de mots de passe"""
    
    @staticmethod
    def hash(password: str) -> str:
        """Hache un mot de passe"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"{salt}${hash_obj.hexdigest()}"
    
    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """Vérifie un mot de passe"""
        salt, stored_hash = hashed.split("$")
        hash_obj = hashlib.sha256((password + salt).encode())
        return hash_obj.hexdigest() == stored_hash
    
    @staticmethod
    def validate(password: str) -> bool:
        """Valide un mot de passe"""
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            return False
        
        if SecurityConfig.PASSWORD_REQUIRE_UPPER and not any(c.isupper() for c in password):
            return False
        
        if SecurityConfig.PASSWORD_REQUIRE_LOWER and not any(c.islower() for c in password):
            return False
        
        if SecurityConfig.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            return False
        
        if SecurityConfig.PASSWORD_REQUIRE_SPECIAL and not any(not c.isalnum() for c in password):
            return False
        
        return True

class RateLimit:
    """Gestion de la limitation de débit"""
    
    def __init__(
        self,
        requests: int = SecurityConfig.RATE_LIMIT_REQUESTS,
        window: int = SecurityConfig.RATE_LIMIT_WINDOW,
        burst: int = SecurityConfig.RATE_LIMIT_BURST
    ):
        self.requests = requests
        self.window = window
        self.burst = burst
        self.attempts: Dict[str, List[datetime]] = {}
    
    def check(self, key: str) -> bool:
        """Vérifie si une requête est autorisée"""
        now = datetime.utcnow()
        
        # Nettoyage des anciennes tentatives
        if key in self.attempts:
            self.attempts[key] = [
                t for t in self.attempts[key]
                if now - t < timedelta(seconds=self.window)
            ]
        
        # Vérification de la limite
        if key not in self.attempts:
            self.attempts[key] = []
        
        if len(self.attempts[key]) >= self.requests:
            return False
        
        self.attempts[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Récupère le nombre de requêtes restantes"""
        if key not in self.attempts:
            return self.requests
        
        now = datetime.utcnow()
        self.attempts[key] = [
            t for t in self.attempts[key]
            if now - t < timedelta(seconds=self.window)
        ]
        
        return max(0, self.requests - len(self.attempts[key]))
    
    def get_reset_time(self, key: str) -> Optional[datetime]:
        """Récupère le temps de réinitialisation"""
        if key not in self.attempts or not self.attempts[key]:
            return None
        
        return min(self.attempts[key]) + timedelta(seconds=self.window)

class LoginAttempt:
    """Gestion des tentatives de connexion"""
    
    def __init__(
        self,
        max_attempts: int = SecurityConfig.MAX_LOGIN_ATTEMPTS,
        lockout_minutes: int = SecurityConfig.LOGIN_LOCKOUT_MINUTES
    ):
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self.attempts: Dict[str, List[datetime]] = {}
        self.locked: Dict[str, datetime] = {}
    
    def record_attempt(self, key: str, success: bool) -> None:
        """Enregistre une tentative de connexion"""
        now = datetime.utcnow()
        
        if success:
            if key in self.attempts:
                del self.attempts[key]
            if key in self.locked:
                del self.locked[key]
            return
        
        if key not in self.attempts:
            self.attempts[key] = []
        
        self.attempts[key].append(now)
        
        if len(self.attempts[key]) >= self.max_attempts:
            self.locked[key] = now + timedelta(minutes=self.lockout_minutes)
    
    def is_locked(self, key: str) -> bool:
        """Vérifie si une clé est verrouillée"""
        if key not in self.locked:
            return False
        
        if datetime.utcnow() > self.locked[key]:
            del self.locked[key]
            return False
        
        return True
    
    def get_lockout_time(self, key: str) -> Optional[datetime]:
        """Récupère le temps de verrouillage"""
        if key not in self.locked:
            return None
        
        if datetime.utcnow() > self.locked[key]:
            del self.locked[key]
            return None
        
        return self.locked[key]
    
    def get_remaining_attempts(self, key: str) -> int:
        """Récupère le nombre de tentatives restantes"""
        if key not in self.attempts:
            return self.max_attempts
        
        return max(0, self.max_attempts - len(self.attempts[key])) 