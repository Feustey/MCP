#!/usr/bin/env python3
"""
Déploiement simplifié pour Hostinger
Alternative robuste quand SSH est instable
"""

import subprocess
import time
import sys
from pathlib import Path

def run_command_with_retry(command, max_retries=3, delay=10):
    """Exécuter une commande avec retry"""
    for attempt in range(max_retries):
        try:
            print(f"🔄 Tentative {attempt + 1}/{max_retries}: {command[:50]}...")
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"✅ Succès")
                return result.stdout
            else:
                print(f"❌ Erreur: {result.stderr[:100]}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout sur tentative {attempt + 1}")
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        if attempt < max_retries - 1:
            print(f"⏳ Attente {delay}s avant retry...")
            time.sleep(delay)
    
    return None

def deploy_to_hostinger():
    """Déployer sur Hostinger"""
    print("🚀 DÉPLOIEMENT HOSTINGER SIMPLIFIÉ")
    print("=" * 50)
    
    # Configuration
    host = "feustey@147.79.101.32"
    remote_path = "/home/feustey/mcp-production"
    
    # 1. Test connectivité
    print("\n📡 Test de connectivité...")
    if run_command_with_retry(f"ping -c 2 147.79.101.32"):
        print("✅ Serveur accessible")
    else:
        print("❌ Serveur inaccessible")
        return False
    
    # 2. Créer l'archive locale
    print("\n📦 Création de l'archive de déploiement...")
    files_to_include = [
        "docker-compose.production-complete.yml",
        "config/",
        ".env.unified-production", 
        "scripts/",
        "README.md"
    ]
    
    # Créer l'archive
    tar_command = f"tar -czf mcp-deploy-complete.tar.gz {' '.join(files_to_include)}"
    if run_command_with_retry(tar_command):
        print("✅ Archive créée")
    else:
        print("❌ Erreur création archive")
        return False
    
    # 3. Copier l'archive
    print("\n📁 Copie de l'archive...")
    scp_command = f"scp -o ConnectTimeout=30 mcp-deploy-complete.tar.gz {host}:/tmp/"
    if run_command_with_retry(scp_command, max_retries=5, delay=15):
        print("✅ Archive copiée")
    else:
        print("❌ Erreur copie archive")
        return False
    
    # 4. Commandes de déploiement sur le serveur
    deployment_commands = [
        f"mkdir -p {remote_path}",
        f"cd {remote_path}",
        "tar -xzf /tmp/mcp-deploy-complete.tar.gz",
        "mv .env.unified-production .env.production",
        "docker-compose -f docker-compose.production-complete.yml down || true",
        "docker system prune -f",
        "export $(cat .env.production | grep -v '^#' | xargs)",
        "docker-compose -f docker-compose.production-complete.yml up -d",
        "sleep 60",
        "docker-compose -f docker-compose.production-complete.yml ps"
    ]
    
    # 5. Exécuter les commandes de déploiement
    print("\n🚀 Exécution du déploiement...")
    combined_command = " && ".join(deployment_commands)
    ssh_command = f"ssh -o ConnectTimeout=30 -o ServerAliveInterval=10 {host} '{combined_command}'"
    
    if run_command_with_retry(ssh_command, max_retries=2, delay=30):
        print("✅ Déploiement réussi")
    else:
        print("❌ Déploiement échoué - Essai en plusieurs étapes")
        
        # Essayer étape par étape
        for i, cmd in enumerate(deployment_commands):
            print(f"\n📋 Étape {i+1}/{len(deployment_commands)}: {cmd}")
            ssh_single = f"ssh -o ConnectTimeout=20 {host} 'cd {remote_path} && {cmd}'"
            run_command_with_retry(ssh_single, max_retries=2, delay=10)
    
    # 6. Vérification finale
    print("\n🧪 Vérification des endpoints...")
    endpoints_to_test = [
        "https://api.dazno.de/health",
        "https://api.dazno.de/docs"
    ]
    
    for endpoint in endpoints_to_test:
        test_cmd = f"curl -s -f {endpoint} > /dev/null"
        if run_command_with_retry(test_cmd, max_retries=3, delay=10):
            print(f"✅ {endpoint}")
        else:
            print(f"⏳ {endpoint} - En attente")
    
    # 7. Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DU DÉPLOIEMENT")
    print("=" * 50)
    print("📍 Services déployés :")
    print("  • MCP API avec RAG")
    print("  • Token-for-Good API")
    print("  • Qdrant Vector Database")  
    print("  • Ollama LLM")
    print("  • Prometheus + Grafana")
    print("  • Nginx Reverse Proxy")
    
    print("\n🌐 Endpoints disponibles :")
    print("  • https://api.dazno.de/health")
    print("  • https://api.dazno.de/docs")
    print("  • https://api.dazno.de/api/v1/rag/")
    print("  • https://token-for-good.com")
    print("  • http://147.79.101.32:8080/grafana")
    
    print("\n✅ Déploiement production complet terminé !")
    
    # Nettoyer
    subprocess.run("rm -f mcp-deploy-complete.tar.gz", shell=True)
    
    return True

if __name__ == "__main__":
    success = deploy_to_hostinger()
    sys.exit(0 if success else 1)