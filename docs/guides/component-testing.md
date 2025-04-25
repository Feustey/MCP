# Guide de Test par Composant

Ce document détaille les approches spécifiques pour tester chaque composant majeur du système MCP.

## Tests du Système RAG

### 1. Tests du Workflow RAG

Le workflow RAG combine recherche et génération, nécessitant des tests spécifiques.

#### Stratégie de Test

```python
@pytest.mark.asyncio
async def test_rag_workflow(mock_db, mock_embedding_service, mock_llm):
    """Teste le flux complet du workflow RAG."""
    # Configuration
    query = "Comment optimiser mon nœud Lightning?"
    mock_docs = [{"content": "Optimisation de nœud Lightning...", "metadata": {...}}]
    
    # Mock des composants
    mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_db.search_similar.return_value = mock_docs
    mock_llm.generate.return_value = "Pour optimiser votre nœud Lightning..."
    
    # Initialisation du workflow
    rag = RAGWorkflow(
        embedding_service=mock_embedding_service,
        database=mock_db,
        llm=mock_llm
    )
    
    # Exécution
    response = await rag.query(query)
    
    # Vérifications
    assert isinstance(response, str)
    assert "optimiser" in response.lower()
    mock_embedding_service.embed_query.assert_called_once_with(query)
    mock_db.search_similar.assert_called_once()
    mock_llm.generate.assert_called_once()
```

#### Pièges Courants
- Ne pas tester le workflow de bout en bout
- Ne pas vérifier les interactions entre composants
- Utiliser des jeux de données trop simplistes

### 2. Tests de Récupération (Retrieval)

La récupération des documents pertinents est cruciale pour la qualité des réponses.

#### Stratégie de Test

```python
def test_document_relevance():
    """Teste la pertinence des documents récupérés."""
    # Configuration
    query = "configuration des canaux lightning"
    docs = [
        {"content": "Guide de configuration des canaux Lightning", "score": 0.85},
        {"content": "Historique de Bitcoin", "score": 0.35},
        {"content": "Optimisation des frais Lightning", "score": 0.75}
    ]
    
    # Exécution
    retriever = EnhancedRetrieval()
    filtered_docs = retriever.filter_by_relevance(docs, threshold=0.7)
    
    # Vérifications
    assert len(filtered_docs) == 2
    assert all(doc["score"] >= 0.7 for doc in filtered_docs)
    assert any("configuration des canaux" in doc["content"] for doc in filtered_docs)
```

#### Métriques à Surveiller
- **Precision@k**: proportion de documents pertinents parmi les k premiers
- **Recall@k**: proportion de documents pertinents récupérés
- **Temps de récupération**: latence de la récupération

### 3. Tests de Génération

La génération de texte doit être testée pour sa qualité et sa cohérence.

#### Stratégie de Test

```python
@pytest.mark.parametrize("query,expected_keywords", [
    ("optimisation des frais", ["base_fee", "fee_rate", "HTLC"]),
    ("ouverture de canal", ["capacité", "nœud", "pair", "liquidité"])
])
async def test_response_quality(query, expected_keywords, mock_rag_workflow):
    """Teste la qualité des réponses générées."""
    # Configuration
    mock_rag_workflow.setup_realistic_response()
    
    # Exécution
    response = await mock_rag_workflow.query(query)
    
    # Vérifications
    for keyword in expected_keywords:
        assert keyword.lower() in response.lower(), f"Mot-clé '{keyword}' manquant dans la réponse"
```

## Tests du Système de Cache

Le système de cache est crucial pour les performances et nécessite des tests spécifiques.

### 1. Tests de Base du Cache

#### Stratégie de Test

```python
@pytest.mark.asyncio
async def test_cache_operations():
    """Teste les opérations de base du cache."""
    # Configuration
    cache = RAGCache()
    await cache.initialize()
    
    test_key = "test:cache:key"
    test_data = {"response": "Test response", "timestamp": "2023-01-01T00:00:00Z"}
    
    try:
        # Test d'écriture
        success = await cache.set(test_key, test_data)
        assert success is True
        
        # Test de lecture
        cached_data = await cache.get(test_key)
        assert cached_data is not None
        assert cached_data["response"] == test_data["response"]
        
        # Test d'existence
        exists = await cache.exists(test_key)
        assert exists is True
        
        # Test de suppression
        deleted = await cache.delete(test_key)
        assert deleted is True
        exists_after = await cache.exists(test_key)
        assert exists_after is False
    finally:
        await cache.close()
```

### 2. Tests d'Expiration du Cache

#### Stratégie de Test

```python
@pytest.mark.asyncio
async def test_cache_expiration():
    """Teste l'expiration des entrées du cache."""
    # Configuration avec TTL court pour le test
    cache = RAGCache(default_ttl=1)  # 1 seconde
    await cache.initialize()
    
    test_key = "test:expiring:key"
    test_data = {"response": "Expiring response"}
    
    try:
        # Écriture avec TTL court
        await cache.set(test_key, test_data)
        
        # Vérification immédiate
        assert await cache.exists(test_key) is True
        
        # Attente de l'expiration
        await asyncio.sleep(2)  # > TTL
        
        # Vérification après expiration
        assert await cache.exists(test_key) is False
    finally:
        await cache.close()
```

## Tests d'Intégration avec MongoDB

MongoDB est utilisé pour le stockage persistant des données.

### 1. Tests avec Mock MongoDB

#### Stratégie de Test

```python
@pytest.mark.asyncio
async def test_mongo_operations(mock_mongo):
    """Teste les opérations MongoDB avec un mock."""
    # Configuration
    mock_mongo.find_one.return_value = {"_id": "test_id", "content": "Test document"}
    mock_mongo.insert_one.return_value = MagicMock(inserted_id="new_id")
    
    # Initialisation
    mongo_ops = MongoOperations(client=mock_mongo)
    
    # Test d'insertion
    doc = {"content": "New document", "metadata": {"source": "test"}}
    doc_id = await mongo_ops.insert_document(doc)
    assert doc_id == "new_id"
    mock_mongo.insert_one.assert_called_once()
    
    # Test de récupération
    document = await mongo_ops.get_document("test_id")
    assert document["content"] == "Test document"
    mock_mongo.find_one.assert_called_once()
```

### 2. Tests avec MongoDB en Mémoire

Pour des tests plus réalistes, utiliser une base de données MongoDB en mémoire.

```python
@pytest.fixture
async def memory_mongo():
    """Fixture pour une base MongoDB en mémoire."""
    from mongomock.aiohttp import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    db = client.test_db
    yield db
    # Nettoyage automatique après le test

@pytest.mark.asyncio
async def test_document_search(memory_mongo):
    """Teste la recherche de documents avec une BD en mémoire."""
    # Insertion de données de test
    docs = [
        {"content": "Lightning Network basics", "embedding": [0.1, 0.2, 0.3]},
        {"content": "Channel management guide", "embedding": [0.2, 0.3, 0.4]},
        {"content": "Fee optimization techniques", "embedding": [0.3, 0.4, 0.5]}
    ]
    collection = memory_mongo.documents
    await collection.insert_many(docs)
    
    # Test de recherche
    mongo_ops = MongoOperations(db=memory_mongo)
    results = await mongo_ops.search_documents("channel management")
    
    # Vérifications
    assert len(results) > 0
    assert any("channel" in doc["content"].lower() for doc in results)
```

## Tests des APIs

Les endpoints API nécessitent des tests spécifiques.

### 1. Tests FastAPI avec TestClient

#### Stratégie de Test

```python
from fastapi.testclient import TestClient
from src.main import app

def test_query_endpoint(mocker):
    """Teste l'endpoint de requête RAG."""
    # Mock du service RAG
    mock_rag = mocker.patch("src.services.rag_service.query")
    mock_rag.return_value = {"response": "Test response", "source_documents": []}
    
    # Création du client de test
    client = TestClient(app)
    
    # Requête de test
    response = client.post(
        "/api/query",
        json={"query": "Test question?", "max_tokens": 100}
    )
    
    # Vérifications
    assert response.status_code == 200
    result = response.json()
    assert "response" in result
    assert result["response"] == "Test response"
    mock_rag.assert_called_once()
```

### 2. Tests Asynchrones des APIs

Pour des tests plus complets des APIs asynchrones.

```python
@pytest.mark.asyncio
async def test_async_api_endpoint(async_client):
    """Teste un endpoint API asynchrone."""
    response = await async_client.post(
        "/api/async_endpoint",
        json={"parameter": "test_value"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
```

## Tests du Système Lightning

Les fonctionnalités spécifiques à Lightning Network nécessitent des tests adaptés.

### 1. Tests des Clients Lightning

#### Stratégie de Test

```python
@pytest.mark.asyncio
async def test_lightning_client(mock_http_client):
    """Teste le client Lightning Network."""
    # Configuration du mock
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "channels": [
            {"channel_id": "123", "capacity": 1000000, "local_balance": 500000}
        ]
    }
    mock_http_client.get.return_value = mock_response
    
    # Initialisation du client
    lightning_client = LightningClient(http_client=mock_http_client)
    
    # Test de récupération des canaux
    channels = await lightning_client.get_channels()
    
    # Vérifications
    assert len(channels) == 1
    assert channels[0]["channel_id"] == "123"
    assert channels[0]["capacity"] == 1000000
    mock_http_client.get.assert_called_once()
```

### 2. Tests d'Analyse de Réseau

#### Stratégie de Test

```python
def test_network_analysis():
    """Teste les algorithmes d'analyse de réseau Lightning."""
    # Création d'un graphe de test
    import networkx as nx
    G = nx.Graph()
    G.add_node("node1", alias="Alice")
    G.add_node("node2", alias="Bob")
    G.add_node("node3", alias="Charlie")
    G.add_edge("node1", "node2", capacity=1000000)
    G.add_edge("node2", "node3", capacity=2000000)
    
    # Test du calcul de centralité
    from src.network_analysis import calculate_centrality
    result = calculate_centrality(G)
    
    # Vérifications
    assert len(result) == 3
    assert "node2" in result  # Nœud central
    assert result["node2"] > result["node1"]  # node2 est plus central
```

## Ressources Complémentaires

- [Stratégie de Test](./testing-strategy.md)
- [Guide de Maintenance des Tests](./test-maintenance.md)
- [Configuration de l'Environnement de Test](./test-environment.md) 