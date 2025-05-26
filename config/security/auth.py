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
    # IPs des serveurs autorisés (à compléter selon l'infrastructure)
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
    
@dataclass 
class RateLimit:
    """Représente une limite de taux"""
    ip: str
    requests: int
    window_start: float
    endpoint: Optional[str] = None

class SecurityManager:
    """Gestionnaire de sécurité principal"""
    
    def __init__(self):
        self.failed_attempts: Dict[str, SecurityAttempt] = {}
        self.rate_limits: Dict[str, RateLimit] = {}
        self.blocked_ips: set = set()
        self.blocked_tokens: set = set()
        
        # Configuration des limites
        self.max_failed_attempts = 5
        self.block_duration = 3600  # 1 heure
        self.rate_limit_window = 3600  # 1 heure
        self.default_rate_limit = 100  # requêtes par heure
        
        # Limites spécifiques par endpoint
        self.endpoint_limits = {
            "/api/v1/auth": 10,
            "/api/v1/login": 10,
            "/api/v1/token": 10,
            "/api/v1/admin": 5,
            "/api/v1/optimize": 50,
            "/api/v1/simulate": 30
        }
    
    def _get_redis_key(self, category: str, identifier: str) -> str:
        """Génère une clé Redis"""
        return f"mcp:security:{category}:{identifier}"
    
    def _store_in_redis(self, key: str, data: Dict, ttl: int = 3600):
        """Stocke des données dans Redis avec TTL"""
        if redis_client:
            try:
                redis_client.setex(key, ttl, json.dumps(data))
            except Exception as e:
                logger.warning(f"Redis storage failed: {e}")
    
    def _get_from_redis(self, key: str) -> Optional[Dict]:
        """Récupère des données depuis Redis"""
        if redis_client:
            try:
                data = redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis retrieval failed: {e}")
        return None
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Vérifie si l'origine est autorisée"""
        if not origin:
            return False
        return origin in ALLOWED_ORIGINS
    
    def is_ip_allowed(self, ip: str) -> bool:
        """Vérifie si l'IP est autorisée"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Vérifier les plages autorisées
            for allowed_range in ALLOWED_IPS:
                if "/" in allowed_range:
                    # Plage réseau
                    if ip_obj in ipaddress.ip_network(allowed_range):
                        return True
                else:
                    # IP spécifique
                    if ip_obj == ipaddress.ip_address(allowed_range):
                        return True
            
            return False
        except ValueError:
            logger.warning(f"Invalid IP address: {ip}")
            return False
    
    def check_rate_limit(self, ip: str, endpoint: str = None, limit: int = None) -> bool:
        """Vérifie le rate limiting"""
        now = time.time()
        limit = limit or self.endpoint_limits.get(endpoint, self.default_rate_limit)
        
        # Clé pour Redis
        redis_key = self._get_redis_key("rate_limit", f"{ip}:{endpoint or 'default'}")
        
        # Récupérer depuis Redis ou mémoire
        rate_data = self._get_from_redis(redis_key)
        if not rate_data and ip in self.rate_limits:
            rate_limit = self.rate_limits[ip]
            rate_data = asdict(rate_limit)
        
        if rate_data:
            requests = rate_data["requests"]
            window_start = rate_data["window_start"]
            
            # Nouvelle fenêtre
            if now - window_start > self.rate_limit_window:
                new_data = {"ip": ip, "requests": 1, "window_start": now, "endpoint": endpoint}
                self.rate_limits[ip] = RateLimit(**new_data)
                self._store_in_redis(redis_key, new_data, self.rate_limit_window)
                return True
            
            # Dans la fenêtre actuelle
            if requests >= limit:
                logger.warning(f"Rate limit exceeded for IP {ip} on endpoint {endpoint}")
                return False
            
            # Incrémenter
            new_requests = requests + 1
            new_data = {"ip": ip, "requests": new_requests, "window_start": window_start, "endpoint": endpoint}
            self.rate_limits[ip] = RateLimit(**new_data)
            self._store_in_redis(redis_key, new_data, self.rate_limit_window)
        else:
            # Première requête
            new_data = {"ip": ip, "requests": 1, "window_start": now, "endpoint": endpoint}
            self.rate_limits[ip] = RateLimit(**new_data)
            self._store_in_redis(redis_key, new_data, self.rate_limit_window)
        
        return True
    
    def record_failed_attempt(self, ip: str):
        """Enregistre une tentative d'authentification échouée"""
        now = time.time()
        redis_key = self._get_redis_key("failed_attempts", ip)
        
        # Récupérer les tentatives existantes
        attempt_data = self._get_from_redis(redis_key)
        if not attempt_data and ip in self.failed_attempts:
            attempt_data = asdict(self.failed_attempts[ip])
        
        if attempt_data:
            count = attempt_data["count"]
            last_attempt = attempt_data["last_attempt"]
            
            # Reset si plus de 1 heure
            if now - last_attempt > 3600:
                new_count = 1
            else:
                new_count = count + 1
        else:
            new_count = 1
        
        # Créer nouveau record
        attempt = SecurityAttempt(
            ip=ip,
            count=new_count,
            last_attempt=now,
            blocked_until=now + self.block_duration if new_count >= self.max_failed_attempts else None
        )
        
        self.failed_attempts[ip] = attempt
        self._store_in_redis(redis_key, asdict(attempt), self.block_duration)
        
        # Bloquer si trop de tentatives
        if new_count >= self.max_failed_attempts:
            self.blocked_ips.add(ip)
            logger.warning(f"IP {ip} blocked after {new_count} failed attempts")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Vérifie si l'IP est bloquée"""
        if ip in self.blocked_ips:
            return True
        
        # Vérifier dans Redis
        redis_key = self._get_redis_key("failed_attempts", ip)
        attempt_data = self._get_from_redis(redis_key)
        
        if attempt_data and attempt_data.get("blocked_until"):
            if time.time() < attempt_data["blocked_until"]:
                return True
            else:
                # Débloquer automatiquement
                self.blocked_ips.discard(ip)
        
        return False
    
    def is_token_blocked(self, token_hash: str) -> bool:
        """Vérifie si un token est bloqué"""
        return token_hash in self.blocked_tokens
    
    def block_token(self, token: str, reason: str = "security_violation"):
        """Bloque un token JWT"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.blocked_tokens.add(token_hash)
        
        # Stocker dans Redis
        redis_key = self._get_redis_key("blocked_tokens", token_hash)
        self._store_in_redis(redis_key, {"reason": reason, "blocked_at": time.time()}, 86400)
        
        logger.warning(f"Token blocked: {token_hash[:16]}... (reason: {reason})")

# Instance globale
security_manager = SecurityManager()

def get_client_ip(request: Request) -> str:
    """Récupère l'IP réelle du client en tenant compte des proxies"""
    # Vérifier les headers de proxy
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Prendre la première IP (client original)
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    
    # Fallback sur l'IP directe
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
    if not security_manager.check_rate_limit(client_ip, endpoint):
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

# Dépendances FastAPI
def require_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dépendance qui vérifie l'authentification complète"""
    # Vérification sécurité générale
    security_info = verify_request_security(request)
    
    try:
        # Vérification JWT
        token_payload = verify_jwt_token(credentials)
        
        # Logging de l'accès authentifié
        logger.info(
            f"Authenticated access: user={token_payload.get('sub')} "
            f"tenant={token_payload.get('tenant_id')} "
            f"ip={security_info['client_ip']} "
            f"endpoint={security_info['endpoint']}"
        )
        
        return {
            "security": security_info,
            "user": token_payload
        }
        
    except HTTPException as e:
        # Enregistrer la tentative échouée
        security_manager.record_failed_attempt(security_info["client_ip"])
        raise e

def require_permissions(*required_permissions: str):
    """Dépendance pour vérifier des permissions spécifiques"""
    def permission_checker(auth_data: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        user_permissions = auth_data["user"].get("permissions", [])
        
        if not verify_permissions(list(required_permissions), user_permissions):
            logger.warning(
                f"Permission denied: user={auth_data['user'].get('sub')} "
                f"required={required_permissions} "
                f"has={user_permissions}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {', '.join(required_permissions)}"
            )
        
        return auth_data
    
    return permission_checker

def require_admin(auth_data: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Dépendance qui vérifie les permissions administrateur"""
    return require_permissions("admin")(auth_data)

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