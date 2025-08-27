#!/usr/bin/env python3
"""
Script d'urgence pour redémarrer les services sur Hostinger
Utilise plusieurs méthodes pour bypasser les problèmes SSH
"""

import subprocess
import time
import urllib.request
import urllib.error
import json

def test_api_endpoint(url):
    """Test un endpoint API"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status
            text = response.read().decode('utf-8')[:200]
            return status_code == 200, text
    except Exception as e:
        return False, str(e)

def try_ssh_alternative_methods():
    """Essaye différentes méthodes pour se connecter au serveur"""
    
    methods = [
        # Méthode 1: SSH avec des options différentes
        "ssh -o ConnectTimeout=5 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no feustey@147.79.101.32 'cd /home/feustey/mcp-production && docker-compose restart'",
        
        # Méthode 2: SCP un script et l'exécuter
        "echo '#!/bin/bash\ncd /home/feustey/mcp-production\ndocker-compose down\ndocker-compose up -d' > /tmp/restart_services.sh",
        "scp -o ConnectTimeout=5 /tmp/restart_services.sh feustey@147.79.101.32:/tmp/",
        "ssh -o ConnectTimeout=5 feustey@147.79.101.32 'bash /tmp/restart_services.sh'",
        
        # Méthode 3: Via API Hostinger si disponible
        "curl -X POST https://api.hostinger.com/v1/websites/restart"
    ]
    
    print("🔄 Tentative de redémarrage des services...")
    
    for i, method in enumerate(methods[:3], 1):  # On évite les commandes curl pour l'instant
        print(f"   Méthode {i}: {method[:50]}...")
        try:
            result = subprocess.run(method, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"   ✅ Succès avec la méthode {i}")
                return True
            else:
                print(f"   ❌ Échec méthode {i}: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  Timeout méthode {i}")
        except Exception as e:
            print(f"   ❌ Erreur méthode {i}: {str(e)[:100]}")
    
    return False

def main():
    print("🚨 RÉPARATION D'URGENCE API DAZNO.DE")
    print("=" * 50)
    
    # Test des endpoints actuels
    endpoints = {
        "API Principal": "https://api.dazno.de/health",
        "RAG": "https://api.dazno.de/rag/health", 
        "Lightning": "https://api.dazno.de/lightning/health",
        "Token-for-Good": "https://api.dazno.de/token/health"
    }
    
    print("\n📊 État actuel des endpoints:")
    working_endpoints = 0
    total_endpoints = len(endpoints)
    
    for name, url in endpoints.items():
        is_working, response = test_api_endpoint(url)
        status = "✅" if is_working else "❌"
        print(f"   {status} {name}: {url}")
        if is_working:
            working_endpoints += 1
            print(f"      Response: {response}")
    
    print(f"\n📈 Score: {working_endpoints}/{total_endpoints} endpoints fonctionnels")
    
    if working_endpoints == total_endpoints:
        print("🎉 Tous les endpoints fonctionnent correctement !")
        return
    
    # Tentative de réparation
    print(f"\n🔧 {total_endpoints - working_endpoints} endpoints à réparer...")
    
    success = try_ssh_alternative_methods()
    
    if success:
        print("\n⏱️  Attente de 30 secondes pour le redémarrage...")
        time.sleep(30)
        
        # Re-test des endpoints
        print("\n📊 Nouvel état des endpoints:")
        working_endpoints_after = 0
        
        for name, url in endpoints.items():
            is_working, response = test_api_endpoint(url)
            status = "✅" if is_working else "❌"
            print(f"   {status} {name}: {url}")
            if is_working:
                working_endpoints_after += 1
        
        if working_endpoints_after > working_endpoints:
            print(f"🎉 Amélioration ! {working_endpoints_after - working_endpoints} endpoints supplémentaires réparés")
        else:
            print("⚠️  Aucune amélioration détectée")
    
    else:
        print("\n❌ Impossible de redémarrer automatiquement les services")
        print("\n📋 Actions manuelles requises:")
        print("1. Connectez-vous au panel Hostinger")
        print("2. Ou contactez le support Hostinger")
        print("3. Ou utilisez un autre client SSH")
        print("4. Commandes à exécuter:")
        print("   cd /home/feustey/mcp-production")
        print("   docker-compose down")
        print("   docker-compose up -d")

if __name__ == "__main__":
    main()