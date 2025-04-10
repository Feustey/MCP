import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.semconv.resource.attributes import ResourceAttributes, HOST_NAME

# Configuration du logging
logger = logging.getLogger(__name__)

# Types d'événements
class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class EventCategory(str, Enum):
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER = "user"
    BUSINESS = "business"
    DATABASE = "database"
    NETWORK = "network"
    LIQUIDITY = "liquidity"
    RAG = "rag"
    ANALYTICS = "analytics"

# Configuration de base de l'observabilité
class ObservabilityConfig:
    def __init__(self, 
                 service_name: str, 
                 version: str, 
                 environment: str = "production",
                 enable_metrics: bool = True,
                 enable_traces: bool = True,
                 enable_structured_logs: bool = True,
                 prometheus_port: int = 8000,
                 log_level: str = "INFO"):
        self.service_name = service_name
        self.version = version
        self.environment = environment
        self.enable_metrics = enable_metrics
        self.enable_traces = enable_traces
        self.enable_structured_logs = enable_structured_logs
        self.prometheus_port = prometheus_port
        self.log_level = log_level
        self.custom_attrs = {}
        
    def add_attribute(self, key: str, value: str):
        """Ajoute un attribut personnalisé à la configuration"""
        self.custom_attrs[key] = value

# Classe principale d'observabilité
class ObservabilityManager:
    _instance = None
    
    def __new__(cls, config: Optional[ObservabilityConfig] = None):
        if cls._instance is None:
            cls._instance = super(ObservabilityManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        if self._initialized:
            return
        
        # Si pas de config, utiliser les valeurs par défaut
        if config is None:
            config = ObservabilityConfig(
                service_name=os.environ.get("SERVICE_NAME", "unknown-service"),
                version=os.environ.get("SERVICE_VERSION", "0.0.1"),
                environment=os.environ.get("ENVIRONMENT", "development")
            )
        
        self.config = config
        self._setup_logging()
        self._setup_tracing()
        self._setup_metrics()
        self._initialized = True
    
    def _setup_logging(self):
        """Configure le système de logging"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(self.config.service_name)
    
    def _setup_tracing(self):
        """Configure le système de traçage"""
        if not self.config.enable_traces:
            self.tracer_provider = None
            self.tracer = None
            return
        
        # Créer un Resource avec les attributs du service
        resource = Resource.create({
            SERVICE_NAME: self.config.service_name,
            ResourceAttributes.SERVICE_VERSION: self.config.version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.config.environment,
            HOST_NAME: os.environ.get("HOSTNAME", "unknown-host"),
            **self.config.custom_attrs
        })
        
        # Configurer le provider de traces
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Ajouter un exporteur de console pour le développement
        console_exporter = ConsoleSpanExporter()
        self.tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        
        # Définir le provider global et obtenir un tracer
        trace.set_tracer_provider(self.tracer_provider)
        self.tracer = trace.get_tracer(self.config.service_name, self.config.version)
        
        # Configuration de la propagation de contexte
        self.propagator = TraceContextTextMapPropagator()
    
    def _setup_metrics(self):
        """Configure le système de métriques"""
        if not self.config.enable_metrics:
            self.meter_provider = None
            self.meter = None
            return
        
        # Créer un Resource avec les attributs du service
        resource = Resource.create({
            SERVICE_NAME: self.config.service_name,
            ResourceAttributes.SERVICE_VERSION: self.config.version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.config.environment,
            HOST_NAME: os.environ.get("HOSTNAME", "unknown-host"),
            **self.config.custom_attrs
        })
        
        # Configurer le lecteur Prometheus
        prometheus_reader = PrometheusMetricReader()
        
        # Configurer le provider de métriques
        self.meter_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
        
        # Définir le provider global et obtenir un compteur
        metrics.set_meter_provider(self.meter_provider)
        self.meter = metrics.get_meter(self.config.service_name, self.config.version)
    
    def create_counter(self, name: str, description: str, unit: str = "1"):
        """Crée un compteur pour suivre des événements cumulatifs"""
        if not self.config.enable_metrics or not self.meter:
            return None
        return self.meter.create_counter(name, description=description, unit=unit)
    
    def create_histogram(self, name: str, description: str, unit: str = "ms"):
        """Crée un histogramme pour suivre des distributions de valeurs"""
        if not self.config.enable_metrics or not self.meter:
            return None
        return self.meter.create_histogram(name, description=description, unit=unit)
    
    def create_gauge(self, name: str, description: str, unit: str = "1"):
        """Crée une jauge pour suivre des valeurs qui montent et descendent"""
        if not self.config.enable_metrics or not self.meter:
            return None
        return self.meter.create_observable_gauge(name, description=description, unit=unit)
    
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None, 
                   context: Optional[Any] = None, kind: Optional[trace.SpanKind] = None):
        """Démarre un span de traçage"""
        if not self.config.enable_traces or not self.tracer:
            return None
        
        ctx = context or trace.get_current_span().get_span_context()
        span = self.tracer.start_span(name, context=ctx, attributes=attributes, kind=kind)
        return span
    
    def end_span(self, span):
        """Termine un span de traçage"""
        if span:
            span.end()
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None, 
                 severity: EventSeverity = EventSeverity.INFO, 
                 category: EventCategory = EventCategory.SYSTEM, 
                 timestamp: Optional[datetime] = None):
        """Ajoute un événement au span courant"""
        if not self.config.enable_traces:
            return
        
        current_span = trace.get_current_span()
        if not current_span or not current_span.is_recording():
            return
        
        event_attrs = attributes or {}
        event_attrs["severity"] = severity.value
        event_attrs["category"] = category.value
        
        current_span.add_event(name, attributes=event_attrs, timestamp=timestamp)
    
    def log_structured(self, message: str, severity: EventSeverity = EventSeverity.INFO, 
                      category: EventCategory = EventCategory.SYSTEM, 
                      context: Optional[Dict[str, Any]] = None, 
                      trace_id: Optional[str] = None, 
                      span_id: Optional[str] = None):
        """Produit un log structuré avec contexte et traces"""
        if not self.config.enable_structured_logs:
            return
        
        # Obtenir le contexte de trace actuel si non fourni
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context() if current_span else None
        
        trace_id = trace_id or (span_context.trace_id if span_context else None)
        span_id = span_id or (span_context.span_id if span_context else None)
        
        # Préparer le contexte du log
        log_context = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.config.service_name,
            "version": self.config.version,
            "environment": self.config.environment,
            "severity": severity.value,
            "category": category.value
        }
        
        # Ajouter les IDs de trace si disponibles
        if trace_id:
            log_context["trace_id"] = trace_id
        if span_id:
            log_context["span_id"] = span_id
        
        # Ajouter le contexte utilisateur
        if context:
            log_context.update(context)
        
        # Déterminer le niveau de log
        log_method = getattr(self.logger, severity.value.lower(), self.logger.info)
        
        # Créer le message structuré
        structured_msg = f"{message} - {log_context}"
        log_method(structured_msg)

# Fonctions utilitaires pour faciliter l'utilisation
def get_observability_manager(service_name: str = None, version: str = None) -> ObservabilityManager:
    """Récupère l'instance globale du gestionnaire d'observabilité ou en crée une nouvelle"""
    instance = ObservabilityManager()
    
    # Si l'instance n'est pas encore initialisée et qu'on a des paramètres
    if not instance._initialized and service_name:
        config = ObservabilityConfig(
            service_name=service_name,
            version=version or "0.0.1"
        )
        instance.__init__(config)
    
    return instance

def trace_function(func=None, name=None, attributes=None):
    """Décorateur pour tracer une fonction"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_observability_manager()
            if not manager.config.enable_traces:
                return func(*args, **kwargs)
            
            span_name = name or f"{func.__module__}.{func.__name__}"
            with manager.tracer.start_as_current_span(span_name, attributes=attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    span.record_exception(e)
                    raise
        return wrapper
    
    # Permettre l'utilisation avec ou sans arguments
    if func is None:
        return decorator
    return decorator(func)

def create_metrics_for_service(service_name: str, version: str):
    """Crée et retourne des métriques communes pour un service"""
    manager = get_observability_manager(service_name, version)
    
    metrics = {
        "requests_total": manager.create_counter(
            f"{service_name}_requests_total", 
            "Nombre total de requêtes reçues"
        ),
        "request_duration": manager.create_histogram(
            f"{service_name}_request_duration_seconds",
            "Durée des requêtes en secondes",
            unit="s"
        ),
        "errors_total": manager.create_counter(
            f"{service_name}_errors_total",
            "Nombre total d'erreurs"
        ),
        "active_tasks": manager.create_gauge(
            f"{service_name}_active_tasks",
            "Nombre de tâches actives"
        )
    }
    
    return metrics

# Exemple d'utilisation
if __name__ == "__main__":
    # Configurer l'observabilité pour le service
    obs_manager = get_observability_manager("demo-service", "1.0.0")
    
    # Créer quelques métriques
    request_counter = obs_manager.create_counter("demo_requests", "Nombre de requêtes de démonstration")
    request_duration = obs_manager.create_histogram("demo_duration", "Durée des opérations de démonstration")
    
    # Créer un span et enregistrer un événement
    with obs_manager.tracer.start_as_current_span("demo-operation") as span:
        # Incrémenter un compteur
        request_counter.add(1, {"endpoint": "/demo", "method": "GET"})
        
        # Enregistrer un événement
        obs_manager.add_event(
            "Opération démarrée",
            {"operation_id": "1234"},
            EventSeverity.INFO,
            EventCategory.SYSTEM
        )
        
        # Simuler une opération
        import time
        start = time.time()
        time.sleep(0.1)  # Simuler du travail
        duration = time.time() - start
        
        # Enregistrer la durée
        request_duration.record(duration, {"operation": "demo"})
        
        # Logger avec contexte structuré
        obs_manager.log_structured(
            "Opération terminée avec succès",
            EventSeverity.INFO,
            EventCategory.PERFORMANCE,
            {"duration_ms": duration * 1000, "operation_id": "1234"}
        )
    
    # Utiliser le décorateur de trace
    @trace_function(name="demo_function", attributes={"type": "example"})
    def example_function(x, y):
        return x + y
    
    result = example_function(3, 4)
    print(f"Résultat: {result}") 