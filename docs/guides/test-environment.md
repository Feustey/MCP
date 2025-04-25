# Configuration de l'Environnement de Test

Ce document détaille la configuration nécessaire pour mettre en place un environnement de test complet pour le projet MCP.

## Prérequis

### Dépendances Système

- **Python 3.9+**
- **MongoDB** (pour les tests d'intégration)
- **Redis** (pour les tests de cache)
- **Docker** (optionnel, pour les tests en conteneurs)

### Paquets Python

Installez les dépendances de test via pip :

```bash
# Installation des dépendances de développement
pip install -r requirements-dev.txt
```

Le fichier `requirements-dev.txt` doit contenir au minimum :
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
mongomock>=4.1.2
pytest-mock>=3.10.0
httpx>=0.24.0
```

## Structure de l'Environnement

### Organisation des Fichiers

```
project/
├── src/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_*.py
│   ├── api/
│   └── load_tests/
├── .env
├── .env.test
└── pytest.ini
```

### Configuration Pytest

Créez un fichier `pytest.ini` à la racine du projet :

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Activer les tests asynchrones
asyncio_mode = auto

# Exclure certains répertoires
norecursedirs = venv .git node_modules

# Marques personnalisées
markers =
    integration: tests d'intégration avec des services externes
    performance: tests de performance
    slow: tests qui prennent plus de temps à s'exécuter
```

## Configuration des Variables d'Environnement

### Fichier `.env.test`

Créez un fichier `.env.test` spécifique pour les tests :

```env
# MongoDB de test
MONGODB_URI=mongodb://localhost:27017/mcp_test

# Redis de test
REDIS_URL=redis://localhost:6379/1

# OpenAI (utiliser une clé dédiée aux tests ou un mock)
OPENAI_API_KEY=test_openai_key

# LNBits (configuration de test)
LNBITS_API_URL=http://localhost:3000
LNBITS_ADMIN_KEY=test_admin_key
LNBITS_INVOICE_KEY=test_invoice_key

# Mode test activé
ENVIRONMENT=test
```

## Mise en Place des Mocks

### Mocking des Services Externes

Utilisez le fichier `conftest.py` pour définir les fixtures de mock réutilisables :

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_openai():
    """Fixture fournissant un mock du client OpenAI."""
    with patch("openai.AsyncClient") as mock:
        client = MagicMock()
        client.embeddings.create = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
        ))
        client.chat.completions.create = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(
                message=MagicMock(content="Réponse de test")
            )]
        ))
        mock.return_value = client
        yield client

@pytest.fixture
def mock_redis():
    """Fixture fournissant un mock de Redis."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.delete = AsyncMock(return_value=1)
    return redis_mock

@pytest.fixture
def mock_http_client():
    """Fixture fournissant un mock de client HTTP."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={})
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    return client
```

## Bases de Données de Test

### MongoDB de Test

#### Option 1 : MongoDB locale

```python
@pytest.fixture(scope="session")
async def mongodb_test():
    """Fixture fournissant une connexion à MongoDB pour les tests."""
    from motor.motor_asyncio import AsyncIOMotorClient
    
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.mcp_test
    
    # Nettoyer la base avant les tests
    await db.documents.delete_many({})
    await db.query_history.delete_many({})
    
    yield db
    
    # Nettoyer après les tests
    await db.documents.delete_many({})
    await db.query_history.delete_many({})
```

#### Option 2 : MongoDB en Mémoire

```python
@pytest.fixture(scope="function")
def mongo_mock():
    """Fixture fournissant une MongoDB mockée en mémoire."""
    import mongomock
    client = mongomock.MongoClient()
    return client.db
```

### Redis de Test

```python
@pytest.fixture
async def redis_test():
    """Fixture fournissant une connexion Redis pour les tests."""
    import redis.asyncio as redis
    
    client = redis.Redis.from_url("redis://localhost:6379/1")
    await client.flushdb()  # Nettoyer la base avant les tests
    
    yield client
    
    await client.flushdb()  # Nettoyer après les tests
    await client.close()
```

## Tests d'Intégration avec Docker

Pour des tests d'intégration plus complets, utilisez Docker Compose :

### Fichier `docker-compose.test.yml`

```yaml
version: '3'

services:
  mongodb:
    image: mongo:4.4
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_DATABASE=mcp_test
  
  redis:
    image: redis:6.0
    ports:
      - "6379:6379"
  
  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    volumes:
      - .:/app
    depends_on:
      - mongodb
      - redis
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/mcp_test
      - REDIS_URL=redis://redis:6379/1
      - OPENAI_API_KEY=test_key
      - ENVIRONMENT=test
    command: pytest -v
```

### Script de lancement

```bash
#!/bin/bash
# run_integration_tests.sh

echo "🔄 Démarrage des services pour les tests d'intégration..."
docker-compose -f docker-compose.test.yml up -d mongodb redis

echo "⏳ Attente du démarrage des services..."
sleep 5

echo "🧪 Exécution des tests d'intégration..."
docker-compose -f docker-compose.test.yml up --build test

echo "🧹 Nettoyage..."
docker-compose -f docker-compose.test.yml down
```

## Analyse de Couverture

Pour mesurer la couverture de code pendant les tests :

```bash
# Exécuter les tests avec rapport de couverture
python -m pytest --cov=src --cov-report=term --cov-report=html

# Visualiser le rapport HTML
open htmlcov/index.html
```

### Configuration de `.coveragerc`

```ini
[run]
source = src
omit = 
    tests/*
    */migrations/*
    venv/*
    */settings.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    raise ImportError
    except ImportError
    if __name__ == .__main__.:
```

## Tests de Performance

Pour les tests de performance, configurez un environnement dédié :

```python
@pytest.fixture(scope="session")
def performance_config():
    """Configuration pour les tests de performance."""
    return {
        "concurrent_users": [1, 5, 10, 20],
        "requests_per_user": 10,
        "request_delay": 0.1,
        "output_dir": "tests/load_tests/results"
    }
```

## Intégration Continue

### Exemple pour GitHub Actions

Créez un fichier `.github/workflows/tests.yml` :

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:4.4
        ports:
          - 27017:27017
      
      redis:
        image: redis:6.0
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest -v --cov=src
      env:
        MONGODB_URI: mongodb://localhost:27017/mcp_test
        REDIS_URL: redis://localhost:6379/1
        OPENAI_API_KEY: ${{ secrets.TEST_OPENAI_KEY }}
        ENVIRONMENT: test
    
    - name: Upload coverage report
      uses: codecov/codecov-action@v1
```

## Dépannage

### Problèmes Courants et Solutions

1. **Erreur de connexion MongoDB**
   ```
   Solution: Vérifiez que MongoDB est en cours d'exécution :
   $ mongod --version
   $ systemctl status mongodb
   ```

2. **Erreur avec les tests asynchrones**
   ```
   Solution: Assurez-vous d'utiliser la bonne configuration dans pytest.ini :
   asyncio_mode = auto
   ```

3. **Conflits de temps d'attente dans les tests**
   ```python
   # Solution: Utilisez une fixture pour remplacer asyncio.sleep
   @pytest.fixture
   def fast_sleep():
       async def _fast_sleep(*args, **kwargs):
           # Ne fait rien, retourne immédiatement
           return
       
       with patch('asyncio.sleep', _fast_sleep):
           yield
   ```

## Ressources Complémentaires

- [Stratégie de Test](./testing-strategy.md)
- [Guide de Maintenance des Tests](./test-maintenance.md)
- [Tests par Composant](./component-testing.md) 