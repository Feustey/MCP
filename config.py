"""
Configuration centralisée pour l'application MCP avec Pydantic Settings
Optimisée pour les performances et la validation

Dernière mise à jour: 9 mai 2025
"""

import os
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pydantic.networks import RedisDsn, HttpUrl
import structlog

logger = structlog.get_logger(__name__)


class DatabaseSettings(BaseSettings):
    """Configuration base de données MongoDB"""
    url: str = Field(..., description="URL MongoDB complète")
    name: str = Field(default="mcp", description="Nom de la base de données")
    max_pool_size: int = Field(default=100, description="Taille max du pool de connexions")
    min_pool_size: int = Field(default=10, description="Taille min du pool de connexions")
    
    @validator('url')
    def validate_mongo_url(cls, v):
        if not v.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError('URL MongoDB invalide')
        return v

    class Config:
        env_prefix = "MONGO_"


class RedisSettings(BaseSettings):
    """Configuration Redis optimisée"""
    host: str = Field(default="localhost", description="Host Redis")
    port: int = Field(default=6379, description="Port Redis")
    username: str = Field(default="default", description="Username Redis")
    password: str = Field(default="", description="Password Redis")
    ssl: bool = Field(default=False, description="Utiliser SSL")
    max_connections: int = Field(default=20, description="Pool de connexions max")
    retry_on_timeout: bool = Field(default=True, description="Retry automatique")
    socket_timeout: float = Field(default=5.0, description="Timeout socket")
    socket_connect_timeout: float = Field(default=5.0, description="Timeout connexion")
    health_check_interval: int = Field(default=30, description="Intervalle health check")
    
    @property
    def url(self) -> str:
        """Construit l'URL Redis complète"""
        protocol = "rediss" if self.ssl else "redis"
        auth_part = f"{self.username}:{self.password}@" if self.password else ""
        return f"{protocol}://{auth_part}{self.host}:{self.port}/0"
    
    class Config:
        env_prefix = "REDIS_"


class AISettings(BaseSettings):
    """Configuration IA et modèles"""
    openai_api_key: str = Field(..., description="Clé API OpenAI")
    openai_model: str = Field(default="gpt-3.5-turbo", description="Modèle OpenAI par défaut")
    openai_embedding_model: str = Field(default="text-embedding-3-small", description="Modèle embeddings")
    openai_max_retries: int = Field(default=3, description="Tentatives max OpenAI")
    openai_timeout: float = Field(default=30.0, description="Timeout OpenAI")
    
    # Ollama local
    ollama_base_url: str = Field(default="http://umbrel.local:11434", description="URL Ollama")
    ollama_model: str = Field(default="mistral:instruct", description="Modèle Ollama")
    
    class Config:
        env_prefix = "AI_"


class LightningSettings(BaseSettings):
    """Configuration Lightning Network"""
    lnd_host: str = Field(default="localhost:10009", description="Host LND")
    lnd_macaroon_path: str = Field(default="", description="Chemin macaroon LND")
    lnd_tls_cert_path: str = Field(default="", description="Chemin certificat TLS")
    lnd_rest_url: str = Field(default="https://127.0.0.1:8080", description="URL REST LND")
    
    # LNBits
    use_internal_lnbits: bool = Field(default=True, description="Utiliser LNBits interne")
    lnbits_url: str = Field(default="http://127.0.0.1:8000/lnbits", description="URL LNBits")
    lnbits_admin_key: str = Field(default="", description="Clé admin LNBits")
    lnbits_invoice_key: str = Field(default="", description="Clé invoice LNBits")
    
    class Config:
        env_prefix = "LIGHTNING_"


class PerformanceSettings(BaseSettings):
    """Configuration performance et optimisation"""
    # Cache
    response_cache_ttl: int = Field(default=3600, description="TTL cache réponses (secondes)")
    embedding_cache_ttl: int = Field(default=86400, description="TTL cache embeddings (secondes)")
    
    # Workers et concurrence
    max_workers: int = Field(default=4, description="Nombre max de workers")
    async_pool_size: int = Field(default=100, description="Taille pool async")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, description="Requêtes par minute")
    rate_limit_window: int = Field(default=60, description="Fenêtre rate limiting")
    
    # Timeouts
    default_timeout: float = Field(default=30.0, description="Timeout par défaut")
    db_timeout: float = Field(default=10.0, description="Timeout base de données")
    http_timeout: float = Field(default=15.0, description="Timeout HTTP")
    
    class Config:
        env_prefix = "PERF_"


class LoggingSettings(BaseSettings):
    """Configuration logging avancée"""
    level: str = Field(default="INFO", description="Niveau de log")
    format: str = Field(default="json", description="Format de log (json|text)")
    enable_structlog: bool = Field(default=True, description="Activer structlog")
    enable_file_logging: bool = Field(default=True, description="Log vers fichier")
    log_file_path: str = Field(default="logs/mcp.log", description="Chemin fichier log")
    max_file_size: int = Field(default=50*1024*1024, description="Taille max fichier (bytes)")
    backup_count: int = Field(default=5, description="Nombre de fichiers backup")
    
    # OpenTelemetry
    enable_tracing: bool = Field(default=False, description="Activer tracing")
    otel_endpoint: Optional[str] = Field(default=None, description="Endpoint OTLP")
    
    class Config:
        env_prefix = "LOG_"


class SecuritySettings(BaseSettings):
    """Configuration sécurité"""
    secret_key: str = Field(..., description="Clé secrète application")
    cors_origins: List[str] = Field(default=["https://dazno.de", "https://api.dazno.de"], description="Origins CORS")
    allowed_hosts: List[str] = Field(default=["*"], description="Hosts autorisés")
    
    # Rate limiting sécurisé
    enable_rate_limiting: bool = Field(default=True, description="Activer rate limiting")
    max_requests_per_minute: int = Field(default=60, description="Requêtes max par minute")
    
    class Config:
        env_prefix = "SECURITY_"


class HeuristicSettings(BaseSettings):
    """Configuration heuristiques Lightning"""
    centrality_weight: float = Field(default=0.4, description="Poids centralité")
    capacity_weight: float = Field(default=0.2, description="Poids capacité")
    reputation_weight: float = Field(default=0.2, description="Poids réputation")
    fees_weight: float = Field(default=0.1, description="Poids frais")
    uptime_weight: float = Field(default=0.1, description="Poids uptime")
    
    # RAG
    vector_weight: float = Field(default=0.7, description="Poids vectoriel RAG")
    
    @validator('*')
    def validate_weights(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Les poids doivent être entre 0.0 et 1.0')
        return v
    
    class Config:
        env_prefix = "HEURISTIC_"


class Settings(BaseSettings):
    """Configuration principale de l'application MCP"""
    
    # Métadonnées
    app_name: str = Field(default="MCP Lightning Network Optimizer", description="Nom application")
    version: str = Field(default="1.0.0", description="Version application")
    environment: str = Field(default="development", description="Environnement")
    debug: bool = Field(default=False, description="Mode debug")
    
    # Serveur
    host: str = Field(default="0.0.0.0", description="Host serveur")
    port: int = Field(default=8000, description="Port serveur")
    reload: bool = Field(default=False, description="Reload automatique")
    
    # Sous-configurations
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    ai: AISettings = AISettings()
    lightning: LightningSettings = LightningSettings()
    performance: PerformanceSettings = PerformanceSettings()
    logging: LoggingSettings = LoggingSettings()
    security: SecuritySettings = SecuritySettings()
    heuristics: HeuristicSettings = HeuristicSettings()
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    def get_database_url(self) -> str:
        """Retourne l'URL de base de données formatée"""
        return self.database.url
    
    def get_redis_url(self) -> str:
        """Retourne l'URL Redis formatée"""
        return self.redis.url
    
    def get_cors_origins(self) -> List[str]:
        """Retourne les origins CORS autorisées"""
        if self.is_development:
            return ["*"]
        return self.security.cors_origins
    
    def setup_logging(self):
        """Configure le logging de l'application"""
        import logging.config
        import os
        
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
                },
                "text": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": self.logging.format,
                    "level": self.logging.level
                }
            },
            "root": {
                "handlers": ["console"],
                "level": self.logging.level
            }
        }
        
        # Vérifier si le logging vers fichier est activé et si le répertoire existe
        if self.logging.enable_file_logging:
            log_dir = os.path.dirname(self.logging.log_file_path)
            if os.path.exists(log_dir) or os.access(os.path.dirname(log_dir), os.W_OK):
                try:
                    config["handlers"]["file"] = {
                        "class": "logging.handlers.RotatingFileHandler",
                        "filename": self.logging.log_file_path,
                        "maxBytes": self.logging.max_file_size,
                        "backupCount": self.logging.backup_count,
                        "formatter": self.logging.format,
                        "level": self.logging.level
                    }
                    config["root"]["handlers"].append("file")
                except Exception as e:
                    # En cas d'erreur, on continue sans le logging vers fichier
                    print(f"⚠️ Impossible de configurer le logging vers fichier: {e}")
            else:
                print(f"⚠️ Répertoire de logs non accessible: {log_dir}")
        
        try:
            logging.config.dictConfig(config)
        except Exception as e:
            # Configuration de fallback simple
            logging.basicConfig(
                level=getattr(logging, self.logging.level.upper()),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            print(f"⚠️ Configuration de logging simplifiée: {e}")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instance globale des settings
settings = Settings()

# Initialisation du logging seulement si pas en mode conteneur
if not os.getenv('LOG_ENABLE_FILE_LOGGING') == 'false':
    try:
        settings.setup_logging()
    except Exception as e:
        # Configuration de fallback
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        print(f"⚠️ Configuration de logging de fallback: {e}")

# Export des configurations héritées pour compatibilité
MONGO_URL = settings.get_database_url()
MONGO_DB_NAME = settings.database.name
REDIS_URL = settings.get_redis_url()
RESPONSE_CACHE_TTL = settings.performance.response_cache_ttl
OPENAI_API_KEY = settings.ai.openai_api_key
OLLAMA_BASE_URL = settings.ai.ollama_base_url
OLLAMA_MODEL = settings.ai.ollama_model

# Configurations Lightning pour compatibilité
LND_HOST = settings.lightning.lnd_host
LND_MACAROON_PATH = settings.lightning.lnd_macaroon_path
LND_TLS_CERT_PATH = settings.lightning.lnd_tls_cert_path
LND_REST_URL = settings.lightning.lnd_rest_url
USE_INTERNAL_LNBITS = settings.lightning.use_internal_lnbits
LNBITS_URL = settings.lightning.lnbits_url
LNBITS_ADMIN_KEY = settings.lightning.lnbits_admin_key
LNBITS_INVOICE_KEY = settings.lightning.lnbits_invoice_key

# Pondérations pour compatibilité
HEURISTIC_WEIGHTS = {
    "centrality": settings.heuristics.centrality_weight,
    "capacity": settings.heuristics.capacity_weight,
    "reputation": settings.heuristics.reputation_weight,
    "fees": settings.heuristics.fees_weight,
    "uptime": settings.heuristics.uptime_weight,
}
VECTOR_WEIGHT = settings.heuristics.vector_weight

# Import logger après configuration
import logging
logger = logging.getLogger(__name__)

logger.info("Configuration chargée avec succès", 
           environment=settings.environment,
           debug=settings.debug) 