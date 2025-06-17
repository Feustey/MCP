# Guide de Déploiement MCP sur Hostinger

> Dernière mise à jour: 12 juin 2025

## Résumé des Corrections

### Problèmes Résolus ✅

1. **Syntaxe Nixpacks corrigée** : 
   - `--config-file` → `--config` 
   - Environnement Python en lecture seule contourné avec virtualenv

2. **Scripts de build fonctionnels** :
   - `scripts/build-simple.sh` : Build local simplifié
   - `scripts/deploy-hostinger.sh` : Déploiement complet corrigé

3. **Configuration Nixpacks optimisée** :
   - Utilisation d'un environnement virtuel Python
   - Installation des dépendances isolée
   - Commandes de démarrage corrigées

## Prérequis

```bash
# Variables d'environnement requises
export OPENAI_API_KEY="votre_clé_openai"
export HOSTINGER_API_TOKEN="1|DuJsnuL7Rm50RZFKFlgV3VRhLe5P6KubyK1yR0za42f5f450"

# Optionnel
export SPARKSEER_API_KEY="votre_clé_sparkseer"
export REDIS_URL="redis://localhost:6379"
```

## Scripts Disponibles

### 1. Build Local Simplifié

```bash
# Script corrigé avec syntaxe Nixpacks valide
./scripts/build-simple.sh
```

**Fonctionnalités :**
- ✅ Syntaxe Nixpacks correcte (`--config` au lieu de `--config-file`)
- ✅ Gestion des environnements Python externally-managed
- ✅ Utilisation d'un environnement virtuel isolé
- ✅ Validation des prérequis
- ✅ Installation automatique de Nixpacks si nécessaire

### 2. Déploiement Complet Hostinger

```bash
# Script de déploiement corrigé
./scripts/deploy-hostinger.sh
```

**Améliorations :**
- ✅ Variables d'environnement corrigées (repository: Feustey/MCP, branch: berty)
- ✅ Build Nixpacks avec syntaxe valide
- ✅ Gestion des erreurs robuste
- ✅ Tests locaux avant déploiement
- ✅ Vérification post-déploiement

## Configuration Nixpacks

### Fichier `nixpacks.toml` Corrigé

```toml
[variables]
NIXPACKS_PYTHON_VERSION = "3.9"
PYTHONUNBUFFERED = "1"
PYTHONDONTWRITEBYTECODE = "1"
PORT = "8000"

[phases.setup]
nixPkgs = [
    "python39",
    "python39Packages.pip", 
    "python39Packages.setuptools",
    "python39Packages.wheel",
    "python39Packages.virtualenv",
    "gcc", "git", "curl", "openssl", "pkg-config", "libffi"
]

[phases.install]
cmds = [
    "python -m venv /opt/venv",
    ". /opt/venv/bin/activate && pip install --upgrade pip",
    ". /opt/venv/bin/activate && pip install -r requirements.txt",
    ". /opt/venv/bin/activate && pip install gunicorn uvicorn[standard]"
]

[phases.build]
cmds = [
    ". /opt/venv/bin/activate && python -m compileall . -f || true"
]

[start]
cmd = ". /opt/venv/bin/activate && gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 2"
```

**Changements clés :**
- ✅ Création d'un environnement virtuel Python isolé
- ✅ Activation du venv pour toutes les commandes pip
- ✅ Commande de démarrage avec venv activé

## Flux de Déploiement

### Étape 1 : Vérification Locale

```bash
# Tester le build localement
OPENAI_API_KEY="test-key" ./scripts/build-simple.sh
```

### Étape 2 : Déploiement Hostinger

```bash
# Déploiement complet
export HOSTINGER_API_TOKEN="1|DuJsnuL7Rm50RZFKFlgV3VRhLe5P6KubyK1yR0za42f5f450"
export OPENAI_API_KEY="votre_vraie_clé"
./scripts/deploy-hostinger.sh
```

### Étape 3 : Vérification

```bash
# Test de l'API déployée
curl https://api.dazno.de/api/v1/health
curl https://api.dazno.de/
```

## Endpoints Disponibles

Une fois déployé, l'API exposera :

- **Health Check** : `GET /api/v1/health`
- **Node Info** : `GET /api/v1/node/{pubkey}/info`  
- **Recommendations** : `GET /api/v1/node/{pubkey}/recommendations`
- **AI Priorities** : `POST /api/v1/node/{pubkey}/priorities`
- **Bulk Analysis** : `POST /api/v1/nodes/bulk-analysis`
- **Metrics** : `GET /api/v1/metrics`
- **Documentation** : `GET /docs`

## Variables d'Environnement Hostinger

Variables requises dans le dashboard Hostinger :

```bash
# Obligatoires
OPENAI_API_KEY=votre_clé_openai
HOSTINGER_API_TOKEN=1|DuJsnuL7Rm50RZFKFlgV3VRhLe5P6KubyK1yR0za42f5f450

# Recommandées  
SPARKSEER_API_KEY=votre_clé_sparkseer
REDIS_URL=redis://localhost:6379
SECRET_KEY=clé_sécurisée_générée
CORS_ORIGINS=https://dazno.de,https://api.dazno.de

# Production
ENVIRONMENT=production
PORT=8000
WORKERS=2
LOG_LEVEL=INFO
```

## Troubleshooting

### Erreur "externally-managed-environment"
✅ **Résolu** : Utilisation d'un environnement virtuel Python

### Erreur "Found argument '--config-file'"  
✅ **Résolu** : Utilisation de `--config` dans la syntaxe Nixpacks

### Erreur "Docker daemon not running"
```bash
# Sur macOS
open -a Docker
sleep 10
docker ps  # Vérifier que Docker fonctionne
```

### Erreur de variables d'environnement
```bash
# Vérifier les variables
echo $OPENAI_API_KEY
echo $HOSTINGER_API_TOKEN

# Les définir si manquantes
export OPENAI_API_KEY="votre_clé"
export HOSTINGER_API_TOKEN="1|DuJsnuL7Rm50RZFKFlgV3VRhLe5P6KubyK1yR0za42f5f450"
```

## État du Projet

- ✅ **Scripts corrigés et fonctionnels**
- ✅ **Configuration Nixpacks valide** 
- ✅ **Syntaxe Docker buildable**
- ✅ **API endpoints opérationnels**
- ✅ **Clé API Hostinger configurée**
- 🚀 **Prêt pour déploiement automatisé**

Le projet MCP est maintenant entièrement configuré pour un déploiement automatisé sur Hostinger avec Nixpacks. 