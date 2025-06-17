"""
Modèles de métriques
Définition des modèles Prometheus pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

from typing import Dict, List, Optional
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client.metrics import MetricWrapperBase

class Metrics:
    """Classe pour gérer les métriques Prometheus"""
    
    # Métriques HTTP
    http_requests_total = Counter(
        "http_requests_total",
        "Nombre total de requêtes HTTP",
        ["method", "endpoint", "status"]
    )
    
    http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "Durée des requêtes HTTP en secondes",
        ["method", "endpoint"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )
    
    http_request_size_bytes = Summary(
        "http_request_size_bytes",
        "Taille des requêtes HTTP en bytes",
        ["method", "endpoint"]
    )
    
    http_response_size_bytes = Summary(
        "http_response_size_bytes",
        "Taille des réponses HTTP en bytes",
        ["method", "endpoint"]
    )
    
    # Métriques d'authentification
    auth_attempts_total = Counter(
        "auth_attempts_total",
        "Nombre total de tentatives d'authentification",
        ["result"]
    )
    
    auth_failures_total = Counter(
        "auth_failures_total",
        "Nombre total d'échecs d'authentification",
        ["reason"]
    )
    
    # Métriques de base de données
    db_operations_total = Counter(
        "db_operations_total",
        "Nombre total d'opérations sur la base de données",
        ["operation", "collection"]
    )
    
    db_operation_duration_seconds = Histogram(
        "db_operation_duration_seconds",
        "Durée des opérations sur la base de données en secondes",
        ["operation", "collection"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
    )
    
    db_connections = Gauge(
        "db_connections",
        "Nombre de connexions à la base de données",
        ["state"]
    )
    
    # Métriques de cache
    cache_operations_total = Counter(
        "cache_operations_total",
        "Nombre total d'opérations sur le cache",
        ["operation", "type"]
    )
    
    cache_hits_total = Counter(
        "cache_hits_total",
        "Nombre total de hits du cache",
        ["type"]
    )
    
    cache_misses_total = Counter(
        "cache_misses_total",
        "Nombre total de misses du cache",
        ["type"]
    )
    
    cache_size_bytes = Gauge(
        "cache_size_bytes",
        "Taille du cache en bytes",
        ["type"]
    )
    
    # Métriques système
    system_cpu_usage = Gauge(
        "system_cpu_usage",
        "Utilisation CPU en pourcentage"
    )
    
    system_memory_usage = Gauge(
        "system_memory_usage",
        "Utilisation mémoire en pourcentage"
    )
    
    system_disk_usage = Gauge(
        "system_disk_usage",
        "Utilisation disque en pourcentage",
        ["mount"]
    )
    
    system_network_in = Counter(
        "system_network_in",
        "Trafic réseau entrant en bytes",
        ["interface"]
    )
    
    system_network_out = Counter(
        "system_network_out",
        "Trafic réseau sortant en bytes",
        ["interface"]
    )
    
    # Métriques d'application
    app_uptime_seconds = Gauge(
        "app_uptime_seconds",
        "Temps de fonctionnement de l'application en secondes"
    )
    
    app_requests_in_progress = Gauge(
        "app_requests_in_progress",
        "Nombre de requêtes en cours",
        ["endpoint"]
    )
    
    app_errors_total = Counter(
        "app_errors_total",
        "Nombre total d'erreurs",
        ["type", "endpoint"]
    )
    
    # Métriques de nœuds Lightning
    node_capacity = Gauge(
        "node_capacity",
        "Capacité du nœud en satoshis",
        ["node_id"]
    )
    
    node_channels = Gauge(
        "node_channels",
        "Nombre de canaux du nœud",
        ["node_id"]
    )
    
    node_score = Gauge(
        "node_score",
        "Score d'optimisation du nœud",
        ["node_id"]
    )
    
    node_status = Gauge(
        "node_status",
        "Statut du nœud (1=actif, 0=inactif)",
        ["node_id"]
    )
    
    # Métriques de simulation
    simulation_duration_seconds = Histogram(
        "simulation_duration_seconds",
        "Durée des simulations en secondes",
        ["node_id", "profile"],
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
    )
    
    simulation_results = Gauge(
        "simulation_results",
        "Résultats des simulations",
        ["node_id", "profile", "metric"]
    )
    
    # Métriques d'optimisation
    optimization_duration_seconds = Histogram(
        "optimization_duration_seconds",
        "Durée des optimisations en secondes",
        ["node_id", "strategy"],
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
    )
    
    optimization_results = Gauge(
        "optimization_results",
        "Résultats des optimisations",
        ["node_id", "strategy", "metric"]
    )
    
    # Métriques d'automatisation
    automation_runs_total = Counter(
        "automation_runs_total",
        "Nombre total d'exécutions d'automatisation",
        ["automation_id", "type"]
    )
    
    automation_duration_seconds = Histogram(
        "automation_duration_seconds",
        "Durée des automatisations en secondes",
        ["automation_id", "type"],
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
    )
    
    automation_errors_total = Counter(
        "automation_errors_total",
        "Nombre total d'erreurs d'automatisation",
        ["automation_id", "type"]
    )
    
    # Métriques de fichiers
    file_uploads_total = Counter(
        "file_uploads_total",
        "Nombre total de téléchargements de fichiers",
        ["type"]
    )
    
    file_downloads_total = Counter(
        "file_downloads_total",
        "Nombre total de téléchargements de fichiers",
        ["type"]
    )
    
    file_size_bytes = Gauge(
        "file_size_bytes",
        "Taille des fichiers en bytes",
        ["type"]
    )
    
    @classmethod
    def get_all_metrics(cls) -> List[MetricWrapperBase]:
        """Récupère toutes les métriques"""
        return [
            value for key, value in cls.__dict__.items()
            if isinstance(value, MetricWrapperBase)
        ]
    
    @classmethod
    def get_metric_by_name(cls, name: str) -> Optional[MetricWrapperBase]:
        """Récupère une métrique par son nom"""
        return getattr(cls, name, None)
    
    @classmethod
    def get_metrics_by_type(cls, metric_type: type) -> List[MetricWrapperBase]:
        """Récupère les métriques par type"""
        return [
            value for value in cls.get_all_metrics()
            if isinstance(value, metric_type)
        ] 