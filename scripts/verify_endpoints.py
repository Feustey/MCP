#!/usr/bin/env python3
"""
Script de vérification des endpoints RAG et Intelligence
Vérifie que tous les endpoints sont bien exposés et accessibles

Dernière mise à jour: 7 janvier 2025
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Token de test (à remplacer par un vrai token pour les tests)
TEST_TOKEN = "Bearer test_token_123"

# Liste des endpoints à vérifier
RAG_ENDPOINTS = [
    ("GET", "/api/v1/rag/health", None, "Santé RAG"),
    ("GET", "/api/v1/rag/stats", None, "Statistiques RAG"),
    ("POST", "/api/v1/rag/query", {
        "query": "Test de requête RAG",
        "max_results": 3,
        "context_type": "lightning",
        "include_validation": False
    }, "Requête RAG"),
    ("POST", "/api/v1/rag/ingest", {
        "documents": ["Document de test"],
        "metadata": {"source": "test"},
        "source_type": "manual"
    }, "Ingestion RAG"),
    ("GET", "/api/v1/rag/history?limit=5", None, "Historique RAG"),
    ("POST", "/api/v1/rag/analyze/node", {
        "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "analysis_type": "performance",
        "time_range": "7d",
        "include_recommendations": True
    }, "Analyse nœud RAG"),
    ("POST", "/api/v1/rag/workflow/execute", {
        "workflow_name": "test_workflow",
        "parameters": {"test": "value"},
        "execute_async": True
    }, "Workflow RAG"),
    ("POST", "/api/v1/rag/validate", {
        "content": "Contenu de test",
        "validation_type": "config",
        "criteria": {"test": "value"}
    }, "Validation RAG"),
    ("POST", "/api/v1/rag/benchmark", {
        "benchmark_type": "performance",
        "comparison_nodes": ["node1", "node2"],
        "metrics": ["fees", "routing"]
    }, "Benchmark RAG"),
    ("GET", "/api/v1/rag/assets/list", None, "Liste assets RAG"),
    ("GET", "/api/v1/rag/assets/test_asset", None, "Asset RAG"),
    ("POST", "/api/v1/rag/cache/clear", None, "Vidage cache RAG"),
    ("GET", "/api/v1/rag/cache/stats", None, "Stats cache RAG")
]

INTELLIGENCE_ENDPOINTS = [
    ("POST", "/api/v1/intelligence/node/analyze", {
        "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "analysis_depth": "comprehensive",
        "include_network_context": True,
        "include_historical_data": True,
        "include_predictions": False
    }, "Analyse intelligente nœud"),
    ("POST", "/api/v1/intelligence/network/analyze", {
        "network_scope": "global",
        "analysis_type": "topology",
        "include_metrics": ["centrality", "connectivity"],
        "time_range": "7d"
    }, "Analyse intelligente réseau"),
    ("POST", "/api/v1/intelligence/optimization/recommend", {
        "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "optimization_target": "fees",
        "constraints": {"min_capacity": 1000000},
        "risk_tolerance": "medium",
        "include_impact_analysis": True
    }, "Recommandations optimisation"),
    ("POST", "/api/v1/intelligence/prediction/generate", {
        "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "prediction_type": "performance",
        "time_horizon": "30d",
        "confidence_level": 0.8
    }, "Génération prédictions"),
    ("POST", "/api/v1/intelligence/comparative/analyze", {
        "node_pubkeys": ["node1", "node2", "node3"],
        "comparison_metrics": ["fees", "routing"],
        "benchmark_type": "peer_group",
        "include_rankings": True
    }, "Analyse comparative"),
    ("POST", "/api/v1/intelligence/alerts/configure", {
        "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "alert_types": ["performance_degradation"],
        "thresholds": {"performance_threshold": 0.7},
        "notification_channels": ["api"]
    }, "Configuration alertes"),
    ("GET", "/api/v1/intelligence/insights/summary", None, "Résumé insights"),
    ("POST", "/api/v1/intelligence/workflow/automated", None, "Workflow automatisé"),
    ("GET", "/api/v1/intelligence/health/intelligence", None, "Santé intelligence")
]

SYSTEM_ENDPOINTS = [
    ("GET", "/api/v1/health", None, "Santé générale"),
    ("GET", "/api/v1/", None, "Endpoint racine"),
    ("GET", "/api/v1/status", None, "Statut système")
]

class EndpointVerifier:
    """Classe pour vérifier les endpoints"""
    
    def __init__(self):
        self.results = []
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_endpoint(self, method: str, path: str, data: Dict = None, description: str = "") -> Dict:
        """Vérifie un endpoint spécifique"""
        url = f"{BASE_URL}{path}"
        headers = {"Authorization": TEST_TOKEN} if method != "GET" or "/health" not in path else {}
        
        try:
            if method == "GET":
                async with self.session.get(url, headers=headers) as response:
                    status = response.status_code
                    content = await response.text()
            elif method == "POST":
                json_data = data if data else {}
                async with self.session.post(url, headers=headers, json=json_data) as response:
                    status = response.status_code
                    content = await response.text()
            else:
                return {
                    "method": method,
                    "path": path,
                    "description": description,
                    "status": "ERROR",
                    "error": f"Méthode {method} non supportée"
                }
            
            # Analyse de la réponse
            if status == 200:
                try:
                    json_content = json.loads(content)
                    return {
                        "method": method,
                        "path": path,
                        "description": description,
                        "status": "SUCCESS",
                        "response_time": "OK",
                        "content_type": "JSON"
                    }
                except json.JSONDecodeError:
                    return {
                        "method": method,
                        "path": path,
                        "description": description,
                        "status": "SUCCESS",
                        "response_time": "OK",
                        "content_type": "TEXT"
                    }
            elif status == 401:
                return {
                    "method": method,
                    "path": path,
                    "description": description,
                    "status": "AUTH_REQUIRED",
                    "note": "Authentification requise"
                }
            elif status == 404:
                return {
                    "method": method,
                    "path": path,
                    "description": description,
                    "status": "NOT_FOUND",
                    "error": "Endpoint non trouvé"
                }
            else:
                return {
                    "method": method,
                    "path": path,
                    "description": description,
                    "status": "ERROR",
                    "error": f"Code de statut: {status}"
                }
                
        except aiohttp.ClientError as e:
            return {
                "method": method,
                "path": path,
                "description": description,
                "status": "CONNECTION_ERROR",
                "error": str(e)
            }
        except Exception as e:
            return {
                "method": method,
                "path": path,
                "description": description,
                "status": "ERROR",
                "error": str(e)
            }
    
    async def check_all_endpoints(self):
        """Vérifie tous les endpoints"""
        print("🔍 Vérification des endpoints MCP - Intelligence RAG")
        print("=" * 60)
        print(f"Base URL: {BASE_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        # Vérification des endpoints système (pas d'auth)
        print("📋 Endpoints Système:")
        print("-" * 40)
        for method, path, data, description in SYSTEM_ENDPOINTS:
            result = await self.check_endpoint(method, path, data, description)
            self.results.append(result)
            self._print_result(result)
        
        print()
        
        # Vérification des endpoints RAG
        print("🧠 Endpoints RAG:")
        print("-" * 40)
        for method, path, data, description in RAG_ENDPOINTS:
            result = await self.check_endpoint(method, path, data, description)
            self.results.append(result)
            self._print_result(result)
        
        print()
        
        # Vérification des endpoints Intelligence
        print("🧠 Endpoints Intelligence:")
        print("-" * 40)
        for method, path, data, description in INTELLIGENCE_ENDPOINTS:
            result = await self.check_endpoint(method, path, data, description)
            self.results.append(result)
            self._print_result(result)
        
        print()
        self._print_summary()
    
    def _print_result(self, result: Dict):
        """Affiche le résultat d'un endpoint"""
        status_icons = {
            "SUCCESS": "✅",
            "AUTH_REQUIRED": "🔐",
            "NOT_FOUND": "❌",
            "CONNECTION_ERROR": "🌐",
            "ERROR": "⚠️"
        }
        
        icon = status_icons.get(result["status"], "❓")
        print(f"{icon} {result['method']} {result['path']}")
        print(f"   {result['description']}")
        
        if result["status"] == "SUCCESS":
            print(f"   ✅ Statut: {result['status']}")
        elif result["status"] == "AUTH_REQUIRED":
            print(f"   🔐 {result['note']}")
        else:
            print(f"   ❌ Erreur: {result['error']}")
        print()
    
    def _print_summary(self):
        """Affiche un résumé des vérifications"""
        print("📊 Résumé des vérifications:")
        print("=" * 60)
        
        total = len(self.results)
        success = len([r for r in self.results if r["status"] == "SUCCESS"])
        auth_required = len([r for r in self.results if r["status"] == "AUTH_REQUIRED"])
        not_found = len([r for r in self.results if r["status"] == "NOT_FOUND"])
        errors = len([r for r in self.results if r["status"] in ["ERROR", "CONNECTION_ERROR"]])
        
        print(f"Total d'endpoints vérifiés: {total}")
        print(f"✅ Succès: {success}")
        print(f"🔐 Authentification requise: {auth_required}")
        print(f"❌ Non trouvés: {not_found}")
        print(f"⚠️ Erreurs: {errors}")
        print()
        
        if not_found > 0:
            print("❌ Endpoints non trouvés:")
            for result in self.results:
                if result["status"] == "NOT_FOUND":
                    print(f"   - {result['method']} {result['path']}")
            print()
        
        if errors > 0:
            print("⚠️ Endpoints avec erreurs:")
            for result in self.results:
                if result["status"] in ["ERROR", "CONNECTION_ERROR"]:
                    print(f"   - {result['method']} {result['path']}: {result['error']}")
            print()
        
        # Recommandations
        print("💡 Recommandations:")
        if not_found == 0 and errors == 0:
            print("✅ Tous les endpoints sont correctement exposés!")
        else:
            print("🔧 Vérifiez la configuration des routes dans l'application")
            print("🔧 Assurez-vous que l'application est démarrée")
            print("🔧 Vérifiez les imports des routers dans config/routes/api.py")


async def main():
    """Fonction principale"""
    try:
        async with EndpointVerifier() as verifier:
            await verifier.check_all_endpoints()
    except KeyboardInterrupt:
        print("\n⏹️ Vérification interrompue par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 Démarrage de la vérification des endpoints MCP")
    print("Assurez-vous que l'application est démarrée sur http://localhost:8000")
    print()
    
    asyncio.run(main()) 