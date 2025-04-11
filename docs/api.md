# Documentation API

## Vue d'ensemble

L'API de MCP fournit des endpoints RESTful pour interagir avec le système RAG. Tous les endpoints sont asynchrones et retournent des réponses au format JSON.

## Authentification

L'API utilise un système d'authentification par signature. Le processus se déroule en trois étapes :

1. Obtenir un message à signer
2. Signer le message avec la clé privée du nœud via Lnbits
3. Vérifier la signature auprès de l'API

### Configuration requise

- URL de base de l'API LNPlus
- URL de base de Lnbits (par défaut: http://192.168.0.45:3007)
- Clé d'administration Lnbits (par défaut: fddac5fb8bf64eec944c89255b98dac4)
- Clé d'invocation Lnbits (par défaut: 3fbbe7e0c2a24b43aa2c6ad6627f44eb)

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

L'API utilise plusieurs types d'exceptions pour gérer les erreurs :

- `LNPlusError`: Erreur générique
- `LNPlusAPIError`: Erreur de l'API
- `LNPlusAuthError`: Erreur d'authentification
- `LNPlusValidationError`: Erreur de validation des données
- `LNPlusRateLimitError`: Limite de taux dépassée
- `LNPlusNetworkError`: Erreur réseau

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

## API LNPlus

### Swaps

#### Liste des swaps
```python
swaps = await client.get_swaps(filters={"status": "pending"})
```

#### Création d'un swap
```python
swap_request = SwapCreationRequest(
    amount=100000,  # en satoshis
    type="inbound"
)
swap = await client.create_swap(swap_request)
```

### Nœuds

#### Métriques d'un nœud
```python
metrics = await client.get_node_metrics(node_id)
```

#### Note d'un nœud
```python
rating = await client.get_node_rating(node_id)
```

#### Réputation d'un nœud
```python
reputation = await client.get_node_reputation(node_id)
```

#### Création d'une note
```python
rating = await client.create_rating(
    target_node_id=node_id,
    is_positive=True,
    comment="Excellent service"
)
```

### Wallet

#### Solde
```python
balance = await client.get_balance()  # en satoshis
```

## Exemple d'utilisation

```python
from lnplus_integration.client import LNPlusClient

async def main():
    client = LNPlusClient()
    try:
        await client.ensure_connected()
        
        # Vérifier le solde
        balance = await client.get_balance()
        print(f"Solde: {balance} satoshis")
        
        # Créer un swap
        swap_request = SwapCreationRequest(
            amount=100000,
            type="inbound"
        )
        swap = await client.create_swap(swap_request)
        print(f"Swap créé: {swap.id}")
        
    finally:
        await client.close()

# Exécuter le code
import asyncio
asyncio.run(main())
```

### Codes d'erreur courants

- `400` : Requête invalide
- `401` : Non authentifié
- `403` : Accès refusé
- `404` : Ressource non trouvée
- `429` : Trop de requêtes
- `500` : Erreur serveur 