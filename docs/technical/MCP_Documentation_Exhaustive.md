# Documentation technique exhaustive MCP
> Dernière mise à jour: 7 mai 2025

# Documentation Exhaustive du Système MCP (Question-Réponse avec RAG et Lightning Network)

## 1. Introduction

**MCP** est un système avancé qui combine deux fonctionnalités principales :
1. Un système de question-réponse basé sur **RAG (Retrieval-Augmented Generation)**
2. Une intégration complète avec le **réseau Lightning** de Bitcoin

Le système est conçu pour fournir :
- Des réponses précises et contextuelles basées sur un corpus de documents
- Des outils d'analyse et d'optimisation pour les nœuds Lightning
- Une architecture robuste, performante et extensible

## 2. Fonctionnalités Clés

### 2.1. Système RAG
*   **Ingestion de Documents :** Capacité à traiter et stocker divers documents pour construire la base de connaissances.
*   **Recherche Sémantique :** Recherche de passages pertinents dans les documents basée sur le sens de la question.
*   **Génération de Réponses Augmentée :** Utilisation des informations récupérées pour générer des réponses cohérentes.
*   **Mise en Cache Intelligente :** Utilisation de Redis pour accélérer les réponses aux questions fréquentes.
*   **Stockage Persistant :** Utilisation de MongoDB pour stocker les documents, les embeddings, l'historique.

### 2.2. Intégration Lightning Network
*   **Validation de Nœuds :** Vérification des clés et des nœuds Lightning.
*   **Optimisation de Nœuds :** Outils d'analyse et d'optimisation des nœuds Lightning.
*   **Analyse du Réseau :** Calcul des centralités et génération de résumés réseau.
*   **Suivi des Performances :** Statistiques et historique des nœuds.
*   **Gestion des Canaux :** Optimisation des canaux de paiement.

### 2.3. Infrastructure
*   **API RESTful :** Interface standardisée pour toutes les fonctionnalités.
*   **Opérations Asynchrones :** Conception basée sur l'asynchronisme.
*   **Monitoring :** Collecte et exposition de métriques.
*   **Sécurité :** Authentification JWT, rate limiting, CORS.
*   **Personnalisation :** Configuration flexible via variables d'environnement.

## 3. Architecture

### 3.1. Vue d'ensemble

MCP adopte une architecture modulaire avec deux composants principaux :
1. Le système RAG pour la gestion des connaissances
2. L'intégration Lightning pour l'analyse et l'optimisation du réseau

### 3.2. Composants Principaux

#### 3.2.1. Système RAG
*   **Workflow RAG (`src/rag.py`) :** Orchestration du processus RAG
*   **Gestion des Données (`src/models.py`) :** Schémas de données
*   **Opérations MongoDB (`src/mongo_operations.py`) :** Gestion de la base de données
*   **Opérations Redis (`src/redis_operations.py`) :** Gestion du cache

#### 3.2.2. Intégration Lightning
*   **Lightning Router (`lightning.py`) :** Gestion des opérations Lightning
*   **Data Aggregator (`data_aggregator.py`) :** Collecte et agrégation des données

#### 3.2.3. Infrastructure
*   **Server (`server.py`) :** Configuration du serveur FastAPI
*   **API (`api.py`) :** Définition des routes et endpoints
*   **Auth Middleware (`auth_middleware.py`) :** Gestion de l'authentification
*   **Cache Manager (`cache_manager.py`) :** Gestion du cache
*   **Rate Limiter (`rate_limiter.py`) :** Limitation du débit
*   **Request Manager (`request_manager.py`) :** Gestion des requêtes
*   **Retry Manager (`retry_manager.py`) :** Gestion des tentatives

### 3.3. Flux de Données

1.  **Système RAG :**
    ```
    Document → Embedding → MongoDB
    Requête → Embedding → Recherche → Cache → Génération → Réponse
    ```

2.  **Lightning Network :**
    ```
    Requête → Validation → Analyse → Optimisation → Réponse
    ```

### 3.4. Technologies Utilisées

*   **Langage :** Python 3.9+
*   **Base de Données :** 
    * MongoDB (documents, embeddings)
    * Redis (cache)
*   **IA :** API OpenAI (embeddings, génération)
*   **Web :** FastAPI (serveur asynchrone)
*   **Lightning :** API Lightning Network
*   **Librairies :** 
    * `motor` (MongoDB async)
    * `redis-py` (Redis async)
    * `openai`
    * `fastapi`
    * `uvicorn`
    * `pytest`

## 4. APIs

### 4.1. API RESTful

#### 4.1.1. Endpoints RAG
*   `POST /query` : Soumission d'une question au système RAG
*   `POST /ingest` : Ingestion de nouveaux documents
*   `GET /stats` : Statistiques du système
*   `GET /recent-queries` : Historique des requêtes

#### 4.1.2. Endpoints Lightning
*   `POST /lightning/validate-key` : Validation de clé Lightning
*   `POST /lightning/validate-node` : Validation de nœud Lightning
*   `POST /optimize-node` : Optimisation de nœud
*   `GET /node/{node_id}/stats` : Statistiques du nœud
*   `GET /node/{node_id}/history` : Historique du nœud
*   `GET /network-summary` : Résumé du réseau
*   `GET /centralities` : Centralités des nœuds
*   `POST /node/{node_id}/optimize` : Optimisation complète

#### 4.1.3. Endpoints Système
*   `GET /health` : État de l'API
*   `GET /` : Documentation interactive

### 4.2. Sécurité

*   **Authentification :** JWT (JSON Web Tokens)
*   **Rate Limiting :** Limites par endpoint
*   **CORS :** Configuration flexible
*   **Validation :** Vérification des entrées
*   **Logging :** Traçage des opérations

### 4.3. Gestion des Erreurs

Format standardisé :
```json
{
    "error": "Description de l'erreur",
    "code": "ERROR_CODE",
    "details": {}
}
```

## 5. Installation et Configuration

### 5.1. Prérequis

*   Python 3.9+
*   MongoDB Community Edition
*   Redis
*   Clé API OpenAI
*   Accès au réseau Lightning

### 5.2. Installation

1.  **Dépendances Système :**
    ```bash
    # MongoDB
    brew tap mongodb/brew
    brew install mongodb-community
    brew services start mongodb-community

    # Redis
    brew install redis
    brew services start redis
    ```

2.  **Environnement Python :**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

### 5.3. Configuration

Fichier `.env` :
```env
# Base de données
MONGODB_URI=mongodb://localhost:27017/mcp
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=votre_clé_api_openai
LIGHTNING_API_KEY=votre_clé_api_lightning

# Configuration
CACHE_TTL=3600
RATE_LIMIT=60
JWT_SECRET=votre_secret_jwt
```

## 6. Utilisation

### 6.1. Système RAG

```python
from src.rag import RAGWorkflow
import asyncio

async def main():
    rag = RAGWorkflow()
    
    # Ingestion
    await rag.ingest_documents("chemin/vers/documents")
    
    # Interrogation
    response = await rag.query("Votre question ?")
    print(response)
```

### 6.2. Lightning Network

```python
from lightning import LightningClient

async def main():
    client = LightningClient()
    
    # Validation de nœud
    validation = await client.validate_node("node_id")
    
    # Optimisation
    optimization = await client.optimize_node("node_id")
    
    # Statistiques
    stats = await client.get_node_stats("node_id")
```

### 6.3. API REST

**Exemple avec curl :**

```bash
# RAG Query
curl -X POST http://localhost:8000/query \
     -H "Authorization: Bearer votre_token" \
     -H "Content-Type: application/json" \
     -d '{"query": "Votre question ?"}'

# Lightning Stats
curl -X GET http://localhost:8000/node/votre_node_id/stats \
     -H "Authorization: Bearer votre_token"
```

## 7. Monitoring et Performance

### 7.1. Métriques

*   **Système RAG :**
    *   Nombre de documents
    *   Taux de cache hit
    *   Temps de réponse
    *   Qualité des réponses

*   **Lightning Network :**
    *   État des nœuds
    *   Performance des canaux
    *   Centralité du réseau
    *   Historique des optimisations

### 7.2. Logging

*   **Niveaux :** INFO, WARNING, ERROR
*   **Format :** JSON structuré
*   **Rotation :** Quotidienne
*   **Rétention :** 30 jours

### 7.3. Alertes

*   **Système :** État des services
*   **Performance :** Seuils de latence
*   **Sécurité :** Tentatives d'accès
*   **Lightning :** État des nœuds

## 8. Sécurité

### 8.1. Authentification

*   **JWT :** Tokens d'accès
*   **Refresh Tokens :** Renouvellement automatique
*   **API Keys :** Pour les services externes

### 8.2. Autorisation

*   **RBAC :** Rôles et permissions
*   **Scope :** Limitation des accès
*   **Audit :** Journal des actions

### 8.3. Protection

*   **Rate Limiting :** Par utilisateur/IP
*   **CORS :** Origines autorisées
*   **Validation :** Entrées sanitaires
*   **Encryption :** Données sensibles

## 9. Maintenance et Support

### 9.1. Backups

*   **MongoDB :** Quotidien
*   **Redis :** Toutes les heures
*   **Logs :** Rotation quotidienne

### 9.2. Mises à jour

*   **Versions :** Semantic Versioning
*   **Migration :** Scripts automatisés
*   **Rollback :** Procédure documentée

### 9.3. Support

*   **Documentation :** Wiki interne
*   **Contact :** Support technique
*   **Incidents :** Procédure d'urgence

## 10. Contribution

*   **Process :** Fork, Branch, PR
*   **Tests :** Unitaires et intégration
*   **Style :** PEP 8
*   **Documentation :** Docstrings

## 11. Licence

*   **Type :** MIT
*   **Copyright :** 2024
*   **Auteurs :** Équipe MCP 