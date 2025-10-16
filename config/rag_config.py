from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional, Literal

class RAGSettings(BaseSettings):
    # Configuration LLM principale (RAG)
    # Par défaut, le RAG utilise Ollama local (Anthropic reste pour le chatbot non-RAG)
    LLM_PROVIDER: Literal["ollama", "openai", "anthropic"] = "ollama"
    LLM_MODEL: str = "llama3:70b-instruct-2025-07-01"
    LLM_TIMEOUT: int = 90

    # Ollama (RAG)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_NUM_PARALLEL: int = 1  # Concurrence pour 70B
    OLLAMA_KEEP_ALIVE: str = "30m"  # Durée de maintien en mémoire
    
    # Modèles Ollama
    GEN_MODEL: str = "llama3:70b-instruct-2025-07-01"
    GEN_MODEL_FALLBACK: str = "llama3:8b-instruct"
    EMBED_MODEL: str = "nomic-embed-text"
    EMBED_DIMENSION: int = 768  # nomic-embed-text: 768, ajuster selon le modèle
    EMBED_VERSION: str = "2025-10-15"
    
    # Paramètres génération
    GEN_TEMPERATURE: float = 0.2
    GEN_TOP_P: float = 0.9
    GEN_MAX_TOKENS: int = 1536
    GEN_NUM_CTX: int = 8192  # Taille du contexte
    
    # Retrieval
    RAG_TOPK: int = 8  # Nombre de chunks à récupérer
    RAG_RERANK_TOP: int = 3  # Nombre de chunks après reranking
    RAG_CONFIDENCE_THRESHOLD: float = 0.35  # Seuil de confiance minimal
    
    # Cache Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL_RETRIEVAL: int = 86400  # 24h pour retrieval
    CACHE_TTL_ANSWER: int = 21600  # 6h pour answer
    CACHE_TTL_EMBED: int = 604800  # 7 jours pour embeddings
    
    # Configuration MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "rag_db"
    MONGODB_COLLECTION_DOCS: str = "documents"
    MONGODB_COLLECTION_QUERIES: str = "query_history"
    
    # Configuration API
    API_TITLE: str = "MCP RAG API"
    API_VERSION: str = "2025-10-15"
    API_PREFIX: str = "/api/v1"
    API_VERSION_HEADER: str = "X-API-Version"
    
    # Configuration Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Configuration Cache
    CACHE_TTL: int = 3600  # 1 heure (défaut legacy)
    CACHE_MAX_SIZE: int = 10000
    
    # Configuration Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_TRACING: bool = True
    TRACING_ENDPOINT: Optional[str] = None
    
    # Configuration Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" ou "text"
    LOG_MASK_SENSITIVE: bool = True  # Masquer les données sensibles
    
    # Configuration Security
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: Optional[str] = Field(default=None, alias="RAG_API_KEY")
    ALLOWED_ORIGINS: List[str] = ["*"]
    ENABLE_AUTH: bool = True
    ENABLE_RATE_LIMIT: bool = True
    
    # Configuration Chunking
    CHUNK_SIZE: int = 800  # Tokens par chunk (700-900 recommandé)
    CHUNK_OVERLAP: int = 120  # Overlap entre chunks
    
    # Configuration Index
    INDEX_NAME: str = "idx:routing:current"  # Alias vers l'index actif
    INDEX_HNSW_M: int = 16  # Paramètre M pour HNSW
    INDEX_HNSW_EF_CONSTRUCTION: int = 200  # EF construction
    
    # Retry et resilience
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 1.0  # Secondes
    CIRCUIT_BREAKER_THRESHOLD: int = 5  # Échecs avant ouverture
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # Secondes avant retry
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permettre des champs supplémentaires

settings = RAGSettings() 
