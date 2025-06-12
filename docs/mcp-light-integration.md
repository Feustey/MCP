# Intégration MCP-Light - API d'Intelligence Lightning

> **Dernière mise à jour**: 15 janvier 2025

## 🎯 Vue d'ensemble

Cette documentation décrit l'intégration des fonctionnalités avancées de **MCP-Light** dans le projet principal MCP, incluant l'API d'intelligence artificielle pour l'optimisation de nœuds Lightning Network et le déploiement automatisé via Nixpacks sur Hostinger.

## 🚀 Nouvelles Fonctionnalités

### 1. **API d'Intelligence Lightning**
- **Endpoints spécialisés** pour l'analyse de nœuds
- **Intégration OpenAI** pour des recommandations contextuelles
- **Client Sparkseer amélioré** avec enrichissement de données
- **Cache Redis haute performance** avec TTL configurables

### 2. **Architecture Microservices**
- **Clients modulaires** (OpenAI, Sparkseer, LNBits)
- **Gestionnaire de cache** avec fallback gracieux
- **Schémas Pydantic** pour la validation stricte
- **Métriques de performance** en temps réel

### 3. **Déploiement Automatisé**
- **Configuration Nixpacks** optimisée pour production
- **Script de déploiement** automatisé pour Hostinger
- **Health checks** et monitoring intégrés
- **Rollback automatique** en cas d'échec

## 📋 Endpoints API Principaux

### Health Check
```http
GET /api/v1/health
```
**Réponse :**
```json
{
  "status": "healthy",
  "services": {
    "sparkseer_api": "connected",
    "openai_api": "connected",
    "cache": "connected",
    "lnbits_api": "connected"
  },
  "version": "1.0.0",
  "cache_stats": {},
  "uptime_seconds": 3600
}
```

### Informations de Nœud
```http
GET /api/v1/node/{pubkey}/info?include_historical=true&use_cache=true
```
**Réponse :**
```json
{
  "pubkey": "03bd7efb...",
  "node_info": {
    "alias": "Lightning Node",
    "color": "#3399ff",
    "features": {}
  },
  "metrics": {
    "total_channels": 25,
    "total_capacity": 50000000,
    "routing_revenue_24h": 1500
  },
  "channels": [],
  "network_position": {},
  "timestamp": "2025-01-15T10:30:00Z",
  "source": "sparkseer+lnbits",
  "cache_hit": true
}
```

### Recommandations Techniques
```http
GET /api/v1/node/{pubkey}/recommendations?category=revenue&priority=high
```
**Réponse :**
```json
{
  "pubkey": "03bd7efb...",
  "recommendations": [
    {
      "type": "fee_adjustment",
      "category": "revenue",
      "action": "Augmenter les frais sur le canal vers ACINQ",
      "reason": "Ce canal route 40% de votre volume avec des frais sous la moyenne",
      "priority": "high",
      "estimated_impact": "Revenus +15%"
    }
  ],
  "total_count": 5,
  "by_category": {"revenue": 3, "connectivity": 2},
  "by_priority": {"high": 2, "medium": 3}
}
```

### Actions Prioritaires (IA)
```http
POST /api/v1/node/{pubkey}/priorities
Content-Type: application/json

{
  "context": "intermediate",
  "goals": ["routing_revenue", "connectivity"],
  "max_actions": 5,
  "budget_limit": 1000000
}
```
**Réponse :**
```json
{
  "pubkey": "03bd7efb...",
  "priority_actions": [
    {
      "priority": 1,
      "action": "Optimiser les frais sur les canaux haute capacité",
      "reasoning": "Analyse basée sur les métriques MCP montre un potentiel de +20% de revenus",
      "impact": "Augmentation estimée de 1500 sats/jour",
      "difficulty": "easy",
      "timeframe": "immediate",
      "command": "lncli updatechanpolicy --base_fee_msat=1000 --fee_rate=0.001",
      "estimated_cost": 0
    }
  ],
  "openai_analysis": "Votre nœud montre une excellente connectivité...",
  "key_metrics": ["routing_revenue_24h", "channel_balance_ratio", "fee_efficiency"],
  "total_estimated_cost": 0,
  "model_used": "gpt-4o-mini"
}
```

### Analyse en Masse
```http
POST /api/v1/nodes/bulk-analysis
Content-Type: application/json

{
  "pubkeys": ["03bd7efb...", "02abcd..."],
  "analysis_types": ["basic", "recommendations"],
  "use_cache": true
}
```

### Métriques de Performance
```http
GET /api/v1/metrics
```
**Réponse :**
```json
{
  "request_count": 1250,
  "average_response_time": 0.85,
  "cache_hit_ratio": 0.78,
  "error_rate": 0.02,
  "last_updated": "2025-01-15T10:30:00Z"
}
```

## 🔧 Configuration

### Variables d'Environnement

```bash
# APIs externes
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
SPARKSEER_API_KEY=your_sparkseer_key
SPARKSEER_BASE_URL=https://api.sparkseer.space

# LNBits
LNBITS_URL=https://your-lnbits.com
LNBITS_API_KEY=your_lnbits_key

# Cache Redis
REDIS_URL=redis://localhost:6379
CACHE_TTL=300
CACHE_NAMESPACE=mcp

# Sécurité
SECRET_KEY=your_secret_key
CORS_ORIGINS=https://dazno.de,https://api.dazno.de
ALLOWED_HOSTS=api.dazno.de

# Production
ENVIRONMENT=production
PORT=8000
WORKERS=2
LOG_LEVEL=INFO
```

### Fichier nixpacks.toml

Le projet inclut une configuration Nixpacks optimisée pour le déploiement sur Hostinger :

```toml
[metadata]
name = "mcp-lightning-optimizer"
version = "1.0.0"

[providers]
python = "3.9"

[start]
cmd = "gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT"

[healthcheck]
path = "/api/v1/health"
interval = "30s"
timeout = "10s"
retries = 3
```

## 🚀 Déploiement sur Hostinger

### Prérequis

1. **Compte Hostinger** avec API activée
2. **Token API Hostinger** configuré
3. **Clés API** (OpenAI, Sparkseer) disponibles
4. **Git repository** accessible

### Déploiement Automatique

```bash
# Variables d'environnement requises
export HOSTINGER_API_TOKEN="your_hostinger_token"
export OPENAI_API_KEY="your_openai_key"
export HOSTINGER_DOMAIN="api.dazno.de"

# Déploiement
./scripts/deploy-hostinger.sh
```

### Déploiement Manuel

```bash
# 1. Configuration
cp env.example .env
# Éditer .env avec vos clés

# 2. Build local (optionnel)
nixpacks build . --name mcp-lightning-optimizer

# 3. Test local
docker run -p 8000:8000 --env-file .env mcp-lightning-optimizer

# 4. Déploiement via interface Hostinger
# Upload du code source et configuration Nixpacks
```

## 🏗️ Architecture Technique

### Structure des Clients

```
src/clients/
├── openai_client.py      # Client IA avec retry et parsing
├── sparkseer_client.py   # Client Sparkseer avec enrichissement
└── lnbits_client.py      # Client existant LNBits
```

### Gestionnaire de Cache

```
src/utils/
└── cache_manager.py      # Cache Redis avec patterns avancés
```

### Modèles de Données

```
app/models/
└── mcp_schemas.py        # Schémas Pydantic complets
```

### Endpoints d'Intelligence

```
app/routes/
└── intelligence.py       # API endpoints MCP-Light
```

## 📊 Fonctionnalités Avancées

### 1. **Cache Intelligent**
- **TTL par type** de données (node_info: 5min, recommendations: 10min)
- **Namespace isolation** pour éviter les collisions
- **Fallback gracieux** si Redis n'est pas disponible
- **Statistiques** en temps réel

### 2. **Clients Robustes**
- **Retry automatique** avec backoff exponentiel
- **Timeout configurables** par service
- **Gestion d'erreurs** granulaire
- **Enrichissement** de données multi-sources

### 3. **IA Contextuelle**
- **Prompts optimisés** pour Lightning Network
- **Parsing structuré** des réponses OpenAI
- **Filtrage** par budget et délai
- **Métriques de suivi** automatiques

### 4. **Monitoring Intégré**
- **Health checks** multi-services
- **Métriques de performance** temps réel
- **Logs structurés** en JSON
- **Alertes** via webhooks

## 🔒 Sécurité

### Protection API
- **CORS configuré** pour domaines autorisés
- **TrustedHost middleware** pour Hostinger
- **Validation stricte** avec Pydantic
- **Rate limiting** via cache

### Données Sensibles
- **Variables d'environnement** pour les clés
- **Logs anonymisés** (pubkeys tronquées)
- **Connexions sécurisées** HTTPS uniquement
- **Secrets rotation** supportée

## 🧪 Tests et Validation

### Tests Automatiques

```bash
# Test de l'API complète
python mcp-light/test_api.py

# Test des endpoints MCP
curl https://api.dazno.de/api/v1/health
curl https://api.dazno.de/api/v1/node/{pubkey}/info
```

### Validation de Performance

```bash
# Métriques en temps réel
curl https://api.dazno.de/api/v1/metrics

# Cache statistics
curl https://api.dazno.de/api/v1/health | jq '.cache_stats'
```

## 📈 Évolutions Future

### Roadmap
1. **Rate limiting avancé** par utilisateur
2. **Métriques Prometheus** natifs
3. **Tests unitaires** complets
4. **Documentation Swagger** enrichie
5. **Support multi-providers** (Amboss, etc.)

### Intégrations Planifiées
- **Webhook notifications** pour les recommandations
- **Dashboard temps réel** avec métriques
- **API versioning** (v2) avec nouvelles fonctionnalités
- **Machine learning** pour prédictions avancées

## 🆘 Troubleshooting

### Problèmes Fréquents

**Cache Redis non disponible**
```bash
# Vérifier la connexion
redis-cli ping

# Logs de débogage
docker logs redis-container
```

**OpenAI rate limiting**
```bash
# Vérifier les quotas
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/usage

# Ajuster le modèle
export OPENAI_MODEL=gpt-3.5-turbo
```

**Sparkseer timeout**
```bash
# Test de connectivité
curl -H "x-api-key: $SPARKSEER_API_KEY" https://api.sparkseer.space/v1/network/summary
```

### Logs de Débogage

```bash
# Logs application
tail -f logs/mcp.log

# Logs Hostinger
hostinger logs --project mcp-lightning-optimizer

# Métriques détaillées
curl https://api.dazno.de/api/v1/health?verbose=true
```

## 📞 Support

- **Documentation API** : https://api.dazno.de/docs
- **Repository** : https://github.com/dazno/mcp
- **Issues** : GitHub Issues
- **Monitoring** : https://api.dazno.de/api/v1/health

---

**Version MCP-Light Integration** : 1.0.0  
**Dernière mise à jour** : 15 janvier 2025  
**Compatibilité** : Python 3.9+, FastAPI 0.111+, Redis 7+ 