# 🚀 Guide de Déploiement MCP v1.0 en Production sur Hostinger

> **Dernière mise à jour:** 16 octobre 2025  
> **Version:** 1.0.0  
> **Statut:** Production Ready

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Préparation des Credentials](#préparation-des-credentials)
4. [Déploiement Rapide](#déploiement-rapide)
5. [Configuration Détaillée](#configuration-détaillée)
6. [Validation](#validation)
7. [Mode Shadow](#mode-shadow)
8. [Monitoring et Maintenance](#monitoring-et-maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Vue d'ensemble

Ce guide vous permet de déployer MCP v1.0 en production sur Hostinger avec :

### Architecture Déployée

```
┌─────────────────┐
│   Internet      │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Nginx  │ :80/:443 (SSL)
    └────┬────┘
         │
    ┌────▼────────┐
    │  MCP API    │ :8000
    └────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    │          │          │          │
┌───▼───┐  ┌──▼────┐  ┌──▼─────┐  ┌▼────────┐
│MongoDB│  │ Redis │  │Qdrant  │  │ Ollama  │
│Atlas  │  │Upstash│  │:6333   │  │:11434   │
└───────┘  └───────┘  └────────┘  └─────────┘
 (Cloud)    (Cloud)    (Docker)    (Docker)
```

### Services

- **MCP API** : Application principale (FastAPI)
- **Nginx** : Reverse proxy avec SSL
- **MongoDB Atlas** : Base de données (cloud)
- **Redis Upstash** : Cache (cloud)
- **Qdrant** : Vector database pour RAG (Docker)
- **Ollama** : LLM local (Docker)

### Caractéristiques

✅ **Mode Shadow** activé par défaut (DRY_RUN=true)  
✅ **SSL/HTTPS** automatique avec Let's Encrypt  
✅ **Auto-restart** avec systemd  
✅ **Monitoring** intégré  
✅ **Backup** automatique

---

## Prérequis

### 1. Serveur Hostinger

- **OS**: Ubuntu 22.04 ou supérieur
- **RAM**: Minimum 8 GB (16 GB recommandé pour Ollama 70B)
- **Disk**: Minimum 100 GB
- **CPU**: 4 cores minimum (8+ recommandé)
- **Accès**: SSH avec privilèges sudo

### 2. Services Cloud Requis

#### MongoDB Atlas (Base de données)
- Compte sur https://cloud.mongodb.com
- Cluster gratuit ou payant
- Obtenir la connection string
- Format: `mongodb+srv://username:password@cluster.mongodb.net/database`

#### Redis Upstash (Cache)
- Compte sur https://upstash.com
- Database Redis gratuite ou payante
- Obtenir la connection string
- Format: `redis://default:password@host:port`

#### Anthropic (IA)
- Compte sur https://console.anthropic.com
- API key pour Claude
- Format: `sk-ant-api03-xxxxx`

### 3. Lightning Network (Optionnel mais recommandé)

- **LNBits** : Instance avec admin key
- **OU LND** : Nœud avec REST API et macaroons

### 4. Domaine DNS

- Domaine configuré pointant vers votre serveur
- Ex: `api.dazno.de` → IP du serveur
- Type A record configuré

---

## Préparation des Credentials

### Étape 1: Obtenir MongoDB Atlas

1. Aller sur https://cloud.mongodb.com
2. Créer un compte / Se connecter
3. Créer un nouveau cluster (gratuit M0 OK pour démarrer)
4. Aller dans **Database Access** → Créer un utilisateur
5. Aller dans **Network Access** → Ajouter votre IP ou `0.0.0.0/0`
6. Cliquer sur **Connect** → **Drivers** → Copier la connection string
7. Remplacer `<password>` par votre mot de passe

```
mongodb+srv://mcp_user:votre_password@cluster.abc123.mongodb.net/mcp_prod?retryWrites=true&w=majority
```

### Étape 2: Obtenir Redis Upstash

1. Aller sur https://upstash.com
2. Créer un compte / Se connecter
3. Créer une nouvelle database Redis
4. Copier la **Redis URL** dans la section **Details**

```
redis://default:AbCd1234EfGh5678@redis-12345.upstash.io:6379
```

### Étape 3: Obtenir Anthropic API Key

1. Aller sur https://console.anthropic.com
2. Créer un compte / Se connecter
3. Aller dans **API Keys**
4. Créer une nouvelle clé

```
sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Étape 4: Obtenir LNBits Credentials (optionnel)

1. Se connecter à votre instance LNBits
2. Aller dans le wallet
3. Copier **Admin Key** et **Invoice/Read Key**

```
LNBITS_URL=https://your-lnbits.com
LNBITS_ADMIN_KEY=xxxxx
```

### Étape 5: Telegram Bot (pour alertes)

1. Parler à @BotFather sur Telegram
2. Créer un nouveau bot: `/newbot`
3. Copier le token
4. Obtenir votre chat ID: parler à @userinfobot

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

---

## Déploiement Rapide

### Option A: Script Automatique (Recommandé)

```bash
# 1. Connexion au serveur
ssh user@votre-serveur-hostinger.com

# 2. Cloner le projet
cd /opt
sudo mkdir -p mcp && sudo chown $USER:$USER mcp
cd mcp
git clone https://github.com/votre-repo/MCP.git .

# 3. Copier le fichier de configuration
cp config_production_hostinger.env .env.production

# 4. Éditer et remplir les credentials
nano .env.production
# Remplir: MONGO_URL, REDIS_URL, ANTHROPIC_API_KEY, etc.

# 5. Lancer le déploiement
./deploy_to_hostinger.sh

# 6. Suivre les instructions à l'écran
```

### Option B: Déploiement Manuel

#### 1. Installation des prérequis

```bash
# Mise à jour système
sudo apt update && sudo apt upgrade -y

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Nginx et Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Se déconnecter et reconnecter pour activer le groupe docker
exit
```

#### 2. Configuration du projet

```bash
# Connexion
ssh user@votre-serveur-hostinger.com

# Créer répertoire
cd /opt
sudo mkdir -p mcp && sudo chown $USER:$USER mcp
cd mcp

# Cloner ou upload
git clone https://github.com/votre-repo/MCP.git .
# OU via SCP depuis votre machine locale:
# scp -r /chemin/local/MCP user@serveur:/opt/mcp/

# Créer les répertoires
mkdir -p mcp-data/{logs,data,rag,backups,reports}
mkdir -p logs/nginx
mkdir -p config/qdrant
mkdir -p ssl
```

#### 3. Configuration .env

```bash
# Copier le template
cp config_production_hostinger.env .env.production

# Éditer
nano .env.production

# Remplir au minimum:
# - MONGO_URL
# - REDIS_URL, REDIS_PASSWORD, REDIS_HOST, REDIS_PORT
# - LNBITS_URL, LNBITS_ADMIN_KEY (si applicable)
# - ANTHROPIC_API_KEY
# - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optionnel)
```

#### 4. Configuration Nginx + SSL

```bash
# Script automatique
sudo ./scripts/configure_nginx_production.sh

# Obtenir certificat SSL
sudo certbot --nginx -d api.dazno.de --agree-tos --email admin@dazno.de

# Vérifier
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. Démarrage des services

```bash
# Démarrer
docker-compose -f docker-compose.production.yml up -d

# Vérifier
docker-compose -f docker-compose.production.yml ps

# Logs
docker-compose -f docker-compose.production.yml logs -f mcp-api
```

#### 6. Initialiser Ollama

```bash
# Option 1: Modèle 70B (puissant mais lourd - 40 GB)
docker exec mcp-ollama ollama pull llama3:70b-instruct-2025-07-01

# Option 2: Modèle 8B (plus rapide - 5 GB)
docker exec mcp-ollama ollama pull llama3:8b-instruct

# Modèle d'embeddings (requis)
docker exec mcp-ollama ollama pull nomic-embed-text

# Vérifier
docker exec mcp-ollama ollama list
```

---

## Configuration Détaillée

### Variables d'Environnement Critiques

#### Obligatoires

| Variable | Description | Exemple |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB Atlas connection | `mongodb+srv://user:pass@cluster.mongodb.net/db` |
| `REDIS_URL` | Redis Upstash connection | `redis://default:pass@host:6379` |
| `JWT_SECRET` | JWT signing key | Auto-généré dans template |
| `SECRET_KEY` | Application secret | Auto-généré dans template |
| `MACAROON_ENCRYPTION_KEY` | Macaroon encryption | Auto-généré dans template |

#### Lightning (si utilisé)

| Variable | Description | Exemple |
|----------|-------------|---------|
| `LNBITS_URL` | LNBits instance URL | `https://legend.lnbits.com` |
| `LNBITS_ADMIN_KEY` | LNBits admin key | `abc123...` |
| `LNBITS_INKEY` | LNBits invoice key | `def456...` |

#### IA

| Variable | Description | Exemple |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | OpenAI key (optionnel) | `sk-...` |

#### Notifications

| Variable | Description | Exemple |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Chat ID | `123456789` |

### Configuration Docker Compose

Le fichier `docker-compose.production.yml` configure:

- **mcp-api**: Application principale
- **nginx**: Reverse proxy
- **qdrant**: Vector database
- **ollama**: LLM local

Pas besoin de modifier ce fichier, tout est configurable via `.env.production`.

---

## Validation

### Validation Automatique

```bash
# Lancer le script de validation
./scripts/validate_deployment.sh
```

Ce script vérifie:
- ✅ Conteneurs Docker
- ✅ API health
- ✅ Nginx et SSL
- ✅ Qdrant
- ✅ Ollama
- ✅ Configuration
- ✅ Logs
- ✅ Connectivité réseau
- ✅ Espace disque
- ✅ Sécurité

### Validation Manuelle

```bash
# 1. Status des conteneurs
docker-compose -f docker-compose.production.yml ps
# Tous doivent être "Up"

# 2. Test API
curl http://localhost:8000/api/v1/health
curl https://api.dazno.de/api/v1/health

# 3. Test Qdrant
docker exec mcp-qdrant-prod curl http://localhost:6333/health

# 4. Test Ollama
docker exec mcp-ollama ollama list

# 5. Logs API
docker-compose -f docker-compose.production.yml logs -f mcp-api
# Pas d'erreurs critiques

# 6. Test SSL
curl -I https://api.dazno.de
# HTTP/2 200

# 7. Documentation
# Ouvrir dans navigateur: https://api.dazno.de/docs
```

---

## Mode Shadow

### Qu'est-ce que le Mode Shadow ?

Le **Mode Shadow** (DRY_RUN=true) est un mode d'observation où MCP:

✅ **Analyse** les canaux Lightning  
✅ **Calcule** les optimisations recommandées  
✅ **Génère** des rapports détaillés  
❌ **N'APPLIQUE PAS** les changements réels

### Pourquoi utiliser le Mode Shadow ?

1. **Validation**: Vérifier que les recommandations sont pertinentes
2. **Apprentissage**: Comprendre la logique d'optimisation
3. **Confiance**: Observer avant d'activer les changements réels
4. **Sécurité**: Zéro risque pendant l'observation

### Durée Recommandée

- **Minimum**: 7 jours
- **Recommandé**: 14 jours
- **Idéal**: 21 jours

### Observation en Mode Shadow

```bash
# 1. Vérifier que le mode shadow est actif
grep "DRY_RUN" .env.production
# Doit afficher: DRY_RUN=true

# 2. Consulter les rapports quotidiens
ls -lh mcp-data/reports/
cat mcp-data/reports/shadow_report_$(date +%Y%m%d).json

# 3. Monitorer
python3 monitor_production.py --duration 300

# 4. Analyser les logs
docker-compose -f docker-compose.production.yml logs mcp-api | grep "SHADOW MODE"
```

### Désactiver le Mode Shadow

**⚠️ Seulement après 7-14 jours d'observation réussie !**

```bash
# 1. Éditer .env.production
nano .env.production

# 2. Changer DRY_RUN=false
# Avant: DRY_RUN=true
# Après: DRY_RUN=false

# 3. Redémarrer l'API
docker-compose -f docker-compose.production.yml restart mcp-api

# 4. Vérifier les logs
docker-compose -f docker-compose.production.yml logs -f mcp-api
# Doit afficher: "PRODUCTION MODE - Real changes enabled"

# 5. Surveiller de près pendant 48h
```

---

## Monitoring et Maintenance

### Monitoring Quotidien

```bash
# Script de monitoring automatique
python3 monitor_production.py --duration 300

# Génère:
# - mcp-data/reports/monitoring_YYYYMMDD.json
# - Alerte Telegram si problème
```

### Commandes Quotidiennes

```bash
# Status rapide
docker-compose -f docker-compose.production.yml ps

# Logs récents
docker-compose -f docker-compose.production.yml logs --tail=100 mcp-api

# Utilisation ressources
docker stats

# Espace disque
df -h
```

### Cron Jobs Recommandés

```bash
# Éditer crontab
crontab -e

# Ajouter:

# Monitoring toutes les 6 heures
0 */6 * * * cd /opt/mcp && python3 monitor_production.py >> logs/monitoring.log 2>&1

# Backup quotidien à 3h du matin
0 3 * * * cd /opt/mcp && ./scripts/backup_daily.sh

# Redémarrage hebdomadaire (dimanche 4h)
0 4 * * 0 cd /opt/mcp && docker-compose -f docker-compose.production.yml restart

# Nettoyage logs anciens (> 30 jours)
0 5 * * * find /opt/mcp/logs -name "*.log" -mtime +30 -delete
```

### Backup Automatique

```bash
# Créer script de backup
cat > scripts/backup_daily.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/mcp/backups

# Backup Qdrant
docker run --rm -v mcp_qdrant_data:/data -v $BACKUP_DIR:/backup alpine \
  tar czf /backup/qdrant_$DATE.tar.gz -C /data .

# Backup config et données
tar czf $BACKUP_DIR/mcp_data_$DATE.tar.gz /opt/mcp/mcp-data /opt/mcp/.env.production

# Cleanup > 30 jours
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x scripts/backup_daily.sh

# Tester
./scripts/backup_daily.sh
```

### Mise à Jour

```bash
# 1. Backup avant mise à jour
./scripts/backup_daily.sh

# 2. Pull nouvelle version
git pull origin main

# 3. Pull nouvelles images
docker-compose -f docker-compose.production.yml pull

# 4. Redémarrer
docker-compose -f docker-compose.production.yml up -d

# 5. Vérifier
./scripts/validate_deployment.sh
```

---

## Troubleshooting

### API ne démarre pas

```bash
# Vérifier les logs
docker-compose -f docker-compose.production.yml logs mcp-api

# Erreurs communes:
# - MongoDB connection failed → Vérifier MONGO_URL
# - Redis connection failed → Vérifier REDIS_URL
# - Module not found → Rebuild l'image

# Solution: Vérifier .env.production
cat .env.production | grep -E "MONGO_URL|REDIS_URL"
```

### Nginx 502 Bad Gateway

```bash
# Vérifier que l'API tourne
curl http://localhost:8000/

# Si ça marche, problème nginx
sudo nginx -t
sudo tail -f /var/log/nginx/mcp_error.log

# Redémarrer nginx
sudo systemctl restart nginx
```

### Certificat SSL expiré

```bash
# Renouveler
sudo certbot renew

# Vérifier expiration
sudo certbot certificates

# Auto-renewal
sudo systemctl status certbot.timer
```

### Ollama out of memory

```bash
# Utiliser modèle plus petit
docker exec mcp-ollama ollama pull llama3:8b-instruct

# Modifier .env.production
nano .env.production
# Changer: GEN_MODEL=llama3:8b-instruct

# Redémarrer
docker-compose -f docker-compose.production.yml restart mcp-api
```

### Qdrant erreurs

```bash
# Vérifier espace disque
df -h

# Recréer le volume
docker-compose -f docker-compose.production.yml down
docker volume rm mcp_qdrant_data
docker-compose -f docker-compose.production.yml up -d
```

### Redis timeout

```bash
# Tester connexion
docker exec mcp-api-prod python3 -c "import redis; import os; r = redis.from_url(os.getenv('REDIS_URL')); print(r.ping())"

# Si échec, vérifier credentials Upstash
# Régénérer la database si nécessaire
```

---

## Support et Ressources

### Documentation

- [PHASE5-STATUS.md](PHASE5-STATUS.md) - Status actuel du projet
- [_SPECS/Roadmap-Production-v1.0.md](_SPECS/Roadmap-Production-v1.0.md) - Roadmap complète
- [docs/backbone-technique-MVP.md](docs/backbone-technique-MVP.md) - Architecture

### Scripts Utiles

| Script | Description |
|--------|-------------|
| `deploy_to_hostinger.sh` | Déploiement automatique |
| `scripts/validate_deployment.sh` | Validation post-déploiement |
| `scripts/configure_nginx_production.sh` | Configuration Nginx |
| `monitor_production.py` | Monitoring |

### Commandes Rapides

```bash
# Status
docker-compose -f docker-compose.production.yml ps

# Logs
docker-compose -f docker-compose.production.yml logs -f

# Restart
docker-compose -f docker-compose.production.yml restart

# Stop
docker-compose -f docker-compose.production.yml down

# Start
docker-compose -f docker-compose.production.yml up -d

# Validation
./scripts/validate_deployment.sh

# Monitoring
python3 monitor_production.py
```

---

## Checklist de Déploiement

### Avant le déploiement

- [ ] Serveur Hostinger provisionné
- [ ] MongoDB Atlas configuré
- [ ] Redis Upstash configuré
- [ ] Anthropic API key obtenue
- [ ] LNBits configuré (si applicable)
- [ ] Domaine DNS pointé vers serveur
- [ ] Telegram bot créé (optionnel)

### Déploiement

- [ ] Docker et Docker Compose installés
- [ ] Projet cloné dans `/opt/mcp`
- [ ] `.env.production` créé et rempli
- [ ] Nginx configuré
- [ ] SSL Let's Encrypt obtenu
- [ ] Services Docker démarrés
- [ ] Ollama modèles téléchargés

### Validation

- [ ] Script `validate_deployment.sh` exécuté
- [ ] API accessible via HTTPS
- [ ] Mode Shadow activé (DRY_RUN=true)
- [ ] Aucune erreur critique dans logs
- [ ] Monitoring configuré
- [ ] Backup automatique configuré

### Post-déploiement

- [ ] Observer 7-14 jours en mode shadow
- [ ] Analyser rapports quotidiens
- [ ] Vérifier alertes Telegram
- [ ] Désactiver mode shadow si validation OK
- [ ] Surveiller 48h après activation

---

## Conclusion

Vous avez maintenant un système MCP v1.0 déployé en production sur Hostinger avec:

✅ **Infrastructure stable** avec Docker  
✅ **Services cloud** (MongoDB, Redis)  
✅ **SSL/HTTPS** automatique  
✅ **Mode Shadow** pour observation sécurisée  
✅ **Monitoring** et alertes  
✅ **Backup** automatique  

**Prochaines étapes:**
1. Observer pendant 7-14 jours en mode shadow
2. Analyser les recommandations
3. Valider la pertinence des optimisations
4. Désactiver le mode shadow
5. Surveiller les performances réelles

**Bon déploiement ! 🚀**

---

**Dernière mise à jour:** 16 octobre 2025  
**Contributeurs:** MCP Team  
**Support:** support@dazno.de

