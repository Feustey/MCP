"""
Module de sécurité asynchrone pour l'API MCP en production
Gestion de l'authentification JWT et autorisation avec Redis asyncio
Version corrigée avec gestion Redis asynchrone cohérente

Auteur: MCP Team
Version: 2.0.0
Dernière mise à jour: 19 septembre 2025
"""

import os
import jwt
import hashlib
import time
import secrets
import ipaddress
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json

# Import Redis asynchrone
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

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

# Connexion Redis asynchrone pour le cache de sécurité
redis_client = None

async def get_redis_client():
    """Obtient ou crée le client Redis asynchrone"""
    global redis_client
    if not REDIS_AVAILABLE:
        return None
    
    if redis_client is None:
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            await redis_client.ping()
            logger.info("Redis async connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Security features will be limited.")
            redis_client = None
    
    return redis_client

@dataclass
class SecurityAttempt:
    """Représente une tentative de sécurité"""
    ip: str
    count: int
    last_attempt: float
    blocked_until: Optional[float] = None

class SecurityManager:
    """Gestionnaire de sécurité centralisé avec support asynchrone"""
    
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
        client = await get_redis_client()
        if not client:
            return False  # Sans Redis, on ne bloque pas
            
        try:
            # Vérifier dans le set des IPs bloquées
            if await client.sismember(self.blocked_ips_key, ip):
                return True
                
            # Vérifier les tentatives échouées
            attempt_data = await client.get(self._get_failed_attempts_key(ip))
            if attempt_data:
                attempt = SecurityAttempt(**json.loads(attempt_data))
                if attempt.blocked_until and time.time() < attempt.blocked_until:
                    return True
        except Exception as e:
            logger.error(f"Error checking blocked IP: {e}")
                
        return False
        
    async def is_token_blocked(self, token_hash: str) -> bool:
        """Vérifie si un token est bloqué"""
        client = await get_redis_client()
        if not client:
            return False  # Sans Redis, on ne peut pas bloquer les tokens
            
        try:
            return await client.sismember(self.blocked_tokens_key, token_hash)
        except Exception as e:
            logger.error(f"Error checking blocked token: {e}")
            return False
        
    async def record_failed_attempt(self, ip: str):
        """Enregistre une tentative échouée"""
        client = await get_redis_client()
        if not client:
            return  # Sans Redis, on ne peut pas enregistrer les tentatives
            
        try:
            key = self._get_failed_attempts_key(ip)
            attempt_data = await client.get(key)
            
            if attempt_data:
                attempt = SecurityAttempt(**json.loads(attempt_data))
            else:
                attempt = SecurityAttempt(ip=ip, count=0, last_attempt=time.time())
                
            attempt.count += 1
            attempt.last_attempt = time.time()
            
            # Bloquer après 5 tentatives échouées
            if attempt.count >= 5:
                attempt.blocked_until = time.time() + 3600  # Blocage d'une heure
                await client.sadd(self.blocked_ips_key, ip)
                logger.warning(f"IP {ip} blocked after {attempt.count} failed attempts")
                
            # Sauvegarder avec expiration de 24h
            await client.setex(
                key,
                24 * 3600,  # 24 heures
                json.dumps(asdict(attempt))
            )
        except Exception as e:
            logger.error(f"Error recording failed attempt: {e}")
        
    async def check_rate_limit(self, ip: str, limit: int = 100) -> bool:
        """Vérifie le rate limiting"""
        client = await get_redis_client()
        if not client:
            return True  # Sans Redis, pas de rate limiting
            
        try:
            key = self._get_rate_limits_key(ip)
            current = await client.get(key)
            
            if current and int(current) >= limit:
                logger.warning(f"Rate limit exceeded for IP {ip}")
                return False
                
            # Incrémenter avec expiration de 1 minute
            async with client.pipeline() as pipe:
                await pipe.incr(key)
                await pipe.expire(key, 60)  # 1 minute
                await pipe.execute()
            
            return True
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # En cas d'erreur, on laisse passer
        
    async def clear_blocked_ip(self, ip: str):
        """Supprime une IP de la liste des bloquées"""
        client = await get_redis_client()
        if not client:
            return
            
        try:
            async with client.pipeline() as pipe:
                await pipe.srem(self.blocked_ips_key, ip)
                await pipe.delete(self._get_failed_attempts_key(ip))
                await pipe.execute()
            logger.info(f"IP {ip} unblocked")
        except Exception as e:
            logger.error(f"Error clearing blocked IP: {e}")
        
    async def clear_blocked_token(self, token_hash: str):
        """Supprime un token de la liste des bloqués"""
        client = await get_redis_client()
        if not client:
            return
            
        try:
            await client.srem(self.blocked_tokens_key, token_hash)
            logger.info(f"Token unblocked")
        except Exception as e:
            logger.error(f"Error clearing blocked token: {e}")
        
    async def block_token(self, token_hash: str):
        """Ajoute un token à la liste des bloqués"""
        client = await get_redis_client()
        if not client:
            return
            
        try:
            await client.sadd(self.blocked_tokens_key, token_hash)
            logger.info(f"Token blocked")
        except Exception as e:
            logger.error(f"Error blocking token: {e}")
        
    async def clear_rate_limits(self, ip: str):
        """Réinitialise les limites de taux pour une IP"""
        client = await get_redis_client()
        if not client:
            return
            
        try:
            await client.delete(self._get_rate_limits_key(ip))
            logger.info(f"Rate limits cleared for IP {ip}")
        except Exception as e:
            logger.error(f"Error clearing rate limits: {e}")

# Instance globale du gestionnaire de sécurité
security_manager = SecurityManager()

async def verify_jwt_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Vérifie et décode le token JWT avec vérifications de sécurité"""
    try:
        token = credentials.credentials
        
        # Obtenir l'IP du client
        client_ip = request.client.host if request.client else "unknown"
        
        # Vérifier si l'IP est bloquée
        if await security_manager.is_ip_blocked(client_ip):
            raise HTTPException(
                status_code=403,
                detail="IP address is blocked"
            )
        
        # Vérifier le rate limiting
        if not await security_manager.check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        # Vérifier si le token est bloqué
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if await security_manager.is_token_blocked(token_hash):
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked"
            )
        
        # Décoder le token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Vérifier l'expiration
        if payload.get("exp", 0) < time.time():
            await security_manager.record_failed_attempt(client_ip)
            raise HTTPException(
                status_code=401,
                detail="Token expired"
            )
        
        # Vérifier l'émetteur
        if payload.get("iss") != "app.dazno.de":
            await security_manager.record_failed_attempt(client_ip)
            raise HTTPException(
                status_code=401,
                detail="Invalid token issuer"
            )
        
        # Vérifier l'audience
        if payload.get("aud") != "api.dazno.de":
            await security_manager.record_failed_attempt(client_ip)
            raise HTTPException(
                status_code=401,
                detail="Invalid token audience"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        await security_manager.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        await security_manager.record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in JWT verification: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

def create_jwt_token(
    user_id: str,
    role: str = "user",
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Crée un nouveau token JWT"""
    payload = {
        "sub": user_id,
        "role": role,
        "iss": "app.dazno.de",
        "aud": "api.dazno.de",
        "iat": time.time(),
        "exp": time.time() + (JWT_EXPIRATION_HOURS * 3600),
        "jti": secrets.token_urlsafe(16)  # Token ID unique
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def revoke_token(token: str):
    """Révoque un token en l'ajoutant à la liste noire"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await security_manager.block_token(token_hash)

def is_ip_allowed(ip: str) -> bool:
    """Vérifie si une IP est dans la liste des IPs autorisées"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        for allowed in ALLOWED_IPS:
            if "/" in allowed:
                # C'est un réseau
                if ip_obj in ipaddress.ip_network(allowed, strict=False):
                    return True
            elif ip == allowed:
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking IP allowlist: {e}")
        return False

def is_origin_allowed(origin: str) -> bool:
    """Vérifie si une origine est autorisée"""
    return origin in ALLOWED_ORIGINS

# Middleware de sécurité pour vérifier les IPs et origines
async def security_middleware(request: Request):
    """Middleware de sécurité pour vérifier les requêtes entrantes"""
    # Obtenir l'IP du client
    client_ip = request.client.host if request.client else None
    
    # En production, vérifier l'IP
    if os.getenv("ENVIRONMENT") == "production":
        if client_ip and not is_ip_allowed(client_ip):
            logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
            raise HTTPException(
                status_code=403,
                detail="Access denied from this IP address"
            )
    
    # Vérifier l'origine
    origin = request.headers.get("origin")
    if origin and not is_origin_allowed(origin):
        logger.warning(f"Blocked request from unauthorized origin: {origin}")
        raise HTTPException(
            status_code=403,
            detail="Access denied from this origin"
        )
    
    return True