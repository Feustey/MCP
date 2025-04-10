from fastapi.testclient import TestClient
import pytest
from datetime import datetime, timedelta
from src.api.v2.monitor.models import (
    AlertConfig, AlertType, AlertSeverity, NotificationChannel,
    EventData, MetricDefinition, TimeRange
)
from src.main import app

client = TestClient(app)

@pytest.fixture
def test_alert():
    """Fixture pour créer une alerte de test"""
    return {
        "name": "Test Alert",
        "description": "Alert for testing",
        "enabled": True,
        "type": AlertType.CHANNEL_BALANCE,
        "severity": AlertSeverity.WARNING,
        "conditions": [
            {
                "metric": "channel_balance_ratio",
                "operator": "<",
                "threshold": 0.2,
                "duration": "1h"
            }
        ],
        "notification_channels": [NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        "template": {
            "title": "Channel Balance Alert",
            "body": "Channel {{channel_id}} is unbalanced"
        },
        "tags": ["test", "channel"]
    }

@pytest.fixture
def test_notification_config():
    """Fixture pour créer une configuration de notification de test"""
    return {
        "name": "Test Email",
        "channel": NotificationChannel.EMAIL,
        "config": {
            "email": "test@example.com",
            "include_details": True
        },
        "enabled": True
    }

def test_get_metrics():
    """Teste l'endpoint pour récupérer les métriques disponibles"""
    response = client.get("/api/v2/monitor/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert isinstance(metrics, list)
    # Vérifie que certaines métriques standard sont présentes
    metric_names = [m["name"] for m in metrics]
    assert "channel_balance_ratio" in metric_names
    assert "node_balance_sats" in metric_names

def test_create_and_get_alert(test_alert):
    """Teste la création et la récupération d'une alerte"""
    # Créer une alerte
    response = client.post("/api/v2/monitor/alerts/configure", json=test_alert)
    assert response.status_code == 200
    created_alert = response.json()
    assert created_alert["name"] == test_alert["name"]
    assert "id" in created_alert
    
    # Récupérer l'alerte créée
    alert_id = created_alert["id"]
    response = client.get(f"/api/v2/monitor/alerts/{alert_id}")
    assert response.status_code == 200
    alert = response.json()
    assert alert["id"] == alert_id
    assert alert["name"] == test_alert["name"]

def test_create_and_delete_alert(test_alert):
    """Teste la création et la suppression d'une alerte"""
    # Créer une alerte
    response = client.post("/api/v2/monitor/alerts/configure", json=test_alert)
    assert response.status_code == 200
    created_alert = response.json()
    
    # Supprimer l'alerte
    alert_id = created_alert["id"]
    response = client.delete(f"/api/v2/monitor/alerts/{alert_id}")
    assert response.status_code == 200
    
    # Vérifier que l'alerte n'existe plus
    response = client.get(f"/api/v2/monitor/alerts/{alert_id}")
    assert response.status_code == 404

def test_configure_notification(test_notification_config):
    """Teste la configuration d'une notification"""
    response = client.post("/api/v2/monitor/notification/configure", json=test_notification_config)
    assert response.status_code == 200
    config = response.json()
    assert config["name"] == test_notification_config["name"]
    assert config["channel"] == test_notification_config["channel"]
    assert "id" in config

def test_query_metrics():
    """Teste la requête de données de métriques"""
    query = {
        "metrics": ["node_balance_sats", "channel_balance_ratio"],
        "start_time": (datetime.now() - timedelta(hours=24)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "step": "1h"
    }
    response = client.post("/api/v2/monitor/metrics/query", json=query)
    assert response.status_code == 200
    result = response.json()
    
    # Vérifier la structure de la réponse
    assert "series" in result
    assert isinstance(result["series"], list)
    
    # Vérifier que les séries contiennent les métriques demandées
    metrics_in_result = [s["metric"] for s in result["series"]]
    assert "node_balance_sats" in metrics_in_result

def test_get_dashboards():
    """Teste la récupération des tableaux de bord"""
    response = client.get("/api/v2/monitor/dashboards")
    assert response.status_code == 200
    dashboards = response.json()
    assert isinstance(dashboards, list)
    
    # Vérifier qu'au moins un tableau de bord existe dans les exemples
    if dashboards:
        assert "name" in dashboards[0]
        assert "widgets" in dashboards[0]

def test_create_dashboard():
    """Teste la création d'un tableau de bord"""
    dashboard = {
        "name": "Test Dashboard",
        "description": "Dashboard for testing",
        "is_default": False,
        "time_range": TimeRange.LAST_DAY,
        "widgets": [
            {
                "title": "Test Widget",
                "type": "line_chart",
                "metrics": ["node_balance_sats"],
                "options": {"showLegend": True},
                "size": {"width": 1, "height": 1},
                "position": {"x": 0, "y": 0}
            }
        ]
    }
    
    response = client.post("/api/v2/monitor/dashboards", json=dashboard)
    assert response.status_code == 200
    created = response.json()
    assert created["name"] == dashboard["name"]
    assert "id" in created
    assert len(created["widgets"]) == 1 