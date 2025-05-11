# Documentation API
> Dernière mise à jour: 7 mai 2025

## Vue d'ensemble

L'API de MCP fournit des endpoints RESTful pour interagir avec deux systèmes principaux :
1. **Système RAG avancé** - Pour les requêtes question-réponse et la gestion des connaissances
2. **Intégration Lightning Network** - Pour l'analyse et l'optimisation des nœuds Lightning

Tous les endpoints sont asynchrones et retournent des réponses au format JSON.

## Authentification

### Authentification API standard

L'authentification se fait via token JWT inclus dans l'en-tête Authorization :
```http
Authorization: Bearer <votre_jwt_token>
```

### Authentification pour accès Lightning

Pour les endpoints Lightning Network, des credentials supplémentaires peuvent être requis :
```env
# Pour accès à un nœud local
LND_MACAROON_HEX=votre_macaroon_hex
LND_TLS_CERT_PATH=chemin_vers_tls.cert

# Pour API keys services externes
AMBOSS_API_KEY=votre_clé_api_amboss
LNROUTER_API_KEY=votre_clé_api_lnrouter
```

## Endpoints RAG

### Documents

#### `POST /rag/documents`

Ingère un nouveau document dans le système.

**Corps de la requête :**
```json
{
    "content": "Contenu du document",
    "source": "document.txt",
    "metadata": {
        "auteur": "John Doe",
        "date": "2024-02-20"
    }
}
```

**Réponse :**
```json
{
    "id": "document_id",
    "status": "success",
    "message": "Document ingéré avec succès"
}
```

#### `POST /rag/documents/batch`

Ingère plusieurs documents en une seule requête.

**Corps de la requête :**
```json
{
    "documents": [
        {
            "content": "Contenu du document 1",
            "source": "doc1.txt",
            "metadata": { "categorie": "technique" }
        },
        {
            "content": "Contenu du document 2",
            "source": "doc2.txt",
            "metadata": { "categorie": "business" }
        }
    ]
}
```

#### `GET /rag/documents/{document_id}`

Récupère un document par son ID.

**Réponse :**
```json
{
    "id": "document_id",
    "content": "Contenu du document",
    "source": "document.txt",
    "metadata": {
        "auteur": "John Doe",
        "date": "2024-02-20"
    },
    "created_at": "2024-02-20T10:00:00Z"
}
```

### Requêtes avancées

#### `POST /rag/query`

Soumet une requête au système RAG avancé.

**Corps de la requête :**
```json
{
    "query": "Votre question ici ?",
    "search_type": "hybrid",  // Options: "vector", "keyword", "hybrid"
    "vector_weight": 0.7,     // Poids relatif recherche vectorielle (0.0-1.0)
    "expand_query": true,     // Utiliser l'expansion de requête
    "context_docs": ["doc1.txt", "doc2.txt"],  // Optionnel
    "max_tokens": 2000,       // Optionnel
    "use_cache": true,        // Utiliser le cache multi-niveau
    "evaluation": false       // Évaluer la réponse automatiquement
}
```

**Réponse :**
```json
{
    "response": "Réponse générée",
    "sources": [
        {
            "document_id": "doc1_id",
            "source": "doc1.txt",
            "relevance_score": 0.92
        },
        {
            "document_id": "doc2_id",
            "source": "doc2.txt",
            "relevance_score": 0.85
        }
    ],
    "processing_time": 1.5,
    "cache_hit": false,
    "cache_level": null,
    "expanded_queries": ["requête reformulée 1", "requête reformulée 2"],
    "evaluation": null
}
```

#### `POST /rag/evaluate`

Évalue la qualité d'une réponse RAG existante.

**Corps de la requête :**
```json
{
    "query_id": "query_id",
    "metrics": ["faithfulness", "relevance", "coherence", "completeness"]
}
```

**Réponse :**
```json
{
    "evaluation": {
        "faithfulness": 0.92,
        "relevance": 0.85,
        "coherence": 0.95,
        "completeness": 0.78,
        "overall": 0.88
    },
    "feedback": "La réponse est très pertinente et cohérente, mais pourrait être plus complète."
}
```

#### `POST /rag/expansion`

Génère des reformulations d'une requête pour améliorer la récupération.

**Corps de la requête :**
```json
{
    "query": "Comment optimiser un nœud Lightning ?",
    "count": 3,
    "diversity": 0.7
}
```

**Réponse :**
```json
{
    "original_query": "Comment optimiser un nœud Lightning ?",
    "expansions": [
        "Quelles sont les meilleures pratiques pour configurer un nœud Lightning Network ?",
        "Comment améliorer les performances de routage d'un nœud Lightning ?",
        "Quels paramètres ajuster pour optimiser la rentabilité d'un nœud Lightning ?"
    ]
}
```

### Cache

#### `GET /rag/cache/stats`

Récupère les statistiques du cache multi-niveau.

**Réponse :**
```json
{
    "cache_l1_size": 256,
    "cache_l2_size": 1024,
    "hit_rate_l1": 0.75,
    "hit_rate_l2": 0.65,
    "overall_hit_rate": 0.82,
    "average_response_time_hit": 0.12,
    "average_response_time_miss": 1.8
}
```

#### `POST /rag/cache/invalidate`

Invalide des entrées de cache spécifiques.

**Corps de la requête :**
```json
{
    "query_patterns": ["optimisation*", "nœud lightning*"],
    "document_ids": ["doc123", "doc456"],
    "level": "all"  // Options: "l1", "l2", "all"
}
```

### Historique

#### `GET /rag/history`

Récupère l'historique des requêtes RAG.

**Paramètres de requête :**
- `limit` : Nombre maximum de requêtes à retourner (défaut: 10)
- `offset` : Nombre de requêtes à ignorer (défaut: 0)
- `filter` : Filtre par texte (optionnel)

**Réponse :**
```json
{
    "queries": [
        {
            "id": "query_id",
            "query": "Question posée",
            "response": "Réponse générée",
            "timestamp": "2024-02-20T10:00:00Z",
            "processing_time": 1.5,
            "cache_hit": false,
            "evaluation_score": 0.88
        }
    ],
    "total": 100,
    "offset": 0,
    "limit": 10
}
```

### Statistiques

#### `GET /rag/stats`

Récupère les statistiques du système RAG.

**Réponse :**
```json
{
    "total_documents": 100,
    "total_queries": 500,
    "average_processing_time": 1.5,
    "cache_hit_rate": 0.8,
    "average_evaluation_score": 0.87,
    "popular_topics": [
        {"topic": "Lightning Network", "count": 120},
        {"topic": "Optimisation", "count": 85}
    ],
    "last_updated": "2024-02-20T10:00:00Z"
}
```

## Endpoints Lightning Network

### Nœuds

#### `GET /nodes/{node_id}`

Récupère les informations d'un nœud Lightning.

**Réponse :**
```json
{
    "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "alias": "FEUSTEY⚡",
    "color": "#ff9900",
    "channels": [
        {
            "channel_id": "123456789",
            "capacity": 5000000,
            "local_balance": 2500000,
            "remote_balance": 2500000,
            "local_fee_rate": 500,
            "remote_fee_rate": 1000
        }
    ],
    "metrics": {
        "centrality": 0.75,
        "uptime": 0.992,
        "forwarded_sats_24h": 1500000
    }
}
```

#### `GET /nodes/enriched/{node_id}`

Récupère les données enrichies multi-sources d'un nœud.

**Paramètres de requête :**
- `sources` : Sources à inclure (ex: "amboss,lnrouter,lnd")

**Réponse :**
```json
{
    "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "alias": "FEUSTEY⚡",
    "basic_info": {
        "color": "#ff9900",
        "public_key": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
    },
    "amboss_data": {
        "uptime": 0.992,
        "reputation_score": 0.87,
        "community_tags": ["reliable", "good_connector"]
    },
    "lnrouter_data": {
        "centrality": {
            "betweenness": 0.78,
            "eigenvector": 0.65,
            "degree": 0.82
        },
        "routing_potential": 0.75
    },
    "lnd_data": {
        "channels": 24,
        "total_capacity": 50000000,
        "avg_fee_rate": 500,
        "forwarding_history": {
            "total_forwarded_24h": 1500000,
            "success_rate": 0.95
        }
    },
    "composite_scores": {
        "reliability": 0.91,
        "routing_potential": 0.83,
        "fee_efficiency": 0.72
    }
}
```

#### `POST /nodes/analyze`

Analyse un nœud Lightning pour obtenir des recommandations.

**Corps de la requête :**
```json
{
    "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "analysis_type": "complete",  // Options: "basic", "complete", "custom"
    "custom_metrics": ["centrality", "fee_efficiency"]  // Si analysis_type est "custom"
}
```

**Réponse :**
```json
{
    "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "alias": "FEUSTEY⚡",
    "analysis": {
        "strengths": [
            "Forte centralité dans le réseau",
            "Bonne réputation"
        ],
        "weaknesses": [
            "Politique de frais sous-optimale",
            "Déséquilibre dans certains canaux"
        ],
        "recommendations": [
            "Augmenter le fee_rate des canaux X, Y, Z",
            "Rééquilibrer les canaux A, B, C"
        ]
    },
    "metrics": {
        "overall_score": 0.78,
        "detailed_scores": {
            "centrality": 0.85,
            "fee_efficiency": 0.65,
            "balance_quality": 0.70
        }
    }
}
```

### Tests A/B

#### `POST /nodes/test/scenario`

Crée un scénario de test A/B pour un nœud.

**Corps de la requête :**
```json
{
    "base_scenario": {
        "name": "Configuration heuristique optimisée",
        "fee_structure": {
            "base_fee_msat": 2000,
            "fee_rate": 300
        },
        "channel_policy": {
            "target_local_ratio": 0.55,
            "rebalance_threshold": 0.25
        }
    },
    "test_duration_minutes": 60,
    "metrics_to_track": ["sats_forwarded", "success_rate", "revenue"]
}
```

**Réponse :**
```json
{
    "test_id": "test_123",
    "scenarios": [
        {
            "id": "heuristic_78f45557",
            "type": "heuristic",
            "name": "Configuration heuristique optimisée"
        },
        {
            "id": "random_edbc385b",
            "type": "random",
            "name": "Configuration aléatoire"
        },
        {
            "id": "baseline_2b90a08b",
            "type": "baseline",
            "name": "Configuration de base"
        }
    ],
    "status": "created",
    "start_time": "2024-02-20T10:00:00Z",
    "end_time": "2024-02-20T11:00:00Z"
}
```

#### `GET /nodes/test/{test_id}/results`

Récupère les résultats d'un test A/B.

**Réponse :**
```json
{
    "test_id": "test_123",
    "status": "completed",
    "start_time": "2024-02-20T10:00:00Z",
    "end_time": "2024-02-20T11:00:00Z",
    "winning_scenario": {
        "id": "heuristic_78f45557",
        "type": "heuristic",
        "score": 0.85
    },
    "results": [
        {
            "scenario_id": "heuristic_78f45557",
            "metrics": {
                "sats_forwarded": 50000,
                "success_rate": 0.95,
                "revenue": 500
            },
            "score": 0.85
        },
        {
            "scenario_id": "random_edbc385b",
            "metrics": {
                "sats_forwarded": 30000,
                "success_rate": 0.90,
                "revenue": 300
            },
            "score": 0.65
        },
        {
            "scenario_id": "baseline_2b90a08b",
            "metrics": {
                "sats_forwarded": 40000,
                "success_rate": 0.92,
                "revenue": 400
            },
            "score": 0.75
        }
    ]
}
```

### Réseau Lightning

#### `GET /network/stats`

Récupère les statistiques du réseau Lightning.

**Réponse :**
```json
{
    "total_nodes": 10000,
    "total_channels": 50000,
    "total_capacity": 5000000000,
    "average_node_capacity": 5000000,
    "top_nodes": [
        {
            "node_id": "node_1",
            "alias": "ACINQ",
            "centrality": 0.95
        },
        {
            "node_id": "node_2",
            "alias": "Bitfinex",
            "centrality": 0.92
        }
    ],
    "fee_statistics": {
        "average_base_fee": 1000,
        "average_fee_rate": 500,
        "median_fee_rate": 400
    }
}
```

## API Intégrée RAG + Lightning

### `POST /integrated/node_query`

Soumet une requête combinant RAG et données de nœuds Lightning.

**Corps de la requête :**
```json
{
    "query": "Comment optimiser mon nœud Lightning pour améliorer la rentabilité ?",
    "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "include_node_data": true,
    "context_preference": "recent"  // Options: "recent", "all", "technical"
}
```

**Réponse :**
```json
{
    "response": "Pour optimiser votre nœud FEUSTEY⚡ et améliorer sa rentabilité, plusieurs leviers sont possibles. D'après l'analyse de votre nœud, voici des recommandations personnalisées: [recommandations détaillées]",
    "sources": [
        {
            "document_id": "doc1_id",
            "source": "lightning_optimization.md",
            "relevance_score": 0.92
        }
    ],
    "node_data_summary": {
        "alias": "FEUSTEY⚡",
        "total_capacity": 50000000,
        "current_fee_policy": {
            "avg_base_fee": 1000,
            "avg_fee_rate": 300
        },
        "key_metrics": {
            "centrality": 0.75,
            "forwarding_efficiency": 0.68
        }
    },
    "recommendations": [
        {
            "action": "Augmenter fee_rate pour canaux X, Y, Z",
            "expected_impact": "Augmentation revenue ~15%",
            "confidence": 0.85
        },
        {
            "action": "Ajouter canal avec nœud ABC",
            "expected_impact": "Amélioration centralité ~10%",
            "confidence": 0.78
        }
    ]
}
```

## Flux et Workflows

### Workflow RAG Avancé

Le flux typique d'une requête RAG avancée est le suivant :

1. **Réception de la requête** : Le client envoie une requête à `/rag/query`
2. **Vérification du cache L1** : Le système vérifie si la réponse est déjà en cache
3. **Expansion de requête** : Si nécessaire, la requête est reformulée et étendue
4. **Vérification du cache L2** : Le système vérifie si des résultats de recherche sont en cache
5. **Recherche hybride** : Combinaison de recherche vectorielle et lexicale
6. **Reranking** : Reclassement des résultats de recherche
7. **Génération de réponse** : Création d'une réponse basée sur le contexte récupéré
8. **Évaluation** : Si demandé, évaluation automatique de la qualité de la réponse
9. **Mise en cache** : Stockage de la réponse et des résultats intermédiaires
10. **Retour au client** : Envoi de la réponse avec métadonnées

### Workflow d'Optimisation Lightning Network

Le flux typique d'optimisation d'un nœud :

1. **Analyse initiale** : Collecte des données via `/nodes/analyze`
2. **Création de scénarios** : Génération de scénarios A/B via `/nodes/test/scenario`
3. **Exécution des tests** : Application des configurations et collecte de métriques
4. **Évaluation des résultats** : Récupération des résultats via `/nodes/test/{test_id}/results`
5. **Optimisation** : Application des configurations gagnantes
6. **Surveillance** : Monitoring continu des performances du nœud

### Workflow Intégré

L'intégration entre RAG et Lightning permet :

1. **Requêtes contextuelles** : Questions sur un nœud spécifique via `/integrated/node_query`
2. **Recommandations personnalisées** : Conseils basés sur les données du nœud et la connaissance RAG
3. **Apprentissage continu** : Ingestion de nouvelles données sur le réseau Lightning
4. **Boucle de feedback** : Amélioration des réponses basée sur les performances des recommandations

## Gestion des erreurs

Toutes les erreurs suivent le format :
```json
{
    "error": "Description de l'erreur",
    "code": "ERROR_CODE",
    "details": {}  // Détails supplémentaires si disponibles
}
```

### Codes d'erreur courants

- `400` : Requête invalide
- `401` : Non authentifié
- `403` : Accès refusé
- `404` : Ressource non trouvée
- `429` : Trop de requêtes
- `500` : Erreur serveur

## Rate Limiting

Les limites de taux sont configurées par endpoint :
- Requêtes RAG : 60/minute
- Ingestion de documents : 30/minute
- Statistiques : 300/minute
- Analyse de nœuds : 30/minute
- Tests A/B : 5/minute

## Versioning

L'API est versionnée via le préfixe de l'URL :
- Version actuelle : `/v1/`
- Exemple : `https://api.example.com/v1/rag/query`

## Compatibilité

- LND: Compatible avec la version 0.16.1-beta et supérieure
- Core Lightning: Versions 0.10.2 et supérieures
