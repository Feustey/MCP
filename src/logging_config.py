"""
Configuration avancée du logging structuré pour MCP
Inclut support pour structlog, OpenTelemetry et monitoring

Dernière mise à jour: 9 janvier 2025
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog
from pythonjsonlogger import jsonlogger
import atexit
from datetime import datetime

from config import settings


class PerformanceFilter(logging.Filter):
    """Filtre pour logger les opérations lentes"""
    
    def __init__(self, threshold_ms: float = 1000.0):
        super().__init__()
        self.threshold_ms = threshold_ms
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Ajoute la durée si présente dans le record
        if hasattr(record, 'duration_ms') and record.duration_ms > self.threshold_ms:
            record.performance_warning = True
        return True


class SensitiveDataFilter(logging.Filter):
    """Filtre pour masquer les données sensibles"""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'key', 'secret', 'credential',
        'api_key', 'auth', 'authorization', 'macaroon'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Masque les données sensibles dans le message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_message(record.msg)
        
        # Masque les données sensibles dans les args
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._sanitize_value(arg) for arg in record.args
            )
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Masque les valeurs sensibles dans un message"""
        for key in self.SENSITIVE_KEYS:
            if key.lower() in message.lower():
                # Remplace les valeurs qui ressemblent à des secrets
                import re
                pattern = rf'({key}["\']?\s*[:=]\s*["\']?)([^"\'\s,}}]+)'
                message = re.sub(pattern, r'\1***MASKED***', message, flags=re.IGNORECASE)
        return message
    
    def _sanitize_value(self, value: Any) -> Any:
        """Masque une valeur si elle est sensible"""
        if isinstance(value, str) and len(value) > 10:
            # Masque les chaînes longues qui pourraient être des secrets
            for key in self.SENSITIVE_KEYS:
                if key in str(value).lower():
                    return "***MASKED***"
        return value


class ContextualFormatter(logging.Formatter):
    """Formatter qui ajoute du contexte automatiquement"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Ajoute des informations contextuelles
        record.environment = settings.environment
        record.service = "mcp"
        record.version = settings.version
        
        # Ajoute l'ID de thread pour le debugging
        import threading
        record.thread_id = threading.current_thread().ident
        
        # Ajoute le timestamp Unix pour les métriques
        record.timestamp = datetime.utcnow().timestamp()
        
        return super().format(record)


def setup_structlog():
    """Configure structlog pour le logging structuré"""
    
    # Processeurs structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Ajoute le contexte de l'application
    processors.append(
        structlog.processors.CallsiteParameterAdder(
            parameters=[structlog.processors.CallsiteParameter.FUNC_NAME,
                       structlog.processors.CallsiteParameter.LINENO]
        )
    )
    
    # Processeur final selon le format
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def setup_opentelemetry():
    """Configure OpenTelemetry pour le tracing"""
    if not settings.log_enable_tracing or not settings.log_otel_endpoint:
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
        
        # Configure le provider
        trace.set_tracer_provider(TracerProvider())
        
        # Configure l'exporteur OTLP
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.log_otel_endpoint,
            insecure=True if "localhost" in settings.log_otel_endpoint else False
        )
        
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        # Auto-instrumentation
        FastAPIInstrumentor.instrument()
        RedisInstrumentor.instrument()
        PymongoInstrumentor.instrument()
        
        structlog.get_logger().info("OpenTelemetry configuré", 
                                   endpoint=settings.log_otel_endpoint)
        
    except ImportError as e:
        structlog.get_logger().warning(
            "OpenTelemetry non disponible", error=str(e)
        )


def create_file_handler() -> logging.Handler:
    """Crée un handler pour les fichiers de log avec rotation"""
    
    # Assure que le répertoire existe
    log_path = Path(settings.log_log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Handler avec rotation
    handler = logging.handlers.RotatingFileHandler(
        filename=settings.log_log_file_path,
        maxBytes=settings.log_max_file_size,
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    
    # Formatter selon le format configuré
    if settings.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(thread_id)s %(environment)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        formatter = ContextualFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(environment)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    handler.setLevel(settings.log_level)
    
    # Ajoute les filtres
    handler.addFilter(SensitiveDataFilter())
    handler.addFilter(PerformanceFilter())
    
    return handler


def create_console_handler() -> logging.Handler:
    """Crée un handler pour la console"""
    
    handler = logging.StreamHandler(sys.stdout)
    
    # Formatter coloré pour le développement
    if settings.environment == "development":
        from rich.logging import RichHandler
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=True
        )
    else:
        # Formatter JSON pour la production
        if settings.log_format == "json":
            formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            formatter = ContextualFormatter()
        handler.setFormatter(formatter)
    
    handler.setLevel(settings.log_level)
    handler.addFilter(SensitiveDataFilter())
    
    return handler


def setup_root_logger():
    """Configure le logger racine"""
    
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Nettoie les handlers existants
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Ajoute le handler console
    console_handler = create_console_handler()
    root_logger.addHandler(console_handler)
    
    # Ajoute le handler fichier si activé
    if settings.log_enable_file_logging:
        try:
            file_handler = create_file_handler()
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.error(f"Erreur configuration logging fichier: {e}")
    
    # Configure les loggers tiers pour réduire le bruit
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_performance_logger(name: str) -> structlog.BoundLogger:
    """Retourne un logger configuré pour les métriques de performance"""
    
    logger = structlog.get_logger(name)
    return logger.bind(category="performance")


def get_security_logger(name: str) -> structlog.BoundLogger:
    """Retourne un logger configuré pour les événements de sécurité"""
    
    logger = structlog.get_logger(name)
    return logger.bind(category="security")


def get_business_logger(name: str) -> structlog.BoundLogger:
    """Retourne un logger configuré pour les événements business"""
    
    logger = structlog.get_logger(name)
    return logger.bind(category="business")


class LoggingManager:
    """Gestionnaire centralisé du logging"""
    
    def __init__(self):
        self.is_configured = False
        self._loggers = {}
    
    def setup(self):
        """Configure le système de logging complet"""
        try:
            if settings.log_enable_structlog:
                setup_structlog()
            
            setup_root_logger()
            setup_opentelemetry()
            
            self.is_configured = True
            logger = self.get_logger("logging_manager")
            logger.info(
                "Système de logging configuré",
                level=settings.log_level,
                format=settings.log_format,
                file_logging=settings.log_enable_file_logging,
                tracing=getattr(settings, 'log_enable_tracing', False)
            )
            
        except Exception as e:
            # Fallback en cas d'erreur
            logging.basicConfig(level=logging.INFO)
            logging.getLogger().error(f"Erreur de configuration du logging: {e}", exc_info=True)
            self.is_configured = False
    
    def get_logger(self, name: str) -> structlog.BoundLogger:
        """Retourne un logger configuré pour un module"""
        if name not in self._loggers:
            self._loggers[name] = structlog.get_logger(name)
        return self._loggers[name]
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """Log une métrique de performance"""
        logger = get_performance_logger(__name__)
        logger.info("Performance metric",
                   operation=operation,
                   duration_ms=duration_ms,
                   **kwargs)
    
    def log_security_event(self, event_type: str, **kwargs):
        """Log un événement de sécurité"""
        logger = get_security_logger(__name__)
        logger.warning("Security event",
                      event_type=event_type,
                      **kwargs)
    
    def shutdown(self):
        """Nettoie les ressources de logging"""
        if not self.is_configured:
            return
        
        # Flush tous les handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
            if hasattr(handler, 'close'):
                handler.close()


# Instance globale
logging_manager = LoggingManager()

# Setup automatique
logging_manager.setup()

# Cleanup à la fermeture
atexit.register(logging_manager.shutdown)

# Exports pour facilité d'utilisation
get_logger = logging_manager.get_logger
log_performance = logging_manager.log_performance
log_security_event = logging_manager.log_security_event 