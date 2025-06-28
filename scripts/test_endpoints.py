#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test des endpoints de l'API MCP
Dernière mise à jour: 7 mai 2025
"""

import requests
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime
import time

class EndpointTester:
    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.auth_token = None
        
    def test_health(self) -> bool:
        """Test l'endpoint de santé"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Erreur sur /health: {str(e)}")
            return False
            
    def authenticate(self) -> bool:
        """Authentification à l'API"""
        try:
            auth_data = {
                "username": "admin",
                "password": "admin"
            }
            response = self.session.post(f"{self.base_url}/auth/token", json=auth_data)
            if response.status_code == 200:
                self.auth_token = response.json()["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                return True
            return False
        except Exception as e:
            print(f"❌ Erreur d'authentification: {str(e)}")
            return False
            
    def test_endpoints(self) -> Dict[str, bool]:
        """Test tous les endpoints de l'API"""
        endpoints = {
            "GET /health": self.test_health,
            "POST /auth/token": self.authenticate,
            "GET /api/v1/nodes": lambda: self.test_get("/api/v1/nodes"),
            "GET /api/v1/metrics": lambda: self.test_get("/api/v1/metrics"),
            "GET /api/v1/analytics": lambda: self.test_get("/api/v1/analytics"),
            "GET /api/v1/config": lambda: self.test_get("/api/v1/config"),
            "GET /api/v1/status": lambda: self.test_get("/api/v1/status"),
            "GET /api/v1/optimization": lambda: self.test_get("/api/v1/optimization")
        }
        
        results = {}
        for name, test_func in endpoints.items():
            print(f"🔍 Test de {name}...")
            success = test_func()
            results[name] = success
            print(f"{'✅' if success else '❌'} {name}")
            time.sleep(1)  # Éviter le rate limiting
            
        return results
        
    def test_get(self, endpoint: str) -> bool:
        """Test un endpoint GET générique"""
        try:
            response = self.session.get(f"{self.base_url}{endpoint}")
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"❌ Erreur sur {endpoint}: {str(e)}")
            return False
            
    def generate_report(self, results: Dict[str, bool]) -> str:
        """Génère un rapport des tests"""
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        report = [
            "📊 Rapport de test des endpoints MCP",
            f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🎯 Score: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)",
            "\nDétails des tests:",
        ]
        
        for endpoint, success in results.items():
            status = "✅" if success else "❌"
            report.append(f"{status} {endpoint}")
            
        return "\n".join(report)

def main():
    """Point d'entrée principal"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost"
    
    print(f"🚀 Démarrage des tests sur {base_url}")
    tester = EndpointTester(base_url)
    
    results = tester.test_endpoints()
    report = tester.generate_report(results)
    
    print("\n" + report)
    
    # Sauvegarde du rapport
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"data/reports/endpoint_test_{timestamp}.txt"
    
    try:
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\n📝 Rapport sauvegardé dans {report_file}")
    except Exception as e:
        print(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
    
    # Code de sortie basé sur le succès des tests
    success_rate = sum(1 for v in results.values() if v) / len(results)
    sys.exit(0 if success_rate >= 0.8 else 1)

if __name__ == "__main__":
    main() 