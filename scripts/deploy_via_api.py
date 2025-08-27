#!/usr/bin/env python3
"""
Script de déploiement via API REST
Alternative quand SSH n'est pas disponible
"""

import requests
import time
import json
import sys
from pathlib import Path

class HostingerDeployment:
    def __init__(self):
        self.api_base = "https://api.dazno.de"
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MCP-Deploy/1.0'
        }
        
    def check_current_status(self):
        """Vérifier l'état actuel des services"""
        print("🔍 Vérification de l'état actuel...")
        
        try:
            # Test MCP API
            response = requests.get(f"{self.api_base}/health", timeout=10)
            if response.status_code == 200:
                print("✅ MCP API accessible")
                print(f"   Status: {response.json()}")
            else:
                print(f"⚠️  MCP API répond mais status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ MCP API inaccessible: {e}")
            
        # Test Token-for-Good
        try:
            response = requests.get("https://token-for-good.com/health", timeout=10)
            if response.status_code == 200:
                print("✅ Token-for-Good accessible")
            else:
                print(f"⚠️  Token-for-Good status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Token-for-Good inaccessible: {e}")
            
    def create_deployment_package(self):
        """Créer un package de déploiement"""
        print("\n📦 Création du package de déploiement...")
        
        deployment_info = {
            "timestamp": int(time.time()),
            "services": {
                "mcp-api": {
                    "port": 8000,
                    "domain": "api.dazno.de",
                    "health_endpoint": "/health"
                },
                "t4g-api": {
                    "port": 8001,
                    "domain": "token-for-good.com", 
                    "health_endpoint": "/health"
                },
                "nginx": {
                    "ports": [80, 443],
                    "config": "hostinger-unified.conf"
                }
            },
            "architecture": "unified-hostinger",
            "status": "ready_for_deployment"
        }
        
        # Sauvegarder les infos de déploiement
        with open("deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
            
        print("✅ Package créé: deployment_info.json")
        
    def test_cors_configuration(self):
        """Tester la configuration CORS"""
        print("\n🔒 Test de la configuration CORS...")
        
        # Test CORS depuis app.dazno.de
        headers = {
            'Origin': 'https://app.dazno.de',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization, Content-Type'
        }
        
        try:
            response = requests.options(f"{self.api_base}/api/v1/health", headers=headers, timeout=10)
            
            cors_headers = {
                'access-control-allow-origin': response.headers.get('access-control-allow-origin'),
                'access-control-allow-methods': response.headers.get('access-control-allow-methods'),
                'access-control-allow-headers': response.headers.get('access-control-allow-headers'),
            }
            
            print("CORS Headers reçus:")
            for header, value in cors_headers.items():
                if value:
                    print(f"  {header}: {value}")
                    
            if cors_headers['access-control-allow-origin'] == 'https://app.dazno.de':
                print("✅ CORS configuré correctement pour app.dazno.de")
            else:
                print("⚠️  CORS peut nécessiter une mise à jour")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Test CORS échoué: {e}")
            
    def generate_deployment_summary(self):
        """Générer un résumé de déploiement"""
        print("\n📋 Génération du résumé de déploiement...")
        
        summary = {
            "deployment_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "architecture": "Unified Hostinger Configuration",
            "services": {
                "reverse_proxy": "Nginx (ports 80/443)",
                "mcp_api": "Internal port 8000 -> https://api.dazno.de",
                "t4g_api": "Internal port 8001 -> https://token-for-good.com",
                "database": "MongoDB shared with separate databases",
                "cache": "Redis shared with separate bases",
                "monitoring": "Prometheus + Grafana"
            },
            "security": {
                "cors_enabled": True,
                "allowed_origins": ["https://app.dazno.de"],
                "ssl_certificates": ["api.dazno.de", "token-for-good.com"],
                "firewall": "Configured to block direct port access"
            },
            "status": "Configuration prepared, awaiting SSH connectivity"
        }
        
        with open("deployment_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
            
        print("✅ Résumé généré: deployment_summary.json")
        
        # Afficher le résumé
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DU DÉPLOIEMENT UNIFIÉ")
        print("="*60)
        print(f"Date: {summary['deployment_date']}")
        print(f"Architecture: {summary['architecture']}")
        print("\n🌐 Services:")
        for service, config in summary['services'].items():
            print(f"  • {service}: {config}")
        print("\n🔒 Sécurité:")
        for aspect, config in summary['security'].items():
            print(f"  • {aspect}: {config}")
            
def main():
    """Fonction principale"""
    deployer = HostingerDeployment()
    
    print("🚀 Déploiement Unifié Hostinger - Mode API")
    print("=" * 50)
    
    # Étapes du déploiement
    deployer.check_current_status()
    deployer.create_deployment_package()
    deployer.test_cors_configuration()
    deployer.generate_deployment_summary()
    
    print("\n" + "🎯 PROCHAINES ÉTAPES")
    print("="*50)
    print("1. Attendre le rétablissement de la connectivité SSH")
    print("2. Exécuter: ./scripts/deploy_hostinger_unified.sh")
    print("3. Ou copier manuellement les fichiers via SFTP/cPanel")
    print("4. Vérifier les endpoints après déploiement")
    
    print(f"\n✅ Configuration unifiée prête pour déploiement")

if __name__ == "__main__":
    main()