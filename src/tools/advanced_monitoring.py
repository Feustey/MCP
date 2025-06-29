#!/usr/bin/env python3
"""
Monitoring avancé pour MCP - Métriques détaillées et alerting
Dernière mise à jour: 7 mai 2025
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import prometheus_client as prom
from prometheus_client import Counter, Gauge, Histogram
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Métriques Prometheus
CHANNEL_BALANCE = Gauge('mcp_channel_balance', 'Balance des canaux', ['channel_id', 'node_id'])
FEE_REVENUE = Counter('mcp_fee_revenue', 'Revenus des frais', ['channel_id', 'node_id'])
REBALANCING_OPS = Counter('mcp_rebalancing_operations', 'Opérations de rebalancing', ['node_id'])
ACTION_LATENCY = Histogram('mcp_action_latency', 'Latence des actions', ['action_type'])
FAILED_ACTIONS = Counter('mcp_failed_actions', 'Actions échouées', ['action_type', 'error_type'])

@dataclass
class ChannelMetrics:
    """Métriques pour un canal Lightning"""
    channel_id: str
    local_balance: int
    remote_balance: int
    last_forward_time: Optional[datetime]
    fee_revenue_24h: int
    forward_count_24h: int
    failure_count_24h: int

class AdvancedMonitoring:
    """
    Système de monitoring avancé pour MCP avec métriques détaillées,
    alerting et intégration Prometheus.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        alert_thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le système de monitoring
        
        Args:
            redis_url: URL de connexion Redis
            alert_thresholds: Seuils d'alerte personnalisés
        """
        self.redis = redis.from_url(redis_url)
        self.alert_thresholds = alert_thresholds or {
            "channel_balance_ratio": 0.1,  # Alerte si balance < 10%
            "fee_revenue_min": 1000,       # Alerte si revenus < 1000 sats/24h
            "failure_rate_max": 0.05,      # Alerte si taux d'échec > 5%
            "inactivity_hours": 24         # Alerte si inactif > 24h
        }
        
    def update_channel_metrics(self, metrics: ChannelMetrics) -> None:
        """
        Met à jour les métriques d'un canal
        
        Args:
            metrics: Métriques du canal à mettre à jour
        """
        try:
            # 1. Mise à jour des métriques Prometheus
            total_balance = metrics.local_balance + metrics.remote_balance
            CHANNEL_BALANCE.labels(
                channel_id=metrics.channel_id,
                node_id=metrics.channel_id.split(':')[0]
            ).set(metrics.local_balance)
            
            # 2. Stockage dans Redis pour historique
            key = f"metrics:channel:{metrics.channel_id}"
            data = {
                "local_balance": metrics.local_balance,
                "remote_balance": metrics.remote_balance,
                "last_forward": metrics.last_forward_time.isoformat() if metrics.last_forward_time else None,
                "fee_revenue_24h": metrics.fee_revenue_24h,
                "forward_count_24h": metrics.forward_count_24h,
                "failure_count_24h": metrics.failure_count_24h,
                "timestamp": datetime.now().isoformat()
            }
            self.redis.setex(key, 7 * 24 * 3600, str(data))  # TTL 7 jours
            
            # 3. Vérification des alertes
            self._check_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques: {e}")
            FAILED_ACTIONS.labels(
                action_type="metric_update",
                error_type=type(e).__name__
            ).inc()
            
    def record_action_result(
        self,
        action_type: str,
        success: bool,
        duration_ms: float,
        error_type: Optional[str] = None
    ) -> None:
        """
        Enregistre le résultat d'une action
        
        Args:
            action_type: Type d'action
            success: Si l'action a réussi
            duration_ms: Durée en millisecondes
            error_type: Type d'erreur si échec
        """
        try:
            # 1. Enregistrer la latence
            ACTION_LATENCY.labels(action_type=action_type).observe(duration_ms)
            
            # 2. Compter les échecs
            if not success:
                FAILED_ACTIONS.labels(
                    action_type=action_type,
                    error_type=error_type or "unknown"
                ).inc()
                
            # 3. Stocker dans Redis pour analyse
            key = f"action_result:{int(time.time())}:{action_type}"
            data = {
                "success": success,
                "duration_ms": duration_ms,
                "error_type": error_type,
                "timestamp": datetime.now().isoformat()
            }
            self.redis.setex(key, 24 * 3600, str(data))  # TTL 24h
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du résultat: {e}")
            
    def get_channel_health_report(self, channel_id: str) -> Dict[str, Any]:
        """
        Génère un rapport de santé pour un canal
        
        Args:
            channel_id: ID du canal
            
        Returns:
            Dict contenant les métriques de santé
        """
        try:
            # 1. Récupérer l'historique des métriques
            key_pattern = f"metrics:channel:{channel_id}*"
            keys = self.redis.keys(key_pattern)
            metrics_history = []
            
            for key in keys:
                data = eval(self.redis.get(key))  # Attention: eval pour demo uniquement
                metrics_history.append(data)
                
            # 2. Calculer les indicateurs de santé
            if not metrics_history:
                return {"status": "unknown", "message": "Pas de données"}
                
            latest = metrics_history[-1]
            total_balance = latest["local_balance"] + latest["remote_balance"]
            balance_ratio = latest["local_balance"] / total_balance if total_balance > 0 else 0
            
            failure_rate = (
                latest["failure_count_24h"] /
                (latest["forward_count_24h"] + latest["failure_count_24h"])
                if latest["forward_count_24h"] + latest["failure_count_24h"] > 0
                else 0
            )
            
            # 3. Générer le rapport
            return {
                "status": "healthy" if balance_ratio > 0.1 and failure_rate < 0.05 else "warning",
                "balance_ratio": balance_ratio,
                "fee_revenue_24h": latest["fee_revenue_24h"],
                "failure_rate": failure_rate,
                "last_forward": latest["last_forward"],
                "recommendations": self._generate_recommendations(latest)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            return {"status": "error", "message": str(e)}
            
    def _check_alerts(self, metrics: ChannelMetrics) -> None:
        """
        Vérifie les conditions d'alerte pour un canal
        
        Args:
            metrics: Métriques du canal
        """
        total_balance = metrics.local_balance + metrics.remote_balance
        if total_balance == 0:
            return
            
        # 1. Alerte balance faible
        balance_ratio = metrics.local_balance / total_balance
        if balance_ratio < self.alert_thresholds["channel_balance_ratio"]:
            self._send_alert(
                "balance_low",
                f"Balance faible sur {metrics.channel_id}: {balance_ratio:.1%}"
            )
            
        # 2. Alerte revenus faibles
        if metrics.fee_revenue_24h < self.alert_thresholds["fee_revenue_min"]:
            self._send_alert(
                "revenue_low",
                f"Revenus faibles sur {metrics.channel_id}: {metrics.fee_revenue_24h} sats/24h"
            )
            
        # 3. Alerte taux d'échec élevé
        total_forwards = metrics.forward_count_24h + metrics.failure_count_24h
        if total_forwards > 0:
            failure_rate = metrics.failure_count_24h / total_forwards
            if failure_rate > self.alert_thresholds["failure_rate_max"]:
                self._send_alert(
                    "high_failures",
                    f"Taux d'échec élevé sur {metrics.channel_id}: {failure_rate:.1%}"
                )
                
        # 4. Alerte inactivité
        if (metrics.last_forward_time and
            datetime.now() - metrics.last_forward_time >
            timedelta(hours=self.alert_thresholds["inactivity_hours"])):
            self._send_alert(
                "inactive_channel",
                f"Canal inactif {metrics.channel_id} depuis {metrics.last_forward_time}"
            )
            
    def _send_alert(self, alert_type: str, message: str) -> None:
        """
        Envoie une alerte
        
        Args:
            alert_type: Type d'alerte
            message: Message d'alerte
        """
        try:
            # 1. Logger l'alerte
            logger.warning(f"ALERTE {alert_type}: {message}")
            
            # 2. Stocker dans Redis
            key = f"alert:{int(time.time())}:{alert_type}"
            data = {
                "type": alert_type,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            self.redis.setex(key, 7 * 24 * 3600, str(data))
            
            # 3. Métriques Prometheus
            FAILED_ACTIONS.labels(
                action_type="alert",
                error_type=alert_type
            ).inc()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'alerte: {e}")
            
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Génère des recommandations basées sur les métriques
        
        Args:
            metrics: Métriques du canal
            
        Returns:
            Liste de recommandations
        """
        recommendations = []
        
        # 1. Recommandations balance
        total_balance = metrics["local_balance"] + metrics["remote_balance"]
        if total_balance > 0:
            balance_ratio = metrics["local_balance"] / total_balance
            if balance_ratio < 0.2:
                recommendations.append(
                    "Considérer un rebalancing pour augmenter la balance locale"
                )
            elif balance_ratio > 0.8:
                recommendations.append(
                    "Considérer un rebalancing pour réduire la balance locale"
                )
                
        # 2. Recommandations revenus
        if metrics["fee_revenue_24h"] < 1000:
            recommendations.append(
                "Revenus faibles - Considérer l'ajustement des frais"
            )
            
        # 3. Recommandations activité
        if metrics["forward_count_24h"] == 0:
            recommendations.append(
                "Canal inactif - Vérifier la connectivité et les frais"
            )
            
        return recommendations 