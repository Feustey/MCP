# Guide de Déploiement MCP en Production
> Dernière mise à jour: 27 mai 2025

## Vue d'ensemble

Ce guide détaille le processus de déploiement du système MCP (Lightning Network Optimization) en production sur `api.dazno.de`.

## Prérequis

### Infrastructure
- Serveur Ubuntu/Debian avec minimum 4GB RAM et 20GB d'espace disque
- Docker et Docker Compose installés
- Certificats SSL (Let's Encrypt recommandé)
- Accès SSH avec privilèges sudo

### Variables d'environnement
Le fichier `.env.production` doit contenir :
```bash
# Base de données
MONGO_ROOT_USER=mcp_admin
MONGO_ROOT_PASSWORD=<mot_de_passe_sécurisé>
REDIS_PASSWORD=<mot_de_passe_redis>

# Sécurité
JWT_SECRET=<clé_jwt_256_bits>
ENCRYPTION_KEY=<clé_chiffrement_256_bits>

# Monitoring
GRAFANA_ADMIN_PASSWORD=<mot_de_passe_grafana>
GRAFANA_SECRET_KEY=<clé_secrète_grafana>

# Notifications
TELEGRAM_BOT_TOKEN=<token_bot_telegram>
TELEGRAM_CHAT_ID=<id_chat_telegram>

# APIs externes
SPARKSEER_API_KEY=<clé_api_sparkseer>
OPENAI_API_KEY=<clé_api_openai>
```

## Architecture de Production

### Services Docker
- **mcp-api** : API principale FastAPI (port 8000)
- **mongodb** : Base de données MongoDB (port 27017)
- **redis** : Cache Redis (port 6379)
- **prometheus** : Monitoring des métriques (port 9090)
- **grafana** : Dashboard de monitoring (port 3000)

### Sécurité
- Authentification JWT avec isolation par tenant
- Rate limiting : 100 requêtes/heure par IP
- HTTPS obligatoire avec certificats Let's Encrypt
- Accès restreint depuis app.dazno.de uniquement
- Chiffrement des données sensibles

## Processus de Déploiement

### 1. Préparation
```bash
# Cloner le repository
git clone https://github.com/Feustey/MCP.git
cd MCP

# Préparer les configurations
./scripts/prepare-config.sh
```

### 2. Validation
```bash
# Valider la configuration (sans Docker)
./scripts/deploy-simple.sh
```

### 3. Déploiement en développement
```bash
# Test en mode développement
./scripts/deploy.sh --dev
```

### 4. Déploiement en production
```bash
# Déploiement complet sur api.dazno.de
sudo ./scripts/deploy.sh
```

## Configuration des Services

### MongoDB
- Configuration sécurisée avec authentification
- Compression des données avec Snappy
- Journalisation activée
- Profiling des requêtes lentes (>100ms)

### Redis
- Authentification par mot de passe
- Politique de mémoire LRU
- Persistance AOF activée
- Commandes dangereuses désactivées

### Prometheus
- Collecte de métriques toutes les 15s
- Rétention de 30 jours
- Monitoring de l'API, MongoDB et Redis

### Grafana
- Dashboards préconfigurés
- Alertes automatiques
- Intégration Prometheus

## Monitoring et Alertes

### Métriques surveillées
- Performance de l'API (latence, erreurs)
- Utilisation des ressources (CPU, mémoire)
- Santé des bases de données
- Taux de succès des paiements Lightning

### Alertes Telegram
- Erreurs critiques
- Dépassement de seuils de performance
- Échecs de déploiement
- Problèmes de connectivité

## Maintenance

### Sauvegardes automatiques
- MongoDB : dump quotidien
- Redis : snapshot toutes les heures
- Configurations : sauvegarde avant chaque déploiement

### Rotation des logs
- Logs applicatifs : 7 jours
- Logs système : 30 jours
- Métriques Prometheus : 30 jours

### Mises à jour
- Déploiement avec rollback automatique
- Tests de santé post-déploiement
- Notifications de statut

## Sécurité

### Authentification
```bash
# Génération d'un token JWT
curl -X POST https://api.dazno.de/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### Rate Limiting
- 100 requêtes/heure par IP
- Quotas spécifiques par API (Sparkseer : 2000/jour)
- Blocage automatique des IPs abusives

### CORS
- Origine autorisée : `https://app.dazno.de`
- Méthodes : GET, POST, PUT, DELETE
- Headers personnalisés autorisés

## Endpoints de Production

### API Principale
- **Base URL** : `https://api.dazno.de`
- **Health Check** : `GET /health`
- **Metrics** : `GET /metrics`
- **Documentation** : `GET /docs`

### Monitoring
- **Prometheus** : `https://api.dazno.de/prometheus/`
- **Grafana** : `https://api.dazno.de/grafana/`

## Dépannage

### Logs
```bash
# Logs de l'API
docker logs mcp-api-prod

# Logs MongoDB
docker logs mcp-mongodb-prod

# Logs Redis
docker logs mcp-redis-prod
```

### Tests de santé
```bash
# Test API
curl https://api.dazno.de/health

# Test MongoDB
docker exec mcp-mongodb-prod mongosh --eval "db.adminCommand('ping')"

# Test Redis
docker exec mcp-redis-prod redis-cli ping
```

### Rollback
```bash
# Rollback automatique en cas d'échec
# Le script de déploiement gère automatiquement les rollbacks
```

## Performance

### Optimisations
- Cache Redis pour les requêtes fréquentes
- Index MongoDB optimisés
- Compression des réponses API
- Pool de connexions configuré

### Métriques cibles
- Latence API : < 200ms (95e percentile)
- Disponibilité : > 99.9%
- Temps de réponse HTLC : < 0.3s
- Taux de succès des paiements : > 95%

## Support

### Contacts
- **Équipe technique** : Notifications Telegram automatiques
- **Logs centralisés** : `/tmp/mcp_logs/` en développement
- **Monitoring** : Dashboard Grafana temps réel

### Documentation
- **API** : `/docs/api/`
- **Architecture** : `/docs/core/`
- **Troubleshooting** : `/docs/technical/` 