"""
Module de sécurité pour l'API MCP en production
Gestion de l'authentification JWT et autorisation pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import jwt
import hashlib
import time
import secrets
import ipaddress
import redis
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json

# Configuration du logging
logger = logging.getLogger("mcp.security")

# Configuration de sécurité
ALLOWED_ORIGINS = [
    "https://app.dazno.de",
    "https://dazno.de",
    "https://www.dazno.de"
]

ALLOWED_IPS = [
    "127.0.0.1",
    "::1",
    # IPs des serveurs autorisés
    "10.0.0.0/8",
    "172.16.0.0/12", 
    "192.168.0.0/16"
]

# Variables d'environnement
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Validation de la configuration
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required")

if len(JWT_SECRET) < 32:
    raise ValueError("JWT_SECRET must be at least 32 characters long")

# Instance de sécurité HTTP Bearer
security = HTTPBearer()

# Connexion Redis pour le cache de sécurité
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
    redis_client = None

@dataclass
class SecurityAttempt:
    """Représente une tentative de sécurité"""
    ip: str
    count: int
    last_attempt: float
    blocked_until: Optional[float] = None

class SecurityManager:
    """Gestionnaire de sécurité centralisé"""
    
    def __init__(self):
        self.redis_prefix = "mcp:security:"
        self.failed_attempts_key = f"{self.redis_prefix}failed_attempts:"
        self.blocked_ips_key = f"{self.redis_prefix}blocked_ips"
        self.blocked_tokens_key = f"{self.redis_prefix}blocked_tokens"
        self.rate_limits_key = f"{self.redis_prefix}rate_limits:"
        
    def _get_failed_attempts_key(self, ip: str) -> str:
        return f"{self.failed_attempts_key}{ip}"
        
    def _get_rate_limits_key(self, ip: str) -> str:
        return f"{self.rate_limits_key}{ip}"
        
    async def is_ip_blocked(self, ip: str) -> bool:
        """Vérifie si une IP est bloquée"""
        # Vérifier dans le set des IPs bloquées
        if await redis_client.sismember(self.blocked_ips_key, ip):
            return True
            
        # Vérifier les tentatives échouées
        attempt_data = await redis_client.get(self._get_failed_attempts_key(ip))
        if attempt_data:
            attempt = SecurityAttempt(**json.loads(attempt_data))
            if attempt.blocked_until and time.time() < attempt.blocked_until:
                return True
                
        return False
        
    async def is_token_blocked(self, token_hash: str) -> bool:
        """Vérifie si un token est bloqué"""
        return await redis_client.sismember(self.blocked_tokens_key, token_hash)
        
    async def record_failed_attempt(self, ip: str):
        """Enregistre une tentative échouée"""
        key = self._get_failed_attempts_key(ip)
        attempt_data = await redis_client.get(key)
        
        if attempt_data:
            attempt = SecurityAttempt(**json.loads(attempt_data))
        else:
            attempt = SecurityAttempt(ip=ip, count=0, last_attempt=time.time())
            
        attempt.count += 1
        attempt.last_attempt = time.time()
        
        # Bloquer après 5 tentatives échouées
        if attempt.count >= 5:
            attempt.blocked_until = time.time() + 3600  # Blocage d'une heure
            await redis_client.sadd(self.blocked_ips_key, ip)
            
        # Sauvegarder avec expiration de 24h
        await redis_client.setex(
            key,
            24 * 3600,  # 24 heures
            json.dumps(asdict(attempt))
        )
        
    async def check_rate_limit(self, ip: str, limit: int = 100) -> bool:
        """Vérifie le rate limiting"""
        key = self._get_rate_limits_key(ip)
        current = await redis_client.get(key)
        
        if current and int(current) >= limit:
            return False
            
        # Incrémenter avec expiration de 1 minute
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # 1 minute
        await pipe.execute()
        
        return True
        
    async def clear_blocked_ip(self, ip: str):
        """Supprime une IP de la liste des bloquées"""
        pipe = redis_client.pipeline()
        pipe.srem(self.blocked_ips_key, ip)
        pipe.delete(self._get_failed_attempts_key(ip))
        await pipe.execute()
        
    async def clear_blocked_token(self, token_hash: str):
        """Supprime un token de la liste des bloqués"""
        await redis_client.srem(self.blocked_tokens_key, token_hash)
        
    async def clear_rate_limits(self, ip: str):
        """Réinitialise les limites de taux pour une IP"""
        await redis_client.delete(self._get_rate_limits_key(ip))

# Instance globale du gestionnaire de sécurité
security_manager = SecurityManager()

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Vérifie et décode le token JWT"""
    try:
        token = credentials.credentials
        
        # Vérifier si le token est bloqué
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if security_manager.is_token_blocked(token_hash):
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked"
            )
        
        # Décoder le token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Vérifier l'expiration
        if payload.get("exp", 0) < time.time():
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )
        
        # Vérifier l'émetteur
        if payload.get("iss") != "app.dazno.de":
            raise HTTPException(
                status_code=401,
                detail="Invalid token issuer"
            )
        
        # Vérifier l'audience
        if payload.get("aud") != "api.dazno.de":
            raise HTTPException(
                status_code=401,
                detail="Invalid token audience"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

def require_auth(request: Request, auth: Dict[str, Any] = Depends(verify_jwt_token)):
    """Middleware d'authentification"""
    # Vérifier l'IP
    client_ip = get_client_ip(request)
    if security_manager.is_ip_blocked(client_ip):
        raise HTTPException(
            status_code=403,
            detail="IP address is blocked"
        )
    
    # Vérifier le rate limiting
    if not security_manager.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
    return auth

def require_permissions(required_permissions: List[str]):
    """Middleware de vérification des permissions"""
    async def permission_checker(auth: Dict[str, Any] = Depends(require_auth)):
        user_permissions = auth.get("permissions", [])
        
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required permission: {permission}"
                )
        
        return auth
    
    return permission_checker

def get_client_ip(request: Request) -> str:
    """Récupère l'IP du client"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host

def verify_request_security(request: Request) -> Dict[str, Any]:
    """Vérifie la sécurité de la requête"""
    client_ip = get_client_ip(request)
    origin = request.headers.get("origin", "")
    user_agent = request.headers.get("user-agent", "")
    endpoint = request.url.path
    
    # Vérification IP bloquée
    if security_manager.is_ip_blocked(client_ip):
        logger.warning(f"Blocked IP attempted access: {client_ip}")
        raise HTTPException(
            status_code=403,
            detail="IP address blocked due to security violations"
        )
    
    # Vérification rate limiting
    if not security_manager.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "3600"}
        )
    
    # Vérification origine pour les requêtes CORS
    if origin and request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        if not security_manager.is_origin_allowed(origin):
            logger.warning(f"Unauthorized origin: {origin} from IP {client_ip}")
            raise HTTPException(
                status_code=403,
                detail="Origin not allowed"
            )
    
    # Détection de bots/crawlers suspects
    suspicious_agents = [
        "bot", "crawler", "spider", "scraper", "scanner",
        "wget", "python-requests", "postman"
    ]
    
    if any(agent in user_agent.lower() for agent in suspicious_agents):
        # Autoriser curl pour les health checks internes
        if not security_manager.is_ip_allowed(client_ip):
            logger.warning(f"Suspicious user agent from {client_ip}: {user_agent}")
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
    
    # Vérification de patterns d'attaque dans l'URL
    dangerous_patterns = [
        "union", "select", "insert", "delete", "update", "drop",
        "script", "javascript", "vbscript", "onload", "onerror",
        "../", "..\\", ".env", "wp-admin", "admin.php"
    ]
    
    if any(pattern in request.url.path.lower() for pattern in dangerous_patterns):
        logger.warning(f"Dangerous pattern detected from {client_ip}: {request.url.path}")
        raise HTTPException(
            status_code=403,
            detail="Request contains dangerous patterns"
        )
    
    return {
        "client_ip": client_ip,
        "origin": origin,
        "user_agent": user_agent,
        "endpoint": endpoint,
        "timestamp": datetime.now().isoformat(),
        "request_id": secrets.token_hex(8)
    }

def create_jwt_token(user_id: str, tenant_id: str, permissions: List[str] = None) -> str:
    """Crée un token JWT pour un utilisateur"""
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "permissions": permissions or [],
        "iss": "app.dazno.de",
        "aud": "api.dazno.de",
        "iat": now.timestamp(),
        "exp": (now + timedelta(hours=JWT_EXPIRATION_HOURS)).timestamp(),
        "jti": secrets.token_hex(16)  # JWT ID unique
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_permissions(required_permissions: List[str], user_permissions: List[str]) -> bool:
    """Vérifie si l'utilisateur a les permissions requises"""
    if "admin" in user_permissions:
        return True  # Admin a toutes les permissions
    
    return all(perm in user_permissions for perm in required_permissions)

def require_admin(auth_data: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Dépendance qui vérifie les permissions administrateur"""
    return require_permissions(["admin"])(auth_data)

def require_tenant_access(resource_tenant_id: str, auth_data: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Vérifie l'accès à une ressource spécifique au tenant"""
    user_tenant_id = auth_data["user"].get("tenant_id")
    user_permissions = auth_data["user"].get("permissions", [])
    
    # Admin peut accéder à tous les tenants
    if "admin" in user_permissions:
        return auth_data
    
    # Vérifier l'appartenance au tenant
    if user_tenant_id != resource_tenant_id:
        logger.warning(
            f"Tenant access denied: user_tenant={user_tenant_id} "
            f"resource_tenant={resource_tenant_id} "
            f"user={auth_data['user'].get('sub')}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: resource belongs to different tenant"
        )
    
    return auth_data

# Utilitaires de sécurité
def generate_secure_token(length: int = 32) -> str:
    """Génère un token sécurisé"""
    return secrets.token_urlsafe(length)

def hash_password(password: str) -> str:
    """Hash un mot de passe avec salt"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{pwd_hash.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe hashé"""
    try:
        salt, pwd_hash = hashed.split(':')
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() == pwd_hash
    except ValueError:
        return False 