# Guide de Déploiement Production Hostinger

> Dernière mise à jour: 27 octobre 2025

## 🎯 Objectif

Ce guide détaille le déploiement complet du système MCP sur le serveur de production Hostinger avec les 5 services essentiels :

1. **MongoDB** - Base de données
2. **Redis** - Cache
3. **MCP API** - Application FastAPI
4. **Nginx** - Reverse proxy
5. **Ollama** - Inférence LLM locale

---

## 📋 Prérequis

### Sur votre machine locale

- [x] Accès SSH au serveur Hostinger
- [x] Clé SSH configurée
- [x] Fichier `.env` configuré
- [x] Scripts de déploiement créés

### Sur le serveur Hostinger

- [x] Docker et Docker Compose installés
- [x] Ports 80, 443, 8000, 11434 disponibles
- [x] Au moins 2 Go de RAM libre
- [x] Au moins 20 Go d'espace disque

---

## 🚀 Options de Déploiement

### Option 1 : Déploiement Local (si Docker Desktop est installé)

Cette option est idéale si vous testez localement avant de déployer en production.

#### 1. Démarrer Docker Desktop

```bash
# Sur macOS
open -a Docker

# Attendre que Docker soit prêt (environ 30 secondes)
docker ps
```

#### 2. Vérifier l'état des services

```bash
./scripts/check_hostinger_services.sh
```

#### 3. Lancer le déploiement complet

```bash
./deploy_hostinger_production.sh
```

Ce script va :
- ✅ Vérifier les prérequis (.env, docker-compose.yml)
- ✅ Arrêter les services existants
- ✅ Rebuilder les images Docker
- ✅ Démarrer MongoDB et Redis
- ✅ Démarrer Ollama et télécharger les modèles
- ✅ Démarrer l'API MCP
- ✅ Démarrer Nginx
- ✅ Valider le déploiement

**Durée estimée** : 15-20 minutes

---

### Option 2 : Déploiement Distant (Production Hostinger)

Cette option déploie directement sur le serveur Hostinger.

#### 1. Préparer les credentials

Avant de commencer, ayez sous la main :
- Adresse du serveur : `user@server.hostinger.com`
- Chemin du projet sur le serveur : `/home/user/mcp` (par exemple)

#### 2. Lancer le déploiement distant

```bash
./deploy_remote_hostinger.sh
```

Le script vous demandera :
```
Entrez l'adresse du serveur Hostinger: root@vps.hostinger.com
Chemin distant du projet (défaut: ~/mcp): /root/mcp
```

Le script va :
- ✅ Tester la connexion SSH
- ✅ Vérifier Docker sur le serveur
- ✅ Synchroniser tous les fichiers nécessaires
- ✅ Exécuter le déploiement sur le serveur
- ✅ Vérifier l'état des services

**Durée estimée** : 10-15 minutes (selon la vitesse de connexion)

---

## 🔍 Vérification Post-Déploiement

### 1. Vérifier l'état des conteneurs

**Local** :
```bash
./scripts/check_hostinger_services.sh
```

**Distant** :
```bash
ssh user@server.hostinger.com 'cd /path/to/mcp && docker-compose -f docker-compose.hostinger.yml ps'
```

Vous devriez voir :
```
NAME          STATUS         PORTS
mcp-mongodb   Up (healthy)   27017/tcp
mcp-redis     Up (healthy)   6379/tcp
mcp-api       Up (healthy)   127.0.0.1:8000->8000/tcp
mcp-nginx     Up             80/tcp, 443/tcp
mcp-ollama    Up (healthy)   11434/tcp
```

### 2. Tester l'API

**Local** :
```bash
curl http://localhost:8000/health
# Attendu: {"status":"healthy","timestamp":"2025-01-07"}

curl http://localhost:8000/docs
# Attendu: Page Swagger UI
```

**Distant** :
```bash
curl https://votre-domaine.com/health
```

### 3. Vérifier les logs

**Local** :
```bash
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api
```

**Distant** :
```bash
ssh user@server.hostinger.com 'cd /path/to/mcp && docker-compose -f docker-compose.hostinger.yml logs -f mcp-api'
```

### 4. Vérifier les modèles Ollama

**Local** :
```bash
docker exec mcp-ollama ollama list
```

Vous devriez voir :
```
NAME              ID              SIZE      MODIFIED
gemma3:1b         abc123...       1.2 GB    2 minutes ago
tinyllama         def456...       637 MB    2 minutes ago
nomic-embed-text  ghi789...       274 MB    2 minutes ago
```

---

## 🛠️ Commandes de Gestion

### Redémarrer tous les services

**Local** :
```bash
./scripts/restart_hostinger_services.sh
```

**Distant** :
```bash
ssh user@server 'cd /path/to/mcp && docker-compose -f docker-compose.hostinger.yml restart'
```

### Redémarrer un service spécifique

**Local** :
```bash
./scripts/restart_hostinger_services.sh mcp-api
```

**Distant** :
```bash
ssh user@server 'cd /path/to/mcp && docker-compose -f docker-compose.hostinger.yml restart mcp-api'
```

### Voir les logs en temps réel

**Local** :
```bash
# Tous les services
docker-compose -f docker-compose.hostinger.yml logs -f

# API uniquement
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api

# Ollama uniquement
docker-compose -f docker-compose.hostinger.yml logs -f ollama
```

### Arrêter tous les services

**Local** :
```bash
docker-compose -f docker-compose.hostinger.yml down
```

**Distant** :
```bash
ssh user@server 'cd /path/to/mcp && docker-compose -f docker-compose.hostinger.yml down'
```

### Nettoyer et redémarrer

```bash
# Arrêter et supprimer les volumes
docker-compose -f docker-compose.hostinger.yml down -v

# Redémarrer proprement
./deploy_hostinger_production.sh
```

---

## 🚨 Dépannage

### Problème : Docker daemon non accessible

**Symptôme** :
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution** :
```bash
# Sur macOS
open -a Docker

# Sur Linux
sudo systemctl start docker
```

### Problème : Un conteneur ne démarre pas

**Diagnostic** :
```bash
docker-compose -f docker-compose.hostinger.yml ps
docker-compose -f docker-compose.hostinger.yml logs [nom-du-service]
```

**Solutions courantes** :

1. **MongoDB ne démarre pas** :
```bash
# Vérifier les permissions
docker volume inspect mcp_mongodb_data
sudo chown -R 999:999 /path/to/volume
```

2. **Redis ne démarre pas** :
```bash
# Nettoyer le volume
docker volume rm mcp_redis_data
docker-compose -f docker-compose.hostinger.yml up -d redis
```

3. **API ne démarre pas** :
```bash
# Vérifier les variables d'environnement
docker-compose -f docker-compose.hostinger.yml config

# Rebuilder l'image
docker-compose -f docker-compose.hostinger.yml build --no-cache mcp-api
```

4. **Ollama ne démarre pas** :
```bash
# Libérer de l'espace disque
docker system prune -af
docker volume prune -f
```

### Problème : Port déjà utilisé

**Symptôme** :
```
Error: port is already allocated
```

**Solution** :
```bash
# Trouver le processus utilisant le port
lsof -i :8000
# ou
netstat -tlnp | grep 8000

# Arrêter le processus
kill -9 [PID]
```

### Problème : Modèles Ollama non téléchargés

**Solution** :
```bash
# Exécuter le script de téléchargement
docker exec mcp-ollama ollama pull gemma3:1b
docker exec mcp-ollama ollama pull tinyllama
docker exec mcp-ollama ollama pull nomic-embed-text

# Vérifier
docker exec mcp-ollama ollama list
```

---

## 📊 Monitoring

### Dashboard temps réel

```bash
watch -n 5 'docker-compose -f docker-compose.hostinger.yml ps'
```

### Utilisation des ressources

```bash
docker stats
```

### Santé des conteneurs

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Logs agrégés

```bash
docker-compose -f docker-compose.hostinger.yml logs --tail=100 --follow
```

---

## ✅ Checklist de Production

Avant de considérer le déploiement comme réussi, vérifiez :

- [ ] Les 5 conteneurs sont actifs (`mcp-mongodb`, `mcp-redis`, `mcp-api`, `mcp-nginx`, `mcp-ollama`)
- [ ] L'API répond sur http://localhost:8000 (ou votre domaine)
- [ ] Nginx répond sur http://localhost:80
- [ ] Les healthchecks sont "healthy" pour MongoDB et Redis
- [ ] Ollama a au moins 1 modèle téléchargé (`gemma3:1b` minimum)
- [ ] Pas d'erreurs critiques dans les logs
- [ ] Le fichier `.env` est sécurisé (`chmod 600 .env`)
- [ ] Les volumes Docker persistent correctement
- [ ] Le mode Shadow est activé (`DRY_RUN=true` dans `.env`)
- [ ] Les certificats SSL sont configurés (si HTTPS)

---

## 📚 Références

- [docker-compose.hostinger.yml](docker-compose.hostinger.yml) - Configuration des services
- [Dockerfile.production](Dockerfile.production) - Build de l'image API
- [nginx-docker.conf](nginx-docker.conf) - Configuration Nginx
- [env.hostinger.example](env.hostinger.example) - Template de configuration

---

## 🆘 Support

En cas de problème :

1. **Vérifier les logs** : `docker-compose -f docker-compose.hostinger.yml logs -f`
2. **Vérifier l'état** : `./scripts/check_hostinger_services.sh`
3. **Redémarrer** : `./scripts/restart_hostinger_services.sh`
4. **Nettoyer et redéployer** : Voir section "Nettoyer et redémarrer"

---

**✨ Le système est maintenant prêt pour la production en mode Shadow !**

