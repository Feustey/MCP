"""
Configuration du logging
Gestion des logs pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any
import json
from pathlib import Path

# Configuration des chemins
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

# Création du répertoire de logs
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Formateur de logs au format JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un record de log en JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Ajouter les extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        # Ajouter l'exception si présente
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data)

class TextFormatter(logging.Formatter):
    """Formateur de logs au format texte"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un record de log en texte"""
        # Format de base
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(module)s:%(funcName)s:%(lineno)d | %(message)s"
        )
        
        # Ajouter les extra fields
        if hasattr(record, "extra"):
            extra_str = " | ".join(f"{k}={v}" for k, v in record.extra.items())
            if extra_str:
                log_format += f" | {extra_str}"
                
        formatter = logging.Formatter(log_format)
        return formatter.format(record)

def setup_logging() -> None:
    """Configure le système de logging"""
    # Niveau de log
    level = getattr(logging, LOG_LEVEL.upper())
    
    # Formateur
    if LOG_FORMAT.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Handler pour les fichiers
    log_file = os.path.join(LOG_DIR, "api.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    
    # Handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configuration des loggers spécifiques
    loggers = {
        "mcp": level,
        "mcp.api": level,
        "mcp.database": level,
        "mcp.cache": level,
        "mcp.security": level,
        "uvicorn": level,
        "uvicorn.access": level,
        "uvicorn.error": level
    }
    
    for logger_name, logger_level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.propagate = True
    
    # Log de démarrage
    logging.info("Logging system initialized", extra={
        "log_dir": LOG_DIR,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT,
        "max_size": LOG_MAX_SIZE,
        "backup_count": LOG_BACKUP_COUNT,
        "retention_days": LOG_RETENTION_DAYS
    })

def cleanup_old_logs() -> None:
    """Nettoie les anciens fichiers de logs"""
    try:
        log_dir = Path(LOG_DIR)
        now = datetime.now()
        
        for log_file in log_dir.glob("*.log.*"):
            # Vérifier l'âge du fichier
            file_age = now - datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_age.days > LOG_RETENTION_DAYS:
                log_file.unlink()
                logging.info(f"Deleted old log file: {log_file}")
                
    except Exception as e:
        logging.error(f"Failed to cleanup old logs: {str(e)}")

def get_logger(name: str) -> logging.Logger:
    """Récupère un logger configuré"""
    return logging.getLogger(name)

# Initialisation
setup_logging()

# Export des fonctions utiles
__all__ = ["get_logger", "cleanup_old_logs"] 