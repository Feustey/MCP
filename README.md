# MCP - Système de Question-Réponse avec RAG

MCP est un système de question-réponse avancé utilisant la technique RAG (Retrieval-Augmented Generation) pour fournir des réponses précises et contextuelles basées sur un corpus de documents.

## Fonctionnalités

- 🔍 Recherche sémantique dans les documents
- 💾 Mise en cache intelligente avec Redis
- 📊 Stockage persistant avec MongoDB
- 🤖 Intégration avec OpenAI pour les embeddings et la génération de texte
- 📈 Monitoring et métriques du système
- 🚨 Système d'alertes configurables
- 📊 Tableaux de bord personnalisables
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

## API de Monitoring et Alertes

MCP inclut un système complet de monitoring et d'alertes qui permet de surveiller l'état du système, de configurer des alertes et d'afficher des métriques via des tableaux de bord interactifs.

### Fonctionnalités principales

- Définition et collecte de métriques pour les performances du système et les opérations métier
- Configuration d'alertes basées sur des conditions métriques
- Notifications multi-canaux (email, Slack, webhook, SMS)
- Tableaux de bord personnalisables avec différents types de visualisations
- API WebSocket pour les événements en temps réel

### Exemples d'utilisation

#### Configuration d'une alerte

```python
import requests

alert_config = {
    "name": "Alerte de déséquilibre de canal",
    "description": "Se déclenche lorsqu'un canal devient trop déséquilibré",
    "enabled": True,
    "type": "channel_balance",
    "severity": "warning",
    "conditions": [
        {
            "metric": "channel_balance_ratio",
            "operator": "<",
            "threshold": 0.2,
            "duration": "1h"
        }
    ],
    "notification_channels": ["email", "in_app"],
    "template": {
        "title": "Déséquilibre de canal détecté",
        "body": "Le canal {{channel_id}} avec {{peer_alias}} est déséquilibré (ratio: {{ratio}})"
    },
    "tags": ["balance", "maintenance"]
}

response = requests.post("http://localhost:8000/api/v2/monitor/alerts/configure", json=alert_config)
print(response.json())
```

#### Abonnement aux événements en temps réel

```python
import websocket
import json

def on_message(ws, message):
    event = json.loads(message)
    print(f"Nouvel événement reçu: {event['title']}")

def on_open(ws):
    # S'abonner aux événements d'alerte
    subscription = {
        "subscribe": ["alert_triggered", "alert_resolved"]
    }
    ws.send(json.dumps(subscription))

ws = websocket.WebSocketApp("ws://localhost:8000/api/v2/monitor/events/subscribe",
                            on_message=on_message,
                            on_open=on_open)
ws.run_forever()
```

## Documentation

- [Guide d'installation](docs/installation.md)
- [Guide d'utilisation](docs/usage.md)
- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Monitoring et Alertes](docs/monitoring.md)

## Tests

```bash
python -m pytest tests/ -v
```

## Structure du projet

```
mcp/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── v1/
│   │   └── v2/
│   │       ├── network_graph/
│   │       ├── predict/
│   │       ├── simulate/
│   │       └── monitor/            # Service de monitoring et alertes
│   │           ├── __init__.py
│   │           ├── models.py        # Modèles de données pour le monitoring
│   │           └── monitor_endpoints.py  # Endpoints API pour le monitoring
│   ├── rag.py              # Workflow RAG principal
│   ├── models.py           # Modèles de données
│   ├── mongo_operations.py # Opérations MongoDB
│   ├── redis_operations.py # Opérations Redis
│   └── database.py         # Configuration de la base de données
├── tests/
│   ├── __init__.py
│   ├── api/
│   │   └── v2/
│   │       └── monitor/    # Tests pour le service de monitoring
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
│   ├── api.md
│   └── monitoring.md        # Documentation spécifique au monitoring
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

# Couche de Sécurité et Fiabilité

Ce projet inclut une couche robuste de sécurité et fiabilité pour les opérations sur les nœuds Lightning. Cette documentation décrit les principales fonctionnalités et comment les utiliser.

## Composants Principaux

### 1. Circuit Breakers

Les circuit breakers protègent le système contre les défaillances des services externes en détectant les erreurs et en interrompant temporairement les appels aux services problématiques.

```python
from src.circuit_breaker import circuit_protected, CircuitBreakerConfig

# Utilisation simple avec le décorateur
@circuit_protected("external_api")
async def call_external_service():
    # votre code ici
    
# Configuration personnalisée
config = CircuitBreakerConfig(
    failure_threshold=5,        # Nombre d'erreurs avant ouverture
    recovery_timeout=30.0,     # Délai avant half-open (secondes)
    reset_timeout=60.0,        # Délai en half-open avant reset (secondes)
    execution_timeout=30.0     # Timeout d'exécution (secondes)
)

@circuit_protected("payment_service", config)
async def process_payment():
    # votre code ici
```

### 2. Stratégies de Retry Avancées

Le système implémente des stratégies de retry avec backoff exponentiel pour gérer les erreurs transitoires.

```python
from src.retry_manager import RetryManager, RetryConfig

# Configuration du retry
retry_config = RetryConfig(
    max_retries=3,            # Nombre maximum de tentatives
    base_delay=1.0,           # Délai initial (secondes)
    max_delay=60.0,           # Délai maximum (secondes)
    backoff_factor=2.0,       # Facteur de multiplication du délai
    jitter=True               # Ajouter de l'aléatoire au délai
)

retry_manager = RetryManager(retry_config)

# Utilisation
async def fetch_data():
    async def api_call():
        # code qui peut échouer
        
    result = await retry_manager.execute(api_call)
```

### 3. Audit de Sécurité

Le système d'audit de sécurité enregistre et surveille toutes les opérations sensibles sur les nœuds Lightning.

```python
from src.security_audit import SecurityAuditManager, SecurityEvent, SecurityLevel

# Initialisation
audit_manager = SecurityAuditManager()

# Journalisation d'événements
await audit_manager.log_event(
    SecurityEvent.API_REQUEST,
    user_id="user123",
    ip_address="192.168.1.1",
    details={"action": "get_info"},
    level=SecurityLevel.LOW
)

# Vérification d'opérations
is_allowed, message = await audit_manager.verify_operation(
    operation="open_channel",
    user_id="user123",
    ip_address="192.168.1.1",
    params={"node_id": "xyz", "amount": 50000},
    signature="abcdef1234567890"
)
```

### 4. Tests de Charge

Des tests de charge sont disponibles pour identifier les goulots d'étranglement du système.

```bash
# Exécuter les tests de charge
pytest tests/load_tests/test_rag_performance.py
```

## Configuration

La configuration se fait via les variables d'environnement dans le fichier `.env`. Un exemple est fourni dans `.env.example`.

Principales configurations :

```ini
# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30

# Retry Manager
RETRY_MAX_RETRIES=3
RETRY_BASE_DELAY=1.0
RETRY_BACKOFF_FACTOR=2.0

# Audit de sécurité
SECURITY_AUDIT_LOG_PATH=logs/security_audit.log
SECURITY_AUDIT_MAX_LOG_SIZE_MB=10
```

## Conseils d'Utilisation

1. **Circuit Breakers** : Utilisez-les pour tous les appels aux services externes (API, bases de données, etc.).

2. **Retry Manager** : Particulièrement utile pour les opérations réseau qui peuvent échouer de manière transitoire.

3. **Audit de Sécurité** : Essentiel pour toutes les opérations sensibles comme l'ouverture/fermeture de canaux et les paiements.

4. **Tests de Charge** : Exécutez-les régulièrement pour surveiller les performances du système, surtout après des modifications importantes.

## Limites et Considérations

- Les circuit breakers sont configurés par service, assurez-vous d'utiliser des noms cohérents pour les identifier.
- L'audit de sécurité génère des logs volumineux, configurez la rotation des logs appropriée.
- Les tests de charge peuvent être intensifs en ressources, préférez les exécuter dans un environnement de test.

## Maintenance

Des tâches périodiques sont nécessaires pour maintenir le système en bon état :

```python
# Nettoyage du cache expiré
await cache_manager.clear_expired_cache()

# Optimisation des index de la base de données
await mongo_ops.optimize_indexes()

# Rotation des logs
await monitoring.rotate_logs()
```

