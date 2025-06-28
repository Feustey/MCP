# Guide de Déploiement MCP RAG sur Hostinger

> Dernière mise à jour: 7 janvier 2025

## Vue d'ensemble

Ce guide détaille le déploiement complet du système MCP (Management Control Protocol) avec fonctionnalités RAG (Retrieval-Augmented Generation) et Intelligence sur un serveur Hostinger.

## Architecture du Déploiement

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Web    │    │   API Gateway   │    │   MCP API       │
│                 │◄──►│   (Nginx)       │◄──►│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Prometheus    │    │   Grafana       │
                       │   (Monitoring)  │◄──►│   (Dashboard)   │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Qdrant        │
                       │   (Vector DB)   │
                       └─────────────────┘
```

## Prérequis

### Sur votre machine locale
- Docker installé
- SSH configuré avec accès au serveur Hostinger
- Git pour récupérer le code

### Sur le serveur Hostinger
- Docker et Docker Compose installés
- Accès SSH activé
- Ports ouverts : 80, 443, 8000, 3000, 9090, 6333
- Certificats SSL configurés pour le domaine

## Configuration

### 1. Variables d'environnement

Créez un fichier `.env.hostinger` avec les variables suivantes :

```bash
# Configuration de base
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO

# Configuration serveur
HOST=0.0.0.0
PORT=8000
RELOAD=false
WORKERS=4

# Base de données MongoDB (Hostinger)
MONGO_URL=mongodb://root:password@localhost:27017/mcp?authSource=admin&retryWrites=true&w=majority

# Redis (Hostinger)
REDIS_URL=redis://localhost:6379/0

# Sécurité
JWT_SECRET_KEY=your-jwt-secret-key-here
SECRET_KEY=your-secret-key-here

# Services externes
LNBITS_URL=https://lnbits.dazno.de
LNBITS_ADMIN_KEY=your-lnbits-admin-key

# RAG et Intelligence
OLLAMA_URL=http://localhost:11434
ANTHROPIC_API_KEY=your-anthropic-api-key

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# SSL/TLS
SSL_ENABLED=true
SSL_CERT_PATH=/etc/ssl/certs/api.dazno.de.crt
SSL_KEY_PATH=/etc/ssl/private/api.dazno.de.key
```

### 2. Configuration SSH

Modifiez le script `scripts/deploy-hostinger-rag.sh` avec vos credentials :

```bash
SSH_HOST="u123456789@your-hostinger-server.com"
SSH_PORT="22"
```

## Déploiement

### Méthode 1 : Script automatisé (Recommandé)

```bash
# Rendre le script exécutable
chmod +x scripts/deploy-hostinger-rag.sh

# Exécuter le déploiement
./scripts/deploy-hostinger-rag.sh
```

### Méthode 2 : Déploiement manuel

```bash
# 1. Construire l'image Docker
docker build -t feustey/dazno:latest .

# 2. Pousser l'image sur Docker Hub
docker push feustey/dazno:latest

# 3. Se connecter au serveur Hostinger
ssh u123456789@your-hostinger-server.com

# 4. Créer les répertoires
mkdir -p ~/mcp-rag/{logs,data,rag,backups,config}

# 5. Télécharger le docker-compose
wget https://raw.githubusercontent.com/Feustey/MCP/berty/docker-compose.hostinger.yml

# 6. Démarrer les services
docker-compose -f docker-compose.hostinger.yml up -d
```

## Services Déployés

### 1. MCP API (FastAPI)
- **Port**: 8000
- **Fonctionnalités**: 
  - 22 endpoints RAG et Intelligence
  - Optimisation des frais Lightning
  - Analyse des nœuds
  - Gestion des métriques

### 2. Nginx (Reverse Proxy)
- **Ports**: 80, 443
- **Fonctionnalités**:
  - SSL/TLS termination
  - Load balancing
  - Rate limiting
  - Compression

### 3. Prometheus (Monitoring)
- **Port**: 9090
- **Fonctionnalités**:
  - Collecte de métriques
  - Alertes
  - Rétention des données

### 4. Grafana (Dashboard)
- **Port**: 3000
- **Credentials**: admin/admin123
- **Fonctionnalités**:
  - Dashboards MCP
  - Visualisation des métriques
  - Alertes

### 5. Qdrant (Vector Database)
- **Port**: 6333
- **Fonctionnalités**:
  - Stockage des embeddings RAG
  - Recherche vectorielle
  - Indexation

## Endpoints Disponibles

### Endpoints RAG (13 endpoints)
```
GET  /api/v1/rag/health                    # Santé du système RAG
POST /api/v1/rag/query                     # Requête RAG
GET  /api/v1/rag/documents                 # Liste des documents
POST /api/v1/rag/documents                 # Ajouter un document
GET  /api/v1/rag/documents/{doc_id}        # Récupérer un document
PUT  /api/v1/rag/documents/{doc_id}        # Mettre à jour un document
DELETE /api/v1/rag/documents/{doc_id}      # Supprimer un document
POST /api/v1/rag/ingest                    # Ingestion de documents
GET  /api/v1/rag/search                    # Recherche sémantique
POST /api/v1/rag/generate                  # Génération de contenu
GET  /api/v1/rag/collections               # Collections disponibles
POST /api/v1/rag/collections               # Créer une collection
DELETE /api/v1/rag/collections/{name}      # Supprimer une collection
```

### Endpoints Intelligence (9 endpoints)
```
GET  /api/v1/intelligence/health/intelligence  # Santé du système Intelligence
POST /api/v1/intelligence/analyze/node         # Analyse d'un nœud
POST /api/v1/intelligence/analyze/network      # Analyse du réseau
GET  /api/v1/intelligence/recommendations      # Recommandations
POST /api/v1/intelligence/optimize/fees        # Optimisation des frais
GET  /api/v1/intelligence/patterns             # Patterns détectés
POST /api/v1/intelligence/predict              # Prédictions
GET  /api/v1/intelligence/insights             # Insights
POST /api/v1/intelligence/learn                # Apprentissage
```

## Monitoring et Maintenance

### Vérification de la santé

```bash
# Vérifier l'état des conteneurs
ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml ps'

# Vérifier les logs
ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml logs -f'

# Test de l'API
curl -f https://api.dazno.de/api/v1/health
```

### Mise à jour

```bash
# Pull de la dernière image
ssh $SSH_HOST 'docker pull feustey/dazno:latest'

# Redémarrage des services
ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml restart mcp-api'
```

### Sauvegarde

```bash
# Sauvegarde des données
ssh $SSH_HOST 'cd ~/mcp-rag && tar -czf backup-$(date +%Y%m%d_%H%M%S).tar.gz data/ rag/ logs/'

# Restauration
ssh $SSH_HOST 'cd ~/mcp-rag && tar -xzf backup-YYYYMMDD_HHMMSS.tar.gz'
```

## Dépannage

### Problèmes courants

1. **API non accessible**
   ```bash
   # Vérifier les logs
   ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml logs mcp-api'
   
   # Vérifier la configuration
   ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml config'
   ```

2. **Problèmes de base de données**
   ```bash
   # Vérifier la connexion MongoDB
   ssh $SSH_HOST 'docker exec mcp-api-hostinger python -c "import pymongo; print(pymongo.MongoClient(\"$MONGO_URL\").server_info())"'
   ```

3. **Problèmes SSL**
   ```bash
   # Vérifier les certificats
   ssh $SSH_HOST 'openssl x509 -in /etc/ssl/certs/api.dazno.de.crt -text -noout'
   ```

### Logs et Debugging

```bash
# Logs en temps réel
ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml logs -f --tail=100'

# Logs d'un service spécifique
ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml logs mcp-api'

# Accès au conteneur
ssh $SSH_HOST 'docker exec -it mcp-api-hostinger bash'
```

## Sécurité

### Bonnes pratiques

1. **Variables d'environnement**
   - Ne jamais commiter les secrets dans Git
   - Utiliser des variables d'environnement sécurisées
   - Rotation régulière des clés

2. **Réseau**
   - Limiter l'accès aux ports sensibles
   - Utiliser des réseaux Docker isolés
   - Configuration de firewall

3. **SSL/TLS**
   - Certificats valides et à jour
   - Configuration HTTPS stricte
   - Headers de sécurité

### Audit de sécurité

```bash
# Vérifier les vulnérabilités Docker
ssh $SSH_HOST 'docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image feustey/dazno:latest'

# Vérifier la configuration SSL
curl -I https://api.dazno.de
```

## Performance

### Optimisations

1. **Docker**
   - Utilisation d'images multi-stage
   - Cache des layers Docker
   - Limitation des ressources

2. **Application**
   - Workers multiples
   - Cache Redis
   - Compression des réponses

3. **Base de données**
   - Indexation optimisée
   - Connexions poolées
   - Requêtes optimisées

### Monitoring des performances

```bash
# Métriques système
ssh $SSH_HOST 'docker stats'

# Métriques application
curl https://api.dazno.de/api/v1/metrics

# Dashboard Grafana
# Accès: https://api.dazno.de:3000
```

## Support

### Ressources utiles

- [Documentation API complète](https://api.dazno.de/docs)
- [Dashboard Grafana](https://api.dazno.de:3000)
- [Métriques Prometheus](https://api.dazno.de:9090)
- [Logs en temps réel](https://api.dazno.de/logs)

### Contact

Pour toute question ou problème :
- Issues GitHub: https://github.com/Feustey/MCP/issues
- Documentation: https://github.com/Feustey/MCP/docs

---

**Note**: Ce guide est spécifique au déploiement sur Hostinger. Pour d'autres plateformes, consultez la documentation correspondante. 