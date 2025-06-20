"""
Configuration centralisée pour l'application MCP avec Pydantic Settings
Optimisée pour les performances et la validation

Dernière mise à jour: 20 juin 2025
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl
import structlog
import logging.config

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Configuration principale de l'application MCP. 
    Charge les variables d'environnement.
    """
    
    # Métadonnées
    app_name: str = "MCP Lightning Network Optimizer"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    dry_run: bool = True

    # Serveur
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Base de données MongoDB
    mongo_url: str = Field(..., alias="MONGO_URL")
    mongo_name: str = Field("mcp", alias="MONGO_NAME")
    
    # Redis
    redis_host: str = Field("localhost", alias="REDIS_HOST")
    redis_port: int = Field(6379, alias="REDIS_PORT")
    redis_username: Optional[str] = Field("default", alias="REDIS_USERNAME")
    redis_password: Optional[str] = Field("", alias="REDIS_PASSWORD")
    redis_ssl: bool = Field(False, alias="REDIS_SSL")

    # IA et modèles
    ai_openai_api_key: str = Field(..., alias="AI_OPENAI_API_KEY")
    ai_openai_model: str = Field("gpt-3.5-turbo", alias="AI_OPENAI_MODEL")
    ai_openai_embedding_model: str = Field("text-embedding-3-small", alias="AI_OPENAI_EMBEDDING_MODEL")

    # LNBits
    lnbits_inkey: str = Field(..., alias="LNBITS_INKEY")
    lnbits_admin_key: Optional[str] = Field(None, alias="LNBITS_ADMIN_KEY")
    lnbits_url: Optional[str] = Field(None, alias="LNBITS_URL")

    # Performance
    perf_response_cache_ttl: int = Field(3600, alias="PERF_RESPONSE_CACHE_TTL")
    perf_embedding_cache_ttl: int = Field(86400, alias="PERF_EMBEDDING_CACHE_TTL")
    perf_max_workers: int = Field(4, alias="PERF_MAX_WORKERS")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_format: str = Field("json", alias="LOG_FORMAT")
    log_enable_structlog: bool = Field(True, alias="LOG_ENABLE_STRUCTLOG")
    log_enable_file_logging: bool = Field(True, alias="LOG_ENABLE_FILE_LOGGING")
    log_log_file_path: str = Field("logs/mcp.log", alias="LOG_LOG_FILE_PATH")
    log_max_file_size: int = Field(10485760, alias="LOG_MAX_FILE_SIZE")
    log_backup_count: int = Field(5, alias="LOG_BACKUP_COUNT")
    log_enable_tracing: bool = Field(False, alias="LOG_ENABLE_TRACING")
    log_otel_endpoint: Optional[str] = Field(None, alias="LOG_OTEL_ENDPOINT")

    # Sécurité
    security_secret_key: str = Field(..., alias="SECURITY_SECRET_KEY")
    security_cors_origins: List[str] = Field(["*"], alias="SECURITY_CORS_ORIGINS")
    security_allowed_hosts: List[str] = Field(["*"], alias="SECURITY_ALLOWED_HOSTS")

    # Heuristiques
    heuristic_centrality_weight: float = Field(0.4, alias="HEURISTIC_CENTRALITY_WEIGHT")
    heuristic_capacity_weight: float = Field(0.2, alias="HEURISTIC_CAPACITY_WEIGHT")
    heuristic_reputation_weight: float = Field(0.2, alias="HEURISTIC_REPUTATION_WEIGHT")
    heuristic_fees_weight: float = Field(0.1, alias="HEURISTIC_FEES_WEIGHT")
    heuristic_uptime_weight: float = Field(0.1, alias="HEURISTIC_UPTIME_WEIGHT")
    heuristic_vector_weight: float = Field(0.7, alias="HEURISTIC_VECTOR_WEIGHT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }


# Instance globale des settings
settings = Settings()

# Accès simplifié à la configuration pour compatibilité
MONGO_URL = settings.mongo_url
MONGO_DB_NAME = settings.mongo_name
DRY_RUN = settings.dry_run
DEBUG_MODE = settings.debug

def get_settings() -> Settings:
    return settings

logger.info(
    "Configuration loaded", 
    env=settings.environment, 
    debug=settings.debug,
    db=settings.mongo_name
) 