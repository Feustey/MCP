#!/usr/bin/env python3
"""
Script de validation de configuration production.

Vérifie que tous les paramètres critiques sont configurés correctement
avant le démarrage en production.

Usage:
    python scripts/validate_production_config.py [--env-file .env.production]

Dernière mise à jour: 15 octobre 2025
"""

import os
import sys
from pathlib import Path
import asyncio

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ConfigValidator:
    """Validateur de configuration production."""
    
    def __init__(self, env_file=".env.production"):
        self.env_file = env_file
        self.errors = []
        self.warnings = []
        self.success = []
        
    def load_env(self):
        """Charge le fichier .env."""
        if not Path(self.env_file).exists():
            self.errors.append(f"❌ Fichier {self.env_file} introuvable")
            return False
            
        # Charger les variables
        with open(self.env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    
        self.success.append(f"✅ Fichier {self.env_file} chargé")
        return True
        
    def check_required_vars(self):
        """Vérifie les variables obligatoires."""
        required = [
            ("LNBITS_URL", "URL de l'instance LNBits"),
            ("LNBITS_API_KEY", "Clé API LNBits"),
            ("MACAROON_ENCRYPTION_KEY", "Clé de chiffrement des macaroons"),
            ("MONGODB_URI", "URI MongoDB"),
        ]
        
        for var, desc in required:
            value = os.getenv(var)
            if not value or value.startswith("CHANGE_ME") or value.startswith("your_"):
                self.errors.append(f"❌ {var} non configuré ({desc})")
            else:
                self.success.append(f"✅ {var} configuré")
                
    def check_dry_run_mode(self):
        """Vérifie que le mode DRY_RUN est activé."""
        dry_run = os.getenv("DRY_RUN", "true").lower()
        
        if dry_run == "true":
            self.success.append("✅ DRY_RUN activé (Shadow Mode) - Sécurisé ✨")
        else:
            self.warnings.append("⚠️  DRY_RUN=false - Mode production réel activé!")
            
    def check_safety_limits(self):
        """Vérifie les limites de sécurité."""
        limits = [
            ("MAX_BASE_FEE_MSAT", 10000, "Frais de base max"),
            ("MAX_FEE_RATE_PPM", 5000, "Taux de frais max"),
            ("COOLDOWN_MINUTES", 60, "Cooldown entre changements"),
        ]
        
        for var, default, desc in limits:
            value = os.getenv(var)
            if value:
                self.success.append(f"✅ {var} = {value} ({desc})")
            else:
                self.warnings.append(f"⚠️  {var} non défini, utilise défaut: {default}")
                
    def check_monitoring(self):
        """Vérifie la configuration du monitoring."""
        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            self.success.append("✅ Notifications Telegram configurées")
        else:
            self.warnings.append("⚠️  Notifications Telegram non configurées")
            
        if os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true":
            self.success.append("✅ Prometheus activé")
        else:
            self.warnings.append("⚠️  Prometheus désactivé")
            
    async def check_lnbits_connection(self):
        """Test de connexion LNBits."""
        try:
            from src.clients.lnbits_client import LNBitsClient
            
            url = os.getenv("LNBITS_URL")
            api_key = os.getenv("LNBITS_API_KEY")
            
            if not url or not api_key:
                return
                
            client = LNBitsClient(url=url, api_key=api_key)
            
            # Test simple (ne fait qu'instancier, pas de requête réelle)
            self.success.append("✅ Client LNBits initialisé")
            
        except Exception as e:
            self.warnings.append(f"⚠️  Erreur initialisation LNBits: {e}")
            
    async def check_mongodb_connection(self):
        """Test de connexion MongoDB."""
        try:
            from pymongo import MongoClient
            from pymongo.server_api import ServerApi
            
            uri = os.getenv("MONGODB_URI")
            if not uri:
                return
                
            # Test connexion (timeout 5s)
            client = MongoClient(uri, serverSelectionTimeoutMS=5000, server_api=ServerApi('1'))
            client.admin.command('ping')
            
            self.success.append("✅ Connexion MongoDB OK")
            client.close()
            
        except Exception as e:
            self.warnings.append(f"⚠️  MongoDB non accessible: {e}")
            
    async def check_redis_connection(self):
        """Test de connexion Redis."""
        try:
            import redis
            
            url = os.getenv("REDIS_URL")
            if not url:
                self.warnings.append("⚠️  REDIS_URL non configuré (cache désactivé)")
                return
                
            # Test connexion
            r = redis.from_url(url, socket_connect_timeout=5)
            r.ping()
            
            self.success.append("✅ Connexion Redis OK")
            r.close()
            
        except Exception as e:
            self.warnings.append(f"⚠️  Redis non accessible: {e}")
            
    def check_file_permissions(self):
        """Vérifie les permissions des fichiers critiques."""
        files_to_check = [
            self.env_file,
            "config/decision_thresholds.yaml"
        ]
        
        for filepath in files_to_check:
            if not Path(filepath).exists():
                continue
                
            stat = Path(filepath).stat()
            mode = oct(stat.st_mode)[-3:]
            
            if mode == "600":
                self.success.append(f"✅ Permissions {filepath}: {mode} (sécurisé)")
            else:
                self.warnings.append(f"⚠️  Permissions {filepath}: {mode} (devrait être 600)")
                
    async def run_all_checks(self):
        """Exécute toutes les vérifications."""
        print("=" * 60)
        print("🔍 VALIDATION CONFIGURATION PRODUCTION MCP")
        print("=" * 60)
        print()
        
        # 1. Charger env
        if not self.load_env():
            return False
            
        # 2. Vérifications synchrones
        self.check_required_vars()
        self.check_dry_run_mode()
        self.check_safety_limits()
        self.check_monitoring()
        self.check_file_permissions()
        
        # 3. Vérifications asynchrones (connexions)
        await self.check_lnbits_connection()
        await self.check_mongodb_connection()
        await self.check_redis_connection()
        
        return True
        
    def print_results(self):
        """Affiche les résultats."""
        print()
        print("=" * 60)
        print("📊 RÉSULTATS")
        print("=" * 60)
        print()
        
        if self.success:
            print("✅ SUCCÈS:")
            for msg in self.success:
                print(f"   {msg}")
            print()
            
        if self.warnings:
            print("⚠️  AVERTISSEMENTS:")
            for msg in self.warnings:
                print(f"   {msg}")
            print()
            
        if self.errors:
            print("❌ ERREURS:")
            for msg in self.errors:
                print(f"   {msg}")
            print()
            
        print("=" * 60)
        
        if self.errors:
            print("❌ VALIDATION ÉCHOUÉE - Corriger les erreurs avant de démarrer")
            return False
        elif self.warnings:
            print("⚠️  VALIDATION PARTIELLE - Vérifier les avertissements")
            return True
        else:
            print("✅ VALIDATION RÉUSSIE - Prêt pour le démarrage")
            return True


async def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Valide la configuration production")
    parser.add_argument("--env-file", default=".env.production", help="Fichier .env à valider")
    args = parser.parse_args()
    
    validator = ConfigValidator(env_file=args.env_file)
    
    await validator.run_all_checks()
    success = validator.print_results()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

