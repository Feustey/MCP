# Architecture du Système

## Vue d'ensemble

MCP est un système de question-réponse basé sur la technique RAG (Retrieval-Augmented Generation) qui combine :
- Une base de données MongoDB pour le stockage persistant
- Redis pour la mise en cache
- OpenAI pour les embeddings et la génération de texte
- Un système de gestion de documents asynchrone

## Composants principaux

### 1. Workflow RAG (`src/rag.py`)

Le cœur du système qui orchestre :
- L'ingestion des documents
- La génération d'embeddings
- La recherche sémantique
- La génération de réponses
- La gestion du cache

### 2. Gestion des données (`src/models.py`)

Définit les modèles de données :
- `Document` : Structure des documents ingérés
- `QueryHistory` : Historique des requêtes
- `SystemStats` : Métriques du système

### 3. Opérations MongoDB (`src/mongo_operations.py`)

Gère toutes les opérations de base de données :
- CRUD des documents
- Historique des requêtes
- Statistiques système
- Indexation et recherche

### 4. Opérations Redis (`src/redis_operations.py`)

Gère le système de cache :
- Mise en cache des réponses
- Gestion des TTL
- Invalidation du cache
- Optimisation des performances

### 5. Configuration (`src/database.py`)

Gère les connexions aux bases de données :
- Configuration MongoDB
- Configuration Redis
- Gestion des connexions asynchrones

## Flux de données

1. **Ingestion de documents**
   ```
   Document → Embedding → MongoDB
   ```

2. **Traitement d'une requête**
   ```
   Requête → Embedding → Recherche → Cache → Génération → Réponse
   ```

3. **Mise en cache**
   ```
   Réponse → Redis (TTL) → Cache hit/miss
   ```

## Sécurité

- Authentification via variables d'environnement
- Validation des entrées
- Connexions sécurisées aux bases de données
- Gestion des erreurs et des exceptions

## Performance

- Opérations asynchrones
- Mise en cache intelligente
- Indexation optimisée
- Gestion de la mémoire

## Monitoring

- Métriques système
- Logs détaillés
- Statistiques d'utilisation
- Alertes et notifications

## Extensibilité

- Architecture modulaire
- Interfaces bien définies
- Configuration flexible
- Support des plugins 