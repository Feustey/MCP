# Documentation des Tests

## Vue d'ensemble

Le système MCP dispose d'une suite complète de tests unitaires, d'intégration et de performance qui couvrent les principaux composants de RAG et Lightning Network. Cette documentation explique la structure des tests, leur objectif et comment les exécuter.

## Structure des Tests

Le répertoire `tests/` est organisé comme suit :

### Tests Principaux
- `test_mcp.py` - Tests de base du système MCP
- `test_mongo_integration.py` - Tests d'intégration avec MongoDB
- `test_circuit_breaker.py` - Tests du mécanisme de protection circuit breaker
- `test_security_audit.py` - Tests de sécurité et audit

### Tests RAG
- `test_advanced_rag.py` - Tests du système RAG avancé
- `test_advanced_generator.py` - Tests du générateur de réponses avancé
- `test_multilevel_cache.py` - Tests du cache multi-niveau
- `test_rag_evaluator.py` - Tests de l'évaluateur automatique de RAG

### Tests Lightning Network
- `test_network_analyzer.py` - Tests de l'analyseur de réseau Lightning
- `test_network_optimizer.py` - Tests de l'optimiseur de nœuds
- `test_amboss_scraper.py` - Tests du scraper de données Amboss
- `test_liquidity_scanner.py` - Tests du scanner de liquidité
- `test_automation_manager.py` - Tests du gestionnaire d'automatisation

### Tests de Charge
Dans le répertoire `tests/load_tests/` :
- `test_rag_performance.py` - Tests de performance du système RAG sous charge

## Configuration des Tests

### Fixtures Partagées

Les fixtures principales sont définies dans `conftest.py` :

```python
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture pour simuler les variables d'environnement."""
    monkeypatch.setenv('SPARKSEER_API_KEY', 'test_api_key')
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.setenv('OPENAI_API_KEY', 'test_openai_key')
    monkeypatch.setenv('MONGODB_URI', 'mongodb://localhost:27017/test')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')

@pytest.fixture
def rag_workflow():
    """Fixture pour créer une instance de RAGWorkflow."""
    workflow = RAGWorkflow()
    workflow.openai_client = AsyncMock()
    workflow.tokenizer = AsyncMock()
    workflow.ingest_documents = AsyncMock()
    workflow.query = AsyncMock(return_value="Test response")
    return workflow
```

### Mocks et Simulateurs

Pour tester les composants qui dépendent de services externes, nous utilisons :
- `AsyncMock` pour simuler les opérations asynchrones
- Mocks de MongoDB et Redis pour les tests d'intégration
- Simulateurs de nœuds Lightning pour tester les interactions avec le réseau

## Tests RAG Avancés

### Test d'Expansion de Requêtes

```python
async def test_query_expansion(rag_workflow):
    """Teste la fonctionnalité d'expansion de requête."""
    for query in TEST_QUERIES[:2]:  # On limite à 2 requêtes pour le test
        expanded = await rag_workflow.query_expander.expand_query(query)
        
        assert expanded["rewritten_query"] != query
        assert len(expanded["sub_queries"]) >= 2
        assert len(expanded["keywords"]) >= 3
```

### Test de Recherche Hybride

```python
async def test_hybrid_search(rag_workflow, query):
    """Teste la recherche hybride avec différentes configurations."""
    configs = [
        {"use_hybrid": True, "use_expansion": True, "desc": "Recherche hybride avec expansion"},
        {"use_hybrid": True, "use_expansion": False, "desc": "Recherche hybride sans expansion"},
        {"use_hybrid": False, "use_expansion": False, "desc": "Recherche vectorielle pure"}
    ]
    
    for config in configs:
        response = await rag_workflow.query(
            query_text=query,
            top_k=5,
            use_hybrid=config["use_hybrid"],
            use_expansion=config["use_expansion"]
        )
        
        assert response is not None
        assert len(response) > 0
```

### Test du Cache Multi-niveau

Les tests du cache multi-niveau vérifient :
- Mise en cache des réponses complètes (L1)
- Mise en cache des résultats de recherche (L2)
- Invalidation intelligente
- Comportement en cas d'échec
- Statistiques de cache

## Tests Lightning Network

### Test de l'Optimiseur de Réseau

```python
@pytest.mark.asyncio
async def test_adjust_channel_fees(optimizer, sample_channel):
    """Test de l'ajustement des frais d'un canal"""
    # Test avec un faible taux de succès
    await optimizer._adjust_channel_fees(sample_channel, 0.7, 600.0)
    
    # Vérification de l'appel à Redis
    assert optimizer.redis_ops.update_channel_fees.called
    call_args = optimizer.redis_ops.update_channel_fees.call_args[0]
    assert call_args[1]["fee_rate"] > sample_channel.fee_rate["fee_rate"]
```

### Test de l'Analyseur de Réseau

Les tests de l'analyseur de réseau vérifient :
- Calcul des métriques de centralité
- Identification des nœuds pivots
- Détection des changements topologiques

### Test du Scanner de Liquidité

```python
@pytest.mark.asyncio
async def test_scan_node_channels(liquidity_scanner):
    """Test du scan des canaux d'un nœud"""
    result = await liquidity_scanner.bulk_scan_node_channels(
        "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        sample_size=3  # Tester seulement 3 canaux
    )
    
    assert result["eligible"] is True
    assert len(result["results"]) > 0
    assert "bidirectional_count" in result
    assert "liquidity_score" in result
```

## Tests d'Intégration

### Test de l'Intégration RAG-Lightning

```python
@pytest.mark.asyncio
async def test_rag_lightning_integration():
    """Test de l'intégration entre RAG et Lightning Network"""
    # Initialisation des composants
    rag = RAGWorkflow()
    node_enricher = EnrichedNodeService()
    
    # Obtention des données du nœud
    node = await node_enricher.get_enriched_node(
        "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
    )
    
    # Création d'un contexte supplémentaire
    context = f"Nœud: {node.alias}, Capacité: {node.lnd_data.get('total_capacity')} sats"
    
    # Requête RAG avec contexte Lightning
    response = await rag.query(
        "Comment optimiser ce nœud Lightning?",
        additional_context=context
    )
    
    assert response is not None
    assert node.alias in response  # La réponse doit mentionner le nœud
```

## Tests de Charge

### Configuration

Les tests de charge dans `tests/load_tests/` utilisent `pytest-benchmark` pour mesurer les performances et `pytest-asyncio` pour les tests asynchrones.

### Test de Performance du RAG

```python
@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_rag_query_performance(benchmark, rag_workflow):
    """Test de performance pour les requêtes RAG."""
    # Préparation des données
    await rag_workflow.ingest_documents("./test_docs/")
    
    # Mesure de performance pour 10 requêtes simultanées
    async def run_queries():
        tasks = [rag_workflow.query(q) for q in BENCHMARK_QUERIES[:10]]
        return await asyncio.gather(*tasks)
    
    # Mesure du temps d'exécution
    results = await benchmark.pedantic(run_queries, iterations=5, rounds=3)
    
    # Vérification des résultats
    assert len(results) == 10
    assert all(r is not None for r in results)
```

## Exécution des Tests

### Tests Unitaires

```bash
# Exécuter tous les tests
pytest

# Exécuter des tests spécifiques
pytest tests/test_advanced_rag.py
pytest tests/test_network_optimizer.py

# Exécuter avec couverture
pytest --cov=.
```

### Tests de Charge

```bash
# Exécuter les tests de charge
pytest tests/load_tests/ -v

# Exécuter avec rapports détaillés
pytest tests/load_tests/ --benchmark-json=output.json
```

### Tests d'Intégration Continue

Les tests sont automatiquement exécutés lors des pushes vers le dépôt via GitHub Actions. La configuration se trouve dans `.github/workflows/tests.yml`.

## Bonnes Pratiques pour les Tests

1. **Isoler les tests** - Chaque test doit être isolé et ne pas dépendre de l'état des autres tests
2. **Utiliser des mocks** - Toujours simuler les services externes pour éviter les appels réels
3. **Tests paramétrés** - Utiliser `@pytest.mark.parametrize` pour tester plusieurs cas d'utilisation
4. **Assertions claires** - Chaque test doit avoir des assertions spécifiques
5. **Tests asynchrones** - Utiliser `@pytest.mark.asyncio` pour les fonctions asynchrones

## Résolution des Problèmes Courants

- **Timeouts** - Augmenter le timeout avec `@pytest.mark.asyncio(timeout=60)`
- **Erreurs de connexion** - Vérifier la disponibilité des services simulés
- **Tests flaky** - Identifier et isoler les tests instables avec `@pytest.mark.flaky(reruns=3)`

# Documentation des tests unitaires
> Dernière mise à jour: 7 mai 2025

