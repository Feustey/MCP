"""
Configuration des variables d'environnement
Gestion des variables d'environnement pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field
from functools import lru_cache

# Configuration du logging
logger = logging.getLogger("mcp.config")

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Environnement
    ENV: str = Field(default="production", env="ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")
    TESTING: bool = Field(default=False, env="TESTING")
    
    # API
    API_TITLE: str = Field(default="MCP Lightning Optimizer API", env="API_TITLE")
    API_VERSION: str = Field(default="1.0.0", env="API_VERSION")
    API_DESCRIPTION: str = Field(default="API pour l'optimisation des nœuds Lightning", env="API_DESCRIPTION")
    API_PREFIX: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Serveur
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    RELOAD: bool = Field(default=False, env="RELOAD")
    
    # Base de données
    MONGO_URI: str = Field(default="mongodb://localhost:27017", env="MONGO_URI")
    MONGO_DB: str = Field(default="mcp", env="MONGO_DB")
    MONGO_USER: Optional[str] = Field(default=None, env="MONGO_USER")
    MONGO_PASSWORD: Optional[str] = Field(default=None, env="MONGO_PASSWORD")
    MONGO_AUTH_SOURCE: str = Field(default="admin", env="MONGO_AUTH_SOURCE")
    MONGO_REPLICA_SET: Optional[str] = Field(default=None, env="MONGO_REPLICA_SET")
    MONGO_SSL: bool = Field(default=True, env="MONGO_SSL")
    MONGO_SSL_CA_CERTS: Optional[str] = Field(default=None, env="MONGO_SSL_CA_CERTS")
    
    # Cache Redis
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_SSL: bool = Field(default=True, env="REDIS_SSL")
    
    # Sécurité
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    ALLOWED_ORIGINS: list = Field(default=["https://app.dazno.de"], env="ALLOWED_ORIGINS")
    ALLOWED_IPS: list = Field(default=["127.0.0.1", "::1"], env="ALLOWED_IPS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_DIR: str = Field(default="logs", env="LOG_DIR")
    LOG_MAX_SIZE: int = Field(default=10485760, env="LOG_MAX_SIZE")  # 10MB
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")
    LOG_RETENTION_DAYS: int = Field(default=30, env="LOG_RETENTION_DAYS")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    ENABLE_TRACING: bool = Field(default=True, env="ENABLE_TRACING")
    
    # Stockage
    STORAGE_TYPE: str = Field(default="local", env="STORAGE_TYPE")
    STORAGE_PATH: str = Field(default="storage", env="STORAGE_PATH")
    STORAGE_MAX_SIZE: int = Field(default=1073741824, env="STORAGE_MAX_SIZE")  # 1GB
    STORAGE_ALLOWED_TYPES: list = Field(default=["image/jpeg", "image/png", "application/pdf"], env="STORAGE_ALLOWED_TYPES")
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    GRAFANA_ADMIN_PASSWORD: Optional[str] = Field(default=None, env="GRAFANA_ADMIN_PASSWORD")
    
    # Performance
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 1 heure
    RATE_LIMIT: int = Field(default=100, env="RATE_LIMIT")  # requêtes par minute
    RATE_LIMIT_BURST: int = Field(default=200, env="RATE_LIMIT_BURST")
    TIMEOUT: int = Field(default=30, env="TIMEOUT")  # secondes
    
    class Config:
        """Configuration Pydantic"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Récupère la configuration de l'application"""
    try:
        settings = Settings()
        logger.info("Loaded application settings", extra={
            "env": settings.ENV,
            "debug": settings.DEBUG,
            "testing": settings.TESTING
        })
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {str(e)}")
        raise

# Instance globale
settings = get_settings()

def get_env_vars() -> Dict[str, Any]:
    """Récupère toutes les variables d'environnement"""
    return {
        "environment": {
            "ENV": settings.ENV,
            "DEBUG": settings.DEBUG,
            "TESTING": settings.TESTING
        },
        "api": {
            "TITLE": settings.API_TITLE,
            "VERSION": settings.API_VERSION,
            "PREFIX": settings.API_PREFIX
        },
        "server": {
            "HOST": settings.HOST,
            "PORT": settings.PORT,
            "WORKERS": settings.WORKERS
        },
        "database": {
            "URI": settings.MONGO_URI,
            "DB": settings.MONGO_DB,
            "SSL": settings.MONGO_SSL
        },
        "cache": {
            "HOST": settings.REDIS_HOST,
            "PORT": settings.REDIS_PORT,
            "SSL": settings.REDIS_SSL
        },
        "security": {
            "JWT_ALGORITHM": settings.JWT_ALGORITHM,
            "JWT_EXPIRATION": settings.JWT_EXPIRATION_HOURS
        },
        "logging": {
            "LEVEL": settings.LOG_LEVEL,
            "FORMAT": settings.LOG_FORMAT,
            "DIR": settings.LOG_DIR
        },
        "monitoring": {
            "METRICS": settings.ENABLE_METRICS,
            "TRACING": settings.ENABLE_TRACING
        },
        "storage": {
            "TYPE": settings.STORAGE_TYPE,
            "PATH": settings.STORAGE_PATH,
            "MAX_SIZE": settings.STORAGE_MAX_SIZE
        },
        "performance": {
            "CACHE_TTL": settings.CACHE_TTL,
            "RATE_LIMIT": settings.RATE_LIMIT,
            "TIMEOUT": settings.TIMEOUT
        }
    } 