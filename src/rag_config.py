from pydantic_settings import BaseSettings
from typing import Dict, Any
from datetime import timedelta

class RAGConfig(BaseSettings):
    # Configuration pour permettre des champs supplémentaires
    model_config = {
        "extra": "allow",
        "env_file": ".env"
    }
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"
    
    # Cache
    redis_url: str = "redis://localhost:6379"
    embedding_cache_ttl: int = 24 * 3600  # 24 heures
    response_cache_ttl: int = 3600        # 1 heure
    context_cache_ttl: int = 4 * 3600     # 4 heures
    
    # MongoDB
    mongo_url: str
    database_name: str = "dazlng"
    
    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_context_docs: int = 5