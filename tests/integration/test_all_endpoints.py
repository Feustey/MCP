"""
Tests d'intégration pour tous les endpoints RAG et Intelligence
Vérifie que tous les endpoints sont bien exposés et fonctionnels

Dernière mise à jour: 7 janvier 2025
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
import json
from datetime import datetime

# Configuration de test
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Token de test (à remplacer par un vrai token pour les tests)
TEST_TOKEN = "Bearer test_token_123"

class TestRAGEndpoints:
    """Tests pour les endpoints RAG"""
    
    @pytest.mark.asyncio
    async def test_rag_query_endpoint(self):
        """Test de l'endpoint de requête RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/query",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "query": "Comment optimiser les frais de mon nœud Lightning ?",
                    "max_results": 5,
                    "context_type": "lightning",
                    "include_validation": True
                }
            )
            
            assert response.status_code in [200, 401]  # 401 si token invalide
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "answer" in data or "error" in data
    
    @pytest.mark.asyncio
    async def test_rag_stats_endpoint(self):
        """Test de l'endpoint de statistiques RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_BASE}/rag/stats")
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "stats" in data
    
    @pytest.mark.asyncio
    async def test_rag_health_endpoint(self):
        """Test de l'endpoint de santé RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_BASE}/rag/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "details" in data
    
    @pytest.mark.asyncio
    async def test_rag_ingest_endpoint(self):
        """Test de l'endpoint d'ingestion RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/ingest",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "documents": ["Document de test pour l'ingestion RAG"],
                    "metadata": {"source": "test", "author": "test_user"},
                    "source_type": "manual"
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
    
    @pytest.mark.asyncio
    async def test_rag_history_endpoint(self):
        """Test de l'endpoint d'historique RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(
                f"{API_BASE}/rag/history?limit=10",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "history" in data
    
    @pytest.mark.asyncio
    async def test_rag_analyze_node_endpoint(self):
        """Test de l'endpoint d'analyse de nœud RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/analyze/node",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
                    "analysis_type": "performance",
                    "time_range": "7d",
                    "include_recommendations": True
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "node_pubkey" in data
    
    @pytest.mark.asyncio
    async def test_rag_workflow_execute_endpoint(self):
        """Test de l'endpoint d'exécution de workflow RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/workflow/execute",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "workflow_name": "node_analysis_workflow",
                    "parameters": {
                        "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
                    },
                    "execute_async": True
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "task_id" in data
    
    @pytest.mark.asyncio
    async def test_rag_validate_endpoint(self):
        """Test de l'endpoint de validation RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/validate",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "content": "Configuration de nœud Lightning pour test",
                    "validation_type": "config",
                    "criteria": {
                        "security_level": "high",
                        "performance_threshold": 0.8
                    }
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "validation_type" in data
    
    @pytest.mark.asyncio
    async def test_rag_benchmark_endpoint(self):
        """Test de l'endpoint de benchmark RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/benchmark",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "benchmark_type": "performance",
                    "comparison_nodes": ["node1", "node2", "node3"],
                    "metrics": ["fees", "routing", "capacity"]
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "benchmark_type" in data
    
    @pytest.mark.asyncio
    async def test_rag_assets_list_endpoint(self):
        """Test de l'endpoint de liste des assets RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(
                f"{API_BASE}/rag/assets/list",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "assets" in data
    
    @pytest.mark.asyncio
    async def test_rag_cache_clear_endpoint(self):
        """Test de l'endpoint de vidage du cache RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/rag/cache/clear",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "message" in data
    
    @pytest.mark.asyncio
    async def test_rag_cache_stats_endpoint(self):
        """Test de l'endpoint de statistiques du cache RAG"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(
                f"{API_BASE}/rag/cache/stats",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "cache_stats" in data


class TestIntelligenceEndpoints:
    """Tests pour les endpoints Intelligence"""
    
    @pytest.mark.asyncio
    async def test_intelligence_node_analyze_endpoint(self):
        """Test de l'endpoint d'analyse intelligente de nœud"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/node/analyze",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
                    "analysis_depth": "comprehensive",
                    "include_network_context": True,
                    "include_historical_data": True,
                    "include_predictions": False
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "node_pubkey" in data
                assert "intelligence_analysis" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_network_analyze_endpoint(self):
        """Test de l'endpoint d'analyse intelligente du réseau"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/network/analyze",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "network_scope": "global",
                    "analysis_type": "topology",
                    "include_metrics": ["centrality", "connectivity", "liquidity"],
                    "time_range": "7d"
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "network_scope" in data
                assert "network_intelligence" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_optimization_recommend_endpoint(self):
        """Test de l'endpoint de recommandations d'optimisation"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/optimization/recommend",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
                    "optimization_target": "fees",
                    "constraints": {
                        "min_capacity": 1000000,
                        "max_risk": 0.3
                    },
                    "risk_tolerance": "medium",
                    "include_impact_analysis": True
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "node_pubkey" in data
                assert "recommendations" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_prediction_generate_endpoint(self):
        """Test de l'endpoint de génération de prédictions"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/prediction/generate",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
                    "prediction_type": "performance",
                    "time_horizon": "30d",
                    "confidence_level": 0.8
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "node_pubkey" in data
                assert "predictions" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_comparative_analyze_endpoint(self):
        """Test de l'endpoint d'analyse comparative"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/comparative/analyze",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "node_pubkeys": ["node1", "node2", "node3"],
                    "comparison_metrics": ["fees", "routing", "capacity"],
                    "benchmark_type": "peer_group",
                    "include_rankings": True
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "node_pubkeys" in data
                assert "comparative_analysis" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_alerts_configure_endpoint(self):
        """Test de l'endpoint de configuration d'alertes intelligentes"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/alerts/configure",
                headers={"Authorization": TEST_TOKEN},
                json={
                    "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
                    "alert_types": ["performance_degradation", "fee_anomaly", "capacity_issue"],
                    "thresholds": {
                        "performance_threshold": 0.7,
                        "fee_anomaly_threshold": 0.3
                    },
                    "notification_channels": ["api", "email"]
                }
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "node_pubkey" in data
                assert "alert_configuration" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_insights_summary_endpoint(self):
        """Test de l'endpoint de résumé des insights"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(
                f"{API_BASE}/intelligence/insights/summary",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "intelligence_summary" in data
                assert "key_trends" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_workflow_automated_endpoint(self):
        """Test de l'endpoint de workflow automatisé"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.post(
                f"{API_BASE}/intelligence/workflow/automated",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "task_id" in data
                assert "workflow_type" in data
    
    @pytest.mark.asyncio
    async def test_intelligence_health_endpoint(self):
        """Test de l'endpoint de santé du système d'intelligence"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(
                f"{API_BASE}/intelligence/health/intelligence",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "intelligence_components" in data


class TestSystemEndpoints:
    """Tests pour les endpoints système"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test de l'endpoint de santé générale"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_BASE}/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test de l'endpoint racine"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(f"{API_BASE}/")
            
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "version" in data
            assert "endpoints" in data
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self):
        """Test de l'endpoint de statut"""
        async with AsyncClient(app=app, base_url=BASE_URL) as ac:
            response = await ac.get(
                f"{API_BASE}/status",
                headers={"Authorization": TEST_TOKEN}
            )
            
            assert response.status_code in [200, 401]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "timestamp" in data
                assert "services" in data


class TestEndpointCoverage:
    """Tests pour vérifier la couverture complète des endpoints"""
    
    def test_all_rag_endpoints_defined(self):
        """Vérifie que tous les endpoints RAG sont définis"""
        expected_rag_endpoints = [
            "POST /api/v1/rag/query",
            "GET /api/v1/rag/stats",
            "POST /api/v1/rag/ingest",
            "GET /api/v1/rag/history",
            "GET /api/v1/rag/health",
            "POST /api/v1/rag/analyze/node",
            "POST /api/v1/rag/workflow/execute",
            "POST /api/v1/rag/validate",
            "POST /api/v1/rag/benchmark",
            "GET /api/v1/rag/assets/list",
            "GET /api/v1/rag/assets/{asset_id}",
            "POST /api/v1/rag/cache/clear",
            "GET /api/v1/rag/cache/stats"
        ]
        
        # Vérification que tous les endpoints sont présents dans l'app
        app_routes = [f"{route.methods} {route.path}" for route in app.routes]
        
        for endpoint in expected_rag_endpoints:
            method, path = endpoint.split(" ", 1)
            assert any(method in route and path in route for route in app_routes), f"Endpoint manquant: {endpoint}"
    
    def test_all_intelligence_endpoints_defined(self):
        """Vérifie que tous les endpoints Intelligence sont définis"""
        expected_intelligence_endpoints = [
            "POST /api/v1/intelligence/node/analyze",
            "POST /api/v1/intelligence/network/analyze",
            "POST /api/v1/intelligence/optimization/recommend",
            "POST /api/v1/intelligence/prediction/generate",
            "POST /api/v1/intelligence/comparative/analyze",
            "POST /api/v1/intelligence/alerts/configure",
            "GET /api/v1/intelligence/insights/summary",
            "POST /api/v1/intelligence/workflow/automated",
            "GET /api/v1/intelligence/health/intelligence"
        ]
        
        # Vérification que tous les endpoints sont présents dans l'app
        app_routes = [f"{route.methods} {route.path}" for route in app.routes]
        
        for endpoint in expected_intelligence_endpoints:
            method, path = endpoint.split(" ", 1)
            assert any(method in route and path in route for route in app_routes), f"Endpoint manquant: {endpoint}"


if __name__ == "__main__":
    # Exécution des tests
    pytest.main([__file__, "-v"]) 