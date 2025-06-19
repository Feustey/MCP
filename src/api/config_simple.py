"""
Configuration simplifiée pour le déploiement MCP sans base de données
Dernière mise à jour: 9 mai 2025
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field

class SimpleSettings(BaseSettings):
    """Configuration simplifiée pour le déploiement sans base de données"""
    
    # Application
    app_name: str = Field(default="MCP Lightning Network Optimizer", description="Nom application")
    version: str = Field(default="1.0.0", description="Version application")
    environment: str = Field(default="development", description="Environnement")
    debug: bool = Field(default=False, description="Mode debug")
    
    # Serveur
    host: str = Field(default="0.0.0.0", description="Host serveur")
    port: int = Field(default=8000, description="Port serveur")
    
    # Mode de fonctionnement
    dry_run: bool = Field(default=True, description="Mode dry-run (pas de changements réels)")
    
    # Logging
    log_level: str = Field(default="INFO", description="Niveau de log")
    
    # API Keys (optionnelles)
    openai_api_key: Optional[str] = Field(default=None, description="Clé API OpenAI")
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instance globale des settings
settings = SimpleSettings()

# Variables d'environnement pour compatibilité
DRY_RUN = settings.dry_run
LOG_LEVEL = settings.log_level
ENVIRONMENT = settings.environment 