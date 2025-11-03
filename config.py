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
    
    @property
    def is_production(self) -> bool:
        """Vérifie si l'environnement est en production"""
        return self.environment.lower() == "production"

    # Base de données MongoDB
    mongo_url: str = Field(..., alias="MONGO_URL")
    mongo_name: str = Field("mcp", alias="MONGO_NAME")
    
    # Redis
    redis_host: str = Field("localhost", alias="REDIS_HOST")
    redis_port: int = Field(6379, alias="REDIS_PORT")
    redis_username: Optional[str] = Field("default", alias="REDIS_USERNAME")
    redis_password: Optional[str] = Field("", alias="REDIS_PASSWORD")
    redis_ssl: bool = Field(False, alias="REDIS_SSL")
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")
    
    def get_redis_url(self) -> str:
        """Génère l'URL Redis complète"""
        if self.redis_url:
            return self.redis_url
        
        # Construction de l'URL depuis les composants
        scheme = "rediss" if self.redis_ssl else "redis"
        auth = ""
        if self.redis_username and self.redis_password:
            auth = f"{self.redis_username}:{self.redis_password}@"
        elif self.redis_password:
            auth = f":{self.redis_password}@"
            
        return f"{scheme}://{auth}{self.redis_host}:{self.redis_port}"

    # IA et modèles
    ai_openai_api_key: str = Field(..., alias="AI_OPENAI_API_KEY")
    ai_openai_model: str = Field("gpt-3.5-turbo", alias="AI_OPENAI_MODEL")
    ai_openai_embedding_model: str = Field("text-embedding-3-small", alias="AI_OPENAI_EMBEDDING_MODEL")
    ai_anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    ai_default_model: str = Field("gpt-4o-mini", alias="MODEL_NAME")
    ai_default_embedding_model: str = Field("text-embedding-ada-002", alias="EMBEDDING_MODEL")
    ai_max_output_tokens: int = Field(600, alias="AI_MAX_OUTPUT_TOKENS")

    # LNBits
    lnbits_inkey: str = Field(..., alias="LNBITS_INKEY")
    lnbits_admin_key: Optional[str] = Field(None, alias="LNBITS_ADMIN_KEY")
    lnbits_url: Optional[str] = Field(None, alias="LNBITS_URL")

    # Performance
    perf_enable_metrics: bool = Field(True, alias="PERF_ENABLE_METRICS")
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
    log_request_sample_rate: float = Field(1.0, alias="LOG_REQUEST_SAMPLE_RATE")

    # Sécurité
    security_secret_key: str = Field(..., alias="SECURITY_SECRET_KEY")
    security_cors_origins: List[str] = Field(
        ["https://app.dazno.de", "https://dazno.de", "https://www.dazno.de"], 
        alias="SECURITY_CORS_ORIGINS"
    )
    security_allowed_hosts: List[str] = Field(
        ["api.dazno.de", "app.dazno.de", "dazno.de", "www.dazno.de", "localhost"], 
        alias="SECURITY_ALLOWED_HOSTS"
    )

    # Qdrant
    qdrant_url: Optional[str] = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, alias="QDRANT_API_KEY")
    qdrant_collection: str = Field("mcp_knowledge", alias="QDRANT_COLLECTION")
    qdrant_vector_size: int = Field(1536, alias="QDRANT_VECTOR_SIZE")
    qdrant_distance: str = Field("Cosine", alias="QDRANT_DISTANCE")

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
