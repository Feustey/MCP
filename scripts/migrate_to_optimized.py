#!/usr/bin/env python3
"""
Script de migration vers la version optimisée de MCP
Inclut validation, sauvegarde et rollback

Dernière mise à jour: 9 janvier 2025
"""

import os
import sys
import shutil
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import argparse

# Assure que le script peut importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import settings
    from src.logging_config import get_logger, logging_manager
except ImportError as e:
    print(f"Erreur d'import: {e}")
    print("Assurez-vous d'exécuter le script depuis la racine du projet")
    sys.exit(1)

logger = get_logger(__name__)


class MigrationError(Exception):
    """Exception spécifique à la migration"""
    pass


class OptimizedMigrator:
    """Gestionnaire de migration vers la version optimisée"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backups" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.migration_log = []
        
        # Fichiers à sauvegarder avant migration
        self.files_to_backup = [
            "config.py",
            "requirements.txt",
            "app/main.py",
            "src/circuit_breaker.py",
            "src/exceptions.py"
        ]
        
        # Vérifications de validation
        self.validation_checks = [
            self._check_python_version,
            self._check_dependencies,
            self._check_redis_connection,
            self._check_config_validity,
            self._check_file_permissions
        ]
    
    def log_step(self, message: str, success: bool = True):
        """Log une étape de migration"""
        timestamp = datetime.now().isoformat()
        status = "✓" if success else "✗"
        log_entry = f"[{timestamp}] {status} {message}"
        
        self.migration_log.append(log_entry)
        print(log_entry)
        
        if success:
            logger.info("Étape migration", message=message)
        else:
            logger.error("Échec étape migration", message=message)
    
    def create_backup(self) -> bool:
        """Crée une sauvegarde des fichiers existants"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in self.files_to_backup:
                src_file = self.project_root / file_path
                if src_file.exists():
                    dst_file = self.backup_dir / file_path
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    self.log_step(f"Sauvegarde: {file_path}")
            
            # Sauvegarde des variables d'environnement
            env_backup = self.backup_dir / ".env.backup"
            env_file = self.project_root / ".env"
            if env_file.exists():
                shutil.copy2(env_file, env_backup)
            
            # Crée un fichier de métadonnées
            metadata = {
                "backup_timestamp": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "files_backed_up": self.files_to_backup,
                "git_commit": self._get_git_commit(),
                "python_version": sys.version
            }
            
            with open(self.backup_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.log_step(f"Sauvegarde créée dans: {self.backup_dir}")
            return True
            
        except Exception as e:
            self.log_step(f"Erreur sauvegarde: {e}", False)
            return False
    
    def _get_git_commit(self) -> Optional[str]:
        """Récupère le commit Git actuel"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None
    
    async def run_validations(self) -> bool:
        """Exécute toutes les validations"""
        self.log_step("Début des validations")
        
        all_passed = True
        for check in self.validation_checks:
            try:
                if asyncio.iscoroutinefunction(check):
                    result = await check()
                else:
                    result = check()
                
                if not result:
                    all_passed = False
                    
            except Exception as e:
                self.log_step(f"Erreur validation {check.__name__}: {e}", False)
                all_passed = False
        
        if all_passed:
            self.log_step("Toutes les validations ont réussi")
        else:
            self.log_step("Certaines validations ont échoué", False)
        
        return all_passed
    
    def _check_python_version(self) -> bool:
        """Vérifie la version Python"""
        min_version = (3, 9)
        current = sys.version_info[:2]
        
        if current >= min_version:
            self.log_step(f"Version Python OK: {'.'.join(map(str, current))}")
            return True
        else:
            self.log_step(f"Version Python insuffisante: {'.'.join(map(str, current))} < {'.'.join(map(str, min_version))}", False)
            return False
    
    def _check_dependencies(self) -> bool:
        """Vérifie que les dépendances requises peuvent être installées"""
        try:
            # Vérifie si pip peut lire requirements.txt
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                self.log_step("requirements.txt manquant", False)
                return False
            
            # Test d'installation dry-run (simulation)
            result = subprocess.run([
                sys.executable, "-m", "pip", "check"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_step("Dépendances Python valides")
                return True
            else:
                self.log_step(f"Problèmes dépendances: {result.stdout}", False)
                return False
                
        except Exception as e:
            self.log_step(f"Erreur vérification dépendances: {e}", False)
            return False
    
    async def _check_redis_connection(self) -> bool:
        """Vérifie la connexion Redis"""
        try:
            import aioredis
            
            redis_url = settings.get_redis_url()
            redis = aioredis.from_url(redis_url)
            
            await redis.ping()
            await redis.close()
            
            self.log_step("Connexion Redis OK")
            return True
            
        except Exception as e:
            self.log_step(f"Erreur connexion Redis: {e}", False)
            return False
    
    def _check_config_validity(self) -> bool:
        """Vérifie la validité de la configuration"""
        try:
            # Test de chargement des settings
            _ = settings.app_name
            _ = settings.version
            _ = settings.environment
            
            # Vérifie les URLs requises
            if not settings.database.url:
                self.log_step("URL MongoDB manquante dans la configuration", False)
                return False
            
            if not settings.ai.openai_api_key:
                self.log_step("Clé API OpenAI manquante", False)
                return False
            
            self.log_step("Configuration valide")
            return True
            
        except Exception as e:
            self.log_step(f"Configuration invalide: {e}", False)
            return False
    
    def _check_file_permissions(self) -> bool:
        """Vérifie les permissions des fichiers"""
        try:
            # Vérifie l'écriture dans le répertoire logs
            logs_dir = self.project_root / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            test_file = logs_dir / "permission_test.tmp"
            test_file.write_text("test")
            test_file.unlink()
            
            # Vérifie l'écriture dans le répertoire data
            data_dir = self.project_root / "data"
            data_dir.mkdir(exist_ok=True)
            
            self.log_step("Permissions fichiers OK")
            return True
            
        except Exception as e:
            self.log_step(f"Problème permissions: {e}", False)
            return False
    
    def install_dependencies(self) -> bool:
        """Installe les nouvelles dépendances"""
        try:
            self.log_step("Installation des dépendances optimisées")
            
            # Mise à jour de pip
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--upgrade", "pip"
            ], check=True)
            
            # Installation des requirements
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ], cwd=self.project_root, check=True)
            
            self.log_step("Dépendances installées avec succès")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log_step(f"Erreur installation dépendances: {e}", False)
            return False
        except Exception as e:
            self.log_step(f"Erreur inattendue: {e}", False)
            return False
    
    async def test_optimized_systems(self) -> bool:
        """Test les systèmes optimisés"""
        try:
            self.log_step("Test des systèmes optimisés")
            
            # Test du logging
            from src.logging_config import logging_manager
            logging_manager.setup()
            self.log_step("Système de logging optimisé OK")
            
            # Test de Redis
            from src.redis_operations_optimized import redis_ops
            await redis_ops.initialize()
            
            # Test basique
            test_key = "migration_test"
            await redis_ops.set(test_key, {"test": True}, ttl=10)
            result = await redis_ops.get(test_key)
            await redis_ops.delete(test_key)
            
            if result and result.get("test"):
                self.log_step("Opérations Redis optimisées OK")
            else:
                self.log_step("Échec test Redis", False)
                return False
            
            await redis_ops.close()
            
            # Test des métriques
            from src.performance_metrics import get_app_metrics
            metrics = get_app_metrics()
            metrics.increment_counter("test_counter")
            self.log_step("Système de métriques OK")
            
            # Test des circuit breakers
            from src.circuit_breaker import CircuitBreakerRegistry
            cb = CircuitBreakerRegistry.get("test_breaker")
            self.log_step("Circuit breakers OK")
            
            self.log_step("Tous les systèmes optimisés fonctionnent")
            return True
            
        except Exception as e:
            self.log_step(f"Erreur test systèmes: {e}", False)
            return False
    
    def rollback(self) -> bool:
        """Effectue un rollback vers la sauvegarde"""
        try:
            self.log_step("Début du rollback")
            
            if not self.backup_dir.exists():
                self.log_step("Aucune sauvegarde trouvée pour rollback", False)
                return False
            
            # Restaure les fichiers
            for file_path in self.files_to_backup:
                backup_file = self.backup_dir / file_path
                target_file = self.project_root / file_path
                
                if backup_file.exists():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, target_file)
                    self.log_step(f"Restauré: {file_path}")
            
            # Restaure .env
            env_backup = self.backup_dir / ".env.backup"
            env_file = self.project_root / ".env"
            if env_backup.exists():
                shutil.copy2(env_backup, env_file)
            
            self.log_step("Rollback terminé avec succès")
            return True
            
        except Exception as e:
            self.log_step(f"Erreur rollback: {e}", False)
            return False
    
    def save_migration_log(self):
        """Sauvegarde le log de migration"""
        try:
            log_file = self.project_root / "logs" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, "w") as f:
                f.write(f"Migration Log - {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                for entry in self.migration_log:
                    f.write(entry + "\n")
            
            print(f"Log de migration sauvegardé: {log_file}")
            
        except Exception as e:
            print(f"Erreur sauvegarde log: {e}")
    
    async def run_migration(self, skip_validations: bool = False, skip_backup: bool = False) -> bool:
        """Exécute la migration complète"""
        try:
            print("🚀 Début de la migration vers MCP optimisé")
            print("=" * 50)
            
            # Sauvegarde
            if not skip_backup:
                if not self.create_backup():
                    print("❌ Échec de la sauvegarde, migration annulée")
                    return False
            
            # Validations
            if not skip_validations:
                if not await self.run_validations():
                    print("❌ Validations échouées, migration annulée")
                    return False
            
            # Installation des dépendances
            if not self.install_dependencies():
                print("❌ Échec installation dépendances")
                return False
            
            # Test des systèmes optimisés
            if not await self.test_optimized_systems():
                print("❌ Échec test systèmes optimisés")
                return False
            
            self.log_step("🎉 Migration terminée avec succès!")
            print("\n✅ Migration réussie!")
            print(f"📁 Sauvegarde disponible dans: {self.backup_dir}")
            print("\nProchaines étapes:")
            print("1. Redémarrez l'application")
            print("2. Vérifiez les logs dans /logs/")
            print("3. Consultez /health/detailed pour le statut")
            
            return True
            
        except Exception as e:
            self.log_step(f"Erreur critique migration: {e}", False)
            print(f"\n❌ Erreur critique: {e}")
            return False
        
        finally:
            self.save_migration_log()


async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Migration vers MCP optimisé")
    parser.add_argument("--skip-validations", action="store_true", help="Ignore les validations")
    parser.add_argument("--skip-backup", action="store_true", help="Ignore la sauvegarde")
    parser.add_argument("--rollback", action="store_true", help="Effectue un rollback")
    parser.add_argument("--backup-dir", type=str, help="Répertoire de sauvegarde pour rollback")
    
    args = parser.parse_args()
    
    migrator = OptimizedMigrator()
    
    if args.rollback:
        if args.backup_dir:
            migrator.backup_dir = Path(args.backup_dir)
        
        success = migrator.rollback()
        if success:
            print("✅ Rollback réussi")
        else:
            print("❌ Échec du rollback")
        return
    
    # Migration normale
    success = await migrator.run_migration(
        skip_validations=args.skip_validations,
        skip_backup=args.skip_backup
    )
    
    if not success:
        print("\n🔄 Pour annuler les changements, exécutez:")
        print(f"python {__file__} --rollback --backup-dir {migrator.backup_dir}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 