# 🐳 Déploiement Docker MCP sur Hostinger
> Date: 7 janvier 2025
> Statut: ✅ **PRÊT POUR DÉPLOIEMENT**

## 🎯 Objectif

Déployer l'application MCP sur Hostinger en utilisant Docker et Docker Compose, avec un déploiement automatique via push Git.

## 📋 Prérequis

### Sur votre machine locale
- Docker et Docker Compose installés
- Git configuré
- Variables d'environnement configurées

### Sur le serveur Hostinger
- Accès SSH au serveur
- Droits sudo (pour installation Docker)

## 🚀 Étapes de Déploiement

### 1. Préparation Locale

#### Configuration des variables d'environnement
```bash
# Définir les variables d'environnement
export AI_OPENAI_API_KEY="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"
export SECURITY_SECRET_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY"
```

#### Test local du déploiement Docker
```bash
# Exécuter le script de déploiement local
chmod +x scripts/deploy_docker_hostinger.sh
./scripts/deploy_docker_hostinger.sh
```

### 2. Push Git pour Déclencher le Déploiement

#### Commit et push des fichiers Docker
```bash
# Ajouter les fichiers de déploiement Docker
git add docker-compose.hostinger.yml Dockerfile.hostinger scripts/start.sh scripts/deploy_hostinger_docker.sh .dockerignore

# Commit des changements
git commit -m "feat: Déploiement Docker pour Hostinger - Configuration complète"

# Push vers la branche berty
git push origin berty
```

### 3. Déploiement sur le Serveur Hostinger

#### Connexion au serveur
```bash
ssh feustey@srv782904
```

#### Exécution du script de déploiement
```bash
# Aller dans le répertoire de l'application
cd /home/feustey

# Exécuter le script de déploiement Docker
chmod +x scripts/deploy_hostinger_docker.sh
./scripts/deploy_hostinger_docker.sh
```

## 📁 Structure des Fichiers Docker

### Fichiers Principaux
- `docker-compose.hostinger.yml` - Configuration Docker Compose pour Hostinger
- `Dockerfile.hostinger` - Image Docker optimisée pour Hostinger
- `scripts/start.sh` - Script de démarrage du conteneur
- `scripts/deploy_hostinger_docker.sh` - Script de déploiement sur le serveur

### Configuration
- `.env.docker` - Variables d'environnement pour Docker (généré automatiquement)
- `.dockerignore` - Fichiers exclus de l'image Docker

## 🔧 Services Déployés

### 1. API MCP (mcp-api)
- **Port**: 8000
- **Image**: Construite localement
- **Health check**: `/health`
- **Logs**: `docker-compose logs mcp-api`

### 2. Reverse Proxy Caddy
- **Ports**: 80, 443
- **Image**: `caddy:2-alpine`
- **Configuration**: SSL automatique avec Let's Encrypt
- **Domain**: `api.dazno.de`

### 3. Monitoring Prometheus
- **Port**: 9090
- **Image**: `prom/prometheus:latest`
- **Configuration**: `config/prometheus/prometheus-prod.yml`

### 4. Dashboard Grafana
- **Port**: 3000
- **Image**: `grafana/grafana:latest`
- **Credentials**: admin/admin123
- **Configuration**: `config/grafana/`

## 🌐 Accès aux Services

### Production
- **API MCP**: https://api.dazno.de
- **Documentation**: https://api.dazno.de/docs
- **Health Check**: https://api.dazno.de/health

### Monitoring (local)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## 📊 Commandes de Gestion

### Vérification du statut
```bash
# Statut des conteneurs
docker-compose -f docker-compose.hostinger.yml ps

# Logs en temps réel
docker-compose -f docker-compose.hostinger.yml logs -f

# Logs d'un service spécifique
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api
```

### Gestion des services
```bash
# Redémarrer tous les services
docker-compose -f docker-compose.hostinger.yml restart

# Redémarrer un service spécifique
docker-compose -f docker-compose.hostinger.yml restart mcp-api

# Arrêter tous les services
docker-compose -f docker-compose.hostinger.yml down

# Arrêter et supprimer les volumes
docker-compose -f docker-compose.hostinger.yml down -v
```

### Mise à jour
```bash
# Mise à jour depuis Git
git pull origin berty

# Reconstruire et redémarrer
docker-compose -f docker-compose.hostinger.yml down
docker-compose -f docker-compose.hostinger.yml build --no-cache
docker-compose -f docker-compose.hostinger.yml --env-file .env.docker up -d
```

## 🔍 Diagnostic et Dépannage

### Vérification de l'API
```bash
# Test local
curl http://localhost:8000/health

# Test via HTTPS
curl https://api.dazno.de/health

# Test avec plus de détails
curl -v https://api.dazno.de/health
```

### Vérification des conteneurs
```bash
# Liste des conteneurs
docker ps

# Informations détaillées
docker inspect mcp-api-hostinger

# Ressources utilisées
docker stats
```

### Logs et erreurs
```bash
# Logs de l'API
docker-compose -f docker-compose.hostinger.yml logs mcp-api

# Logs de Caddy
journalctl -u caddy -f

# Logs système
journalctl -f
```

## 🔧 Configuration Avancée

### Variables d'environnement personnalisées
Modifier le fichier `.env.docker` pour ajuster :
- Configuration des bases de données
- Paramètres de performance
- Configuration de sécurité
- Paramètres de logging

### Configuration Caddy personnalisée
Modifier `/etc/caddy/Caddyfile` pour :
- Ajouter des domaines supplémentaires
- Configurer des règles de rate limiting
- Ajouter des headers de sécurité
- Configurer des redirections

### Monitoring personnalisé
- Ajouter des dashboards Grafana
- Configurer des alertes Prometheus
- Personnaliser les métriques collectées

## 🚨 Résolution de Problèmes

### Erreur 502 Bad Gateway
```bash
# Vérifier que l'API est démarrée
docker-compose -f docker-compose.hostinger.yml ps

# Vérifier les logs de l'API
docker-compose -f docker-compose.hostinger.yml logs mcp-api

# Redémarrer l'API
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

### Problème de connectivité aux bases de données
```bash
# Tester MongoDB
docker exec mcp-api-hostinger python3 -c "
import pymongo
client = pymongo.MongoClient('$MONGO_URL', serverSelectionTimeoutMS=5000)
client.admin.command('ping')
print('MongoDB OK')
"

# Tester Redis
docker exec mcp-api-hostinger python3 -c "
import redis
r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT, password='$REDIS_PASSWORD', ssl=True)
r.ping()
print('Redis OK')
"
```

### Problème de certificat SSL
```bash
# Vérifier le statut de Caddy
systemctl status caddy

# Redémarrer Caddy
systemctl restart caddy

# Vérifier les certificats
ls -la /etc/letsencrypt/live/api.dazno.de/
```

## 📈 Monitoring et Alertes

### Métriques disponibles
- **API**: Temps de réponse, taux d'erreur, nombre de requêtes
- **Système**: CPU, mémoire, disque, réseau
- **Base de données**: Connexions, requêtes, performance
- **Cache**: Hit rate, taille, évictions

### Alertes configurées
- API non accessible (erreur 502)
- Temps de réponse élevé (> 2s)
- Taux d'erreur élevé (> 5%)
- Utilisation mémoire élevée (> 80%)
- Disque plein (> 90%)

## 🔄 Mise à Jour Continue

### Déploiement automatique
1. Modifications locales
2. Tests locaux avec Docker
3. Commit et push vers `berty`
4. Déploiement automatique sur Hostinger

### Rollback
```bash
# Retour à la version précédente
git reset --hard HEAD~1
git push origin berty --force

# Ou restauration depuis backup
tar -xzf backups/backup_YYYYMMDD_HHMMSS.tar.gz
```

## ✅ Checklist de Déploiement

- [ ] Variables d'environnement configurées
- [ ] Test local Docker réussi
- [ ] Fichiers Docker commités et poussés
- [ ] Script de déploiement exécuté sur le serveur
- [ ] API accessible via HTTPS
- [ ] Health check fonctionnel
- [ ] Monitoring opérationnel
- [ ] Logs sans erreurs critiques
- [ ] Documentation accessible

## 📞 Support

En cas de problème :
1. Vérifier les logs : `docker-compose logs -f`
2. Tester l'API : `curl https://api.dazno.de/health`
3. Vérifier les conteneurs : `docker ps`
4. Consulter les logs système : `journalctl -f`

---

**Statut : DÉPLOIEMENT DOCKER PRÊT** 🐳 