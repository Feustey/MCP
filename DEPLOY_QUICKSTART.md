# 🚀 Guide de Déploiement Rapide - MCP v1.0

> **Phase 1 - Infrastructure Stable**  
> Temps estimé: 2-3 heures  
> Dernière mise à jour: 12 octobre 2025

---

## ✅ PRÉREQUIS

Avant de commencer, assurez-vous d'avoir :

- [ ] Accès SSH au serveur production
- [ ] Accès sudo sur le serveur
- [ ] Domaine configuré (api.dazno.de → IP serveur)
- [ ] Compte MongoDB Atlas (ou prêt à créer)
- [ ] Compte Redis Cloud/Upstash (ou prêt à créer)
- [ ] Telegram Bot Token (pour alertes)

---

## 📦 ÉTAPE 1 : DÉPLOIEMENT SERVEUR (30 min)

### 1.1 Configuration Nginx + HTTPS

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32

# Aller dans le répertoire du projet
cd /home/feustey/mcp-production

# Exécuter le script de configuration Nginx
sudo ./scripts/configure_nginx_production.sh
```

**Attendu** : ✅ Nginx configuré, port 80/443 prêt

### 1.2 Installer Let's Encrypt

```bash
# Installer certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Obtenir le certificat SSL
sudo certbot --nginx -d api.dazno.de

# Vérifier le renouvellement automatique
sudo systemctl status certbot.timer
```

**Attendu** : ✅ SSL A+ sur https://www.ssllabs.com/ssltest/

### 1.3 Configuration Systemd

```bash
# Exécuter le script de configuration
sudo ./scripts/configure_systemd_autostart.sh

# Vérifier que le service fonctionne
sudo systemctl status mcp-api

# Voir les logs en temps réel
sudo journalctl -u mcp-api -f
```

**Attendu** : ✅ Service actif et auto-restart configuré

### 1.4 Configuration Logrotate

```bash
# Installer la configuration
sudo ./scripts/setup_logrotate.sh

# Tester la rotation
sudo logrotate -d /etc/logrotate.d/mcp-api
```

**Attendu** : ✅ Logs rotationnés quotidiennement

---

## ☁️ ÉTAPE 2 : SERVICES CLOUD (45 min)

### 2.1 MongoDB Atlas

1. **Créer un compte** : https://www.mongodb.com/cloud/atlas/register
2. **Créer un cluster** :
   - Tier: M10 (Production, 2GB RAM) - ~$60/mois
   - Region: AWS eu-west-1 (Frankfurt)
   - Cluster Name: `mcp-prod`

3. **Configurer l'accès** :
   - Database Access : Créer user `mcp_user` avec mot de passe
   - Network Access : Ajouter IP serveur (147.79.101.32)

4. **Récupérer la connection string** :
   ```
   mongodb+srv://mcp_user:PASSWORD@cluster.mongodb.net/mcp_prod
   ```

5. **Créer la base et collections** :
   ```javascript
   // Via MongoDB Compass ou shell
   use mcp_prod;
   db.createCollection("nodes");
   db.createCollection("channels");
   db.createCollection("policies");
   db.createCollection("metrics");
   db.createCollection("decisions");
   
   // Créer les indexes
   db.nodes.createIndex({ "node_id": 1, "created_at": -1 });
   db.channels.createIndex({ "channel_id": 1, "node_id": 1 });
   db.policies.createIndex({ "channel_id": 1, "applied_at": -1 });
   db.metrics.createIndex({ "node_id": 1, "timestamp": -1 });
   db.decisions.createIndex({ "node_id": 1, "decision_type": 1 });
   ```

**Attendu** : ✅ Cluster actif, connection string récupérée

### 2.2 Redis Cloud

1. **Créer un compte** : https://redis.com/try-free/
   - Ou Upstash : https://upstash.com/

2. **Créer une instance** :
   - Tier: 250MB RAM (~$10/mois)
   - Region: AWS eu-west-1
   - TLS: Enabled

3. **Récupérer la connection string** :
   ```
   rediss://default:PASSWORD@redis-cluster.cloud.redislabs.com:6379
   ```

**Attendu** : ✅ Instance active, connection string récupérée

### 2.3 Configuration .env

```bash
# Sur le serveur
cd /home/feustey/mcp-production

# Copier le template
cp env.production.example .env

# Éditer avec vos credentials
nano .env
```

**Variables à configurer** :
```bash
# MongoDB Atlas
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/mcp_prod

# Redis Cloud
REDIS_URL=rediss://default:pass@redis-cluster.cloud.redislabs.com:6379

# Secrets (générer avec: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=votre-secret-genere
JWT_SECRET_KEY=votre-jwt-secret-genere
MACAROON_ENCRYPTION_KEY=votre-macaroon-key-genere

# Telegram (optionnel mais recommandé)
TELEGRAM_BOT_TOKEN=votre-bot-token
TELEGRAM_CHAT_ID=votre-chat-id

# Mode production
ENVIRONMENT=production
DRY_RUN=true  # true = shadow mode
SHADOW_MODE_ENABLED=true
```

**Sauvegarder et quitter** : `Ctrl+X`, `Y`, `Enter`

---

## 🐳 ÉTAPE 3 : DOCKER (Optionnel, 30 min)

Si vous préférez Docker au lieu de Python direct :

```bash
# Builder l'image
./scripts/deploy_docker_production.sh

# L'image sera déployée en blue/green automatiquement
```

**OU** utiliser Docker Compose :

```bash
# Éditer docker-compose.production.yml si nécessaire
nano docker-compose.production.yml

# Démarrer
docker-compose -f docker-compose.production.yml up -d

# Voir les logs
docker-compose -f docker-compose.production.yml logs -f
```

---

## ✅ ÉTAPE 4 : VALIDATION (15 min)

### 4.1 Tests de Base

```bash
# Test 1: API accessible localement
curl http://localhost:8000/

# Test 2: API via nginx
curl http://localhost/

# Test 3: API via HTTPS (domaine)
curl https://api.dazno.de/

# Test 4: Health check détaillé
curl https://api.dazno.de/api/v1/health/detailed

# Test 5: Documentation Swagger
curl https://api.dazno.de/docs
# Ouvrir dans navigateur: https://api.dazno.de/docs
```

**Attendu** : 
- ✅ Tous les tests retournent 200 OK
- ✅ Format JSON valide
- ✅ Status "healthy" ou "degraded" (acceptable si Redis/MongoDB pas encore connectés)

### 4.2 Tests Services Cloud

```bash
# Test MongoDB
curl -X POST https://api.dazno.de/api/v1/nodes/ \
  -H "Content-Type: application/json" \
  -d '{"node_id": "test", "pubkey": "03abc..."}'

# Test Redis (cache)
curl https://api.dazno.de/api/v1/lightning/scores/node/test

# Vérifier les logs
sudo journalctl -u mcp-api -n 50
```

### 4.3 Tests Systemd

```bash
# Test 1: Auto-restart
sudo systemctl restart mcp-api
sleep 10
sudo systemctl status mcp-api  # Devrait être "active (running)"

# Test 2: Crash simulation
sudo kill -9 $(pgrep -f "uvicorn.*app.main")
sleep 15
sudo systemctl status mcp-api  # Devrait être redémarré automatiquement

# Test 3: Auto-start au boot (ne pas exécuter maintenant)
# sudo reboot
# Après reboot:
# sudo systemctl status mcp-api
```

### 4.4 Monitoring

```bash
# Lancer le monitoring
cd /home/feustey/mcp-production
python monitor_production.py --duration 60 --api-url https://api.dazno.de

# Devrait montrer:
# - Uptime: 100%
# - Failures: 0
# - Response time: < 500ms
```

---

## 📊 ÉTAPE 5 : MONITORING CONTINU (5 min)

### 5.1 Configurer le Monitoring Automatique

```bash
# Créer un cron pour monitoring quotidien
crontab -e

# Ajouter cette ligne:
0 */6 * * * cd /home/feustey/mcp-production && /home/feustey/mcp-production/venv/bin/python monitor_production.py --duration 300 >> logs/monitoring_cron.log 2>&1
```

**Explication** : Exécute le monitoring toutes les 6 heures pendant 5 minutes

### 5.2 Alertes Telegram

Si configuré, vous recevrez des alertes pour :
- ✅ Service down
- ✅ Erreurs critiques
- ✅ Performance dégradée
- ✅ Failures multiples

---

## 🎯 CHECKLIST FINALE

### Infrastructure ✅

- [ ] ✅ Nginx configuré et fonctionnel
- [ ] ✅ SSL Let's Encrypt actif (A+ rating)
- [ ] ✅ Service systemd avec auto-restart
- [ ] ✅ Logrotate configuré (rotation quotidienne)

### Services Cloud ✅

- [ ] ✅ MongoDB Atlas cluster actif
- [ ] ✅ Redis Cloud instance active
- [ ] ✅ Connection strings dans .env
- [ ] ✅ Collections et indexes créés

### API ✅

- [ ] ✅ API accessible via HTTPS
- [ ] ✅ Health check retourne "healthy"
- [ ] ✅ Documentation Swagger accessible
- [ ] ✅ Logs propres sans erreurs critiques

### Monitoring ✅

- [ ] ✅ Monitoring script fonctionnel
- [ ] ✅ Cron configuré pour checks réguliers
- [ ] ✅ Alertes Telegram actives (optionnel)
- [ ] ✅ Logs rotationnés automatiquement

---

## 🐛 TROUBLESHOOTING

### Problème : API ne répond pas

```bash
# Vérifier le service
sudo systemctl status mcp-api

# Voir les logs récents
sudo journalctl -u mcp-api -n 100

# Vérifier le port
sudo netstat -tuln | grep 8000

# Redémarrer si nécessaire
sudo systemctl restart mcp-api
```

### Problème : SSL ne fonctionne pas

```bash
# Vérifier nginx
sudo nginx -t

# Recharger nginx
sudo systemctl reload nginx

# Logs nginx
sudo tail -f /var/log/nginx/mcp_error.log
```

### Problème : MongoDB connection failed

```bash
# Vérifier la connection string dans .env
grep MONGODB_URL .env

# Tester la connexion
python -c "from pymongo import MongoClient; client = MongoClient('YOUR_MONGODB_URL'); print(client.server_info())"

# Vérifier l'IP whitelistée sur MongoDB Atlas
```

### Problème : Redis connection failed

```bash
# Vérifier la connection string
grep REDIS_URL .env

# Tester la connexion
python -c "import redis; r = redis.from_url('YOUR_REDIS_URL'); r.ping(); print('OK')"
```

---

## 📞 COMMANDES UTILES

### Logs

```bash
# Logs API (systemd)
sudo journalctl -u mcp-api -f

# Logs API (fichiers)
tail -f logs/api_direct.log

# Logs Nginx
sudo tail -f /var/log/nginx/mcp_access.log
sudo tail -f /var/log/nginx/mcp_error.log
```

### Service Management

```bash
# Status
sudo systemctl status mcp-api

# Start/Stop/Restart
sudo systemctl start mcp-api
sudo systemctl stop mcp-api
sudo systemctl restart mcp-api

# Reload (sans downtime)
sudo systemctl reload mcp-api

# Logs
sudo journalctl -u mcp-api --since "1 hour ago"
```

### Tests Rapides

```bash
# Healthcheck
curl https://api.dazno.de/

# Metrics
curl https://api.dazno.de/metrics

# Swagger
xdg-open https://api.dazno.de/docs  # Linux
open https://api.dazno.de/docs      # macOS
```

---

## 🎉 SUCCÈS !

Si toutes les étapes sont complétées :

✅ **Phase 1 - Infrastructure Stable : COMPLÈTE**

Vous êtes maintenant prêt pour :
- 🔥 **Phase 2 : Core Engine** (LNBits, Optimiseur, Decision)
- 📊 **Shadow Mode** pendant 21 jours
- 🚀 **Production Contrôlée** avec vrais nœuds

---

## 📚 DOCUMENTATION COMPLÈTE

- **Roadmap complète** : `_SPECS/Roadmap-Production-v1.0.md`
- **Status détaillé** : `IMPLEMENTATION_PHASE1_STATUS.md`
- **Phase 5 status** : `PHASE5-STATUS.md`

---

## 🆘 SUPPORT

En cas de problème :
1. Consulter `IMPLEMENTATION_PHASE1_STATUS.md`
2. Vérifier les logs (`sudo journalctl -u mcp-api -n 100`)
3. Consulter la documentation complète
4. Créer une issue GitHub avec les logs

---

**Déploiement créé le** : 12 octobre 2025  
**Version** : 1.0.0  
**Status** : ✅ PRÊT POUR PRODUCTION

