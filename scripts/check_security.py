#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de vérification de la configuration de sécurité MCP
Dernière mise à jour: 7 mai 2025
"""

import os
import sys
import json
import yaml
import requests
from typing import Dict, List, Optional
from datetime import datetime
import subprocess

class SecurityChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def check_docker_compose(self, file_path: str = "docker-compose.hostinger-local.yml") -> bool:
        """Vérifie la configuration Docker Compose"""
        try:
            with open(file_path) as f:
                config = yaml.safe_load(f)
                
            # Vérification des services
            services = config.get("services", {})
            
            # MongoDB
            mongo = services.get("mongodb", {})
            if not mongo.get("environment", {}).get("MONGO_INITDB_ROOT_PASSWORD"):
                self.issues.append("❌ Mot de passe MongoDB non défini")
            if "27017:27017" in str(mongo.get("ports", [])):
                self.warnings.append("⚠️ Port MongoDB exposé publiquement")
                
            # Redis
            redis = services.get("redis", {})
            if not "--requirepass" in str(redis.get("command", "")):
                self.issues.append("❌ Mot de passe Redis non défini")
            if "6379:6379" in str(redis.get("ports", [])):
                self.warnings.append("⚠️ Port Redis exposé publiquement")
                
            # API
            api = services.get("mcp-api", {})
            if not api.get("environment", {}).get("SECURITY_SECRET_KEY"):
                self.issues.append("❌ Clé secrète API non définie")
            if "*" in str(api.get("environment", {}).get("SECURITY_CORS_ORIGINS")):
                self.warnings.append("⚠️ CORS autorisé pour tous les domaines")
                
            return len(self.issues) == 0
            
        except Exception as e:
            self.issues.append(f"❌ Erreur lors de la vérification Docker Compose: {str(e)}")
            return False
            
    def check_nginx_config(self, file_path: str = "config/nginx/api.dazno.de.conf") -> bool:
        """Vérifie la configuration Nginx"""
        try:
            with open(file_path) as f:
                config = f.read()
                
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options",
                "X-XSS-Protection",
                "Content-Security-Policy"
            ]
            
            for header in security_headers:
                if header not in config:
                    self.warnings.append(f"⚠️ Header de sécurité manquant: {header}")
                    
            if "ssl_protocols TLSv1.2 TLSv1.3;" not in config:
                self.issues.append("❌ Protocoles SSL/TLS non restreints")
                
            if "server_tokens off;" not in config:
                self.warnings.append("⚠️ Tokens serveur Nginx exposés")
                
            return len(self.issues) == 0
            
        except Exception as e:
            self.issues.append(f"❌ Erreur lors de la vérification Nginx: {str(e)}")
            return False
            
    def check_ssl_certificates(self) -> bool:
        """Vérifie les certificats SSL"""
        try:
            cert_path = "/etc/letsencrypt/live/api.dazno.de/fullchain.pem"
            key_path = "/etc/letsencrypt/live/api.dazno.de/privkey.pem"
            
            if not os.path.exists(cert_path):
                self.issues.append("❌ Certificat SSL non trouvé")
            if not os.path.exists(key_path):
                self.issues.append("❌ Clé privée SSL non trouvée")
                
            # Vérification de la validité du certificat
            if os.path.exists(cert_path):
                result = subprocess.run(["openssl", "x509", "-in", cert_path, "-noout", "-dates"],
                                     capture_output=True, text=True)
                if "notAfter" in result.stdout:
                    expiry = result.stdout.split("notAfter=")[1].strip()
                    self.warnings.append(f"ℹ️ Certificat SSL expire le: {expiry}")
                    
            return len(self.issues) == 0
            
        except Exception as e:
            self.issues.append(f"❌ Erreur lors de la vérification SSL: {str(e)}")
            return False
            
    def check_backup_config(self) -> bool:
        """Vérifie la configuration des sauvegardes"""
        try:
            backup_paths = [
                "config/backup/backup.sh",
                "config/backup/crontab",
                "config/backup/cleanup.sh"
            ]
            
            for path in backup_paths:
                if not os.path.exists(path):
                    self.issues.append(f"❌ Fichier de sauvegarde manquant: {path}")
                    
            if os.path.exists("config/backup/crontab"):
                with open("config/backup/crontab") as f:
                    if not any("backup.sh" in line for line in f):
                        self.issues.append("❌ Tâche cron de sauvegarde non configurée")
                        
            return len(self.issues) == 0
            
        except Exception as e:
            self.issues.append(f"❌ Erreur lors de la vérification des sauvegardes: {str(e)}")
            return False
            
    def generate_report(self) -> str:
        """Génère un rapport de sécurité"""
        report = [
            "🔒 Rapport de sécurité MCP",
            f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🎯 Score: {len(self.issues)} problèmes, {len(self.warnings)} avertissements\n"
        ]
        
        if self.issues:
            report.append("\n🚨 Problèmes critiques:")
            for issue in self.issues:
                report.append(f"  {issue}")
                
        if self.warnings:
            report.append("\n⚠️ Avertissements:")
            for warning in self.warnings:
                report.append(f"  {warning}")
                
        if not self.issues and not self.warnings:
            report.append("\n✅ Aucun problème de sécurité détecté!")
            
        return "\n".join(report)

def main():
    """Point d'entrée principal"""
    print("🔍 Démarrage de la vérification de sécurité...")
    checker = SecurityChecker()
    
    # Exécution des vérifications
    checker.check_docker_compose()
    checker.check_nginx_config()
    checker.check_ssl_certificates()
    checker.check_backup_config()
    
    # Génération et sauvegarde du rapport
    report = checker.generate_report()
    print("\n" + report)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"data/reports/security_check_{timestamp}.txt"
    
    try:
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\n📝 Rapport sauvegardé dans {report_file}")
    except Exception as e:
        print(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
    
    # Code de sortie basé sur la présence de problèmes critiques
    sys.exit(1 if checker.issues else 0)

if __name__ == "__main__":
    main() 