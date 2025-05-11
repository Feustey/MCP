# MCP - Monitoring, Control, and Planning for Lightning Network
> Dernière mise à jour: 7 mai 2025

MCP est un système d'analyse avancée pour les nœuds Lightning Network utilisant le Retrieval-Augmented Generation (RAG) pour fournir des analyses pertinentes et des réponses aux questions sur les nœuds Lightning.

## Architecture

MCP est construit autour d'une architecture modulaire qui comprend les composants suivants :

```
┌───────────────────────┐     ┌───────────────────────┐
│ Couche Données        │     │ Couche Application    │
│ ---------------       │     │ ---------------       │
│ - MongoDB             │◄────┤ - API REST (FastAPI)  │
│ - Redis (cache)       │     │ - RAG Pipeline        │
│ - Vector Store        │     │ - Llama Integration   │
└───────────────────────┘     └───────────────────────┘
             ▲                            ▲
             │                            │
             └────────────────┬──────────┘
                              │
                  ┌───────────▼───────────┐
                  │ Couche Services        │
                  │ ---------------        │
                  │ - Node Analysis        │
                  │ - Report Generation    │
                  │ - Query Processing     │
                  │ - LN Graph Connectivity│
                  │ - LND Native Support   │
                  └───────────────────────┘
```

### Principaux composants :

- **RAG Workflow** : Cœur du système qui orchestre l'ingestion des documents, la recherche sémantique et la génération de réponses.
- **MongoDB** : Stockage persistant pour les documents, les embeddings, les rapports et les statistiques.
- **Redis** : Système de cache pour optimiser les performances.
- **API REST** : Interface pour interagir avec le système.
- **CLI** : Interface en ligne de commande pour les opérations courantes.
- **LND Client** : Client natif pour la communication directe avec un nœud LND via gRPC.
- **LNRouter Client** : Client pour accéder à la structure du graphe Lightning global.
- **EnrichedNode** : Centralisation des métadonnées multi-sources des nœuds.
- **HistoricalSnapshot** : Système de capture de snapshots longitudinaux.

## Fonctionnalités Lightning Network Avancées

MCP intègre désormais des fonctionnalités avancées pour l'analyse et la gestion du réseau Lightning :

1. **Connectivité au graphe Lightning public** via le client LNRouter pour compléter les données d'Amboss
2. **Support natif LND/Core Lightning** via gRPC pour un contrôle total de votre nœud
   - Compatible avec LND v0.16.1-beta et versions supérieures
   - Supporte les dernières améliorations de routage MPP
3. **Centralisation des métadonnées multi-sources** avec la classe EnrichedNode
4. **Suivi historique longitudinal** pour l'analyse des tendances

Pour plus de détails, consultez [la documentation complète des fonctionnalités Lightning](docs/lightning_features.md).

## Modules optionnels et imports conditionnels

Certaines fonctionnalités avancées du projet MCP reposent sur des modules externes optionnels qui ne sont pas strictement nécessaires au fonctionnement de base, mais activent des capacités supplémentaires si installés :

- **RAGAS** : Permet l'évaluation automatique des réponses générées par le système RAG. Si le module `ragas` n'est pas installé, l'évaluation automatique sera désactivée (voir les imports conditionnels dans `rag/rag.py` et `rag/rag_evaluator.py`).
    - Pour activer cette fonctionnalité, installez :
      ```bash
      pip install ragas
      ```
- **Autres modules optionnels** : Certains modules peuvent être importés de façon conditionnelle pour des extensions futures. Consultez le code source pour plus de détails.

**Remarque :** Les imports conditionnels sont gérés proprement dans le code. Si un module optionnel n'est pas installé, une fonctionnalité avancée sera simplement désactivée sans bloquer le reste du système. Un message d'avertissement sera affiché dans les logs.

## Installation

### Prérequis

- Python 3.8+
- MongoDB
- Redis
- Accès aux modèles Llama (ou configuration pour OpenAI)
- Node LND (optionnel, pour les fonctionnalités avancées)

### Installation des dépendances

```bash
# Cloner le dépôt
git clone https://github.com/yourusername/mcp.git
cd mcp

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditez le fichier .env avec vos configurations
```

## Configuration

Créez un fichier `.env` avec les variables suivantes :

```
# MongoDB
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=mcp_db

# Redis
REDIS_URL=redis://localhost:6379/0
RESPONSE_CACHE_TTL=3600

# Modèles
USE_OPENAI_EMBEDDINGS=true
OPENAI_API_KEY=your_openai_api_key
LLAMA_MODEL_PATH=meta-llama/Llama-2-7b-chat-hf

# Configuration LND (optionnel)
LND_HOST=localhost:10009
LND_MACAROON_PATH=/path/to/.lnd/data/chain/bitcoin/mainnet/admin.macaroon
LND_TLS_CERT_PATH=/path/to/.lnd/tls.cert

# Configuration historique (optionnel)
TARGET_NODES=pubkey1,pubkey2
INCLUDE_POPULAR_NODES=true
POPULAR_NODE_LIMIT=100
```

## Utilisation

### Lancer l'API

```bash
python run_mcp.py api --host 127.0.0.1 --port 8000
```

L'API sera accessible à l'adresse http://127.0.0.1:8000 avec la documentation Swagger à http://127.0.0.1:8000/api/docs.

### Utiliser l'interface CLI

```bash
# Analyser un nœud Lightning
python run_mcp.py cli analyze 02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f

# Lister les nœuds analysés
python run_mcp.py cli list_nodes

# Interroger le système RAG
python run_mcp.py cli query "Comment optimiser les frais pour un nœud Lightning Network ?"

# Ingérer des documents
python run_mcp.py cli ingest ./docs/knowledge_base

# Afficher les statistiques
python run_mcp.py cli stats

# Exécuter un snapshot historique
python run_mcp.py cli snapshot

# Obtenir un nœud enrichi
python run_mcp.py cli get_enriched_node 02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f
```

## API REST

L'API REST (v1) expose les endpoints suivants :

- **GET /** : Vérifier que l'API est opérationnelle
- **GET /health** : Vérifier l'état des services
- **POST /rag/query** : Interroger le système RAG
- **GET /rag/stats** : Récupérer les statistiques du système RAG
- **GET /nodes** : Récupérer la liste des nœuds analysés
- **POST /nodes/analyze/{node_id}** : Analyser un nœud
- **GET /nodes/{node_id}/reports** : Récupérer les rapports d'un nœud
- **GET /nodes/{node_id}/enriched** : Récupérer les données enrichies d'un nœud
- **GET /network/stats** : Récupérer les statistiques du réseau Lightning
- **POST /lnd/update_policy** : Mettre à jour les politiques de frais (nœud local)

## Développement

### Structure du projet

```
mcp/
├── docs/                   # Documentation
│   ├── architecture.md     # Documentation de l'architecture
│   ├── usage.md            # Guide d'utilisation
│   └── lightning_features.md # Documentation fonctionnalités Lightning
├── src/                    # Code source
│   ├── api/                # API REST
│   │   ├── main.py         # Point d'entrée FastAPI
│   │   └── ...
│   ├── models/             # Modèles de données
│   │   ├── enriched_node.py # Modèle centralisant les métadonnées
│   │   └── ...
│   ├── services/           # Services
│   │   ├── lnrouter_client.py # Client LNRouter
│   │   ├── lnd_client.py   # Client LND natif
│   │   └── ...
│   ├── scripts/            # Scripts utilitaires
│   │   ├── historical_snapshot.py # Capture de données historiques
│   │   └── ...
│   ├── rag.py              # Workflow RAG
│   ├── mongo_operations.py # Opérations MongoDB
│   ├── redis_operations.py # Opérations Redis
│   ├── rag_monitoring.py   # Monitoring du système RAG
│   └── cli.py              # Interface en ligne de commande
├── tests/                  # Tests
├── .env.example            # Exemple de configuration
├── requirements.txt        # Dépendances Python
└── README.md               # Ce fichier
```

### Tests

```bash
# Exécuter les tests
pytest

# Exécuter les tests avec couverture
pytest --cov=src
```

## Monitoring

Le système intègre un module de monitoring qui collecte des métriques sur :

- Nombre total de documents
- Nombre de requêtes
- Temps de traitement moyen
- Taux de hit du cache
- Évolution historique des nœuds Lightning

Ces métriques sont accessibles via l'API REST et l'interface CLI.

## Intégration avec l'Application Daznode

MCP-llama fournit les API et données structurées qui peuvent être utilisées par l'application Daznode pour la visualisation et l'analyse du réseau Lightning. Daznode se concentre sur l'expérience utilisateur, tandis que MCP-llama fournit les données et les fonctionnalités sous-jacentes.

## Licence

Ce projet est sous licence [MIT](LICENSE).

## Contribution

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour les directives de contribution.

# MCP-llama
