# Guide de Démarrage Rapide

Ce guide vous aidera à démarrer rapidement avec MCP.

## Premiers Pas

### 1. Initialisation du RAG

```python
from src import AugmentedRAG, EnhancedRetrieval

# Initialisation du RAG
rag = AugmentedRAG(
    model_name="gpt-4",
    embedding_model="all-MiniLM-L6-v2"
)

# Initialisation de la récupération améliorée
retrieval = EnhancedRetrieval(
    vector_db_conn=your_vector_db,
    direct_db_conn=your_mongo_db
)
```

### 2. Création d'une Hypothèse

```python
from src import HypothesisManager

# Initialisation du gestionnaire d'hypothèses
hypothesis_manager = HypothesisManager(mongo_ops=your_mongo_ops)

# Création d'une hypothèse de frais
hypothesis = await hypothesis_manager.create_fee_hypothesis(
    node_id="your_node_id",
    channel_id="your_channel_id",
    new_base_fee=1000,
    new_fee_rate=100
)
```

### 3. Simulation de Changements

```python
from src import simulate_changes

# Simulation des changements
await simulate_changes("your_node_id")
```

## Exemples Complets

### Optimisation des Frais

```python
from src import AugmentedRAG, HypothesisManager, simulate_changes

async def optimize_fees(node_id: str, channel_id: str):
    # Initialisation
    rag = AugmentedRAG()
    hypothesis_manager = HypothesisManager()
    
    # Analyse des performances actuelles
    analysis = await rag.query_augmented(
        query=f"Analyse des performances du canal {channel_id}"
    )
    
    # Création d'hypothèses
    hypothesis = await hypothesis_manager.create_fee_hypothesis(
        node_id=node_id,
        channel_id=channel_id,
        new_base_fee=1000,
        new_fee_rate=100
    )
    
    # Simulation des changements
    await simulate_changes(node_id)
    
    # Évaluation des résultats
    results = await hypothesis_manager.evaluate_fee_hypothesis(
        hypothesis.hypothesis_id
    )
    
    return results
```

### Gestion des Canaux

```python
from src import NetworkOptimizer, AutomationManager

async def manage_channels(node_id: str):
    # Initialisation
    optimizer = NetworkOptimizer()
    automation = AutomationManager()
    
    # Analyse du réseau
    analysis = await optimizer.analyze_network(node_id)
    
    # Application des optimisations
    for suggestion in analysis.suggestions:
        if suggestion.type == "fee_optimization":
            await automation.update_fee_rate(
                channel_id=suggestion.channel_id,
                base_fee=suggestion.new_base_fee,
                fee_rate=suggestion.new_fee_rate
            )
        elif suggestion.type == "liquidity":
            await automation.rebalance_channel(
                channel_id=suggestion.channel_id,
                amount=suggestion.amount,
                direction=suggestion.direction
            )
```

## Bonnes Pratiques

### RAG
- Utilisez des requêtes spécifiques
- Exploitez le contexte enrichi
- Ajustez les paramètres selon vos besoins

### Hypothèses
- Commencez par de petits changements
- Surveillez les impacts
- Validez les résultats

### Automatisation
- Configurez des seuils de sécurité
- Mettez en place des alertes
- Gardez un historique des changements

## Prochaines Étapes

- [Concepts Avancés](../concepts/rag/overview.md)
- [API Reference](../api/reference/overview.md)
- [Best Practices](../guides/best-practices/rag-best-practices.md) 