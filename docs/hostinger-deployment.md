# Déploiement MCP sur Hostinger

**Dernière mise à jour: 9 mai 2025**

Ce guide détaille le déploiement de l'application MCP (Moniteur et Contrôleur de Performance) sur un serveur Hostinger.

## Prérequis

- Serveur VPS Hostinger avec accès SSH
- Python 3.8+ installé
- Droits sudo sur le serveur

## Installation

### 1. Connexion au serveur

```bash
ssh feustey@srv782904
```

### 2. Configuration initiale

Exécutez le script de configuration automatique :

```bash
cd /home/feustey
bash scripts/setup_hostinger.sh
```

Ce script va :
- Installer les dépendances système
- Créer un environnement virtuel Python
- Installer toutes les dépendances Python (version simplifiée)
- Configurer les répertoires nécessaires
- Créer un fichier `.env` de base avec les bases de données Hostinger

### 3. Vérification de l'installation

```bash
bash scripts/status_hostinger.sh
```

## Démarrage de l'application

### Mode interactif (pour tests)

```bash
bash scripts/start_hostinger.sh
```

### Mode arrière-plan (production)

```bash
bash scripts/start_hostinger_background.sh
```

## Gestion de l'application

### Vérifier le statut

```bash
bash scripts/status_hostinger.sh
```

### Arrêter l'application

```bash
bash scripts/stop_hostinger.sh
```

### Redémarrer l'application

```bash
bash scripts/stop_hostinger.sh
bash scripts/start_hostinger_background.sh
```

## Accès à l'application

Une fois démarrée, l'application est accessible via :

- **API principale** : `http://votre-ip:8000`
- **Documentation Swagger** : `http://votre-ip:8000/docs`
- **Health check** : `http://votre-ip:8000/health`

## Endpoints disponibles

### Endpoints de base
- `GET /health` - Vérification de l'état de santé
- `GET /docs` - Documentation interactive de l'API

### Endpoints de simulation
- `GET /api/v1/simulate/profiles` - Liste des profils de simulation
- `POST /api/v1/simulate/node` - Génération d'une simulation de nœud

### Endpoints d'optimisation
- `POST /api/v1/optimize/node/{node_id}` - Optimisation d'un nœud
- `GET /api/v1/dashboard/metrics` - Métriques du tableau de bord

## Configuration

### Variables d'environnement

Le fichier `.env` contient les configurations suivantes :

```env
# Configuration MCP pour Hostinger
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO

# Configuration serveur
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Base de données MongoDB (Hostinger)
MONGO_URL=mongodb://root:password@host:27017/?directConnection=true
MONGO_NAME=mcp

# Redis (Hostinger)
REDIS_HOST=host
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=password
REDIS_SSL=true
```

### Mode DRY_RUN

Par défaut, l'application fonctionne en mode `DRY_RUN=true`, ce qui signifie qu'elle simule les actions sans les appliquer réellement. Pour passer en mode production :

1. Modifiez le fichier `.env`
2. Changez `DRY_RUN=true` en `DRY_RUN=false`
3. Redémarrez l'application

## Dépendances

### Version simplifiée

L'installation utilise `requirements-hostinger.txt` qui contient une version simplifiée des dépendances pour éviter les conflits :

- ✅ **FastAPI, Uvicorn** - Serveur web
- ✅ **Redis, MongoDB** - Bases de données
- ✅ **OpenAI, LangChain** - IA et traitement
- ✅ **Pydantic** - Validation des données
- ❌ **sentence-transformers** - Retiré pour éviter les conflits PyTorch
- ❌ **OpenTelemetry** - Retiré pour simplifier

### Installation optionnelle de sentence-transformers

Si vous avez besoin de `sentence-transformers` pour des fonctionnalités RAG avancées :

```bash
bash scripts/install_sentence_transformers.sh
```

Ce script installe PyTorch CPU et sentence-transformers de manière compatible.

## Monitoring et logs

### Logs de l'application

```bash
# Suivre les logs en temps réel
tail -f logs/app.log

# Voir les dernières lignes
tail -n 50 logs/app.log
```

### Vérification des processus

```bash
# Voir les processus Python en cours
ps aux | grep python

# Vérifier l'utilisation des ressources
top -p $(pgrep -f "uvicorn src.api.main:app")
```

## Dépannage

### Erreur "ModuleNotFoundError: No module named 'pydantic'"

Cette erreur indique que les dépendances ne sont pas installées. Solution :

```bash
bash scripts/setup_hostinger.sh
```

### Erreur de conflit de dépendances

Si vous rencontrez des conflits avec PyTorch ou sentence-transformers :

```bash
# Utiliser la version simplifiée
rm -rf venv
bash scripts/setup_hostinger.sh

# Ou installer sentence-transformers séparément
bash scripts/install_sentence_transformers.sh
```

### Erreur de port déjà utilisé

Si le port 8000 est déjà utilisé :

```bash
# Voir ce qui utilise le port 8000
sudo netstat -tlnp | grep :8000

# Arrêter l'application précédente
bash scripts/stop_hostinger.sh
```

### Problème de permissions

```bash
# Vérifier les permissions
ls -la /home/feustey/

# Corriger les permissions si nécessaire
chmod +x scripts/*.sh
chown -R feustey:feustey /home/feustey/
```

## Sécurité

### Firewall

Assurez-vous que le port 8000 est ouvert dans votre firewall :

```bash
# Vérifier le statut du firewall
sudo ufw status

# Ouvrir le port 8000 si nécessaire
sudo ufw allow 8000
```

### HTTPS (recommandé)

Pour une utilisation en production, configurez HTTPS avec Let's Encrypt :

```bash
# Installation de Certbot
sudo apt-get install certbot

# Génération du certificat
sudo certbot certonly --standalone -d votre-domaine.com
```

## Sauvegarde

### Sauvegarde des données

```bash
# Créer une sauvegarde
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ rag/RAG_assets/ logs/
```

### Restauration

```bash
# Restaurer une sauvegarde
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
```

## Support

En cas de problème :

1. Vérifiez les logs : `tail -f logs/app.log`
2. Consultez le statut : `bash scripts/status_hostinger.sh`
3. Redémarrez l'application : `bash scripts/stop_hostinger.sh && bash scripts/start_hostinger_background.sh`

## Mise à jour

Pour mettre à jour l'application :

```bash
# Arrêter l'application
bash scripts/stop_hostinger.sh

# Mettre à jour le code (git pull ou upload des fichiers)

# Réinstaller les dépendances si nécessaire
bash scripts/setup_hostinger.sh

# Redémarrer l'application
bash scripts/start_hostinger_background.sh
``` 