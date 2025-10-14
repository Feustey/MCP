# 🚀 Guide de Déploiement Immédiat - MCP v1.0

> **Guide ultra-rapide** : Déployer MCP v1.0 en production en moins de 30 minutes
> 
> Date: 13 octobre 2025  
> Version: 1.0.0

---

## ⚡ Déploiement en 3 Commandes

```bash
# 1. Se connecter au serveur
ssh feustey@147.79.101.32

# 2. Aller dans le projet
cd /home/feustey/mcp-production

# 3. Lancer le déploiement automatique
sudo ./scripts/deploy_all.sh
```

**C'est tout !** Le script va :
- ✅ Configurer Nginx + SSL
- ✅ Installer le service systemd
- ✅ Configurer logrotate
- ✅ Builder et déployer Docker
- ✅ Valider l'installation
- ✅ Générer un rapport

**Temps estimé : 15-20 minutes**

---

## 📋 Prérequis

### Sur le Serveur

✅ Accès SSH avec sudo  
✅ Domaine pointant vers le serveur (api.dazno.de → 147.79.101.32)  
✅ Ports 80 et 443 ouverts  
✅ Au moins 2GB RAM disponible  
✅ 10GB espace disque  

### Credentials à Préparer

Vous aurez besoin de :
- [ ] MongoDB Atlas connection string
- [ ] Redis Cloud connection string
- [ ] LNBits API URL + Admin Key
- [ ] Telegram Bot Token (optionnel)
- [ ] Anthropic API Key (pour RAG, optionnel)

---

## 🎯 Déploiement Étape par Étape

### Étape 1 : Connexion au Serveur (1 min)

```bash
ssh feustey@147.79.101.32
cd /home/feustey/mcp-production
```

### Étape 2 : Vérifier les Fichiers (1 min)

```bash
# Vérifier que tous les scripts sont présents
ls -la scripts/

# Devrait afficher :
# - configure_nginx_production.sh
# - configure_systemd_autostart.sh
# - setup_logrotate.sh
# - deploy_docker_production.sh
# - deploy_all.sh
```

### Étape 3 : Configurer .env (5 min)

```bash
# Copier le template
cp env.production.example .env

# Éditer avec vos credentials
nano .env
```

**Variables critiques à configurer :**

```bash
# Application
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true  # Shadow mode par défaut

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=2

# MongoDB Atlas (à obtenir après création cluster)
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/mcp_prod
MONGODB_DATABASE=mcp_prod

# Redis Cloud (à obtenir après création instance)
REDIS_URL=rediss://default:password@redis.cloud.redislabs.com:6379

# LNBits
LNBITS_URL=https://your-lnbits.com
LNBITS_ADMIN_KEY=your_admin_key_here

# Sécurité
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")

# Monitoring (optionnel)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Étape 4 : Déploiement Automatique (15 min)

```bash
# Lancer le script de déploiement complet
sudo ./scripts/deploy_all.sh

# Ou avec options :
sudo ./scripts/deploy_all.sh --skip-ssl      # Skip configuration SSL
sudo ./scripts/deploy_all.sh --skip-docker   # Skip déploiement Docker
```

**Le script va :**
1. Vérifier les dépendances
2. Backup des configs existantes
3. Configurer Nginx
4. Installer certificat SSL (Let's Encrypt)
5. Configurer service systemd
6. Configurer logrotate
7. Builder image Docker
8. Déployer containers
9. Valider l'installation
10. Générer un rapport

### Étape 5 : Vérification (2 min)

```bash
# Test API via HTTP
curl http://localhost:8000/

# Test API via HTTPS
curl https://api.dazno.de/

# Check services
sudo systemctl status nginx
sudo systemctl status mcp-api

# Check Docker
docker-compose -f docker-compose.production.yml ps

# Logs temps réel
journalctl -u mcp-api -f
```

### Étape 6 : Provisionner Services Cloud (30 min)

#### MongoDB Atlas

1. Se connecter à https://cloud.mongodb.com
2. Créer nouveau cluster :
   - **Tier** : M10 (Production, 2GB RAM)
   - **Region** : eu-west-1 (Frankfurt)
   - **Backup** : Daily snapshots, 7 jours rétention
3. Network Access : Whitelist IP serveur (147.79.101.32)
4. Database Access : Créer user avec droits readWrite
5. Récupérer connection string
6. Mettre à jour `.env` :
   ```bash
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/mcp_prod
   ```

#### Redis Cloud

1. Se connecter à https://redis.com/try-free/ (ou Upstash)
2. Créer nouvelle database :
   - **Tier** : 250MB RAM
   - **Region** : eu-west-1
   - **TLS** : Enabled
3. Récupérer connection string
4. Mettre à jour `.env` :
   ```bash
   REDIS_URL=rediss://default:password@redis.cloud.redislabs.com:6379
   ```

#### Restart après Config

```bash
# Restart service pour prendre en compte le nouveau .env
sudo systemctl restart mcp-api

# Ou restart Docker
docker-compose -f docker-compose.production.yml restart
```

### Étape 7 : Tests de Validation (5 min)

```bash
# Lancer les tests end-to-end
python test_production_pipeline.py

# Devrait afficher :
# ✅ Environment Configuration: PASSED
# ✅ Rollback System: PASSED
# ✅ Node Simulator: PASSED
# ✅ Core Fee Optimizer: PASSED
# ⚠ Health Endpoint: PARTIAL (à vérifier)

# Tests de monitoring
python monitor_production.py --api-url https://api.dazno.de --duration 60

# Devrait montrer :
# API Status: healthy
# Response Time: < 500ms
# Uptime: 100%
```

---

## 🔥 Déploiement Ultra-Rapide (Sans Questions)

Si vous avez déjà tout préparé :

```bash
# One-liner complet
ssh feustey@147.79.101.32 "cd /home/feustey/mcp-production && sudo ./scripts/deploy_all.sh" && echo "✅ Déployé !"
```

---

## ⚙️ Options de Déploiement

### Déploiement Partiel

```bash
# Nginx uniquement
sudo ./scripts/configure_nginx_production.sh

# Systemd uniquement
sudo ./scripts/configure_systemd_autostart.sh

# Docker uniquement
./scripts/deploy_docker_production.sh

# Logrotate uniquement
sudo ./scripts/setup_logrotate.sh
```

### Déploiement avec Docker Uniquement

```bash
cd /home/feustey/mcp-production

# Build
docker-compose -f docker-compose.production.yml build

# Deploy
docker-compose -f docker-compose.production.yml up -d

# Logs
docker-compose -f docker-compose.production.yml logs -f
```

### Déploiement avec Systemd Uniquement

```bash
# Activer et démarrer
sudo systemctl enable mcp-api
sudo systemctl start mcp-api

# Status
sudo systemctl status mcp-api

# Logs
journalctl -u mcp-api -f
```

---

## 🚨 Troubleshooting

### Problème : Nginx ne démarre pas

```bash
# Vérifier la configuration
sudo nginx -t

# Voir les erreurs
sudo journalctl -u nginx -n 50

# Restart
sudo systemctl restart nginx
```

### Problème : SSL ne fonctionne pas

```bash
# Vérifier certbot
sudo certbot certificates

# Renouveler manuellement
sudo certbot renew --dry-run
sudo certbot renew

# Re-configurer
sudo certbot --nginx -d api.dazno.de
```

### Problème : API ne répond pas

```bash
# Check si le service tourne
sudo systemctl status mcp-api
docker-compose ps

# Check les logs
journalctl -u mcp-api -n 100
docker-compose logs mcp-api

# Check le port
sudo netstat -tulpn | grep 8000

# Restart
sudo systemctl restart mcp-api
# ou
docker-compose restart
```

### Problème : MongoDB connection failed

```bash
# Vérifier le .env
cat .env | grep MONGODB

# Test de connexion
python3 -c "from pymongo import MongoClient; client = MongoClient('YOUR_MONGODB_URL'); print(client.server_info())"

# Vérifier le firewall MongoDB Atlas
# Network Access → Add IP Address → 147.79.101.32
```

### Problème : Redis connection failed

```bash
# Vérifier le .env
cat .env | grep REDIS

# Test de connexion
redis-cli -u "YOUR_REDIS_URL" ping

# Devrait retourner PONG
```

---

## 📊 Post-Déploiement

### Monitoring 24/7

```bash
# Lancer monitoring en background
nohup python monitor_production.py --duration 86400 > monitoring.log 2>&1 &

# Voir le monitoring
tail -f monitoring.log

# Voir les rapports
ls -la monitoring_data/
cat monitoring_data/monitoring_$(date +%Y%m%d).json
```

### Logs Quotidiens

```bash
# Logs Nginx
tail -f /var/log/nginx/mcp_api_access.log
tail -f /var/log/nginx/mcp_api_error.log

# Logs API
journalctl -u mcp-api -f
tail -f logs/api.log

# Logs Docker
docker-compose logs -f mcp-api
```

### Alertes Telegram

Si configuré, vous recevrez automatiquement :
- 🟢 Service démarré
- 🟡 Performance dégradée
- 🔴 Service down
- ✅ Optimisation appliquée
- ❌ Erreur critique

---

## 🎯 Checklist Complète

### Avant Déploiement

- [ ] Accès SSH fonctionnel
- [ ] Domaine configuré (DNS)
- [ ] Ports 80/443 ouverts
- [ ] .env configuré
- [ ] Credentials MongoDB/Redis prêts
- [ ] Backup effectué

### Pendant Déploiement

- [ ] Script `deploy_all.sh` lancé
- [ ] Nginx configuré
- [ ] SSL installé
- [ ] Systemd configuré
- [ ] Docker déployé
- [ ] Tests passés

### Après Déploiement

- [ ] API répond (HTTP + HTTPS)
- [ ] Services actifs (nginx, mcp-api)
- [ ] MongoDB connecté
- [ ] Redis connecté
- [ ] Logs propres (no errors)
- [ ] Monitoring actif
- [ ] Alertes configurées
- [ ] Documentation lue

---

## 🏆 Validation Finale

```bash
# Test complet
curl -s https://api.dazno.de/ | jq .

# Devrait retourner :
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2025-10-13T..."
}

# Test endpoints
curl https://api.dazno.de/docs          # Swagger UI
curl https://api.dazno.de/health        # Health check
curl https://api.dazno.de/api/v1/       # API routes

# Tests end-to-end
python test_production_pipeline.py      # 80%+ pass rate

# Monitoring
python monitor_production.py            # Status healthy
```

---

## 📚 Ressources

### Documentation

- [Roadmap Production v1.0](_SPECS/Roadmap-Production-v1.0.md)
- [Phase 1 Status](IMPLEMENTATION_PHASE1_STATUS.md)
- [Quick Start](PHASE5-QUICKSTART.md)
- [Backbone Technique](docs/backbone-technique-MVP.md)

### Scripts

- `scripts/deploy_all.sh` - Déploiement complet
- `scripts/configure_nginx_production.sh` - Nginx + SSL
- `scripts/configure_systemd_autostart.sh` - Systemd
- `scripts/deploy_docker_production.sh` - Docker
- `monitor_production.py` - Monitoring
- `test_production_pipeline.py` - Tests

### Support

- 📧 Email: support@dazno.de
- 💬 Telegram: @mcp_support
- 📖 Docs: https://github.com/yourusername/MCP

---

## 🎉 Succès !

Si tout est ✅, félicitations ! Vous avez déployé MCP v1.0 en production.

**Prochaines étapes :**
1. Activer Shadow Mode (21 jours minimum)
2. Observer les recommandations
3. Valider avec experts (> 80% agreement)
4. Tester sur 1 canal pilote
5. Expansion progressive

---

**Version** : 1.0.0  
**Date** : 13 octobre 2025  
**Auteur** : MCP Team  
**Status** : Production Ready ✅
