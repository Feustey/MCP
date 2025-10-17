# 🔄 Changements MongoDB & Redis en Local

> **Date**: 16 octobre 2025  
> **Version**: 1.0.0-local-db  
> **Statut**: ✅ Appliqué

---

## 📋 Résumé des Changements

MongoDB et Redis ont été **configurés en LOCAL** dans Docker au lieu d'utiliser des services cloud (MongoDB Atlas et Redis Upstash).

### Avantages
✅ **Gratuit** - Pas de frais cloud  
✅ **Performance** - Latence minimale  
✅ **Contrôle total** - Données sur votre serveur  
✅ **Simplicité** - Moins de credentials à gérer  

### Inconvénients
⚠️ **Ressources** - Consomme RAM/CPU du serveur (~1 GB)  
⚠️ **Backup** - Vous devez gérer les sauvegardes  
⚠️ **Scaling** - Pas de scaling automatique  

---

## 🔧 Fichiers Modifiés

### 1. `docker-compose.production.yml`

**Ajouté** :
- Service `mongodb` (MongoDB 7.0)
- Service `redis` (Redis 7-alpine)
- Volumes `mongodb_data`, `mongodb_config`, `redis_data`
- Dépendances `mongodb` et `redis` dans `mcp-api`
- Volumes MongoDB et Redis dans service `backup`

**Détails** :
```yaml
mongodb:
  - Image: mongo:7.0
  - Port: 27017 (exposé uniquement au réseau Docker)
  - User: mcp_admin
  - Password: mcp_secure_password_2025
  - Database: mcp_prod

redis:
  - Image: redis:7-alpine
  - Port: 6379 (exposé uniquement au réseau Docker)
  - Password: mcp_redis_password_2025
```

### 2. `config_production_hostinger.env`

**Modifié** :
- Section MongoDB : `mongodb://mcp_admin:mcp_secure_password_2025@mongodb:27017/mcp_prod`
- Section Redis : `redis://:mcp_redis_password_2025@redis:6379/0`
- Ajout de `MONGO_ROOT_PASSWORD`
- Changé `REDIS_TLS=false`

**Avant (Cloud)** :
```bash
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/...
REDIS_URL=redis://default:password@redis-xxxxx.upstash.io:6379
```

**Après (Local)** :
```bash
MONGO_URL=mongodb://mcp_admin:mcp_secure_password_2025@mongodb:27017/mcp_prod?authSource=admin
REDIS_URL=redis://:mcp_redis_password_2025@redis:6379/0
```

### 3. `scripts/backup_daily.sh`

**Ajouté** :
- Backup MongoDB avec `mongodump`
- Backup Redis avec `BGSAVE` + volume backup
- Nettoyage automatique des backups MongoDB/Redis

**Nouvelles sections** :
```bash
# 1/6 - Backup MongoDB Local
# 2/6 - Backup Redis Local
# 3/6 - Backup Qdrant (ancien 1/5)
# ...
```

### 4. `scripts/validate_deployment.sh`

**Ajouté** :
- Test 4: MongoDB Local
  - Health check avec `mongosh`
  - Test authentification
  - Vérification database
  
- Test 5: Redis Local
  - Health check avec `redis-cli`
  - Test Read/Write
  - Vérification persistence

**Modifié** :
- Liste des conteneurs à vérifier (ajout mongodb-prod et redis-prod)
- Tests de configuration (MongoDB local au lieu d'Atlas)
- Numérotation des tests (12 tests au lieu de 10)

### 5. `START_HERE_DEPLOY.txt`

**Modifié** :
- Section "Préparez vos credentials" : Retiré MongoDB Atlas et Redis Upstash
- Section "Architecture" : Ajouté MongoDB et Redis en local
- Liste des conteneurs mise à jour

**Avant** :
```
Créez et collectez:
• MongoDB Atlas
• Redis Upstash
• Anthropic API
```

**Après** :
```
Créez et collectez:
• Anthropic API
✅ MongoDB et Redis sont en LOCAL (Docker) - pas besoin de cloud !
```

---

## 🗄️ Architecture Mise à Jour

### Services Docker

```
┌─────────────────────────────────────────────────┐
│              MCP Production Stack               │
├─────────────────────────────────────────────────┤
│                                                 │
│  Internet → Nginx (SSL) → MCP API              │
│                     ↓                           │
│              Docker Network                     │
│                     ↓                           │
│  ┌──────────┬──────────┬──────────┬──────────┐ │
│  │ MongoDB  │  Redis   │ Qdrant   │ Ollama   │ │
│  │ (27017)  │ (6379)   │ (6333)   │ (11434)  │ │
│  │ LOCAL    │ LOCAL    │ LOCAL    │ LOCAL    │ │
│  └──────────┴──────────┴──────────┴──────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Volumes Persistants

| Volume | Taille | Contenu | Backup |
|--------|--------|---------|--------|
| `mcp_mongodb_data` | 100MB-5GB | Base de données | ✅ Quotidien |
| `mcp_mongodb_config` | <1MB | Configuration MongoDB | ✅ Quotidien |
| `mcp_redis_data` | 10MB-1GB | Cache Redis | ✅ Quotidien |
| `mcp_qdrant_data` | 1GB-10GB | Vector database | ✅ Quotidien |
| `mcp_ollama_data` | 5GB-40GB | Modèles LLM | ❌ |

---

## 🔐 Credentials Générés

### MongoDB
```bash
Username: mcp_admin
Password: mcp_secure_password_2025
Database: mcp_prod
Auth Database: admin
```

### Redis
```bash
Password: mcp_redis_password_2025
Database: 0
```

⚠️ **Ces passwords sont dans `config_production_hostinger.env`**  
Changez-les si nécessaire avant le déploiement.

---

## 📦 Backup Automatique

Le script `backup_daily.sh` sauvegarde maintenant :

1. **MongoDB** : `mongodump` → `mongodb_YYYYMMDD_HHMMSS.tar.gz`
2. **Redis** : Volume backup → `redis_YYYYMMDD_HHMMSS.tar.gz`
3. **Qdrant** : Volume backup → `qdrant_YYYYMMDD_HHMMSS.tar.gz`
4. **Ollama** : Skip (trop volumineux, re-downloadable)
5. **App Data** : `mcp-data/` → `mcp_data_YYYYMMDD_HHMMSS.tar.gz`
6. **Config** : `.env.production` → `env_production_YYYYMMDD_HHMMSS.backup`

**Rétention** : 30 jours (nettoyage automatique)

**Cron recommandé** :
```bash
0 3 * * * /opt/mcp/scripts/backup_daily.sh
```

---

## 🧪 Validation

Le script `validate_deployment.sh` teste maintenant :

1. Docker Compose (6 conteneurs)
2. API Health
3. Nginx + SSL
4. **MongoDB Local** (nouveau !)
   - Health check
   - Authentification
   - Database exists
5. **Redis Local** (nouveau !)
   - Health check
   - Read/Write
   - Persistence
6. Qdrant
7. Ollama
8. Configuration
9. Logs
10. Network connectivity
11. Disk space
12. Security

**Total** : 12 tests (au lieu de 10)

---

## 🚀 Commandes de Gestion

### MongoDB

```bash
# Se connecter à MongoDB
docker exec -it mcp-mongodb-prod mongosh -u mcp_admin -p mcp_secure_password_2025 --authenticationDatabase admin

# Lister les databases
docker exec mcp-mongodb-prod mongosh -u mcp_admin -p mcp_secure_password_2025 --authenticationDatabase admin --eval "db.getMongo().getDBNames()"

# Backup manuel
docker exec mcp-mongodb-prod mongodump -u mcp_admin -p mcp_secure_password_2025 --authenticationDatabase admin --db mcp_prod --out /backup/manual

# Restore
docker exec mcp-mongodb-prod mongorestore -u mcp_admin -p mcp_secure_password_2025 --authenticationDatabase admin --db mcp_prod /backup/manual/mcp_prod
```

### Redis

```bash
# Se connecter à Redis
docker exec -it mcp-redis-prod redis-cli -a mcp_redis_password_2025

# Vérifier status
docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 INFO

# Test ping
docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 ping

# Sauvegarder manuellement
docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 BGSAVE

# Vider le cache
docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 FLUSHALL
```

---

## ⚠️ Points d'Attention

### Consommation Ressources

**MongoDB** :
- RAM : ~300-500 MB
- CPU : 5-10% en idle, 20-50% en charge
- Disk : 100 MB initialement, peut croître

**Redis** :
- RAM : ~50-200 MB
- CPU : 1-5% en idle
- Disk : Minimal (persistence RDB)

**Recommandation** : Minimum 8 GB RAM serveur (16 GB idéal)

### Monitoring

Surveillez l'utilisation avec :
```bash
# Stats conteneurs
docker stats

# Espace disque
df -h

# Taille volumes
docker system df -v
```

---

## 🔄 Rollback (si nécessaire)

Si vous voulez revenir à MongoDB Atlas et Redis Upstash :

1. **Modifier `config_production_hostinger.env`** :
   ```bash
   MONGO_URL=mongodb+srv://...
   REDIS_URL=redis://...@upstash.io:6379
   ```

2. **Commenter services dans `docker-compose.production.yml`** :
   ```yaml
   # mongodb:
   #   ...
   # redis:
   #   ...
   ```

3. **Retirer dépendances** :
   ```yaml
   mcp-api:
     depends_on:
       # - mongodb
       # - redis
       - qdrant
       - ollama
   ```

4. **Redémarrer** :
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

---

## ✅ Checklist de Vérification

Après déploiement, vérifiez :

- [ ] Conteneurs `mcp-mongodb-prod` et `mcp-redis-prod` sont "Up (healthy)"
- [ ] Test MongoDB : `docker exec mcp-mongodb-prod mongosh --eval "db.adminCommand('ping')"`
- [ ] Test Redis : `docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 ping`
- [ ] API se connecte à MongoDB : Vérifier logs `docker logs mcp-api-prod`
- [ ] API se connecte à Redis : Vérifier logs
- [ ] Backup fonctionne : `./scripts/backup_daily.sh`
- [ ] Validation complète : `./scripts/validate_deployment.sh`

---

## 📞 Support

En cas de problème :

1. **Logs MongoDB** : `docker logs mcp-mongodb-prod`
2. **Logs Redis** : `docker logs mcp-redis-prod`
3. **Logs API** : `docker logs mcp-api-prod`
4. **Script validation** : `./scripts/validate_deployment.sh`

---

**Dernière mise à jour** : 16 octobre 2025  
**Version** : 1.0.0-local-db  
**Statut** : ✅ Production Ready

