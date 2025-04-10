from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    notelm_api_key: str
    notelm_base_url: str = "https://api.notelm.com/v1"
    sparkseer_api_key: str
    openai_api_key: str
    amboss_api_key: str
    
    # Redis Configuration
    redis_url: str
    redis_host: str
    redis_port: str
    cache_ttl: str
    
    # MongoDB Configuration
    mongodb_uri: str
    mongodb_db_name: str
    
    # JWT Configuration
    jwt_secret: str
    
    # Environment
    environment: str
    
    # RAG Configuration
    rag_data_path: str
    model_name: str
    embedding_model: str
    
    # Base de donnees
    database_url: str
    
    # Gmail Configuration
    gmail_email: Optional[str] = None
    gmail_password: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore additional environment variables

def get_settings() -> Settings:
    return Settings()
