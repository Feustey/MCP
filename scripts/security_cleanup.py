#!/usr/bin/env python3
"""
Script de nettoyage des vulnérabilités de sécurité critique
Génère par Claude Code - Audit de sécurité MCP

🔴 URGENT: Ce script corrige les vulnérabilités critiques identifiées
"""

import os
import re
import json
import shutil
import secrets
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class SecurityCleanup:
    """Nettoyage automatisé des vulnérabilités de sécurité"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.backup_dir = self.base_path / "backups" / f"security_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.vulnerabilities_found = []
        self.fixes_applied = []
        
    def scan_hardcoded_secrets(self) -> List[Dict]:
        """Scan pour les secrets en dur dans le code"""
        print("🔍 Scanning for hardcoded secrets...")
        
        secret_patterns = [
            (r'password\s*[=:]\s*["\']([^"\']+)["\']', 'password'),
            (r'secret\s*[=:]\s*["\']([^"\']+)["\']', 'secret'),
            (r'api[_-]?key\s*[=:]\s*["\']([^"\']+)["\']', 'api_key'),
            (r'token\s*[=:]\s*["\']([^"\']+)["\']', 'token'),
            (r'[A-Za-z0-9]{64,}', 'potential_secret'),  # Long strings
        ]
        
        vulnerable_files = []
        
        # Fichiers à scanner (éviter les dossiers de backup et venv)
        exclude_dirs = {'backups', 'venv_new', 'venv_rag', '.git', 'node_modules', '__pycache__'}
        
        for file_path in self.base_path.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix in {'.py', '.yml', '.yaml', '.sh', '.env', '.md'} and
                not any(excluded in file_path.parts for excluded in exclude_dirs)):
                
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    for pattern, secret_type in secret_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            if len(match.group(1) if match.groups() else match.group()) > 10:
                                vulnerable_files.append({
                                    'file': str(file_path.relative_to(self.base_path)),
                                    'type': secret_type,
                                    'line': content[:match.start()].count('\n') + 1,
                                    'match': match.group()[:50] + '...' if len(match.group()) > 50 else match.group()
                                })
                                
                except Exception as e:
                    print(f"⚠️  Error reading {file_path}: {e}")
        
        self.vulnerabilities_found.extend(vulnerable_files)
        print(f"🚨 Found {len(vulnerable_files)} potential hardcoded secrets")
        return vulnerable_files
    
    def scan_eval_usage(self) -> List[Dict]:
        """Scan pour les usages dangereux de eval()"""
        print("🔍 Scanning for dangerous eval() usage...")
        
        eval_files = []
        
        for file_path in self.base_path.rglob('*.py'):
            if not any(excluded in file_path.parts for excluded in {'backups', 'venv_new', 'venv_rag', '.git'}):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Recherche eval() avec contexte
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'eval(' in line and not line.strip().startswith('#'):
                            eval_files.append({
                                'file': str(file_path.relative_to(self.base_path)),
                                'line': i,
                                'code': line.strip(),
                                'context': lines[max(0, i-2):i+2]  # Contexte autour
                            })
                            
                except Exception as e:
                    print(f"⚠️  Error reading {file_path}: {e}")
        
        self.vulnerabilities_found.extend(eval_files)
        print(f"🚨 Found {len(eval_files)} dangerous eval() usages")
        return eval_files
    
    def create_backup(self):
        """Créer une sauvegarde avant modifications"""
        print(f"💾 Creating backup in {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder les fichiers critiques
        critical_files = [
            'docker-compose*.yml',
            'deploy*.sh',
            '*.env*',
            'src/services/parallel_retrieval_system.py',
            'src/tools/advanced_monitoring.py',
            'src/optimizers/advanced_fee_optimizer.py'
        ]
        
        for pattern in critical_files:
            for file_path in self.base_path.rglob(pattern):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.base_path)
                    backup_path = self.backup_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path)
    
    def fix_eval_usage(self):
        """Correction automatique des usages dangereux de eval()"""
        print("🔧 Fixing dangerous eval() usage...")
        
        fixes = {
            'eval(doc_data["embedding"])': 'json.loads(doc_data["embedding"])',
            'eval(market_data)': 'json.loads(market_data)',
            'eval(self.redis.get(key))': 'json.loads(self.redis.get(key) or "{}")',
            'eval(test_data)': 'json.loads(test_data)',
            'eval(doc_data)': 'json.loads(doc_data)',
            'eval(state_str)': 'json.loads(state_str)',
            'eval(actions_str)': 'json.loads(actions_str)'
        }
        
        eval_files = [
            'src/services/parallel_retrieval_system.py',
            'src/tools/advanced_monitoring.py',
            'src/optimizers/advanced_fee_optimizer.py',
            'src/tools/ab_testing.py',
            'src/tools/rag_integration.py',
            'src/tools/generate_optimization_report.py'
        ]
        
        for file_path_str in eval_files:
            file_path = self.base_path / file_path_str
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    original_content = content
                    
                    # Appliquer les corrections
                    for dangerous, safe in fixes.items():
                        if dangerous in content:
                            content = content.replace(dangerous, safe)
                            print(f"  ✅ Fixed {dangerous} in {file_path_str}")
                    
                    # Ajouter import json si nécessaire
                    if 'json.loads' in content and 'import json' not in content:
                        if content.startswith('import') or content.startswith('from'):
                            # Ajouter après les imports existants
                            lines = content.split('\n')
                            import_end = 0
                            for i, line in enumerate(lines):
                                if line.startswith(('import ', 'from ')) or line.strip() == '':
                                    import_end = i
                                else:
                                    break
                            lines.insert(import_end + 1, 'import json')
                            content = '\n'.join(lines)
                        else:
                            content = 'import json\n' + content
                    
                    if content != original_content:
                        file_path.write_text(content, encoding='utf-8')
                        self.fixes_applied.append(f"Fixed eval() in {file_path_str}")
                        
                except Exception as e:
                    print(f"❌ Error fixing {file_path_str}: {e}")
    
    def generate_secure_env_template(self):
        """Générer un template .env sécurisé"""
        print("📝 Generating secure .env template...")
        
        env_template = """# MCP Security Configuration Template
# 🔒 GENERATED BY SECURITY AUDIT - Ne jamais committer de vraies valeurs!

# ================================
# SECRETS DE SÉCURITÉ (OBLIGATOIRES)
# ================================
# Générer avec: python -c "import secrets; print(secrets.token_urlsafe(64))"
SECURITY_SECRET_KEY=CHANGE_ME_GENERATE_SECURE_64_BYTE_KEY
JWT_SECRET=CHANGE_ME_GENERATE_SECURE_JWT_SECRET

# ================================
# BASE DE DONNÉES
# ================================
MONGO_USERNAME=mcp_user
MONGO_PASSWORD=CHANGE_ME_GENERATE_SECURE_PASSWORD
MONGO_DB=mcp
MONGO_HOST=mongodb
MONGO_PORT=27017

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME_GENERATE_SECURE_REDIS_PASSWORD
REDIS_SSL=false
REDIS_MAX_CONNECTIONS=20

# ================================
# API KEYS EXTERNES
# ================================
OPENAI_API_KEY=sk-CHANGE_ME_YOUR_OPENAI_KEY
AI_OPENAI_API_KEY=sk-CHANGE_ME_YOUR_OPENAI_KEY
ANTHROPIC_API_KEY=sk-ant-CHANGE_ME_YOUR_ANTHROPIC_KEY
SPARKSEER_API_KEY=CHANGE_ME_YOUR_SPARKSEER_KEY

# ================================
# LIGHTNING NETWORK
# ================================
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_INKEY=CHANGE_ME_YOUR_LNBITS_INVOICE_KEY
LNBITS_ADMIN_KEY=CHANGE_ME_YOUR_LNBITS_ADMIN_KEY

# ================================
# MONITORING
# ================================
GRAFANA_PASSWORD=CHANGE_ME_SECURE_GRAFANA_PASSWORD
GRAFANA_SECRET_KEY=CHANGE_ME_GENERATE_SECURE_GRAFANA_SECRET

# ================================
# TELEGRAM (OPTIONNEL)
# ================================
TELEGRAM_BOT_TOKEN=CHANGE_ME_YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=CHANGE_ME_YOUR_CHAT_ID

# ================================
# SÉCURITÉ
# ================================
SECURITY_CORS_ORIGINS=["https://app.dazno.de","https://dazno.de"]
SECURITY_ALLOWED_HOSTS=["api.dazno.de","localhost","127.0.0.1"]

# ================================
# ENVIRONNEMENT
# ================================
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
WORKERS=4

# ================================
# INSTRUCTIONS IMPORTANTES
# ================================
# 1. Copiez ce fichier vers .env
# 2. Remplacez TOUS les CHANGE_ME par de vraies valeurs
# 3. Générez des secrets forts avec des outils cryptographiques
# 4. Ne jamais committer le fichier .env final
# 5. Utilisez un gestionnaire de secrets en production
"""
        
        template_path = self.base_path / '.env.template.secure'
        template_path.write_text(env_template)
        self.fixes_applied.append("Created secure .env template")
        print(f"  ✅ Created {template_path}")
    
    def generate_security_script(self):
        """Générer un script de génération de secrets"""
        print("🔐 Generating secret generation script...")
        
        script_content = '''#!/usr/bin/env python3
"""
Générateur de secrets sécurisés pour MCP
Généré par Claude Code - Audit de sécurité
"""

import secrets
import string
import base64
import hashlib

def generate_secret_key(length=64):
    """Générer une clé secrète sécurisée"""
    return secrets.token_urlsafe(length)

def generate_password(length=32):
    """Générer un mot de passe fort"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret():
    """Générer un secret JWT sécurisé"""
    return base64.b64encode(secrets.token_bytes(64)).decode('ascii')

def main():
    print("🔐 MCP Security Secrets Generator")
    print("=" * 50)
    
    secrets_to_generate = {
        'SECURITY_SECRET_KEY': generate_secret_key(64),
        'JWT_SECRET': generate_jwt_secret(),
        'MONGO_PASSWORD': generate_password(32),
        'REDIS_PASSWORD': generate_password(32),
        'GRAFANA_PASSWORD': generate_password(16),
        'GRAFANA_SECRET_KEY': generate_secret_key(32)
    }
    
    print("\\n📋 Secrets générés (à copier dans votre .env):")
    print("-" * 50)
    
    for key, value in secrets_to_generate.items():
        print(f"{key}={value}")
    
    print("\\n⚠️  IMPORTANT:")
    print("- Copiez ces valeurs dans votre fichier .env")
    print("- Ne partagez jamais ces secrets")
    print("- Régénérez-les régulièrement")
    print("- Utilisez un gestionnaire de secrets en production")

if __name__ == "__main__":
    main()
'''
        
        script_path = self.base_path / 'scripts' / 'generate_secrets.py'
        script_path.write_text(script_content)
        script_path.chmod(0o755)  # Rendre exécutable
        self.fixes_applied.append("Created secret generation script")
        print(f"  ✅ Created {script_path}")
    
    def create_gitignore_security(self):
        """Mettre à jour .gitignore pour la sécurité"""
        print("🚫 Updating .gitignore for security...")
        
        gitignore_path = self.base_path / '.gitignore'
        
        security_rules = """
# ================================
# SECURITY - NEVER COMMIT THESE
# ================================
*.env
*.env.*
!*.env.template*
!*.env.example*
secrets/
credentials/
keys/
*.key
*.pem
*.p12
*.pfx

# Database dumps
*.sql
*.dump
backup_*

# Configuration with secrets
config/production/*
deploy_*.sh
*_secrets.yml
*_credentials.json
"""
        
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if "SECURITY - NEVER COMMIT THESE" not in content:
                gitignore_path.write_text(content + security_rules)
                self.fixes_applied.append("Updated .gitignore for security")
        else:
            gitignore_path.write_text(security_rules)
            self.fixes_applied.append("Created .gitignore with security rules")
        
        print("  ✅ Updated .gitignore")
    
    def generate_report(self):
        """Générer un rapport de correction"""
        print("📊 Generating security fix report...")
        
        report = f"""# RAPPORT DE CORRECTION SÉCURITÉ MCP
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Généré par: Claude Code Security Audit

## 🚨 VULNÉRABILITÉS TROUVÉES
Total: {len(self.vulnerabilities_found)}

### Secrets hardcodés détectés:
"""
        
        for vuln in self.vulnerabilities_found:
            if isinstance(vuln, dict) and 'type' in vuln:
                report += f"- {vuln['file']}:{vuln.get('line', 'N/A')} - {vuln['type']} - {vuln.get('match', 'N/A')}\n"
        
        report += f"""
## ✅ CORRECTIONS APPLIQUÉES
Total: {len(self.fixes_applied)}

"""
        
        for fix in self.fixes_applied:
            report += f"- {fix}\n"
        
        report += """
## 🔧 ACTIONS REQUISES MANUELLEMENT

### 1. URGENT - Nettoyage des secrets (0-24h)
- [ ] Examiner tous les fichiers avec secrets détectés
- [ ] Remplacer par des variables d'environnement
- [ ] Supprimer les secrets de l'historique Git si nécessaire
- [ ] Révoquer et régénérer tous les secrets exposés

### 2. Configuration sécurisée (1-3 jours)
- [ ] Utiliser le script generate_secrets.py pour créer de nouveaux secrets
- [ ] Configurer un gestionnaire de secrets (vault)
- [ ] Mettre en place la rotation automatique des secrets
- [ ] Tester l'application avec la nouvelle configuration

### 3. Monitoring et prévention (1 semaine)
- [ ] Configurer des alertes pour détection de secrets
- [ ] Mettre en place des pre-commit hooks
- [ ] Former l'équipe sur les bonnes pratiques
- [ ] Audit de sécurité régulier

## 🚨 NOTES IMPORTANTES
- Sauvegarde créée dans: backups/security_cleanup_*
- Ne jamais committer de vrais secrets
- Tester en environnement sécurisé avant production
- Considérer un pentest après corrections
"""
        
        report_path = self.base_path / f'SECURITY_FIX_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        report_path.write_text(report)
        print(f"  ✅ Report saved to {report_path}")
        
        return report
    
    def run_cleanup(self):
        """Exécuter le nettoyage complet"""
        print("🚀 Starting MCP Security Cleanup...")
        print("=" * 60)
        
        # 1. Créer backup
        self.create_backup()
        
        # 2. Scanner les vulnérabilités
        self.scan_hardcoded_secrets()
        self.scan_eval_usage()
        
        # 3. Appliquer les corrections
        self.fix_eval_usage()
        self.generate_secure_env_template()
        self.generate_security_script()
        self.create_gitignore_security()
        
        # 4. Générer rapport
        report = self.generate_report()
        
        print("\n" + "=" * 60)
        print("✅ SECURITY CLEANUP COMPLETED!")
        print(f"📊 {len(self.vulnerabilities_found)} vulnerabilities found")
        print(f"🔧 {len(self.fixes_applied)} fixes applied")
        print("📋 Manual actions required - see report")
        print("=" * 60)
        
        return report

if __name__ == "__main__":
    import sys
    
    base_path = sys.argv[1] if len(sys.argv) > 1 else "."
    cleanup = SecurityCleanup(base_path)
    cleanup.run_cleanup()