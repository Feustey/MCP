#!/usr/bin/env python3
"""
Audit de sécurité automatisé pour MCP.

Vérifie :
- Pas de secrets hardcodés dans le code
- Permissions fichiers
- Dépendances vulnérables
- Configuration sécurisée

Usage:
    python scripts/security_audit.py [--fix]

Dernière mise à jour: 15 octobre 2025
"""

import os
import re
import sys
from pathlib import Path
import subprocess
import json

class SecurityAuditor:
    """Auditeur de sécurité."""
    
    def __init__(self, fix=False):
        self.fix = fix
        self.issues = []
        self.warnings = []
        self.passed = []
        self.root = Path(__file__).parent.parent
        
    def scan_hardcoded_secrets(self):
        """Recherche de secrets hardcodés dans le code."""
        print("🔍 Scanning hardcoded secrets...")
        
        patterns = [
            (r'api_key\s*=\s*["\']([^"\']+)["\']', "API Key"),
            (r'password\s*=\s*["\']([^"\']+)["\']', "Password"),
            (r'secret\s*=\s*["\']([^"\']+)["\']', "Secret"),
            (r'token\s*=\s*["\']([^"\']+)["\']', "Token"),
            (r'mongodb://[^:]+:([^@]+)@', "MongoDB password in URL"),
        ]
        
        exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.cache'}
        exclude_files = {'security_audit.py', 'test_', '.md', '.txt', '.log'}
        
        found_secrets = []
        
        for py_file in self.root.rglob("*.py"):
            # Skip excluded directories
            if any(ex in str(py_file) for ex in exclude_dirs):
                continue
            if any(py_file.name.startswith(ex) for ex in exclude_files):
                continue
                
            try:
                content = py_file.read_text()
                
                for pattern, secret_type in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Ignorer les valeurs de test
                        value = match.group(1) if match.groups() else ""
                        if value and not any(test in value.lower() for test in ['test', 'example', 'your_', 'change_me']):
                            found_secrets.append({
                                "file": str(py_file.relative_to(self.root)),
                                "type": secret_type,
                                "line": content[:match.start()].count('\n') + 1
                            })
            except Exception as e:
                self.warnings.append(f"Erreur lecture {py_file}: {e}")
                
        if found_secrets:
            self.issues.append({
                "severity": "HIGH",
                "category": "Hardcoded Secrets",
                "count": len(found_secrets),
                "details": found_secrets[:5]  # Montrer les 5 premiers
            })
        else:
            self.passed.append("✅ Aucun secret hardcodé trouvé")
            
    def check_file_permissions(self):
        """Vérifie les permissions des fichiers sensibles."""
        print("🔐 Checking file permissions...")
        
        sensitive_files = [
            ".env",
            ".env.production",
            "config/decision_thresholds.yaml",
            "data/macaroons",
        ]
        
        issues_found = []
        
        for filepath in sensitive_files:
            path = self.root / filepath
            if not path.exists():
                continue
                
            stat = path.stat()
            mode = oct(stat.st_mode)[-3:]
            
            # Fichiers : doivent être 600 (rw-------)
            # Répertoires : doivent être 700 (rwx------)
            expected = "700" if path.is_dir() else "600"
            
            if mode != expected:
                issue = {
                    "file": str(path.relative_to(self.root)),
                    "current": mode,
                    "expected": expected
                }
                issues_found.append(issue)
                
                if self.fix:
                    try:
                        os.chmod(path, int(expected, 8))
                        issue["fixed"] = True
                    except Exception as e:
                        issue["error"] = str(e)
                        
        if issues_found:
            self.issues.append({
                "severity": "MEDIUM",
                "category": "File Permissions",
                "count": len(issues_found),
                "details": issues_found
            })
        else:
            self.passed.append("✅ Permissions fichiers OK")
            
    def check_dependencies_vulnerabilities(self):
        """Vérifie les vulnérabilités dans les dépendances."""
        print("🔬 Checking dependencies vulnerabilities...")
        
        try:
            # Installer safety si pas installé
            result = subprocess.run(
                ["pip", "show", "safety"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.warnings.append("⚠️ Package 'safety' non installé - skip vulnerability check")
                return
                
            # Exécuter safety check
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.root
            )
            
            if result.returncode == 0:
                self.passed.append("✅ Aucune vulnérabilité connue dans les dépendances")
            else:
                try:
                    vulns = json.loads(result.stdout)
                    self.issues.append({
                        "severity": "HIGH",
                        "category": "Vulnerable Dependencies",
                        "count": len(vulns),
                        "details": vulns[:3]  # 3 premières
                    })
                except:
                    self.warnings.append("⚠️ Erreur parsing résultats safety")
                    
        except FileNotFoundError:
            self.warnings.append("⚠️ 'safety' non installé - utilisez: pip install safety")
            
    def check_env_file_in_git(self):
        """Vérifie que .env n'est pas commité dans git."""
        print("📁 Checking .env in git...")
        
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                cwd=self.root
            )
            
            tracked_files = result.stdout.split('\n')
            env_files = [f for f in tracked_files if '.env' in f and not f.endswith('.example')]
            
            if env_files:
                self.issues.append({
                    "severity": "CRITICAL",
                    "category": "Env Files in Git",
                    "count": len(env_files),
                    "details": env_files
                })
            else:
                self.passed.append("✅ Aucun fichier .env dans git")
                
        except Exception as e:
            self.warnings.append(f"⚠️ Erreur vérification git: {e}")
            
    def check_secure_defaults(self):
        """Vérifie que les valeurs par défaut sont sécurisées."""
        print("⚙️  Checking secure defaults...")
        
        # Vérifier config/decision_thresholds.yaml
        config_file = self.root / "config" / "decision_thresholds.yaml"
        
        if config_file.exists():
            try:
                import yaml
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                    
                safety = config.get('safety_limits', {})
                
                checks = [
                    (safety.get('base_fee_msat_max', 0) <= 10000, "base_fee_msat_max trop élevé"),
                    (safety.get('fee_rate_ppm_max', 0) <= 5000, "fee_rate_ppm_max trop élevé"),
                    (safety.get('cooldown_minutes', 0) >= 60, "cooldown_minutes trop court"),
                ]
                
                for check, msg in checks:
                    if not check:
                        self.warnings.append(f"⚠️ {msg}")
                    else:
                        self.passed.append(f"✅ {msg.split()[0]} OK")
                        
            except Exception as e:
                self.warnings.append(f"⚠️ Erreur lecture config: {e}")
        else:
            self.warnings.append("⚠️ Config decision_thresholds.yaml introuvable")
            
    def check_cors_configuration(self):
        """Vérifie la configuration CORS."""
        print("🌐 Checking CORS configuration...")
        
        cors_origins = os.getenv("CORS_ORIGINS", "")
        
        if not cors_origins:
            self.warnings.append("⚠️ CORS_ORIGINS non configuré")
        elif "*" in cors_origins:
            self.issues.append({
                "severity": "MEDIUM",
                "category": "CORS Configuration",
                "details": "CORS_ORIGINS contient '*' (wildcard) - non sécurisé en production"
            })
        else:
            self.passed.append("✅ CORS configuré de manière sécurisée")
            
    def run_audit(self):
        """Exécute l'audit complet."""
        print("=" * 60)
        print("🔒 AUDIT DE SÉCURITÉ MCP")
        print("=" * 60)
        print()
        
        self.scan_hardcoded_secrets()
        self.check_file_permissions()
        self.check_dependencies_vulnerabilities()
        self.check_env_file_in_git()
        self.check_secure_defaults()
        self.check_cors_configuration()
        
        return self.print_results()
        
    def print_results(self):
        """Affiche les résultats."""
        print()
        print("=" * 60)
        print("📊 RÉSULTATS AUDIT")
        print("=" * 60)
        print()
        
        # Résumé
        critical = len([i for i in self.issues if i.get('severity') == 'CRITICAL'])
        high = len([i for i in self.issues if i.get('severity') == 'HIGH'])
        medium = len([i for i in self.issues if i.get('severity') == 'MEDIUM'])
        
        print(f"🔴 Issues critiques : {critical}")
        print(f"🟠 Issues haute sévérité : {high}")
        print(f"🟡 Issues moyenne sévérité : {medium}")
        print(f"⚠️  Avertissements : {len(self.warnings)}")
        print(f"✅ Checks passés : {len(self.passed)}")
        print()
        
        # Détails issues
        if self.issues:
            print("❌ ISSUES DÉTECTÉS:")
            for issue in self.issues:
                severity = issue['severity']
                category = issue['category']
                print(f"\n[{severity}] {category}:")
                if 'count' in issue:
                    print(f"  Nombre: {issue['count']}")
                if 'details' in issue:
                    for detail in issue['details'][:3]:  # 3 premiers
                        print(f"  - {detail}")
            print()
            
        # Avertissements
        if self.warnings:
            print("⚠️  AVERTISSEMENTS:")
            for warning in self.warnings:
                print(f"  {warning}")
            print()
            
        # Succès
        if self.passed:
            print("✅ CHECKS RÉUSSIS:")
            for passed in self.passed:
                print(f"  {passed}")
            print()
            
        print("=" * 60)
        
        # Verdict final
        if critical > 0:
            print("❌ AUDIT ÉCHOUÉ - Issues critiques à corriger immédiatement")
            return False
        elif high > 0:
            print("⚠️  AUDIT PARTIEL - Issues haute sévérité à corriger avant production")
            return False
        elif medium > 0 or self.warnings:
            print("⚠️  AUDIT PASSÉ AVEC AVERTISSEMENTS - Vérifier avant production")
            return True
        else:
            print("✅ AUDIT RÉUSSI - Aucun problème de sécurité détecté")
            return True


def main():
    """Point d'entrée."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit de sécurité MCP")
    parser.add_argument("--fix", action="store_true", help="Corriger les problèmes automatiquement si possible")
    args = parser.parse_args()
    
    auditor = SecurityAuditor(fix=args.fix)
    success = auditor.run_audit()
    
    if args.fix:
        print("\n🔧 Mode --fix activé - Certains problèmes ont été corrigés automatiquement")
        
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

