# MCP - Système de Question-Réponse avec RAG

MCP est un système de question-réponse avancé utilisant la technique RAG (Retrieval-Augmented Generation) pour fournir des réponses précises et contextuelles basées sur un corpus de documents.

## Fonctionnalités

- 🔍 Recherche sémantique dans les documents
- 💾 Mise en cache intelligente avec Redis
- 📊 Stockage persistant avec MongoDB
- 🤖 Intégration avec OpenAI pour les embeddings et la génération de texte
- 📈 Monitoring et métriques du système
- 🔄 Gestion asynchrone des opérations

## Prérequis

- Python 3.9+
- MongoDB Community Edition
- Redis
- Clé API OpenAI

## Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-username/mcp.git
cd mcp
```

2. Installer les dépendances système :
```bash
# MongoDB
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Redis
brew install redis
brew services start redis
```

3. Configurer l'environnement Python :
```bash
python -m venv .venv
source .venv/bin/activate  # Sur Unix/macOS
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

## Utilisation rapide

```python
from src.rag import RAGWorkflow

# Initialisation
rag = RAGWorkflow()

# Ingestion de documents
await rag.ingest_documents("chemin/vers/documents")

# Interrogation
response = await rag.query("Votre question ici ?")
```

## Documentation

- [Guide d'installation](docs/installation.md)
- [Guide d'utilisation](docs/usage.md)
- [Architecture](docs/architecture.md)
- [API](docs/api.md)

## Tests

```bash
python -m pytest tests/ -v
```

## Structure du projet

```
mcp/
├── src/
│   ├── __init__.py
│   ├── rag.py              # Workflow RAG principal
│   ├── models.py           # Modèles de données
│   ├── mongo_operations.py # Opérations MongoDB
│   ├── redis_operations.py # Opérations Redis
│   └── database.py         # Configuration de la base de données
├── tests/
│   ├── __init__.py
│   ├── test_mcp.py
│   └── test_mongo_integration.py
├── prompts/
│   ├── system_prompt.txt
│   ├── query_prompt.txt
│   └── response_prompt.txt
├── docs/
│   ├── installation.md
│   ├── usage.md
│   ├── architecture.md
│   └── api.md
├── requirements.txt
├── .env.example
└── README.md
```

## Contribution

1. Fork le projet
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Contact

Votre Nom - [@votre_twitter](https://twitter.com/votre_twitter)

Lien du projet : [https://github.com/votre-username/mcp](https://github.com/votre-username/mcp)

