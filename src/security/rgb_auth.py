"""
Système d'authentification et de sécurité pour les APIs RGB

Ce module fournit :
- Authentification JWT pour les APIs RGB
- Validation des tokens mainnet RGB++
- Gestion des permissions et des rôles
- Rate limiting pour les endpoints RGB
- Audit et logging sécurisé
- Validation des signatures RGB

Dernière mise à jour: 23 août 2025
"""

import jwt
import asyncio
import json
import logging
import hashlib
import hmac
import secrets
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis.asyncio as redis
import time
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# Configuration du logging sécurisé
logger = logging.getLogger("rgb-auth")

class RGBPermission(Enum):
    """Permissions pour les APIs RGB"""
    READ_ASSETS = "read_assets"
    CREATE_ASSETS = "create_assets"
    TRANSFER_ASSETS = "transfer_assets"
    READ_CONTRACTS = "read_contracts"
    DEPLOY_CONTRACTS = "deploy_contracts"
    EXECUTE_CONTRACTS = "execute_contracts"
    READ_TRANSACTIONS = "read_transactions"
    SUBMIT_TRANSACTIONS = "submit_transactions"
    ADMIN_ACCESS = "admin_access"
    MAINNET_ACCESS = "mainnet_access"

class RGBRole(Enum):
    """Rôles utilisateur pour RGB"""
    ANONYMOUS = "anonymous"
    USER = "user"
    DEVELOPER = "developer"
    VALIDATOR = "validator"
    ADMIN = "admin"
    SYSTEM = "system"

@dataclass
class RGBUser:
    """Représentation d'un utilisateur RGB"""
    user_id: str
    username: str
    role: RGBRole
    permissions: List[RGBPermission]
    public_key: Optional[str]
    api_key_hash: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    login_count: int
    is_active: bool
    metadata: Dict[str, Any]

@dataclass
class RGBToken:
    """Token d'authentification RGB"""
    token_id: str
    user_id: str
    token_type: str  # "api_key", "jwt", "session"
    permissions: List[RGBPermission]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime]
    use_count: int
    is_active: bool

class RGBSecurity:
    """
    Gestionnaire de sécurité pour les APIs RGB
    
    Fournit l'authentification, l'autorisation et la sécurité
    pour toutes les opérations RGB
    """
    
    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        token_expiry: int = 3600,  # 1 heure
        redis_url: Optional[str] = None,
        rate_limit_requests: int = 100,  # par minute
        rate_limit_window: int = 60
    ):
        """
        Initialise le gestionnaire de sécurité RGB
        
        Args:
            jwt_secret: Secret pour signer les tokens JWT
            jwt_algorithm: Algorithme de signature JWT
            token_expiry: Durée de vie des tokens en secondes
            redis_url: URL Redis pour le cache et rate limiting
            rate_limit_requests: Nombre max de requêtes par fenêtre
            rate_limit_window: Taille de la fenêtre en secondes
        """
        self.jwt_secret = jwt_secret or os.getenv("RGB_JWT_SECRET") or secrets.token_urlsafe(64)
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry = token_expiry
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        
        # Redis pour le cache et rate limiting
        self.redis_client: Optional[redis.Redis] = None
        
        # Cache local des utilisateurs et tokens
        self._user_cache: Dict[str, RGBUser] = {}
        self._token_cache: Dict[str, RGBToken] = {}
        
        # Permissions par rôle
        self.role_permissions = self._init_role_permissions()
        
        logger.info("RGB Security initialisé")
    
    def _init_role_permissions(self) -> Dict[RGBRole, List[RGBPermission]]:
        """Initialise les permissions par rôle"""
        return {
            RGBRole.ANONYMOUS: [
                RGBPermission.READ_ASSETS,
                RGBPermission.READ_CONTRACTS,
                RGBPermission.READ_TRANSACTIONS
            ],
            RGBRole.USER: [
                RGBPermission.READ_ASSETS,
                RGBPermission.TRANSFER_ASSETS,
                RGBPermission.READ_CONTRACTS,
                RGBPermission.READ_TRANSACTIONS,
                RGBPermission.SUBMIT_TRANSACTIONS
            ],
            RGBRole.DEVELOPER: [
                RGBPermission.READ_ASSETS,
                RGBPermission.CREATE_ASSETS,
                RGBPermission.TRANSFER_ASSETS,
                RGBPermission.READ_CONTRACTS,
                RGBPermission.DEPLOY_CONTRACTS,
                RGBPermission.EXECUTE_CONTRACTS,
                RGBPermission.READ_TRANSACTIONS,
                RGBPermission.SUBMIT_TRANSACTIONS
            ],
            RGBRole.VALIDATOR: [
                RGBPermission.READ_ASSETS,
                RGBPermission.READ_CONTRACTS,
                RGBPermission.READ_TRANSACTIONS,
                RGBPermission.SUBMIT_TRANSACTIONS
            ],
            RGBRole.ADMIN: [perm for perm in RGBPermission],  # Toutes les permissions
            RGBRole.SYSTEM: [perm for perm in RGBPermission]   # Toutes les permissions
        }
    
    async def connect(self):
        """Établit les connexions nécessaires"""
        try:
            if self.redis_url:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Connexion Redis établie pour RGB Security")
                
        except Exception as e:
            logger.error(f"Erreur connexion Redis: {e}")
            # Continuer sans Redis si nécessaire
    
    async def disconnect(self):
        """Ferme les connexions"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    # Authentification JWT
    def create_jwt_token(
        self,
        user: RGBUser,
        custom_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crée un token JWT pour un utilisateur
        
        Args:
            user: Utilisateur RGB
            custom_claims: Claims supplémentaires
            
        Returns:
            Token JWT signé
        """
        try:
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=self.token_expiry)
            
            payload = {
                "sub": user.user_id,
                "username": user.username,
                "role": user.role.value,
                "permissions": [p.value for p in user.permissions],
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
                "iss": "mcp-rgb-api",
                "aud": "rgb-clients"
            }
            
            if custom_claims:
                payload.update(custom_claims)
            
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            # Cache le token
            rgb_token = RGBToken(
                token_id=hashlib.sha256(token.encode()).hexdigest()[:16],
                user_id=user.user_id,
                token_type="jwt",
                permissions=user.permissions,
                expires_at=expires_at,
                created_at=now,
                last_used=None,
                use_count=0,
                is_active=True
            )
            self._token_cache[token] = rgb_token
            
            logger.info(f"Token JWT créé pour {user.username}")
            return token
            
        except Exception as e:
            logger.error(f"Erreur création token JWT: {e}")
            raise
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Vérifie et décode un token JWT
        
        Args:
            token: Token JWT à vérifier
            
        Returns:
            Payload du token si valide, None sinon
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                audience="rgb-clients",
                issuer="mcp-rgb-api"
            )
            
            # Mettre à jour l'usage du token
            if token in self._token_cache:
                self._token_cache[token].last_used = datetime.utcnow()
                self._token_cache[token].use_count += 1
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT expiré")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token JWT invalide: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur vérification JWT: {e}")
            return None
    
    # Gestion des API Keys
    def generate_api_key(
        self,
        user: RGBUser,
        permissions: Optional[List[RGBPermission]] = None,
        expires_at: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """
        Génère une nouvelle API key pour un utilisateur
        
        Args:
            user: Utilisateur RGB
            permissions: Permissions spécifiques (par défaut: permissions du rôle)
            expires_at: Date d'expiration (optionnelle)
            
        Returns:
            Tuple (api_key, api_key_hash)
        """
        try:
            # Générer une clé aléatoire sécurisée
            api_key = f"rgb_{secrets.token_urlsafe(32)}"
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Permissions par défaut selon le rôle
            if permissions is None:
                permissions = self.role_permissions.get(user.role, [])
            
            # Créer le token
            rgb_token = RGBToken(
                token_id=api_key_hash[:16],
                user_id=user.user_id,
                token_type="api_key",
                permissions=permissions,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                last_used=None,
                use_count=0,
                is_active=True
            )
            
            # Cache le token
            self._token_cache[api_key_hash] = rgb_token
            
            logger.info(f"API key générée pour {user.username}")
            return api_key, api_key_hash
            
        except Exception as e:
            logger.error(f"Erreur génération API key: {e}")
            raise
    
    def verify_api_key(self, api_key: str) -> Optional[RGBToken]:
        """
        Vérifie une API key
        
        Args:
            api_key: Clé API à vérifier
            
        Returns:
            RGBToken si valide, None sinon
        """
        try:
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Vérifier dans le cache
            if api_key_hash in self._token_cache:
                token = self._token_cache[api_key_hash]
                
                # Vérifier l'expiration
                if token.expires_at and token.expires_at < datetime.utcnow():
                    logger.warning(f"API key expirée: {token.token_id}")
                    return None
                
                # Vérifier si active
                if not token.is_active:
                    logger.warning(f"API key inactive: {token.token_id}")
                    return None
                
                # Mettre à jour l'usage
                token.last_used = datetime.utcnow()
                token.use_count += 1
                
                return token
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur vérification API key: {e}")
            return None
    
    # Rate Limiting
    async def check_rate_limit(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Vérifie le rate limiting pour un identifiant
        
        Args:
            identifier: Identifiant unique (user_id, IP, etc.)
            limit: Limite de requêtes (par défaut: configuration)
            window: Fenêtre en secondes (par défaut: configuration)
            
        Returns:
            Tuple (is_allowed, rate_info)
        """
        try:
            limit = limit or self.rate_limit_requests
            window = window or self.rate_limit_window
            
            if not self.redis_client:
                # Sans Redis, permettre toutes les requêtes
                return True, {
                    "allowed": True,
                    "limit": limit,
                    "remaining": limit,
                    "reset_at": int(time.time() + window)
                }
            
            # Clé Redis pour le rate limiting
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - window
            
            # Pipeline Redis pour atomicité
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)  # Supprimer les anciennes entrées
            pipe.zcard(key)  # Compter les requêtes actuelles
            pipe.zadd(key, {str(current_time): current_time})  # Ajouter la requête actuelle
            pipe.expire(key, window)  # Définir l'expiration
            
            results = await pipe.execute()
            current_requests = results[1]
            
            if current_requests >= limit:
                return False, {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_at": current_time + window,
                    "retry_after": window
                }
            
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit - current_requests - 1,
                "reset_at": current_time + window
            }
            
        except Exception as e:
            logger.error(f"Erreur rate limiting: {e}")
            # En cas d'erreur, permettre la requête
            return True, {
                "allowed": True,
                "error": str(e)
            }
    
    # Validation des signatures RGB
    def verify_rgb_signature(
        self,
        message: bytes,
        signature: bytes,
        public_key: bytes
    ) -> bool:
        """
        Vérifie une signature ED25519 RGB
        
        Args:
            message: Message original
            signature: Signature à vérifier
            public_key: Clé publique ED25519
            
        Returns:
            True si signature valide, False sinon
        """
        try:
            # Charger la clé publique ED25519
            ed25519_public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
            
            # Vérifier la signature
            ed25519_public_key.verify(signature, message)
            return True
            
        except InvalidSignature:
            logger.warning("Signature RGB invalide")
            return False
        except Exception as e:
            logger.error(f"Erreur vérification signature RGB: {e}")
            return False
    
    def create_rgb_signature(
        self,
        message: bytes,
        private_key: bytes
    ) -> bytes:
        """
        Crée une signature ED25519 RGB
        
        Args:
            message: Message à signer
            private_key: Clé privée ED25519
            
        Returns:
            Signature ED25519
        """
        try:
            # Charger la clé privée ED25519
            ed25519_private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
            
            # Créer la signature
            signature = ed25519_private_key.sign(message)
            return signature
            
        except Exception as e:
            logger.error(f"Erreur création signature RGB: {e}")
            raise
    
    # Gestion des utilisateurs
    async def create_user(
        self,
        username: str,
        role: RGBRole = RGBRole.USER,
        public_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RGBUser:
        """
        Crée un nouvel utilisateur RGB
        
        Args:
            username: Nom d'utilisateur
            role: Rôle de l'utilisateur
            public_key: Clé publique optionnelle
            metadata: Métadonnées supplémentaires
            
        Returns:
            Utilisateur RGB créé
        """
        try:
            user_id = hashlib.sha256(f"{username}_{int(time.time())}".encode()).hexdigest()[:16]
            permissions = self.role_permissions.get(role, [])
            
            user = RGBUser(
                user_id=user_id,
                username=username,
                role=role,
                permissions=permissions,
                public_key=public_key,
                api_key_hash=None,
                created_at=datetime.utcnow(),
                last_login=None,
                login_count=0,
                is_active=True,
                metadata=metadata or {}
            )
            
            # Cache l'utilisateur
            self._user_cache[user_id] = user
            
            logger.info(f"Utilisateur RGB créé: {username} ({role.value})")
            return user
            
        except Exception as e:
            logger.error(f"Erreur création utilisateur: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[RGBUser]:
        """
        Récupère un utilisateur par son ID
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            RGBUser si trouvé, None sinon
        """
        return self._user_cache.get(user_id)
    
    def check_permission(
        self,
        user: RGBUser,
        required_permission: RGBPermission
    ) -> bool:
        """
        Vérifie qu'un utilisateur a une permission
        
        Args:
            user: Utilisateur RGB
            required_permission: Permission requise
            
        Returns:
            True si permission accordée, False sinon
        """
        return required_permission in user.permissions or RGBPermission.ADMIN_ACCESS in user.permissions
    
    # Audit et logging
    async def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO"
    ):
        """
        Enregistre un événement de sécurité
        
        Args:
            event_type: Type d'événement
            user_id: ID de l'utilisateur concerné
            details: Détails supplémentaires
            severity: Niveau de sévérité (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "details": details or {},
                "severity": severity
            }
            
            # Log selon la sévérité
            if severity == "DEBUG":
                logger.debug(f"RGB Security Event: {json.dumps(log_entry)}")
            elif severity == "INFO":
                logger.info(f"RGB Security Event: {json.dumps(log_entry)}")
            elif severity == "WARNING":
                logger.warning(f"RGB Security Event: {json.dumps(log_entry)}")
            elif severity == "ERROR":
                logger.error(f"RGB Security Event: {json.dumps(log_entry)}")
            elif severity == "CRITICAL":
                logger.critical(f"RGB Security Event: {json.dumps(log_entry)}")
            
            # Stocker dans Redis si disponible
            if self.redis_client:
                key = f"security_events:{datetime.utcnow().strftime('%Y-%m-%d')}"
                await self.redis_client.lpush(key, json.dumps(log_entry))
                await self.redis_client.expire(key, 86400 * 30)  # 30 jours
                
        except Exception as e:
            logger.error(f"Erreur logging événement sécurité: {e}")


# Dépendances FastAPI pour l'authentification
security = HTTPBearer()
rgb_security = RGBSecurity()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> RGBUser:
    """
    Dépendance FastAPI pour récupérer l'utilisateur courant
    
    Args:
        credentials: Credentials HTTP Bearer
        
    Returns:
        Utilisateur RGB authentifié
        
    Raises:
        HTTPException: Si authentification échoue
    """
    try:
        token = credentials.credentials
        
        # Essayer JWT d'abord
        payload = rgb_security.verify_jwt_token(token)
        if payload:
            user = await rgb_security.get_user(payload["sub"])
            if user and user.is_active:
                await rgb_security.log_security_event("jwt_auth_success", user.user_id)
                return user
        
        # Essayer API Key
        rgb_token = rgb_security.verify_api_key(token)
        if rgb_token:
            user = await rgb_security.get_user(rgb_token.user_id)
            if user and user.is_active:
                await rgb_security.log_security_event("api_key_auth_success", user.user_id)
                return user
        
        # Authentification échouée
        await rgb_security.log_security_event("auth_failure", None, {"token": token[:10] + "..."}, "WARNING")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification invalide ou expiré"
        )
        
    except Exception as e:
        await rgb_security.log_security_event("auth_error", None, {"error": str(e)}, "ERROR")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur d'authentification"
        )

def require_permission(permission: RGBPermission):
    """
    Décorateur pour exiger une permission spécifique
    
    Args:
        permission: Permission requise
        
    Returns:
        Fonction de dépendance FastAPI
    """
    def permission_dependency(user: RGBUser = Depends(get_current_user)) -> RGBUser:
        if not rgb_security.check_permission(user, permission):
            rgb_security.log_security_event(
                "permission_denied",
                user.user_id,
                {"required_permission": permission.value},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission requise: {permission.value}"
            )
        return user
    
    return permission_dependency

async def check_rate_limit_dependency(request: Request):
    """
    Dépendance FastAPI pour le rate limiting
    
    Args:
        request: Requête FastAPI
        
    Raises:
        HTTPException: Si limite de taux dépassée
    """
    try:
        # Utiliser l'IP client comme identifiant
        client_ip = request.client.host
        
        allowed, rate_info = await rgb_security.check_rate_limit(client_ip)
        
        if not allowed:
            await rgb_security.log_security_event(
                "rate_limit_exceeded",
                None,
                {"client_ip": client_ip, "rate_info": rate_info},
                "WARNING"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Limite de taux dépassée",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info.get("remaining", 0)),
                    "X-RateLimit-Reset": str(rate_info.get("reset_at", 0)),
                    "Retry-After": str(rate_info.get("retry_after", 60))
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur rate limiting dependency: {e}")
        # En cas d'erreur, permettre la requête