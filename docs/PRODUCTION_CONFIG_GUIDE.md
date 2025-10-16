# Guide de Configuration Production MCP

> Dernière mise à jour: 15 octobre 2025

## 📋 Checklist Avant Déploiement

### 1. Créer le fichier de configuration

```bash
cp env.production.template .env.production
chmod 600 .env.production  # Permissions restrictives
```

### 2. Configuration Minimale Requise

Ces variables **DOIVENT** être configurées avant le démarrage :

#### A. LNBits / LND Connection
```bash
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_API_KEY=<votre_clé_api>
```

#### B. Sécurité - Générer les clés de chiffrement
```bash
# Générer MACAROON_ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copier le résultat dans .env.production
MACAROON_ENCRYPTION_KEY=<résultat_de_la_commande>
```

#### C. Base de données
```bash
# MongoDB Atlas (recommandé pour production)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/mcp_prod

# Ou MongoDB local
MONGODB_URI=mongodb://localhost:27017/mcp_prod
```

### 3. Configuration des Limites de Sécurité

Dans `config/decision_thresholds.yaml`, vérifier :

```yaml
safety_limits:
  base_fee_msat_min: 0
  base_fee_msat_max: 10000  # 10 sats max
  fee_rate_ppm_min: 1
  fee_rate_ppm_max: 5000  # 0.5% max
  
  max_fee_change_percent: 50  # ±50% max par changement
  cooldown_minutes: 60  # 1h minimum entre changements
```

### 4. Mode Shadow (OBLIGATOIRE au démarrage)

```bash
DRY_RUN=true  # ⚠️ NE PAS modifier avant validation
```

**Ne passer à `DRY_RUN=false` qu'après** :
- ✅ 14 jours minimum de shadow mode
- ✅ 0 erreurs critiques dans les logs
- ✅ Validation des recommandations par un expert
- ✅ Tests sur 1 canal non-critique

---

## 🔐 Sécurité

### Génération de Clés

```bash
# MACAROON_ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# API_SECRET_KEY (64 caractères aléatoires)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Permissions Fichiers

```bash
# Production
chmod 600 .env.production
chmod 600 config/decision_thresholds.yaml
chmod 700 data/macaroons/

# Logs
mkdir -p /var/log/mcp
chmod 755 /var/log/mcp
```

### Secrets Management

**Options recommandées** :
1. **HashiCorp Vault** (entreprise)
2. **AWS Secrets Manager** (cloud)
3. **Docker Secrets** (si Docker Swarm)

```bash
# Exemple Docker Secrets
echo "your_api_key" | docker secret create lnbits_api_key -
```

---

## 📊 MongoDB Atlas Configuration

### 1. Créer un Cluster

1. Aller sur [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Créer un compte gratuit ou payant
3. Créer un cluster M10 minimum (production)

### 2. Configuration Réseau

```bash
# Whitelist IP du serveur MCP
Network Access → Add IP Address → <IP_de_votre_serveur>

# Ou pour dev (non recommandé en prod)
0.0.0.0/0  # Toutes IPs
```

### 3. Créer un Utilisateur

```bash
Database Access → Add New Database User
Username: mcp_prod_user
Password: <générer_mot_de_passe_fort>
Privileges: Read and write to any database
```

### 4. Obtenir la Connection String

```bash
Connect → Connect your application → Driver: Python, Version: 3.12+
Copier: mongodb+srv://mcp_prod_user:<password>@cluster.mongodb.net/mcp_prod
```

### 5. Créer les Index (après premier démarrage)

```javascript
// Se connecter au cluster
use mcp_prod

// Index pour performance
db.channels.createIndex({ "node_id": 1, "channel_id": 1 })
db.channels.createIndex({ "created_at": -1 })
db.policies.createIndex({ "channel_id": 1, "applied_at": -1 })
db.decisions.createIndex({ "node_id": 1, "decision_type": 1, "created_at": -1 })
db.transactions.createIndex({ "transaction_id": 1 })
db.backups.createIndex({ "created_at": 1 })  // Pour cleanup
```

---

## 🗄️ Redis Cloud Configuration

### Option 1 : Redis Cloud

1. Créer compte sur [Redis Cloud](https://redis.com/redis-enterprise-cloud/)
2. Créer une base de données (30MB gratuit)
3. Obtenir l'endpoint et password

```bash
REDIS_URL=redis://default:<password>@redis-12345.c123.us-east-1-1.ec2.redns.redis-cloud.com:12345
REDIS_TLS=true
```

### Option 2 : Upstash (Serverless)

1. Créer compte sur [Upstash](https://upstash.com/)
2. Créer une base Redis
3. Copier l'URL REST

```bash
REDIS_URL=<upstash_redis_url>
```

### Option 3 : Redis Local (Dev uniquement)

```bash
# Docker
docker run -d --name redis -p 6379:6379 redis:alpine

REDIS_URL=redis://localhost:6379
```

---

## 📧 Notifications (Telegram)

### 1. Créer un Bot Telegram

1. Parler à [@BotFather](https://t.me/botfather)
2. Envoyer `/newbot`
3. Suivre les instructions
4. Copier le token

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 2. Obtenir votre Chat ID

1. Parler à [@userinfobot](https://t.me/userinfobot)
2. Il vous donnera votre Chat ID

```bash
TELEGRAM_CHAT_ID=123456789
```

### 3. Tester

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage" \
  -d "chat_id=<TELEGRAM_CHAT_ID>" \
  -d "text=Test MCP Notifications ✅"
```

---

## 🔍 Monitoring Setup

### Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana

1. Ajouter Prometheus comme data source
2. Importer dashboard MCP (à créer)
3. Configurer alertes

```bash
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=<générer_depuis_grafana>
```

---

## ✅ Validation Configuration

Avant de démarrer, vérifier :

```bash
# Script de validation
python3 scripts/validate_production_config.py

# Doit afficher :
# ✅ LNBits connection OK
# ✅ MongoDB connection OK
# ✅ Redis connection OK
# ✅ All safety limits configured
# ✅ Macaroon encryption key present
# ✅ DRY_RUN is enabled (Shadow Mode)
```

---

## 🚀 Démarrage

### Mode Shadow (Recommandé)

```bash
# 1. Vérifier configuration
cat .env.production | grep DRY_RUN
# Doit afficher: DRY_RUN=true

# 2. Démarrer
docker-compose -f docker-compose.production.yml up -d

# 3. Vérifier logs
docker-compose logs -f mcp-api

# 4. Vérifier santé
curl http://localhost:8000/
```

### Monitoring Continu

```bash
# Lancer monitoring 24/7
python3 monitor_production.py --duration unlimited &

# Rapport quotidien
echo "0 9 * * * cd /path/to/mcp && python3 scripts/daily_shadow_report.py" | crontab -
```

---

## 📈 Transition Shadow → Production

Après **minimum 14 jours** de shadow mode :

### 1. Analyse

```bash
# Générer rapport complet
python3 scripts/shadow_mode_analysis.py

# Vérifier métriques
# - 0 erreurs critiques
# - Taux de succès > 95%
# - Latence < 500ms
# - Validation expert
```

### 2. Activation Test (1 canal)

```bash
# Modifier .env.production
DRY_RUN=false
MAX_CHANNELS_PER_RUN=1  # 1 seul canal

# Redémarrer
docker-compose restart mcp-api

# Observer 48h
```

### 3. Activation Progressive

```bash
# Si test OK après 48h
MAX_CHANNELS_PER_RUN=5  # 5 canaux
# Observer 1 semaine

# Si toujours OK
MAX_CHANNELS_PER_RUN=  # Pas de limite (ou unlimited)
```

---

## 🆘 Rollback d'Urgence

En cas de problème :

```bash
# 1. Passer immédiatement en DRY_RUN
sed -i 's/DRY_RUN=false/DRY_RUN=true/' .env.production
docker-compose restart mcp-api

# 2. Rollback manuel si nécessaire
python3 -m src.tools.rollback_orchestrator rollback \
  --transaction-id <id> \
  --reason "Emergency rollback"

# 3. Analyser logs
docker-compose logs mcp-api --tail=1000 > emergency.log
```

---

## 📞 Support

### Logs

```bash
# Logs temps réel
docker-compose logs -f mcp-api

# Logs spécifiques
docker-compose logs mcp-api | grep ERROR
docker-compose logs mcp-api | grep "rollback"

# Export pour analyse
docker-compose logs mcp-api > logs_export_$(date +%Y%m%d).txt
```

### Debugging

```bash
# Entrer dans le container
docker-compose exec mcp-api /bin/bash

# Vérifier connexions
python3 -c "from src.clients.lnbits_client import LNBitsClient; import asyncio; asyncio.run(LNBitsClient().get_node_info())"

# Test complet
python3 scripts/test_phase2_integration.py
```

---

## 📚 Références

- [Roadmap Production](../_SPECS/Roadmap-Production-v1.0.md)
- [Architecture Technique](./backbone-technique-MVP.md)
- [Tests d'Intégration](../scripts/test_phase2_integration.py)
- [Monitoring Production](../monitor_production.py)

---

**⚠️ RAPPEL IMPORTANT** : Toujours démarrer en Shadow Mode (DRY_RUN=true) et observer minimum 14 jours avant activation réelle.

