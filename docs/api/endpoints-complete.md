# 📚 Documentation Complète des Endpoints MCP - Intelligence RAG
> Dernière mise à jour: 7 janvier 2025

## 🎯 Vue d'ensemble

Cette documentation présente tous les endpoints exposés par l'API MCP pour l'intelligence RAG (Retrieval-Augmented Generation) et l'analyse des nœuds Lightning Network.

## 🔗 Base URL
```
Production: https://api.dazno.de/api/v1
Développement: http://localhost:8000/api/v1
```

## 🔐 Authentification

Tous les endpoints (sauf `/health`) nécessitent une authentification JWT :
```
Authorization: Bearer <jwt_token>
```

---

## 🧠 Endpoints RAG (`/api/v1/rag`)

### 1. **Requête RAG** - `POST /api/v1/rag/query`
Effectue une requête RAG avec contexte Lightning.

**Corps de la requête :**
```json
{
  "query": "Comment optimiser les frais de mon nœud Lightning ?",
  "max_results": 5,
  "context_type": "lightning",
  "include_validation": true
}
```

**Réponse :**
```json
{
  "status": "success",
  "answer": "Analyse détaillée de l'optimisation des frais...",
  "sources": ["doc1", "doc2"],
  "confidence": 0.92,
  "validation": "Validation Ollama du rapport...",
  "processing_time": 1.2
}
```

### 2. **Statistiques RAG** - `GET /api/v1/rag/stats`
Récupère les statistiques détaillées du système RAG.

**Réponse :**
```json
{
  "status": "success",
  "stats": {
    "total_documents": 1250,
    "total_queries": 567,
    "cache_hit_rate": 0.85,
    "average_response_time": 0.8
  },
  "system_info": {
    "total_documents": 1250,
    "total_queries": 567,
    "cache_hit_rate": 0.85,
    "average_response_time": 0.8,
    "last_updated": "2025-01-07T10:00:00Z"
  }
}
```

### 3. **Ingestion de documents** - `POST /api/v1/rag/ingest`
Ingestion de documents dans le système RAG avec métadonnées.

**Corps de la requête :**
```json
{
  "documents": ["Contenu du document 1", "Contenu du document 2"],
  "metadata": {
    "source": "lightning_network_guide",
    "author": "MCP Team"
  },
  "source_type": "manual"
}
```

### 4. **Historique des requêtes** - `GET /api/v1/rag/history`
Récupère l'historique des requêtes RAG avec pagination.

**Paramètres :**
- `limit` (int, optionnel) : Nombre maximum de résultats (défaut: 50)

### 5. **Santé du système RAG** - `GET /api/v1/rag/health`
Vérification complète de la santé du système RAG.

**Réponse :**
```json
{
  "status": "healthy",
  "details": {
    "redis": true,
    "mongo": true,
    "rag_instance": true
  },
  "additional_info": {
    "timestamp": "2025-01-07T10:00:00Z",
    "version": "1.0.0",
    "components": {
      "redis": true,
      "mongo": true,
      "rag_instance": true,
      "embedding_service": true,
      "llm_service": true
    }
  }
}
```

### 6. **Analyse de nœud RAG** - `POST /api/v1/rag/analyze/node`
Analyse complète d'un nœud Lightning avec RAG.

**Corps de la requête :**
```json
{
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "analysis_type": "performance",
  "time_range": "7d",
  "include_recommendations": true
}
```

### 7. **Exécution de workflow** - `POST /api/v1/rag/workflow/execute`
Exécute un workflow RAG spécifique.

**Corps de la requête :**
```json
{
  "workflow_name": "node_analysis_workflow",
  "parameters": {
    "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
  },
  "execute_async": true
}
```

### 8. **Validation de contenu** - `POST /api/v1/rag/validate`
Valide du contenu avec le système RAG.

**Corps de la requête :**
```json
{
  "content": "Configuration de nœud Lightning...",
  "validation_type": "config",
  "criteria": {
    "security_level": "high",
    "performance_threshold": 0.8
  }
}
```

### 9. **Benchmarks** - `POST /api/v1/rag/benchmark`
Exécute des benchmarks avec le système RAG.

**Corps de la requête :**
```json
{
  "benchmark_type": "performance",
  "comparison_nodes": ["node1", "node2", "node3"],
  "metrics": ["fees", "routing", "capacity"]
}
```

### 10. **Liste des assets** - `GET /api/v1/rag/assets/list`
Liste tous les assets RAG disponibles.

### 11. **Récupération d'asset** - `GET /api/v1/rag/assets/{asset_id}`
Récupère un asset RAG spécifique.

### 12. **Vidage du cache** - `POST /api/v1/rag/cache/clear`
Vide le cache RAG.

### 13. **Statistiques du cache** - `GET /api/v1/rag/cache/stats`
Récupère les statistiques du cache RAG.

---

## 🧠 Endpoints Intelligence (`/api/v1/intelligence`)

### 1. **Analyse intelligente de nœud** - `POST /api/v1/intelligence/node/analyze`
Analyse intelligente complète d'un nœud Lightning.

**Corps de la requête :**
```json
{
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "analysis_depth": "comprehensive",
  "include_network_context": true,
  "include_historical_data": true,
  "include_predictions": false
}
```

**Réponse :**
```json
{
  "status": "success",
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "analysis_depth": "comprehensive",
  "intelligence_analysis": "Analyse intelligente détaillée...",
  "validation": "Validation de l'analyse...",
  "key_insights": ["Insight 1", "Insight 2"],
  "recommendations": ["Recommandation 1", "Recommandation 2"],
  "risk_assessment": {
    "risk_level": "medium",
    "risk_factors": ["facteur1", "facteur2"]
  },
  "performance_metrics": {
    "score": 0.85,
    "efficiency": 0.92
  },
  "network_position": {
    "centrality": 0.75,
    "connectivity": 0.88
  },
  "timestamp": "2025-01-07T10:00:00Z"
}
```

### 2. **Analyse intelligente du réseau** - `POST /api/v1/intelligence/network/analyze`
Analyse intelligente du réseau Lightning.

**Corps de la requête :**
```json
{
  "network_scope": "global",
  "analysis_type": "topology",
  "include_metrics": ["centrality", "connectivity", "liquidity"],
  "time_range": "7d"
}
```

### 3. **Recommandations d'optimisation** - `POST /api/v1/intelligence/optimization/recommend`
Recommandations d'optimisation intelligentes.

**Corps de la requête :**
```json
{
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "optimization_target": "fees",
  "constraints": {
    "min_capacity": 1000000,
    "max_risk": 0.3
  },
  "risk_tolerance": "medium",
  "include_impact_analysis": true
}
```

### 4. **Génération de prédictions** - `POST /api/v1/intelligence/prediction/generate`
Génération de prédictions intelligentes.

**Corps de la requête :**
```json
{
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "prediction_type": "performance",
  "time_horizon": "30d",
  "confidence_level": 0.8
}
```

### 5. **Analyse comparative** - `POST /api/v1/intelligence/comparative/analyze`
Analyse comparative intelligente entre nœuds.

**Corps de la requête :**
```json
{
  "node_pubkeys": ["node1", "node2", "node3"],
  "comparison_metrics": ["fees", "routing", "capacity"],
  "benchmark_type": "peer_group",
  "include_rankings": true
}
```

### 6. **Configuration d'alertes intelligentes** - `POST /api/v1/intelligence/alerts/configure`
Configuration d'alertes intelligentes.

**Corps de la requête :**
```json
{
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "alert_types": ["performance_degradation", "fee_anomaly", "capacity_issue"],
  "thresholds": {
    "performance_threshold": 0.7,
    "fee_anomaly_threshold": 0.3
  },
  "notification_channels": ["api", "email"]
}
```

### 7. **Résumé des insights** - `GET /api/v1/intelligence/insights/summary`
Résumé des insights d'intelligence.

**Réponse :**
```json
{
  "status": "success",
  "intelligence_summary": "Résumé des insights clés...",
  "key_trends": ["Tendance 1", "Tendance 2"],
  "optimization_opportunities": ["Opportunité 1", "Opportunité 2"],
  "identified_risks": ["Risque 1", "Risque 2"],
  "strategic_recommendations": ["Recommandation 1", "Recommandation 2"],
  "global_metrics": {
    "network_health": 0.85,
    "average_node_score": 0.72
  },
  "timestamp": "2025-01-07T10:00:00Z"
}
```

### 8. **Workflow automatisé** - `POST /api/v1/intelligence/workflow/automated`
Exécution d'un workflow d'intelligence automatisé.

**Réponse :**
```json
{
  "status": "started",
  "task_id": "intelligence_workflow_20250107_100000",
  "workflow_type": "automated_intelligence",
  "message": "Workflow d'intelligence démarré en arrière-plan",
  "estimated_duration": "5-10 minutes",
  "timestamp": "2025-01-07T10:00:00Z"
}
```

### 9. **Santé du système d'intelligence** - `GET /api/v1/intelligence/health/intelligence`
Santé du système d'intelligence.

**Réponse :**
```json
{
  "status": "healthy",
  "intelligence_components": {
    "rag_system": true,
    "prediction_engine": true,
    "optimization_engine": true,
    "alert_system": true,
    "comparative_analysis": true,
    "network_intelligence": true
  },
  "last_updated": "2025-01-07T10:00:00Z",
  "version": "1.0.0"
}
```

---

## 🔧 Endpoints Système

### 1. **Santé générale** - `GET /api/v1/health`
Vérification de santé générale.

### 2. **Statut du système** - `GET /api/v1/status`
Récupère le statut du système avec informations utilisateur.

### 3. **Métriques admin** - `GET /api/v1/admin/metrics`
Récupère les métriques système (admin uniquement).

---

## 📊 Codes de réponse

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Non autorisé |
| 404 | Ressource non trouvée |
| 500 | Erreur serveur interne |
| 503 | Service indisponible |

---

## 🔒 Sécurité

### Authentification
- Tous les endpoints nécessitent un token JWT valide
- Format : `Authorization: Bearer <token>`

### Permissions
- **rag**: Accès aux fonctionnalités RAG
- **intelligence**: Accès aux fonctionnalités d'intelligence
- **admin**: Accès administrateur complet

### Rate Limiting
- 100 requêtes par minute par utilisateur
- 1000 requêtes par heure par utilisateur

---

## 📈 Monitoring

### Métriques disponibles
- Temps de réponse moyen
- Taux de succès des requêtes
- Utilisation du cache RAG
- Nombre d'analyses d'intelligence
- Erreurs par endpoint

### Logs
- Toutes les requêtes sont loggées
- Erreurs détaillées avec contexte
- Métriques de performance

---

## 🚀 Déploiement

### Variables d'environnement requises
```bash
# Base de données
MONGO_URL=mongodb://...
REDIS_URL=redis://...

# Sécurité
JWT_SECRET_KEY=...
SECRET_KEY=...

# Services externes
LNBITS_URL=...
LNBITS_ADMIN_KEY=...

# RAG et Intelligence
ANTHROPIC_API_KEY=...
```

### Health Checks
- `/api/v1/health` - Santé générale
- `/api/v1/rag/health` - Santé RAG
- `/api/v1/intelligence/health/intelligence` - Santé Intelligence

---

## 📝 Notes d'utilisation

1. **Performance** : Les requêtes RAG peuvent prendre 1-3 secondes
2. **Cache** : Les réponses sont mises en cache pour améliorer les performances
3. **Validation** : Toutes les analyses sont validées par Ollama
4. **Asynchrone** : Les workflows longs sont exécutés en arrière-plan
5. **Monitoring** : Toutes les métriques sont collectées pour l'optimisation

---

## 🔗 Liens utiles

- **Documentation Swagger** : `https://api.dazno.de/docs`
- **Documentation ReDoc** : `https://api.dazno.de/redoc`
- **Statut du service** : `https://api.dazno.de/api/v1/health`
- **Support** : support@dazno.de 
