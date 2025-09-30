from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional

class RAGSettings(BaseSettings):
    # Configuration LLM principale
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT: int = 60

    # Configuration Redis pour le cache et rate limiting
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    
    # Configuration MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "rag_db"
    
    # Configuration API
    API_TITLE: str = "MCP RAG API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Configuration Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Configuration Cache
    CACHE_TTL: int = 3600  # 1 heure
    CACHE_MAX_SIZE: int = 10000
    
    # Configuration Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Configuration Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configuration Security
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: Optional[str] = Field(default=None, alias="RAG_API_KEY")
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = RAGSettings() 
