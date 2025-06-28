"""
Modèles de journalisation
Définition des modèles de logs pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

class JSONFormatter(logging.Formatter):
    """Formateur de logs au format JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formate un enregistrement de log en JSON"""
        
        # Données de base
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Ajout des informations supplémentaires
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Ajout des informations d'exception
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
        """Formate un enregistrement de log en texte"""
        
        # Format de base
        log_format = (
            "%(asctime)s [%(levelname)s] %(message)s "
            "(%(module)s:%(funcName)s:%(lineno)d)"
        )
        
        # Ajout des informations supplémentaires
        if hasattr(record, "extra"):
            extra_str = " ".join(f"{k}={v}" for k, v in record.extra.items())
            log_format += f" {extra_str}"
        
        # Ajout des informations d'exception
        if record.exc_info:
            log_format += "\n%(exc_info)s"
        
        return super().format(record)

class LogConfig:
    """Configuration des logs"""
    
    # Niveaux de log
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    # Formats de log
    FORMATS = {
        "json": JSONFormatter,
        "text": TextFormatter
    }
    
    # Configuration par défaut
    DEFAULT_CONFIG = {
        "level": "INFO",
        "format": "json",
        "log_dir": "logs",
        "max_size": 10 * 1024 * 1024,  # 10 MB
        "backup_count": 5,
        "retention_days": 30
    }
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        level: str = "INFO",
        format: str = "json",
        log_dir: str = "logs",
        max_size: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        retention_days: int = 30
    ) -> logging.Logger:
        """Configure et retourne un logger"""
        
        # Création du logger
        logger = logging.getLogger(name)
        logger.setLevel(cls.LEVELS.get(level, logging.INFO))
        
        # Création du répertoire de logs
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration du handler de fichier
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / f"{name}.log",
            maxBytes=max_size,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(cls.FORMATS[format]())
        logger.addHandler(file_handler)
        
        # Configuration du handler de console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(cls.FORMATS[format]())
        logger.addHandler(console_handler)
        
        return logger
    
    @classmethod
    def get_audit_logger(
        cls,
        name: str = "audit",
        **kwargs
    ) -> logging.Logger:
        """Configure et retourne un logger d'audit"""
        
        # Configuration spécifique pour l'audit
        audit_config = {
            "level": "INFO",
            "format": "json",
            "log_dir": "logs/audit",
            "max_size": 50 * 1024 * 1024,  # 50 MB
            "backup_count": 10,
            "retention_days": 365
        }
        audit_config.update(kwargs)
        
        return cls.get_logger(name, **audit_config)
    
    @classmethod
    def get_error_logger(
        cls,
        name: str = "error",
        **kwargs
    ) -> logging.Logger:
        """Configure et retourne un logger d'erreurs"""
        
        # Configuration spécifique pour les erreurs
        error_config = {
            "level": "ERROR",
            "format": "json",
            "log_dir": "logs/error",
            "max_size": 20 * 1024 * 1024,  # 20 MB
            "backup_count": 5,
            "retention_days": 90
        }
        error_config.update(kwargs)
        
        return cls.get_logger(name, **error_config)
    
    @classmethod
    def get_access_logger(
        cls,
        name: str = "access",
        **kwargs
    ) -> logging.Logger:
        """Configure et retourne un logger d'accès"""
        
        # Configuration spécifique pour l'accès
        access_config = {
            "level": "INFO",
            "format": "json",
            "log_dir": "logs/access",
            "max_size": 100 * 1024 * 1024,  # 100 MB
            "backup_count": 5,
            "retention_days": 30
        }
        access_config.update(kwargs)
        
        return cls.get_logger(name, **access_config)
    
    @classmethod
    def get_performance_logger(
        cls,
        name: str = "performance",
        **kwargs
    ) -> logging.Logger:
        """Configure et retourne un logger de performance"""
        
        # Configuration spécifique pour la performance
        perf_config = {
            "level": "INFO",
            "format": "json",
            "log_dir": "logs/performance",
            "max_size": 30 * 1024 * 1024,  # 30 MB
            "backup_count": 5,
            "retention_days": 60
        }
        perf_config.update(kwargs)
        
        return cls.get_logger(name, **perf_config)
    
    @classmethod
    def get_security_logger(
        cls,
        name: str = "security",
        **kwargs
    ) -> logging.Logger:
        """Configure et retourne un logger de sécurité"""
        
        # Configuration spécifique pour la sécurité
        security_config = {
            "level": "WARNING",
            "format": "json",
            "log_dir": "logs/security",
            "max_size": 20 * 1024 * 1024,  # 20 MB
            "backup_count": 10,
            "retention_days": 365
        }
        security_config.update(kwargs)
        
        return cls.get_logger(name, **security_config) 