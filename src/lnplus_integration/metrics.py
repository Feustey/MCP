from prometheus_client import Counter, Histogram, Gauge
import time
from typing import Dict, Any

class LNPlusMetrics:
    def __init__(self):
        # Compteurs de requêtes
        self.request_counter = Counter(
            'lnplus_requests_total',
            'Total des requêtes LNPlus',
            ['method', 'endpoint', 'status']
        )
        
        # Latence des requêtes
        self.latency = Histogram(
            'lnplus_request_latency_seconds',
            'Latence des requêtes LNPlus',
            ['method', 'endpoint']
        )
        
        # Métriques de l'état du système
        self.balance_gauge = Gauge(
            'lnplus_wallet_balance_satoshis',
            'Solde du wallet en satoshis'
        )
        
        self.node_count = Gauge(
            'lnplus_known_nodes',
            'Nombre de nœuds connus'
        )
        
        self.swap_count = Gauge(
            'lnplus_active_swaps',
            'Nombre de swaps actifs'
        )

    def record_request(self, method: str, endpoint: str, status: str, duration: float):
        """Enregistre une requête et sa latence"""
        self.request_counter.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.latency.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def update_balance(self, balance: int):
        """Met à jour le solde du wallet"""
        self.balance_gauge.set(balance)

    def update_node_count(self, count: int):
        """Met à jour le nombre de nœuds connus"""
        self.node_count.set(count)

    def update_swap_count(self, count: int):
        """Met à jour le nombre de swaps actifs"""
        self.swap_count.set(count)

# Instance singleton
metrics = LNPlusMetrics() 