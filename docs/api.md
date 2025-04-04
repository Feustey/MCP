# Documentation API

## Vue d'ensemble

L'API de MCP fournit des endpoints RESTful pour interagir avec le système RAG. Tous les endpoints sont asynchrones et retournent des réponses au format JSON.

## Authentification

L'authentification se fait via les variables d'environnement :
```env
OPENAI_API_KEY=votre_clé_api_openai
```

## Endpoints

### Documents

#### `POST /documents`

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

#### `GET /documents/{document_id}`

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

### Requêtes

#### `POST /query`

Soumet une requête au système RAG.

**Corps de la requête :**
```json
{
    "query": "Votre question ici ?",
    "context_docs": ["doc1.txt", "doc2.txt"],  // Optionnel
    "max_tokens": 2000  // Optionnel
}
```

**Réponse :**
```json
{
    "response": "Réponse générée",
    "sources": ["doc1.txt", "doc2.txt"],
    "processing_time": 1.5,
    "cache_hit": false
}
```

### Historique

#### `GET /history`

Récupère l'historique des requêtes.

**Paramètres de requête :**
- `limit` : Nombre maximum de requêtes à retourner (défaut: 10)
- `offset` : Nombre de requêtes à ignorer (défaut: 0)

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
            "cache_hit": false
        }
    ],
    "total": 100,
    "offset": 0,
    "limit": 10
}
```

### Statistiques

#### `GET /stats`

Récupère les statistiques du système.

**Réponse :**
```json
{
    "total_documents": 100,
    "total_queries": 500,
    "average_processing_time": 1.5,
    "cache_hit_rate": 0.8,
    "last_updated": "2024-02-20T10:00:00Z"
}
```

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
- Requêtes : 60/minute
- Ingestion de documents : 30/minute
- Statistiques : 300/minute

## Versioning

L'API est versionnée via le préfixe de l'URL :
- Version actuelle : `/v1/`
- Exemple : `https://api.example.com/v1/query`

## Webhooks

Le système supporte les webhooks pour les événements importants :
- Nouveau document ingéré
- Requête traitée
- Erreur système

Configuration des webhooks :
```json
{
    "url": "https://votre-webhook.com/endpoint",
    "events": ["document.created", "query.processed"],
    "secret": "votre_secret"
}
``` 