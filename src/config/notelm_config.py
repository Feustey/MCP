from pydantic_settings import BaseSettings
from functools import lru_cache

class NotelmSettings(BaseSettings):
    api_key: str
    base_url: str = "https://api.notelm.com/v1"

    class Config:
        env_prefix = "NOTELM_"

@lru_cache()
def get_notelm_settings() -> NotelmSettings:
    return NotelmSettings() 