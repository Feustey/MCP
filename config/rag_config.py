import json
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field
from typing import List, Optional, Literal

class RAGSettings(BaseSettings):
    # Configuration LLM principale (RAG)
    # Par défaut, le RAG utilise Ollama local (Anthropic reste pour le chatbot non-RAG)
    LLM_PROVIDER: Literal["ollama", "openai", "anthropic"] = "ollama"
    LLM_MODEL: str = "llama3.1:8b"
    LLM_TIMEOUT: int = 120

    # Ollama (RAG)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_NUM_PARALLEL: int = 3  # Concurrence pour 8B (peut gérer plus)
    OLLAMA_KEEP_ALIVE: str = "30m"  # Durée de maintien en mémoire
    
    # Modèles Ollama
    GEN_MODEL: str = "llama3.1:8b"
    GEN_MODEL_FALLBACK: str = "phi3:medium"
    EMBED_MODEL: str = "nomic-embed-text"
    EMBED_DIMENSION: int = 768  # nomic-embed-text: 768, ajuster selon le modèle
    EMBED_VERSION: str = "2025-10-15"
    
    # Paramètres génération (optimisés pour modèle 8B)
    GEN_TEMPERATURE: float = 0.3
    GEN_TOP_P: float = 0.9
    GEN_MAX_TOKENS: int = 1200
    GEN_NUM_CTX: int = 8192  # Taille du contexte
    
    # Retrieval (optimisé pour modèle léger)
    RAG_TOPK: int = 5  # Nombre de chunks à récupérer
    RAG_RERANK_TOP: int = 2  # Nombre de chunks après reranking
    RAG_CONFIDENCE_THRESHOLD: float = 0.40  # Seuil de confiance minimal
    
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
    # Lue comme str depuis l'env pour accepter CSV ou JSON (évite JSONDecodeError si vide/CSV)
    allowed_origins_raw: str = Field(default="*", validation_alias="ALLOWED_ORIGINS")

    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        v = (self.allowed_origins_raw or "").strip()
        if not v or v == "*":
            return ["*"]
        if v.startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [x.strip() for x in v.split(",") if x.strip()] or ["*"]

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
    
    # === OPTIMISATIONS RAG AVANCÉES (Nov 2025) ===
    
    # Hybrid Search (Dense + Sparse)
    ENABLE_HYBRID_SEARCH: bool = True
    HYBRID_DENSE_WEIGHT: float = 0.7  # Poids recherche dense (embeddings)
    HYBRID_SPARSE_WEIGHT: float = 0.3  # Poids recherche sparse (BM25)
    HYBRID_RRF_K: int = 60  # Paramètre k pour Reciprocal Rank Fusion
    
    # Query Expansion
    ENABLE_QUERY_EXPANSION: bool = True
    QUERY_EXPANSION_MAX_VARIANTS: int = 5  # Max variantes de requête
    QUERY_EXPANSION_SYNONYMS: bool = True  # Synonymes Lightning Network
    QUERY_EXPANSION_ABBREVIATIONS: bool = True  # Expansion abréviations
    QUERY_EXPANSION_RELATED_CONCEPTS: bool = True  # Concepts reliés
    QUERY_EXPANSION_MULTILINGUAL: bool = True  # Support FR/EN
    
    # Advanced Reranking
    ENABLE_ADVANCED_RERANKING: bool = True
    RERANK_SIMILARITY_WEIGHT: float = 0.50  # Poids similarité sémantique
    RERANK_RECENCY_WEIGHT: float = 0.20  # Poids fraîcheur
    RERANK_QUALITY_WEIGHT: float = 0.15  # Poids qualité document
    RERANK_POPULARITY_WEIGHT: float = 0.10  # Poids popularité
    RERANK_DIVERSITY_WEIGHT: float = 0.05  # Poids diversité
    RERANK_RECENCY_DECAY_DAYS: int = 90  # Jours pour decay complet
    
    # Dynamic Context Window
    ENABLE_DYNAMIC_CONTEXT: bool = True
    DYNAMIC_CONTEXT_DEFAULT: str = "medium"  # simple|medium|complex|very_complex
    DYNAMIC_CONTEXT_AUTO_DETECT: bool = True  # Détection automatique
    
    # Index Type
    INDEX_TYPE: str = "redis_hnsw"  # "faiss" ou "redis_hnsw"
    INDEX_USE_GPU: bool = False  # GPU pour embeddings (si disponible)
    
    # Batch Processing
    EMBEDDING_BATCH_SIZE: int = 32  # CPU: 32, GPU: 128
    EMBEDDING_MAX_CONCURRENT_BATCHES: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permettre des champs supplémentaires

settings = RAGSettings() 
