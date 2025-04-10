# Documentation API

## Vue d'ensemble

L'API de MCP fournit des endpoints RESTful pour interagir avec le système RAG. Tous les endpoints sont asynchrones et retournent des réponses au format JSON.

## Authentification

L'authentification se fait via JWT (JSON Web Tokens). Tous les endpoints (sauf `/health`) nécessitent un token JWT valide dans l'en-tête de la requête.

## Endpoints

### Requêtes RAG

#### `POST /query`

Soumet une requête au système RAG.

**Paramètres :**
- `query_text` (string) : Le texte de la requête

**Réponse :**
```json
{
    "response": "Réponse générée par le système RAG"
}
```

### Ingestion de Documents

#### `POST /ingest`

Ingère des documents depuis un répertoire spécifié.

**Paramètres :**
- `directory` (string) : Chemin du répertoire contenant les documents à ingérer

**Réponse :**
```json
{
    "status": "success" // ou "error"
}
```

### Statistiques

#### `GET /stats`

Récupère les statistiques du système.

**Réponse :**
```json
{
    // Statistiques détaillées du système
}
```

### Historique des Requêtes

#### `GET /recent-queries`

Récupère l'historique des requêtes récentes.

**Paramètres de requête :**
- `limit` (integer, optionnel) : Nombre maximum de requêtes à retourner (défaut: 10)

**Réponse :**
```json
[
    {
        // Détails de la requête
    }
]
```

### Santé du Système

#### `GET /health`

Vérifie l'état de santé de l'application.

**Réponse :**
```json
{
    "status": "healthy"
}
```

## Gestion des erreurs

Toutes les erreurs suivent le format standard FastAPI :
```json
{
    "detail": "Description de l'erreur"
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

Le système implémente un rate limiting via le `RateLimiter` qui utilise le `CacheManager` pour gérer les limites de requêtes.

## Sécurité

- CORS est configuré pour permettre les requêtes depuis n'importe quelle origine
- L'authentification JWT est requise pour tous les endpoints sauf `/health`
- Les en-têtes de sécurité sont gérés par FastAPI

## Logging

Le système utilise un logging configuré au niveau INFO pour tracer les opérations importantes et les erreurs.

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