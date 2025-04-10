from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks, WebSocket, WebSocketDisconnect, Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import time
from src.auth.jwt import get_current_user
from src.auth.models import User
from .models import (
    AlertConfig, NotificationConfig, EventFilter, EventData, 
    MetricDefinition, MetricQuery, SubscriptionRequest, SubscriptionResponse,
    AlertSeverity, AlertType, NotificationChannel, TimeRange, MonitoringDashboard
)
from pydantic import BaseModel, Field
from enum import Enum
from collections import defaultdict

# Définition des modèles de données
class MetricType(str, Enum):
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"

class Metric(BaseModel):
    id: str
    name: str
    description: str
    type: MetricType
    current_value: Optional[float] = None
    unit: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

# Définitions locales - ajustées pour correspondre à models.py
class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    IN_APP = "in_app"

class NotificationConfig(BaseModel):
    id: str
    name: str
    type: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True

class AlertCondition(BaseModel):
    metric_id: str
    threshold: float
    operator: str
    duration_seconds: Optional[int] = None

class Alert(BaseModel):
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: AlertCondition
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    notification_channels: List[str] = []

class EventType(str, Enum):
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    METRIC_THRESHOLD = "metric_threshold"
    SYSTEM = "system"

class Event(BaseModel):
    id: str
    type: EventType
    source: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    acknowledged: bool = False

class AlertCreate(BaseModel):
    name: str
    description: str
    severity: AlertSeverity
    condition: AlertCondition
    notification_channels: List[str] = []

class AlertUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    condition: Optional[AlertCondition] = None
    status: Optional[AlertStatus] = None
    notification_channels: Optional[List[str]] = None

class NotificationConfigCreate(BaseModel):
    name: str
    type: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True

class MetricQuery(BaseModel):
    metrics: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    interval: Optional[str] = None
    aggregation: Optional[str] = None

class MetricDataPoint(BaseModel):
    timestamp: datetime
    value: float
    tags: Dict[str, str] = Field(default_factory=dict)

class MetricData(BaseModel):
    metric_id: str
    metric_name: str
    datapoints: List[MetricDataPoint]

class DashboardWidget(BaseModel):
    id: str
    name: str
    type: str
    metrics: List[str]
    config: Dict[str, Any]

class Dashboard(BaseModel):
    id: str
    name: str
    description: str
    widgets: List[DashboardWidget]

# Créer le router
router = APIRouter(
    prefix="/api/v2/monitor",
    tags=["Monitoring and Alerts v2"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Base de données en mémoire temporaire pour les exemples
# En production, ces données seraient stockées dans une base de données
class MonitoringDB:
    """Base de données en mémoire pour le monitoring"""
    
    def __init__(self):
        """Initialise la base de données"""
        self.alerts = {}  # alert_id -> AlertConfig
        self.events = []  # Liste d'EventData
        self.metrics = {}  # metric_name -> MetricDefinition
        self.metric_data = {}  # metric_name -> {timestamp: value}
        self.subscriptions = {}  # subscription_id -> SubscriptionRequest
        self.active_websockets = {}  # subscription_id -> List[WebSocket]
        self.notification_configs = {}  # notification_channel -> NotificationConfig
        self.dashboards = {}  # dashboard_id -> MonitoringDashboard
        
        # Pré-remplir avec des données d'exemple
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialise des données d'exemple"""
        # Ajouter des définitions de métriques
        self.metrics = {
            "node_balance_sats": MetricDefinition(
                name="node_balance_sats",
                description="Balance totale du nœud en satoshis",
                type="gauge",
                scope="node",
                unit="satoshis",
                labels=["node_id"]
            ),
            "channel_balance_ratio": MetricDefinition(
                name="channel_balance_ratio",
                description="Ratio de balance dans un canal (0-1)",
                type="gauge",
                scope="channel",
                unit="ratio",
                labels=["channel_id", "node_id", "peer_id"]
            ),
            "payment_success_rate": MetricDefinition(
                name="payment_success_rate",
                description="Taux de réussite des paiements",
                type="gauge",
                scope="payment",
                unit="percentage",
                labels=["node_id"]
            ),
            "routing_fee_earned": MetricDefinition(
                name="routing_fee_earned",
                description="Frais de routage gagnés",
                type="counter",
                scope="node",
                unit="satoshis",
                labels=["node_id", "channel_id"]
            ),
            "peer_online_ratio": MetricDefinition(
                name="peer_online_ratio",
                description="Ratio de temps où un pair est en ligne",
                type="gauge",
                scope="node",
                unit="ratio",
                labels=["node_id", "peer_id"]
            ),
        }
        
        # Ajouter des exemples d'alertes
        self.alerts = {
            "alert-1": AlertConfig(
                name="Channel Balance Alert",
                description="Alerte lorsqu'un canal devient trop déséquilibré",
                enabled=True,
                type=AlertType.CHANNEL_BALANCE,
                severity=AlertSeverity.WARNING,
                conditions=[
                    {
                        "metric": "channel_balance_ratio",
                        "operator": "<",
                        "threshold": 0.2,
                        "duration": "1h"
                    }
                ],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                template={
                    "title": "Déséquilibre de canal détecté",
                    "body": "Le canal {{channel_id}} avec {{peer_alias}} est déséquilibré (ratio: {{ratio}})"
                },
                tags=["balance", "maintenance"]
            ),
            "alert-2": AlertConfig(
                name="Payment Failure Alert",
                description="Alerte lorsque le taux d'échec des paiements dépasse un seuil",
                enabled=True,
                type=AlertType.PAYMENT_FAILURE,
                severity=AlertSeverity.ERROR,
                conditions=[
                    {
                        "metric": "payment_success_rate",
                        "operator": "<",
                        "threshold": 0.85,
                        "duration": "30m"
                    }
                ],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                template={
                    "title": "Taux d'échec des paiements élevé",
                    "body": "Le taux de réussite des paiements est tombé à {{rate}}%"
                },
                tags=["payments", "critical"]
            ),
        }
        
        # Ajouter des exemples d'événements
        current_time = datetime.utcnow()
        self.events = [
            EventData(
                id=str(uuid.uuid4()),
                type="channel_balance",
                severity=AlertSeverity.WARNING,
                source="node-1",
                timestamp=current_time - timedelta(hours=2),
                title="Déséquilibre de canal",
                message="Déséquilibre détecté dans le canal 123456",
                details={
                    "channel_id": "123456",
                    "balance_ratio": 0.15,
                    "peer_alias": "GreenNode"
                },
                related_entities=["channel-123456", "node-green1"],
                tags=["balance", "maintenance"]
            ),
            EventData(
                id=str(uuid.uuid4()),
                type="peer_status",
                severity=AlertSeverity.INFO,
                source="node-1",
                timestamp=current_time - timedelta(hours=1),
                title="Pair déconnecté",
                message="Pair déconnecté: NodeAlpha",
                details={
                    "peer_id": "node-alpha",
                    "duration": 300  # secondes
                },
                related_entities=["node-alpha"],
                tags=["connectivity"]
            ),
            EventData(
                id=str(uuid.uuid4()),
                type="payment_failure",
                severity=AlertSeverity.ERROR,
                source="node-1",
                timestamp=current_time - timedelta(minutes=15),
                title="Échec de paiement",
                message="Échec des paiements vers NodeBeta",
                details={
                    "payment_hash": "abcdef1234567890",
                    "destination": "node-beta",
                    "amount": 50000,
                    "failure_reason": "no_route"
                },
                related_entities=["node-beta"],
                tags=["payments", "routing"]
            ),
        ]
        
        # Ajouter des exemples de données métriques (24h de données)
        base_time = int(time.time()) - (24 * 3600)
        node_balance = 5000000  # 5M sats
        self.metric_data["node_balance_sats"] = {}
        
        for i in range(0, 24 * 12):  # 24 heures, 5 minute intervals
            timestamp = base_time + (i * 300)
            # Ajouter un peu de bruit aléatoire
            variation = (0.98 + 0.04 * (i % 3))
            self.metric_data["node_balance_sats"][timestamp] = node_balance * variation
            
            # Simuler une croissance progressive du solde
            if i % 12 == 0:  # Toutes les heures
                node_balance += 10000  # +10k sats
        
        # Configurer des notifications
        self.notification_configs = {
            "email": NotificationConfig(
                id="email-config-1",
                name="Email Configuration",
                channel=NotificationChannel.EMAIL,
                type=NotificationChannel.EMAIL,
                config={
                    "recipients": ["admin@example.com"],
                    "smtp_server": "smtp.example.com",
                    "smtp_port": "587",
                    "username": "alert_user",
                    "password": "********"
                },
                enabled=True
            ),
            "slack": NotificationConfig(
                id="slack-config-1",
                name="Slack Configuration",
                channel=NotificationChannel.SLACK,
                type=NotificationChannel.SLACK,
                config={
                    "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
                    "channel": "#lightning-alerts"
                },
                enabled=True
            ),
        }
        
        # Configurer des tableaux de bord
        self.dashboards = {
            "dashboard-1": MonitoringDashboard(
                id="dashboard-1",
                name="Vue d'ensemble du nœud",
                description="Tableau de bord pour surveiller l'état général du nœud",
                panels=[
                    {
                        "id": "balance_history",
                        "type": "time_series",
                        "title": "Historique de la balance",
                        "metric": "node_balance_sats",
                        "position": {"x": 0, "y": 0, "w": 12, "h": 8}
                    },
                    {
                        "id": "channel_count",
                        "type": "stat",
                        "title": "Nombre de canaux",
                        "metric": "node_channels_count",
                        "position": {"x": 12, "y": 0, "w": 6, "h": 4}
                    }
                ],
                refresh_interval=30,
                time_range=TimeRange.LAST_DAY
            ),
        }

# Initialiser la base de données temporaire
monitoring_db = MonitoringDB()

# Gestionnaire d'événements en temps réel
class EventManager:
    """Gestionnaire d'événements et de notifications"""
    
    def __init__(self, db: MonitoringDB):
        """Initialise le gestionnaire d'événements"""
        self.db = db
        self.active_connections = {}  # client_id -> WebSocket
    
    async def register_connection(self, client_id: str, websocket: WebSocket):
        """Enregistre une nouvelle connexion WebSocket"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def remove_connection(self, client_id: str):
        """Supprime une connexion WebSocket"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def broadcast_event(self, event: EventData):
        """Diffuse un événement à tous les clients connectés"""
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(event.dict())
            except Exception:
                disconnected.append(client_id)
        
        # Nettoyer les connexions fermées
        for client_id in disconnected:
            self.remove_connection(client_id)
    
    async def notify_subscribers(self, event: EventData, subscriptions: Dict[str, List[WebSocket]]):
        """Notifie les abonnés spécifiques d'un événement"""
        for subscription_id, websockets in subscriptions.items():
            subscription = self.db.subscriptions.get(subscription_id)
            if not subscription:
                continue
                
            # Vérifier si cet abonné est intéressé par ce type d'événement
            if event.type not in subscription.event_types:
                continue
                
            # Vérifier la sévérité
            if subscription.severities and event.severity not in subscription.severities:
                continue
                
            # Vérifier la source
            if subscription.sources and event.source not in subscription.sources:
                continue
                
            # Envoyer l'événement à tous les websockets de cet abonné
            for websocket in websockets:
                try:
                    await websocket.send_json(event.dict())
                except Exception:
                    # Websocket fermé, le nettoyer plus tard
                    pass

# Initialiser le gestionnaire d'événements
event_manager = EventManager(monitoring_db)

# Endpoints pour les alertes
@router.post("/alerts/configure", response_model=AlertConfig)
async def configure_alert(
    alert_config: AlertConfig = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Configure une nouvelle alerte ou met à jour une alerte existante.
    
    Cette endpoint permet de définir des conditions d'alerte basées sur des
    métriques, avec différents niveaux de sévérité et canaux de notification.
    
    Les alertes peuvent être configurées pour surveiller l'équilibre des canaux,
    la connectivité des nœuds, les échecs de paiement et d'autres conditions.
    """
    # Générer un nouvel ID si c'est une nouvelle alerte
    alert_id = str(uuid.uuid4())
    
    # Valider les conditions
    for condition in alert_config.conditions:
        if condition.metric not in monitoring_db.metrics:
            raise HTTPException(status_code=400, detail=f"Métrique inconnue: {condition.metric}")
    
    # Valider les canaux de notification
    for channel in alert_config.notification_channels:
        if channel not in [c for c in NotificationChannel]:
            raise HTTPException(status_code=400, detail=f"Canal de notification invalide: {channel}")
    
    # Enregistrer la configuration
    monitoring_db.alerts[alert_id] = alert_config
    
    return alert_config

@router.get("/alerts", response_model=List[AlertConfig])
async def get_alerts(
    enabled: Optional[bool] = Query(None, description="Filtrer par état d'activation"),
    type: Optional[AlertType] = Query(None, description="Filtrer par type d'alerte"),
    severity: Optional[AlertSeverity] = Query(None, description="Filtrer par sévérité"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des alertes configurées avec filtrage optionnel.
    
    Cette endpoint permet de voir toutes les alertes actuellement configurées
    dans le système, avec la possibilité de filtrer par état, type ou sévérité.
    """
    alerts = list(monitoring_db.alerts.values())
    
    # Appliquer les filtres
    if enabled is not None:
        alerts = [a for a in alerts if a.enabled == enabled]
    
    if type:
        alerts = [a for a in alerts if a.type == type]
    
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    return alerts

@router.get("/alerts/{alert_id}", response_model=AlertConfig)
async def get_alert(
    alert_id: str = Path(..., description="Identifiant de l'alerte"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les détails d'une alerte spécifique.
    
    Cette endpoint permet de consulter la configuration complète
    d'une alerte particulière, identifiée par son ID unique.
    """
    if alert_id not in monitoring_db.alerts:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    return monitoring_db.alerts[alert_id]

@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str = Path(..., description="Identifiant de l'alerte"),
    current_user: User = Depends(get_current_user)
):
    """
    Supprime une alerte configurée.
    
    Cette endpoint permet de supprimer définitivement une alerte
    qui n'est plus nécessaire.
    """
    if alert_id not in monitoring_db.alerts:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    del monitoring_db.alerts[alert_id]
    
    return {"status": "success", "message": f"Alerte {alert_id} supprimée"}

@router.post("/notification/configure", response_model=NotificationConfig)
async def configure_notification(
    notification_config: NotificationConfig = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Configure un canal de notification.
    
    Cette endpoint permet de définir comment les alertes doivent être
    envoyées, avec des configurations pour différents canaux comme
    l'email, Slack, Telegram ou les webhooks.
    """
    # Valider le canal
    if notification_config.channel not in [c for c in NotificationChannel]:
        raise HTTPException(status_code=400, detail=f"Canal de notification invalide: {notification_config.channel}")
    
    # Valider les identifiants selon le canal
    if notification_config.channel == NotificationChannel.EMAIL:
        required_creds = ["smtp_server", "smtp_port", "username", "password"]
        if not notification_config.config or not all(key in notification_config.config for key in required_creds):
            raise HTTPException(status_code=400, detail=f"Identifiants incomplets pour le canal email")
    
    elif notification_config.channel == NotificationChannel.WEBHOOK:
        if not notification_config.config or "url" not in notification_config.config:
            raise HTTPException(status_code=400, detail="URL du webhook manquante")
    
    # Enregistrer la configuration
    monitoring_db.notification_configs[notification_config.channel.value] = notification_config
    
    return notification_config

# Endpoints pour les événements
@router.get("/events", response_model=List[EventData])
async def get_events(
    filter: EventFilter = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les événements enregistrés avec filtrage.
    
    Cette endpoint permet de consulter l'historique des événements du système,
    avec divers filtres pour affiner les résultats selon le type, la sévérité,
    la source ou la plage de temps.
    """
    events = monitoring_db.events
    
    # Appliquer les filtres
    if filter.types:
        events = [e for e in events if e.type in filter.types]
    
    if filter.severities:
        events = [e for e in events if e.severity in filter.severities]
    
    if filter.sources:
        events = [e for e in events if e.source in filter.sources]
    
    if filter.time_range:
        if filter.time_range.start:
            events = [e for e in events if e.timestamp >= filter.time_range.start]
        
        if filter.time_range.end:
            events = [e for e in events if e.timestamp <= filter.time_range.end]
        
        if filter.time_range.duration:
            # Convertir la durée en timedelta
            units = {'h': 'hours', 'd': 'days', 'w': 'weeks', 'm': 'minutes'}
            amount = int(filter.time_range.duration[:-1])
            unit = filter.time_range.duration[-1]
            
            if unit in units:
                kwargs = {units[unit]: amount}
                start_time = datetime.utcnow() - timedelta(**kwargs)
                events = [e for e in events if e.timestamp >= start_time]
    
    if filter.tags:
        events = [e for e in events if e.tags and any(tag in filter.tags for tag in e.tags)]
    
    # Limiter le nombre de résultats
    if filter.limit:
        events = events[:filter.limit]
    
    # Trier par horodatage (plus récent en premier)
    events.sort(key=lambda e: e.timestamp, reverse=True)
    
    return events

@router.post("/events/acknowledge/{event_id}")
async def acknowledge_event(
    event_id: str = Path(..., description="Identifiant de l'événement"),
    current_user: User = Depends(get_current_user)
):
    """
    Acquitte un événement spécifique.
    
    Cette endpoint permet de marquer un événement comme traité,
    ce qui peut être utile pour le suivi des incidents et le reporting.
    """
    # Trouver l'événement
    event = next((e for e in monitoring_db.events if e.id == event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    # Mettre à jour l'événement
    event.acknowledged = True
    event.acknowledged_by = current_user.username
    event.acknowledged_at = datetime.utcnow()
    
    return {"status": "success", "message": f"Événement {event_id} acquitté"}

# Endpoints pour les métriques
@router.get("/metrics", response_model=List[MetricDefinition])
async def get_metrics(
    scope: Optional[str] = Query(None, description="Filtrer par portée"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des métriques disponibles.
    
    Cette endpoint fournit des informations sur toutes les métriques
    qui peuvent être suivies et utilisées pour configurer des alertes.
    """
    metrics = list(monitoring_db.metrics.values())
    
    # Appliquer le filtre de portée
    if scope:
        metrics = [m for m in metrics if m.scope == scope]
    
    return metrics

@router.post("/metrics/query")
async def query_metrics(
    query: MetricQuery = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les données de métriques selon une requête spécifique.
    
    Cette endpoint permet d'interroger les données historiques des métriques
    avec différentes options d'agrégation et de filtrage, utile pour
    l'analyse et la visualisation.
    """
    result = {}
    
    # Vérifier que toutes les métriques existent
    for metric_name in query.metrics:
        if metric_name not in monitoring_db.metrics:
            raise HTTPException(status_code=400, detail=f"Métrique inconnue: {metric_name}")
    
    # Déterminer la plage de temps
    start_time = None
    end_time = datetime.utcnow()
    
    if query.time_range.start:
        start_time = query.time_range.start
    
    if query.time_range.end:
        end_time = query.time_range.end
    
    if query.time_range.duration:
        # Convertir la durée en timedelta
        units = {'h': 'hours', 'd': 'days', 'w': 'weeks', 'm': 'minutes'}
        amount = int(query.time_range.duration[:-1])
        unit = query.time_range.duration[-1]
        
        if unit in units:
            kwargs = {units[unit]: amount}
            start_time = end_time - timedelta(**kwargs)
    
    # Convertir en timestamps unix
    start_ts = int(start_time.timestamp()) if start_time else 0
    end_ts = int(end_time.timestamp())
    
    # Récupérer les données pour chaque métrique
    for metric_name in query.metrics:
        if metric_name in monitoring_db.metric_data:
            # Filtrer les données selon la plage de temps
            time_series = {
                ts: value
                for ts, value in monitoring_db.metric_data[metric_name].items()
                if start_ts <= ts <= end_ts
            }
            
            # Trier les points de données
            sorted_points = sorted(time_series.items())
            
            # Convertir en format lisible
            result[metric_name] = {
                "times": [datetime.fromtimestamp(ts).isoformat() for ts, _ in sorted_points],
                "values": [value for _, value in sorted_points],
                "metric": monitoring_db.metrics[metric_name].dict(),
            }
    
    return result

# Endpoints pour les abonnements
@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_events(
    subscription: SubscriptionRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    S'abonne aux événements selon des critères spécifiques.
    
    Cette endpoint permet de créer un abonnement pour recevoir des
    notifications en temps réel lorsque certains types d'événements
    se produisent, via WebSocket ou webhook.
    """
    # Valider les types d'événements
    all_event_types = set(alert.type.value for alert in monitoring_db.alerts.values())
    all_event_types.update(["system", "custom"])  # Ajouter des types spéciaux
    
    for event_type in subscription.event_types:
        if event_type not in all_event_types and event_type != "*":
            raise HTTPException(status_code=400, detail=f"Type d'événement inconnu: {event_type}")
    
    # Générer un ID d'abonnement
    subscription_id = str(uuid.uuid4())
    
    # Enregistrer l'abonnement
    monitoring_db.subscriptions[subscription_id] = subscription
    monitoring_db.active_websockets[subscription_id] = []
    
    # Préparer la réponse
    websocket_url = None
    if subscription.delivery_method == "websocket":
        websocket_url = f"/api/v2/monitor/ws/{subscription_id}"
    
    response = SubscriptionResponse(
        subscription_id=subscription_id,
        event_types=subscription.event_types,
        created_at=datetime.utcnow(),
        status="active",
        websocket_url=websocket_url
    )
    
    return response

@router.delete("/subscribe/{subscription_id}")
async def unsubscribe(
    subscription_id: str = Path(..., description="Identifiant de l'abonnement"),
    current_user: User = Depends(get_current_user)
):
    """
    Annule un abonnement aux événements.
    
    Cette endpoint permet de supprimer un abonnement existant
    et d'arrêter de recevoir les notifications correspondantes.
    """
    if subscription_id not in monitoring_db.subscriptions:
        raise HTTPException(status_code=404, detail="Abonnement non trouvé")
    
    # Supprimer l'abonnement
    del monitoring_db.subscriptions[subscription_id]
    
    # Fermer les WebSockets associés
    for websocket in monitoring_db.active_websockets.get(subscription_id, []):
        try:
            await websocket.close()
        except Exception:
            pass
    
    # Supprimer l'entrée des WebSockets
    if subscription_id in monitoring_db.active_websockets:
        del monitoring_db.active_websockets[subscription_id]
    
    return {"status": "success", "message": f"Abonnement {subscription_id} annulé"}

@router.websocket("/ws/{subscription_id}")
async def websocket_endpoint(websocket: WebSocket, subscription_id: str):
    """
    Établit une connexion WebSocket pour recevoir des événements en temps réel.
    
    Cette endpoint permet de se connecter à un flux d'événements spécifique
    en utilisant l'ID d'abonnement obtenu lors de la création de l'abonnement.
    """
    # Vérifier que l'abonnement existe
    if subscription_id not in monitoring_db.subscriptions:
        await websocket.accept()
        await websocket.send_json({"error": "Abonnement non trouvé"})
        await websocket.close()
        return
    
    # Accepter la connexion
    await websocket.accept()
    
    # Enregistrer le WebSocket
    if subscription_id not in monitoring_db.active_websockets:
        monitoring_db.active_websockets[subscription_id] = []
    
    monitoring_db.active_websockets[subscription_id].append(websocket)
    
    try:
        # Envoyer un message initial
        await websocket.send_json({
            "type": "connected",
            "subscription_id": subscription_id,
            "message": "Connexion établie"
        })
        
        # Boucle de maintien de la connexion
        while True:
            data = await websocket.receive_text()
            # Si on reçoit un ping, répondre avec un pong
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        # Nettoyer lorsque le client se déconnecte
        if subscription_id in monitoring_db.active_websockets and websocket in monitoring_db.active_websockets[subscription_id]:
            monitoring_db.active_websockets[subscription_id].remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Nettoyer en cas d'erreur
        if subscription_id in monitoring_db.active_websockets and websocket in monitoring_db.active_websockets[subscription_id]:
            monitoring_db.active_websockets[subscription_id].remove(websocket)

# Endpoints pour les tableaux de bord
@router.get("/dashboards", response_model=List[MonitoringDashboard])
async def get_dashboards(
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la liste des tableaux de bord de monitoring.
    
    Cette endpoint fournit tous les tableaux de bord configurés
    qui peuvent être utilisés pour visualiser les métriques et
    surveiller l'état du système.
    """
    return list(monitoring_db.dashboards.values())

@router.get("/dashboards/{dashboard_id}", response_model=MonitoringDashboard)
async def get_dashboard(
    dashboard_id: str = Path(..., description="Identifiant du tableau de bord"),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère un tableau de bord spécifique.
    
    Cette endpoint permet de consulter la configuration complète
    d'un tableau de bord particulier, identifié par son ID unique.
    """
    if dashboard_id not in monitoring_db.dashboards:
        raise HTTPException(status_code=404, detail="Tableau de bord non trouvé")
    
    return monitoring_db.dashboards[dashboard_id]

@router.post("/dashboards", response_model=MonitoringDashboard)
async def create_dashboard(
    dashboard: MonitoringDashboard = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Crée un nouveau tableau de bord de monitoring.
    
    Cette endpoint permet de définir un nouveau tableau de bord
    pour visualiser les métriques importantes et surveiller
    l'état du système de manière personnalisée.
    """
    # Générer un ID si nécessaire
    if dashboard.id == "auto" or not dashboard.id:
        dashboard.id = str(uuid.uuid4())
    
    # Vérifier que l'ID n'existe pas déjà
    if dashboard.id in monitoring_db.dashboards:
        raise HTTPException(status_code=409, detail="Un tableau de bord avec cet ID existe déjà")
    
    # Enregistrer le tableau de bord
    monitoring_db.dashboards[dashboard.id] = dashboard
    
    return dashboard 