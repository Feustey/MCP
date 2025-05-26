# Guide de Déploiement Production MCP
> Dernière mise à jour: 7 mai 2025

## Vue d'ensemble

Ce guide détaille la procédure complète de déploiement de MCP en production sur le serveur `api.dazno.de`.

## 📋 Prérequis

### Infrastructure
- Serveur avec Docker et Docker Compose installés
- Minimum 4GB RAM, 2 CPU cores, 50GB storage
- Accès SSH au serveur de production
- Domaine configuré avec certificats SSL

### Variables d'environnement
Créer le fichier `.env.production` basé sur `config/env.production.template` avec :

```bash
# Mots de passe sécurisés (générer avec des outils crypto)
MONGO_ROOT_PASSWORD=<password_securise_mongodb>
REDIS_PASSWORD=<password_securise_redis>
JWT_SECRET=<secret_jwt_256_bits>
GRAFANA_ADMIN_PASSWORD=<password_grafana>
GRAFANA_SECRET_KEY=<secret_grafana>

# APIs externes
SPARKSEER_API_KEY=<votre_cle_sparkseer>

# Notifications Telegram
TELEGRAM_BOT_TOKEN=<token_bot_telegram>
TELEGRAM_CHAT_ID=<id_chat_telegram>
```

## 🚀 Déploiement automatisé

### Script de déploiement
```bash
# Rendre le script exécutable
chmod +x scripts/deploy-production.sh

# Lancer le déploiement
./scripts/deploy-production.sh
```

Le script effectue automatiquement :
1. ✅ Vérification des prérequis
2. 📁 Création des répertoires système
3. 💾 Sauvegarde des données existantes
4. 🛑 Arrêt des services actuels
5. 🏗️ Construction des images Docker
6. 🚀 Démarrage des services
7. 🔍 Vérification de la santé des services

## 🏗️ Architecture des services

### Services principaux
- **mcp-api**: API principale FastAPI
- **mongodb**: Base de données principale
- **redis**: Cache et sessions
- **qdrant**: Base vectorielle pour RAG

### Monitoring et alertes
- **prometheus**: Collecte de métriques
- **grafana**: Dashboards et visualisation
- **alertmanager**: Gestion des alertes
- **node-exporter**: Métriques système

### Maintenance
- **backup**: Sauvegardes automatiques quotidiennes
- **cleanup**: Nettoyage des anciennes sauvegardes

## 📊 Monitoring

### Accès aux dashboards
- **Grafana**: `https://api.dazno.de/grafana`
- **Prometheus**: `https://api.dazno.de/prometheus` (admin)
- **API Health**: `https://api.dazno.de/health`

### Métriques surveillées
- Utilisation CPU et mémoire
- Latence et taux d'erreur API
- État des bases de données
- Performance des optimisations MCP

### Alertes configurées
- **Critique**: Services down, erreurs API >5%
- **Warning**: Ressources >85%, latence élevée
- **Info**: Sauvegardes, optimisations

## 🔧 Commandes de maintenance

### Vérification du statut
```bash
# Status de tous les services
docker-compose -f docker-compose.prod.yml ps

# Logs en temps réel
docker logs -f mcp-api-prod
docker logs -f mcp-mongodb-prod
```

### Gestion des services
```bash
# Redémarrage d'un service
docker-compose -f docker-compose.prod.yml restart mcp-api

# Mise à jour sans interruption
docker-compose -f docker-compose.prod.yml up -d --no-deps mcp-api

# Arrêt complet
docker-compose -f docker-compose.prod.yml down
```

### Sauvegardes manuelles
```bash
# Déclencher une sauvegarde manuelle
docker exec mcp-backup-prod /usr/local/bin/backup.sh

# Lister les sauvegardes
ls -la /opt/mcp/backups/
```

## 🔐 Sécurité

### Ports exposés
- `8000`: API MCP (via reverse proxy)
- `3000`: Grafana (via reverse proxy)
- `9090`: Prometheus (admin interne)

### Authentification
- **API**: JWT avec expiration 24h
- **Grafana**: Admin user configuré
- **Bases de données**: Authentification requise

### Volumes persistants
```
/opt/mcp/data/mongodb    # Données MongoDB
/opt/mcp/data/redis      # Données Redis  
/opt/mcp/data/grafana    # Configuration Grafana
/opt/mcp/data/prometheus # Métriques Prometheus
/opt/mcp/data/qdrant     # Vecteurs RAG
/opt/mcp/backups/        # Sauvegardes
/opt/mcp/logs/           # Logs applicatifs
```

## 🚨 Procédures d'urgence

### Rollback rapide
1. Arrêter les services : `docker-compose -f docker-compose.prod.yml down`
2. Restaurer les données depuis `/opt/mcp/backups/`
3. Redémarrer l'ancienne version

### Restauration de sauvegarde
```bash
# Arrêter les services
docker-compose -f docker-compose.prod.yml down

# Restaurer MongoDB
mongorestore --host localhost --port 27017 \
  --username admin --password <password> \
  --authenticationDatabase admin \
  /path/to/backup/mongodb/

# Restaurer Redis
redis-cli -p 6379 -a <password> --rdb /path/to/backup/redis_dump.rdb

# Redémarrer
docker-compose -f docker-compose.prod.yml up -d
```

### Debug des problèmes
```bash
# Vérifier les logs d'erreur
docker logs mcp-api-prod | grep ERROR

# Vérifier l'utilisation des ressources
docker stats

# Tester la connectivité aux services
docker exec mcp-api-prod curl -f http://localhost:8000/health
```

## 📈 Performance

### Limites de ressources
- **API**: 2 CPU, 2GB RAM
- **MongoDB**: 1 CPU, 1GB RAM  
- **Redis**: 0.5 CPU, 512MB RAM
- **Autres services**: Limités selon besoins

### Optimisations appliquées
- Cache Redis avec éviction LRU
- MongoDB avec compression snappy
- API multi-worker (4 workers)
- Connexions limitées et pool management

## 🔄 Mises à jour

### Procédure de mise à jour
1. Tester en environnement staging
2. Créer sauvegarde automatique
3. Déployer la nouvelle version
4. Vérifier les health checks
5. Monitorer les métriques

### Mise à jour zero-downtime
```bash
# Construire nouvelle image
docker-compose -f docker-compose.prod.yml build mcp-api

# Mise à jour progressive
docker-compose -f docker-compose.prod.yml up -d --no-deps mcp-api
```

## 📞 Support

### Contacts d'urgence
- **Admin système**: alerts@dazno.de
- **Notifications**: Canal Telegram configuré
- **Documentation**: Ce guide et `/docs/`

### Logs de monitoring
- **Application**: `/opt/mcp/logs/mcp.log`
- **Accès**: `/opt/mcp/logs/access.log`  
- **Erreurs**: `/opt/mcp/logs/error.log`
- **Sauvegardes**: Notifications Telegram

---

> ⚠️ **Important**: Toujours tester les procédures en staging avant la production !
> 
> 📧 **Contact**: Pour toute question, contacter l'équipe via alerts@dazno.de 