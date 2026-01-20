"""
Système de métriques de performance pour MCP
Collecte automatique, agrégation et monitoring des performances

Dernière mise à jour: 9 janvier 2025
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import threading
import statistics
import json
from enum import Enum

from config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types de métriques"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """Point de métrique avec timestamp"""
    value: Union[float, int]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramData:
    """Données d'histogramme pour les métriques de distribution"""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    buckets: Dict[float, int] = field(default_factory=dict)
    
    def add_value(self, value: float):
        """Ajoute une valeur à l'histogramme"""
        self.values.append(value)
        
        # Met à jour les buckets prédéfinis
        buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, float('inf')]
        for bucket in buckets:
            if value <= bucket:
                self.buckets[bucket] = self.buckets.get(bucket, 0) + 1
    
    @property
    def percentiles(self) -> Dict[str, float]:
        """Calcule les percentiles"""
        if not self.values:
            return {}
        
        sorted_values = sorted(self.values)
        return {
            "p50": statistics.median(sorted_values),
            "p90": statistics.quantiles(sorted_values, n=10)[8] if len(sorted_values) >= 10 else sorted_values[-1],
            "p95": statistics.quantiles(sorted_values, n=20)[18] if len(sorted_values) >= 20 else sorted_values[-1],
            "p99": statistics.quantiles(sorted_values, n=100)[98] if len(sorted_values) >= 100 else sorted_values[-1],
        }
    
    @property
    def statistics(self) -> Dict[str, float]:
        """Statistiques de base"""
        if not self.values:
            return {}
        
        return {
            "min": min(self.values),
            "max": max(self.values),
            "mean": statistics.mean(self.values),
            "count": len(self.values),
            "sum": sum(self.values)
        }


class Metric:
    """Classe de base pour les métriques"""
    
    def __init__(self, name: str, metric_type: MetricType, description: str = ""):
        self.name = name
        self.type = metric_type
        self.description = description
        self.created_at = datetime.utcnow()
        self._lock = threading.Lock()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la métrique en dictionnaire"""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }


class Counter(Metric):
    """Métrique de compteur (toujours croissante)"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.COUNTER, description)
        self.value = 0
    
    def increment(self, amount: Union[int, float] = 1, labels: Dict[str, str] = None):
        """Incrémente le compteur"""
        with self._lock:
            self.value += amount
        
        logger.debug("Métrique compteur incrémentée",
                    metric=self.name,
                    value=self.value,
                    increment=amount,
                    labels=labels or {})
    
    def get_value(self) -> Union[int, float]:
        """Retourne la valeur actuelle"""
        return self.value
    
    def reset(self):
        """Remet à zéro le compteur"""
        with self._lock:
            self.value = 0


class Gauge(Metric):
    """Métrique de jauge (peut augmenter ou diminuer)"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.GAUGE, description)
        self.value = 0
        self.history: deque = deque(maxlen=100)  # Garde les 100 dernières valeurs
    
    def set(self, value: Union[int, float], labels: Dict[str, str] = None):
        """Définit la valeur de la jauge"""
        with self._lock:
            self.value = value
            self.history.append(MetricPoint(value, labels=labels or {}))
        
        logger.debug("Métrique jauge mise à jour",
                    metric=self.name,
                    value=value,
                    labels=labels or {})
    
    def increment(self, amount: Union[int, float] = 1):
        """Incrémente la jauge"""
        with self._lock:
            self.value += amount
    
    def decrement(self, amount: Union[int, float] = 1):
        """Décrémente la jauge"""
        with self._lock:
            self.value -= amount
    
    def get_value(self) -> Union[int, float]:
        """Retourne la valeur actuelle"""
        return self.value
    
    def get_history(self) -> List[MetricPoint]:
        """Retourne l'historique des valeurs"""
        return list(self.history)


class Histogram(Metric):
    """Métrique d'histogramme pour les distributions"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.HISTOGRAM, description)
        self.data = HistogramData()
    
    def observe(self, value: float, labels: Dict[str, str] = None):
        """Observe une valeur"""
        with self._lock:
            self.data.add_value(value)
        
        logger.debug("Métrique histogramme observée",
                    metric=self.name,
                    value=value,
                    labels=labels or {})
    
    def get_percentiles(self) -> Dict[str, float]:
        """Retourne les percentiles"""
        return self.data.percentiles
    
    def get_statistics(self) -> Dict[str, float]:
        """Retourne les statistiques"""
        return self.data.statistics


class Timer(Metric):
    """Métrique de chronométrage"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.TIMER, description)
        self.histogram = HistogramData()
        self._start_times: Dict[str, float] = {}
    
    def start(self, operation_id: str = "default") -> str:
        """Démarre un chronométrage"""
        self._start_times[operation_id] = time.time()
        return operation_id
    
    def stop(self, operation_id: str = "default", labels: Dict[str, str] = None) -> Optional[float]:
        """Arrête un chronométrage et retourne la durée"""
        if operation_id not in self._start_times:
            logger.warning("Timer non démarré", metric=self.name, operation_id=operation_id)
            return None
        
        duration = (time.time() - self._start_times.pop(operation_id)) * 1000  # en millisecondes
        
        with self._lock:
            self.histogram.add_value(duration)
        
        logger.debug("Métrique timer enregistrée",
                    metric=self.name,
                    duration_ms=duration,
                    operation_id=operation_id,
                    labels=labels or {})
        
        return duration
    
    @asynccontextmanager
    async def measure(self, labels: Dict[str, str] = None):
        """Context manager pour mesurer automatiquement"""
        operation_id = f"async_{time.time()}"
        self.start(operation_id)
        try:
            yield
        finally:
            self.stop(operation_id, labels)
    
    def get_statistics(self) -> Dict[str, float]:
        """Retourne les statistiques de timing"""
        return self.histogram.statistics
    
    def get_percentiles(self) -> Dict[str, float]:
        """Retourne les percentiles de timing"""
        return self.histogram.percentiles


class PerformanceTracker:
    """Tracker principal des performances avec collecte automatique"""
    
    def __init__(self, component_name: str, enabled: bool = True):
        self.component_name = component_name
        self.enabled = enabled
        self.metrics: Dict[str, Metric] = {}
        self._collection_interval = 120  # secondes - AUGMENTÉ DE 30s À 120s pour réduire charge CPU
        self._collection_task: Optional[asyncio.Task] = None
        # Désactiver les métriques système par défaut en production (coûteux en CPU)
        self._system_metrics_enabled = (
            getattr(settings, "perf_enable_system_metrics", False) and enabled
        )
        self._lock = threading.Lock()
        
        # Métriques système par défaut
        if self.enabled:
            self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Initialise les métriques par défaut"""
        self.register_counter("requests_total", "Nombre total de requêtes")
        self.register_counter("errors_total", "Nombre total d'erreurs")
        self.register_gauge("active_connections", "Connexions actives")
        self.register_histogram("response_time", "Temps de réponse en ms")
        self.register_timer("operation_duration", "Durée des opérations")
    
    def register_counter(self, name: str, description: str = "") -> Counter:
        """Enregistre un compteur"""
        if not self.enabled:
            return None
        metric = Counter(f"{self.component_name}_{name}", description)
        self.metrics[name] = metric
        logger.debug("Compteur enregistré", metric=name, component=self.component_name)
        return metric
    
    def register_gauge(self, name: str, description: str = "") -> Gauge:
        """Enregistre une jauge"""
        if not self.enabled:
            return None
        metric = Gauge(f"{self.component_name}_{name}", description)
        self.metrics[name] = metric
        logger.debug("Jauge enregistrée", metric=name, component=self.component_name)
        return metric
    
    def register_histogram(self, name: str, description: str = "") -> Histogram:
        """Enregistre un histogramme"""
        if not self.enabled:
            return None
        metric = Histogram(f"{self.component_name}_{name}", description)
        self.metrics[name] = metric
        logger.debug("Histogramme enregistré", metric=name, component=self.component_name)
        return metric
    
    def register_timer(self, name: str, description: str = "") -> Timer:
        """Enregistre un timer"""
        if not self.enabled:
            return None
        metric = Timer(f"{self.component_name}_{name}", description)
        self.metrics[name] = metric
        logger.debug("Timer enregistré", metric=name, component=self.component_name)
        return metric
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Récupère une métrique par nom"""
        return self.metrics.get(name)
    
    def increment_counter(self, name: str, amount: Union[int, float] = 1, labels: Dict[str, str] = None):
        """Incrémente un compteur"""
        if not self.enabled:
            return
        metric = self.get_metric(name)
        if isinstance(metric, Counter):
            metric.increment(amount, labels)
    
    def set_gauge(self, name: str, value: Union[int, float], labels: Dict[str, str] = None):
        """Met à jour une jauge"""
        if not self.enabled:
            return
        metric = self.get_metric(name)
        if isinstance(metric, Gauge):
            metric.set(value, labels)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe une valeur dans un histogramme"""
        if not self.enabled:
            return
        metric = self.get_metric(name)
        if isinstance(metric, Histogram):
            metric.observe(value, labels)
    
    def start_timer(self, name: str, operation_id: str = "default") -> str:
        """Démarre un timer"""
        metric = self.get_metric(name)
        if isinstance(metric, Timer):
            return metric.start(operation_id)
        return operation_id
    
    def stop_timer(self, name: str, operation_id: str = "default", labels: Dict[str, str] = None) -> Optional[float]:
        """Arrête un timer"""
        metric = self.get_metric(name)
        if isinstance(metric, Timer):
            return metric.stop(operation_id, labels)
        return None
    
    @asynccontextmanager
    async def measure_time(self, operation_name: str, labels: Dict[str, str] = None):
        """Context manager pour mesurer le temps d'exécution"""
        if not self.enabled:
            yield
            return
        timer = self.get_metric("operation_duration")
        if isinstance(timer, Timer):
            async with timer.measure(labels):
                yield
        else:
            yield
    
    def record_request(self, success: bool = True, response_time_ms: Optional[float] = None):
        """Enregistre une requête avec ses métriques"""
        if not self.enabled:
            return
        self.increment_counter("requests_total")
        
        if not success:
            self.increment_counter("errors_total")
        
        if response_time_ms is not None:
            self.observe_histogram("response_time", response_time_ms)
    
    async def start_collection(self):
        """Démarre la collecte automatique de métriques système"""
        if not self.enabled or not self._system_metrics_enabled:
            logger.info("Collecte de métriques désactivée", 
                       enabled=self.enabled, 
                       system_metrics_enabled=self._system_metrics_enabled,
                       component=self.component_name)
            return
        if self._collection_task and not self._collection_task.done():
            logger.warning("Collecte de métriques déjà en cours", component=self.component_name)
            return
        
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Collecte de métriques démarrée", 
                   component=self.component_name,
                   interval_seconds=self._collection_interval)
    
    async def stop_collection(self):
        """Arrête la collecte automatique"""
        if not self.enabled:
            return
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Collecte de métriques arrêtée", component=self.component_name)
    
    async def _collection_loop(self):
        """Boucle de collecte des métriques système"""
        if not self.enabled:
            return
        while True:
            try:
                await asyncio.sleep(self._collection_interval)
                
                if self._system_metrics_enabled:
                    await self._collect_system_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Erreur collecte métriques", error=str(e))
    
    async def _collect_system_metrics(self):
        """Collecte les métriques système"""
        try:
            import psutil
            
            # Exécuter dans un thread séparé pour ne pas bloquer la boucle asyncio
            def collect_metrics():
                # Métriques CPU et mémoire avec intervalle de mesure de 1s pour plus de précision
                cpu_percent = psutil.cpu_percent(interval=1)  # AJOUT: intervalle 1s pour mesure stable
                memory = psutil.virtual_memory()
                
                # Métriques de processus
                process = psutil.Process()
                process_memory = process.memory_info().rss
                process_cpu = process.cpu_percent(interval=0.5)  # AJOUT: intervalle 0.5s
                
                return {
                    "cpu_usage_percent": cpu_percent,
                    "memory_usage_percent": memory.percent,
                    "memory_available_bytes": memory.available,
                    "process_memory_bytes": process_memory,
                    "process_cpu_percent": process_cpu
                }
            
            # Exécuter dans un thread séparé pour éviter de bloquer asyncio
            metrics = await asyncio.to_thread(collect_metrics)
            
            # Mettre à jour les jauges avec les résultats
            for metric_name, value in metrics.items():
                self.set_gauge(metric_name, value)
            
        except ImportError:
            # psutil non disponible
            pass
        except Exception as e:
            logger.error("Erreur collecte métriques système", error=str(e))
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Retourne toutes les métriques sous forme de dictionnaire"""
        if not self.enabled:
            return {}
        result = {}
        
        for name, metric in self.metrics.items():
            metric_data = metric.to_dict()
            
            if isinstance(metric, Counter):
                metric_data["value"] = metric.get_value()
            elif isinstance(metric, Gauge):
                metric_data["value"] = metric.get_value()
                metric_data["history"] = [
                    {"value": point.value, "timestamp": point.timestamp.isoformat(), "labels": point.labels}
                    for point in metric.get_history()[-10:]  # Dernières 10 valeurs
                ]
            elif isinstance(metric, (Histogram, Timer)):
                metric_data["statistics"] = metric.get_statistics()
                metric_data["percentiles"] = metric.get_percentiles()
            
            result[name] = metric_data
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des métriques principales"""
        if not self.enabled:
            return {
                "component": self.component_name,
                "timestamp": datetime.utcnow().isoformat(),
                "metrics_count": 0
            }
        summary = {
            "component": self.component_name,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics_count": len(self.metrics)
        }
        
        # Métriques de base
        requests_total = self.get_metric("requests_total")
        if isinstance(requests_total, Counter):
            summary["requests_total"] = requests_total.get_value()
        
        errors_total = self.get_metric("errors_total")
        if isinstance(errors_total, Counter):
            summary["errors_total"] = errors_total.get_value()
            if summary.get("requests_total", 0) > 0:
                summary["error_rate"] = (errors_total.get_value() / summary["requests_total"]) * 100
        
        response_time = self.get_metric("response_time")
        if isinstance(response_time, Histogram):
            stats = response_time.get_statistics()
            if stats:
                summary["avg_response_time_ms"] = stats.get("mean", 0)
                summary["response_time_p95_ms"] = response_time.get_percentiles().get("p95", 0)
        
        return summary
    
    def export_prometheus_format(self) -> str:
        """Exporte les métriques au format Prometheus"""
        if not self.enabled:
            return ""
        lines = []
        
        for name, metric in self.metrics.items():
            metric_name = f"{self.component_name}_{name}"
            
            # Ligne HELP
            if metric.description:
                lines.append(f"# HELP {metric_name} {metric.description}")
            
            # Ligne TYPE
            if isinstance(metric, Counter):
                lines.append(f"# TYPE {metric_name} counter")
                lines.append(f"{metric_name} {metric.get_value()}")
            elif isinstance(metric, Gauge):
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(f"{metric_name} {metric.get_value()}")
            elif isinstance(metric, (Histogram, Timer)):
                lines.append(f"# TYPE {metric_name} histogram")
                stats = metric.get_statistics()
                if stats:
                    lines.append(f"{metric_name}_count {stats.get('count', 0)}")
                    lines.append(f"{metric_name}_sum {stats.get('sum', 0)}")
                    
                    # Buckets pour histogramme
                    if hasattr(metric, 'data') and metric.data.buckets:
                        for bucket, count in metric.data.buckets.items():
                            lines.append(f"{metric_name}_bucket{{le=\"{bucket}\"}} {count}")
        
        return "\n".join(lines)


# Instance globale pour les métriques de l'application
app_metrics = PerformanceTracker("mcp_app", enabled=getattr(settings, "perf_enable_metrics", True))

# Fonctions d'interface simplifiée
def get_app_metrics() -> PerformanceTracker:
    """Retourne le tracker de métriques de l'application"""
    return app_metrics

def record_request(success: bool = True, response_time_ms: Optional[float] = None):
    """Enregistre une requête"""
    app_metrics.record_request(success, response_time_ms)

def increment_counter(name: str, amount: Union[int, float] = 1, labels: Dict[str, str] = None):
    """Incrémente un compteur"""
    app_metrics.increment_counter(name, amount, labels)

def set_gauge(name: str, value: Union[int, float], labels: Dict[str, str] = None):
    """Met à jour une jauge"""
    app_metrics.set_gauge(name, value, labels)

async def measure_time(operation_name: str, labels: Dict[str, str] = None):
    """Context manager pour mesurer le temps"""
    return app_metrics.measure_time(operation_name, labels) 
