# Documentation Technique MCP
> Dernière mise à jour: 7 mai 2025

## Sommaire

1. [Introduction](#1-introduction)
2. [Architecture du Système](#2-architecture-du-système)
3. [Environnement Technique](#3-environnement-technique)
4. [Scripts Principaux](#4-scripts-principaux)
5. [Modules et Bibliothèques](#5-modules-et-bibliothèques)
6. [Système RAG](#6-système-rag)
7. [Bases de Données](#7-bases-de-données)
8. [API et Interfaces](#8-api-et-interfaces)
9. [Sécurité](#9-sécurité)
10. [Workflow Opérationnel](#10-workflow-opérationnel)
11. [Tests et Validation](#11-tests-et-validation)
12. [Annexes](#12-annexes)

## 1. Introduction

### 1.1 Objectif du Document

Ce document constitue la référence technique complète du projet MCP (Monitor, Control, Predict), un système d'optimisation pour les nœuds Lightning Network. Il détaille l'architecture, les composants, les dépendances et les workflows du système pour faciliter son développement, sa maintenance et son évolution.

### 1.2 Vue d'Ensemble du Projet

MCP est un système d'optimisation pour les nœuds Lightning Network qui utilise des tests A/B et une boucle de feedback, enrichi par un système RAG (Retrieval-Augmented Generation). Le système collecte des données sur les performances des nœuds, analyse ces données, et génère des recommandations pour optimiser leur configuration et leur liquidité.

## 2. Architecture du Système

### 2.1 Vue d'Ensemble de l'Architecture

MCP est un système intégré qui combine deux fonctionnalités principales :
1. Un système avancé de **question-réponse basé sur RAG** (Retrieval-Augmented Generation)
2. Une suite d'outils d'**analyse et d'optimisation pour Lightning Network**

Le système s'appuie sur :
- MongoDB pour le stockage persistant des documents, embeddings et données historiques
- Redis pour le cache multi-niveau et la gestion des requêtes fréquentes
- Llama et OpenAI pour les embeddings et la génération de texte
- Une architecture asynchrone pour les performances et la scalabilité

### 2.2 Composants Principaux

#### 2.2.1 Système RAG
- **Workflow RAG** : Orchestration de l'ingestion, génération d'embeddings, recherche et génération de réponses
- **Récupération hybride** : Combinaison de recherche vectorielle et lexicale
- **Expansion de requêtes** : Reformulation et génération de requêtes alternatives
- **Génération avancée** : Optimisation des réponses par sélection intelligente du contexte
- **Cache multi-niveau** : Système de cache pour réponses, résultats de recherche et expansions de requêtes
- **Évaluation RAG** : Évaluation automatique de la qualité des réponses

#### 2.2.2 Intégration Lightning Network
- **Client LND/LNBits** : Interface avec les nœuds Lightning
- **Enrichissement de nœuds** : Centralisation des métadonnées multi-sources
- **Gestion de scénarios de test** : Framework pour tests A/B sur les nœuds
- **Optimisation de configuration** : Algorithmes d'optimisation pour les nœuds

#### 2.2.3 Infrastructure Partagée
- **Gestion des données** : Modèles de données unifiés
- **Opérations MongoDB** : Gestion de toutes les opérations de base de données
- **API REST** : Exposition des fonctionnalités via HTTP

### 2.3 Flux de Données

Le système comprend deux flux de données principaux :

1. **Système RAG avancé** : Traite les requêtes utilisateur via un système de cache multiniveau, recherche hybride et génération de réponses.
2. **Intégration Lightning Network** : Collecte et enrichit les données des nœuds Lightning pour l'optimisation et les tests A/B.

## 3. Environnement Technique

### 3.1 Prérequis Système

- Python 3.9 ou supérieur
- MongoDB 4.4 ou supérieur
- Redis 6.0 ou supérieur
- LNBits et LND v0.16.1-beta ou supérieur pour intégration Lightning

### 3.2 Dépendances Principales

| Catégorie | Bibliothèque | Version | Description |
|-----------|--------------|---------|-------------|
| **Framework Web** | FastAPI | 0.111.0 | API web et endpoints REST |
| | Uvicorn | 0.27.1 | Serveur ASGI pour FastAPI |
| | Gunicorn | 23.0.0 | Serveur WSGI pour production |
| **Base de données** | Motor | ≥3.0.0,<4.0.0 | Client MongoDB asynchrone |
| | PyMongo | 4.6.3 | Client MongoDB synchrone |
| | Redis | 5.0.1 | Client Redis pour cache |
| **IA et RAG** | OpenAI | 1.67.0 | Intégration OpenAI API |
| | LlamaIndex | - | Framework RAG |
| | FAISS-CPU | - | Recherche par similarité vectorielle |
| | LangChain | - | Framework pour applications IA |
| **Utilitaires** | Pydantic | ≥1.10.0,<3.0.0 | Validation de données |
| | Python-dotenv | ≥1.0.0 | Gestion variables d'environnement |
| | Python-jose | 3.4.0 | Authentification JWT |
| | Bech32 | 1.2.0 | Décodage d'adresses Lightning |
| **Visualisation** | Plotly | ≥5.18.0 | Graphiques interactifs |
| | Pandas | ≥2.2.3 | Manipulation de données |
| | Streamlit | ≥1.29.0 | Interfaces utilisateur |
| **Tests** | Pytest | 8.0.0 | Tests unitaires et d'intégration |
| | Pytest-asyncio | 0.23.5 | Tests asynchrones |
| | Pytest-cov | 4.1.0 | Couverture de test |

### 3.3 Configuration de l'Environnement

```bash
# Création de l'environnement virtuel
python3.9 -m venv venv

# Activation de l'environnement
source venv/bin/activate

# Installation des dépendances
pip install -r requirements.txt

# Configuration des variables d'environnement
cp .env.example .env
# Éditer .env avec les valeurs appropriées
```

## 4. Scripts Principaux

### 4.1 run_test_system.py

**Fonctionnalité** : Point d'entrée principal pour exécuter les scénarios de test A/B sur les nœuds Lightning.

**Dépendances** :
- `asyncio`, `json`, `time`, `random`, `datetime`, `logging`, `dotenv`
- `lnbits_client.LNBitsClient`
- `test_scenarios.TestScenarioManager`, `test_scenarios.ActionTracker`
- `optimize_feustey_config.calculate_score`

**Fonctions principales** :
- `create_test_scenario()` : Crée un scénario de test avec des valeurs réalistes
- `simulate_metrics_after()` : Simule les métriques après une action (en test)
- `test_feedback_loop()` : Teste un cycle complet de la boucle de feedback
- `run_test_cycle()` : Exécute un cycle de test complet avec A/B testing

**Flux d'exécution** :
1. Initialisation du client LNBits et du gestionnaire de scénarios
2. Création de scénarios de test A/B
3. Configuration du nœud avec chaque scénario
4. Démarrage d'une session de test pour chaque scénario
5. Collecte des métriques et analyse des résultats
6. Identification du scénario gagnant et ajustement des poids si nécessaire

**Paramètres d'entrée** : Aucun argument direct, utilise les variables d'environnement du fichier `.env`

**Résultat** : Exécution des scénarios de test et ajustement du modèle d'optimisation

### 4.2 test_scenarios.py

**Fonctionnalité** : Gestion des scénarios de test A/B et évaluation des résultats.

**Dépendances** :
- Bibliothèques standard : `typing`, `asyncio`, `uuid`, `datetime`, `json`, `logging`, `csv`, `pathlib`, `collections`, `statistics`
- `lnbits_client.LNBitsClient`
- `app.services.network_topology.NetworkTopologyAnalyzer`
- `app.services.performance_dashboard.PerformanceDashboard`

**Classes principales** :
1. **PerformanceTracker** : 
   - Analyse les performances des différentes stratégies dans le temps
   - Maintient des statistiques sur les performances et les séquences de victoires
   - Génère des rapports de performance et des visualisations

2. **ActionEvaluator** : 
   - Évalue les actions et calcule les ajustements de poids
   - Intègre des garde-fous contre les biais et l'oscillation
   - Calcule la volatilité des stratégies

3. **ActionTracker** : 
   - Suit les actions et leurs résultats
   - Identifie les gagnants des tests A/B
   - Maintient l'historique des actions et des métriques

4. **TestScenarioManager** : 
   - Configure les nœuds avec différents scénarios
   - Génère des scénarios de test A/B
   - Gère les sessions de test et récupère les métriques

**Paramètres clés** :
- `min_threshold` : Seuil minimal pour ajuster les poids (évite l'oscillation)
- `volatility_threshold` : Seuil de volatilité pour réduire la sensibilité
- `decay_rate` : Taux de décroissance pour la moyenne mobile

**Entrées/Sorties** :
- Entrée : Données de configuration des nœuds, métriques avant tests
- Sortie : Actions tracées, métriques après tests, scénario gagnant, ajustements de poids recommandés

### 4.3 run_rag_workflow.sh

**Fonctionnalité** : Script shell pour exécuter le workflow complet du système RAG.

**Dépendances** :
- Environnement bash
- Python et environnement virtuel
- MongoDB et Redis (optionnel)
- Scripts Python : `run_aggregation.py`, `feustey_fee_optimizer.py`, `feustey_rag_optimization.py`, `rag_asset_generator.py`

**Étapes d'exécution** :
1. Vérification et configuration de l'environnement (Python, MongoDB, Redis)
2. Création des répertoires RAG_assets nécessaires
3. Agrégation des données (`run_aggregation.py`)
4. Optimisation des frais de feustey (`feustey_fee_optimizer.py`)
5. Optimisation RAG pour feustey (`feustey_rag_optimization.py`)
6. Génération des assets RAG complets (`rag_asset_generator.py`)
7. Vérification des résultats et création de liens vers les derniers rapports

**Paramètres** : Mode simulation (booléen) - détermine si des données de test sont générées

**Sorties** :
- Rapports dans `rag/RAG_assets/reports/`
- Logs dans `logs/workflow_TIMESTAMP.log`

### 4.4 Autres Scripts Importants

#### 4.4.1 run_aggregation.py
- **Fonctionnalité** : Agrège les données de différentes sources pour les analyses
- **Dépendances** : MongoDB, pandas, modules de collecte de données
- **Sortie** : Données agrégées dans MongoDB et fichiers CSV

#### 4.4.2 feustey_rag_optimization.py
- **Fonctionnalité** : Optimise la configuration des nœuds feustey avec RAG
- **Dépendances** : Système RAG, données historiques, modèles d'optimisation
- **Sortie** : Recommandations d'optimisation dans `rag/RAG_assets/reports/feustey/`

#### 4.4.3 topup_wallet.py
- **Fonctionnalité** : Alimente le wallet LNBits pour les tests
- **Dépendances** : LNBitsClient, variables d'environnement
- **Paramètres** : Montant à ajouter au wallet

## 5. Modules et Bibliothèques

### 5.1 Modules Principaux

#### 5.1.1 src/api/
- Endpoints API pour l'accès aux fonctionnalités du système
- Versioning API et documentation Swagger

#### 5.1.2 src/clients/
- **LNBitsClient** : Interface avec LNBits pour la gestion des nœuds Lightning
- **AmbossClient** : Récupération des données de réputation des nœuds

#### 5.1.3 src/optimizers/
- Algorithmes d'optimisation pour les paramètres des nœuds Lightning
- Modèles de simulation et prédiction

#### 5.1.4 src/scanners/
- Scanner de nœuds pour découverte et analyse
- Scanner de liquidité pour évaluation des canaux

#### 5.1.5 app/services/
- Services d'application pour scoring et visualisation
- `network_topology.py` : Analyse de topologie du réseau
- `performance_dashboard.py` : Visualisation des performances

### 5.2 Système RAG

#### 5.2.1 rag/rag.py
- Workflow principal du système RAG
- Orchestration de l'ingestion, recherche et génération

#### 5.2.2 rag/hybrid_retriever.py
- Combinaison de recherche vectorielle et lexicale
- Fusion pondérée des résultats

#### 5.2.3 rag/generators/
- Générateurs d'assets pour le système RAG
- Création de rapports et documentation

## 6. Système RAG

### 6.1 Architecture RAG

Le système RAG (Retrieval-Augmented Generation) combine la recherche d'information et la génération de texte pour produire des réponses précises et contextuelles.

#### 6.1.1 Composants Principaux
- **Ingestion** : Traitement des documents et conversion en représentations vectorielles
- **Stockage** : Base de données MongoDB pour les documents et leurs embeddings
- **Récupération** : Système de recherche hybride combinant similarité vectorielle et recherche lexicale
- **Génération** : Utilisation de modèles LLM (Llama, OpenAI) pour produire des réponses contextuelles

#### 6.1.2 Flux de Données RAG
```
Requête → Cache L1 → Prétraitement → Expansion → Embedding → Recherche hybride → Reranking → Génération → Évaluation → Réponse
```

### 6.2 Ingestion et Prétraitement

- **Formats supportés** : Texte, PDF, Markdown
- **Segmentation** : Découpage des documents en chunks adaptés à la fenêtre de contexte des LLM
- **Nettoyage** : Normalisation du texte, élimination des artefacts

### 6.3 Systèmes de Recherche

#### 6.3.1 Recherche Vectorielle
- **Modèle d'embedding** : Llama/OpenAI pour la conversion texte-vecteurs
- **Indexation** : FAISS pour la recherche par similarité vectorielle
- **Métrique** : Similarité cosinus pour évaluer la proximité sémantique

#### 6.3.2 Recherche Lexicale
- **Algorithme** : BM25 pour la recherche par mots-clés
- **Avantages** : Capture les termes spécifiques absents de la recherche sémantique

#### 6.3.3 Fusion Hybride
- Combinaison pondérée des résultats des deux approches
- Reranking pour optimiser la pertinence finale

### 6.4 Génération et Évaluation

- **Modèles supportés** : Llama3, Mistral, modèles OpenAI
- **Prompt engineering** : Structuration des prompts pour maximiser la qualité des réponses
- **Évaluation** : Métriques de fidélité, pertinence, et exhaustivité

## 7. Bases de Données

### 7.1 MongoDB

#### 7.1.1 Collections Principales
- **documents** : Documents ingérés et leurs métadonnées
- **embeddings** : Vecteurs d'embeddings associés aux documents
- **nodes** : Données des nœuds Lightning Network
- **actions** : Actions et résultats des tests
- **metrics** : Métriques collectées au fil du temps

#### 7.1.2 Schéma des Documents

```json
{
  "document": {
    "_id": "ObjectId",
    "title": "String",
    "content": "String",
    "metadata": {
      "source": "String",
      "author": "String",
      "created_at": "DateTime"
    },
    "chunks": [
      {
        "text": "String",
        "index": "Integer"
      }
    ],
    "created_at": "DateTime",
    "updated_at": "DateTime"
  },
  
  "embedding": {
    "_id": "ObjectId",
    "document_id": "ObjectId",
    "chunk_index": "Integer",
    "vector": "Array<Float>",
    "model": "String"
  },
  
  "node": {
    "_id": "ObjectId",
    "node_id": "String",
    "alias": "String",
    "pubkey": "String",
    "channels": [
      {
        "chan_id": "String",
        "capacity": "Integer",
        "local_balance": "Integer",
        "remote_balance": "Integer",
        "remote_pubkey": "String"
      }
    ],
    "metrics": {
      "uptime": "Float",
      "centrality": "Float",
      "reputation": "Float"
    },
    "updated_at": "DateTime"
  },
  
  "action": {
    "_id": "ObjectId",
    "action_id": "String",
    "node_id": "String",
    "scenario_id": "String",
    "action_type": "String",
    "config": "Object",
    "metrics_before": "Object",
    "metrics_after": "Object",
    "delta": "Object",
    "created_at": "DateTime",
    "updated_at": "DateTime"
  }
}
```

### 7.2 Redis

#### 7.2.1 Utilisation
- Cache multi-niveau pour le système RAG
- Stockage temporaire des résultats de recherche
- Mémorisation des réponses fréquentes

#### 7.2.2 Structure des Clés
- `rag:response:{hash_query}` : Réponses complètes
- `rag:search:{hash_query}` : Résultats de recherche
- `rag:expansion:{hash_query}` : Requêtes expansées

## 8. API et Interfaces

### 8.1 API REST

#### 8.1.1 Endpoints RAG
- `POST /api/v1/rag/query` : Soumet une requête au système RAG
- `POST /api/v1/rag/ingest` : Ingère un nouveau document
- `GET /api/v1/rag/documents` : Liste les documents disponibles

#### 8.1.2 Endpoints Lightning
- `GET /api/v1/nodes/{node_id}` : Récupère les informations d'un nœud
- `POST /api/v1/nodes/{node_id}/optimize` : Lance l'optimisation d'un nœud
- `GET /api/v1/tests` : Liste les tests en cours ou terminés

#### 8.1.3 Authentification
- JWT pour sécuriser les accès API
- Différents niveaux d'autorisation (lecture, écriture, admin)

### 8.2 Interfaces Utilisateur

#### 8.2.1 Interface Web (Streamlit)
- Visualisation des performances des nœuds
- Interface de requête pour le système RAG
- Tableaux de bord pour les métriques

#### 8.2.2 Interface CLI
- Commandes pour lancer les workflows
- Outils de diagnostic et maintenance

## 9. Sécurité

### 9.1 Authentification et Autorisation

- **JWT** : Authentification basée sur JSON Web Tokens
- **Rôles** : Admin, utilisateur, lecture seule
- **Expiration** : Tokens avec durée limitée et refresh token

### 9.2 Sécurisation des Données

- **Chiffrement** : Données sensibles chiffrées au repos
- **Variables d'environnement** : Secrets gérés via fichier .env
- **Sanitization** : Validation des entrées avec Pydantic

### 9.3 Connexions Sécurisées

- **TLS/SSL** : Communication chiffrée pour les APIs
- **Pare-feu** : Restriction des accès aux services MongoDB et Redis
- **Rate Limiting** : Limitation du nombre de requêtes avec SlowAPI

## 10. Workflow Opérationnel

### 10.1 Déploiement

#### 10.1.1 Préparation
```bash
# Cloner le dépôt
git clone [repository-url]
cd MCP

# Créer et configurer l'environnement
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec les paramètres appropriés
```

#### 10.1.2 Démarrage des Services
```bash
# Démarrer MongoDB et Redis si nécessaire
docker-compose up -d mongodb redis

# Lancer le serveur API
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 10.2 Workflows Principaux

#### 10.2.1 Workflow RAG
```bash
./run_rag_workflow.sh
```

#### 10.2.2 Workflow de Test A/B
```bash
python run_test_system.py
```

### 10.3 Monitoring et Maintenance

- **Logs** : Centralisés dans le dossier `/logs/`
- **Métriques** : Accessibles via l'API et les tableaux de bord
- **Alertes** : Configuration possible pour les événements critiques

## 11. Tests et Validation

### 11.1 Tests Unitaires

- **Framework** : pytest avec pytest-asyncio
- **Couverture** : pytest-cov pour analyse de la couverture
- **Localisation** : `/tests/`

### 11.2 Tests d'Intégration

- **Environnement** : Configuration de test dans `.env.test`
- **Scénarios** : Test de bout en bout du système

### 11.3 Tests de Charge

- **Outils** : Locust pour simulation de charge
- **Métriques** : Temps de réponse, taux d'erreur, débit

## 12. Annexes

### 12.1 Glossaire

- **RAG** : Retrieval-Augmented Generation, système combinant recherche et génération
- **LLM** : Large Language Model, modèle de langage de grande taille
- **Lightning Network** : Réseau de paiement Layer 2 pour Bitcoin
- **Canal Lightning** : Connexion bidirectionnelle entre deux nœuds Lightning
- **A/B Testing** : Méthode de test comparatif entre différentes configurations

### 12.2 Guide de Dépannage

#### 12.2.1 Problèmes Courants MongoDB
- **Connexion refusée** : Vérifier l'URL MongoDB et le démarrage du service
- **Timeout** : Vérifier les paramètres de connexion et les règles de pare-feu

#### 12.2.2 Problèmes LNBits/LND
- **Erreur d'authentification** : Vérifier les clés API dans .env
- **Nœud inaccessible** : Vérifier la connectivité réseau et le statut du nœud

### 12.3 Ressources

- Documentation Lightning Network: [Lightning Network Specification](https://github.com/lightning/bolts)
- Documentation LNBits: [LNBits Documentation](https://lnbits.github.io/lnbits-legend/)
- Documentation RAG: [LlamaIndex Documentation](https://docs.llamaindex.ai/) 