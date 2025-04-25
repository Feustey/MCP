from pydantic_settings import BaseSettings
from functools import lru_cache

class LNPlusSettings(BaseSettings):
    """Configuration pour l'API LightningNetwork.plus"""
    api_key: str
    base_url: str = "https://lightningnetwork.plus/api/2"
    node_id: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 1

    class Config:
        env_prefix = "LNPLUS_"
        env_file = ".env"

@lru_cache()
def get_lnplus_settings() -> LNPlusSettings:
    """Obtient la configuration LN+"""
    return LNPlusSettings() 