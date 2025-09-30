# Guide d'utilisation
> Dernière mise à jour: 7 mai 2025

## Configuration initiale

1. Assurez-vous que les services MongoDB et Redis sont en cours d'exécution
2. Configurez vos variables d'environnement dans le fichier `.env`
3. Installez les dépendances Python : `pip install -r requirements.txt`
4. Pour les fonctionnalités Lightning Network, configurez les crédentials LND/LNBits dans `.env`

## Utilisation du RAG avancé

### Initialisation du workflow RAG

```python
from src.rag import RAGWorkflow

# Initialisation complète du système RAG
rag_system = await init_rag_system()

# Ou création manuelle d'une instance avec options
rag = RAGWorkflow(
    vector_weight=0.7,  # Poids relatif recherche vectorielle vs lexicale
    use_hybrid_search=True,  # Utilisation du retrievers hybride
    use_query_expansion=True,  # Expansion automatique des requêtes
    cache_level="multi"  # Options: "none", "simple", "multi"
)

# Ingestion de documents
await rag.ingest_documents("chemin/vers/documents")
```

### Interrogation avancée

```python
# Question simple avec recherche hybride
response = await rag.query("Quelle est la structure du projet ?")

# Requête avec expansion automatique
response = await rag.query(
    "Comment optimiser un nœud Lightning ?",
    use_query_expansion=True,
    expansion_count=3
)

# Requête avec options avancées
response = await rag.query(
    "Comment fonctionne le système de cache ?",
    search_type="hybrid",
    vector_weight=0.8,
    context_docs=["cache.py", "redis_operations.py"],
    rerank_results=True,
    max_tokens=2000,
    evaluate_response=True
)

# Accès aux métadonnées de la réponse
print(f"Sources: {response.sources}")
print(f"Temps de traitement: {response.processing_time}s")
print(f"Score d'évaluation: {response.evaluation_score}")
print(f"Requêtes étendues: {response.expanded_queries}")
```

### Utilisation du cache multi-niveau

```python

# Création d'une instance du cache multi-niveau
cache = MultiLevelCache(
    redis_url="redis://localhost:6379/0",
    ttl_l1=3600,  # TTL pour le cache de réponses
    ttl_l2=7200   # TTL pour le cache de recherche
)

# Vérification manuelle du cache
cached_response = await cache.get_response("ma_question_clé")

# Affichage des statistiques de cache
cache_stats = await cache.get_stats()
print(f"Hit rate L1: {cache_stats['hit_rate_l1']}")
print(f"Hit rate L2: {cache_stats['hit_rate_l2']}")

# Invalidation sélective de cache
await cache.invalidate_by_pattern("*Lightning*")
```

### Évaluation automatique de réponses

```python

# Création d'un évaluateur
evaluator = RAGEvaluator()

# Évaluation d'une réponse
evaluation = await evaluator.evaluate_response(
    query="Comment fonctionne le réseau Lightning ?",
    response="Le réseau Lightning est un protocole de paiement...",
    context=["Le réseau Lightning est une solution de seconde couche...", "..."],
    metrics=["faithfulness", "relevance", "coherence", "completeness"]
)

print(f"Score global: {evaluation.overall_score}")
print(f"Détails: {evaluation.detailed_scores}")
```

## Utilisation des fonctionnalités Lightning Network

### Client LNBits

```python
from lnbits_client import LNBitsClient

# Initialisation du client
client = LNBitsClient()  # Utilise les variables d'environnement

# Récupération des informations du wallet
wallet_info = await client.get_wallet_info()
print(f"Solde: {wallet_info['balance']} sats")

# Récupération des canaux existants
channels = await client.get_channels()
for channel in channels:
    print(f"Canal: {channel['chan_id']} - Capacité: {channel['capacity']} sats")

# Mise à jour de la politique de frais
await client.update_channel_policy(
    chan_id="123456789",
    base_fee_msat=1000,
    fee_rate=500
)
```

### Enrichissement de données de nœuds

```python
from models.enriched_node import EnrichedNode, DataSourceRegistry

# Récupération d'un nœud enrichi avec toutes les sources
node = await EnrichedNode.from_all_sources(
    "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
)

# Affichage des données
print(f"Alias: {node.alias}")
print(f"Réputation Amboss: {node.amboss_data.get('reputation_score')}")
print(f"Centralité: {node.lnrouter_data.get('centrality', {}).get('betweenness')}")
print(f"Capacité totale: {node.lnd_data.get('total_capacity')} sats")

# Récupération des scores composites
reliability = node.get_composite_score("reliability")
print(f"Score de fiabilité: {reliability}")

# Mise à jour des données spécifiques
await node.update(sources=["lnd"])
```

### Test de scénarios A/B

```python
from test_scenarios import TestScenarioManager

# Initialisation du manager
manager = TestScenarioManager(client)

# Création d'un scénario de test
base_scenario = {
    "name": "Configuration optimisée",
    "fee_structure": {
        "base_fee_msat": 2000,
        "fee_rate": 300
    },
    "channel_policy": {
        "target_local_ratio": 0.55,
        "rebalance_threshold": 0.25
    }
}

# Génération de scénarios A/B
scenarios = await manager.generate_a_b_test(base_scenario)

# Exécution d'un test
for scenario in scenarios:
    # Configuration du nœud avec le scénario
    await manager.configure_node(scenario)
    
    # Démarrage d'une session de test
    test_id = await manager.start_test_session(
        scenario_id=scenario['id'],
        duration_minutes=60,
        payment_count=100
    )
    
    # ... attendre la fin du test ...
    
    # Récupération des résultats
    metrics = await manager.get_test_metrics(test_id)
    print(f"Scénario {scenario['id']} - Sats forwardés: {metrics.get('sats_forwarded_24h')}")

# Identification du scénario gagnant
winner = await manager.action_tracker.identify_winners([s["id"] for s in scenarios])
print(f"Scénario gagnant: {winner['scenario_id']} ({winner['action_type']})")
```

## Intégration RAG + Lightning Network

### Requêtes contextuelles sur les nœuds

```python
from src.rag import RAGWorkflow
from models.enriched_node import EnrichedNode

# Initialisation des composants
rag = RAGWorkflow()
node_id = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

# Obtention des données du nœud
node = await EnrichedNode.from_all_sources(node_id)

# Préparation du contexte additionnel
node_context = f"""
Alias: {node.alias}
Capacité totale: {node.lnd_data.get('total_capacity', 'N/A')} sats
Nombre de canaux: {len(node.lnd_data.get('channels', []))}
Score de centralité: {node.lnrouter_data.get('centrality', {}).get('betweenness', 'N/A')}
Politique de frais moyenne: {node.lnd_data.get('avg_fee_rate', 'N/A')} ppm
"""

# Requête RAG intégrée
response = await rag.query(
    f"Comment optimiser le nœud {node.alias} pour améliorer sa rentabilité ?",
    additional_context=node_context,
    search_type="hybrid",
    vector_weight=0.8
)

print(response.text)
```

### Analyse basée sur les connaissances

```python
from optimize_feustey_config import calculate_score, optimize_config

# Calcul du score actuel avec les poids par défaut
current_score = calculate_score(node.lnd_data)

# Récupération de connaissances via RAG
knowledge = await rag.query(
    f"Quelles sont les meilleures pratiques pour configurer les frais d'un nœud Lightning avec {len(node.lnd_data.get('channels', []))} canaux et une capacité de {node.lnd_data.get('total_capacity', 0)} sats?",
    search_type="hybrid"
)

# Utilisation de cette connaissance pour informer l'optimisation
optimized_config = await optimize_config(
    node_data=node.lnd_data,
    network_position=node.lnrouter_data.get('centrality', {}),
    additional_guidance=knowledge.text
)

print("Configuration optimisée:")
print(f"Base fee: {optimized_config['base_fee_msat']} msat")
print(f"Fee rate: {optimized_config['fee_rate']} ppm")
```

## Utilisation via l'API

### Client API Python

```python
import aiohttp
import json

async def query_mcp_api(endpoint, method="GET", data=None, token=None):
    url = f"http://localhost:8000/v1/{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url, headers=headers) as response:
                return await response.json()
        elif method == "POST":
            async with session.post(url, headers=headers, json=data) as response:
                return await response.json()

# Exemple d'utilisation
async def main():
    # Requête RAG
    rag_response = await query_mcp_api(
        "rag/query",
        method="POST",
        data={"query": "Comment optimiser un nœud Lightning ?"},
        token="votre_jwt_token"
    )
    
    # Récupération d'un nœud enrichi
    node_data = await query_mcp_api(
        f"nodes/enriched/02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        token="votre_jwt_token"
    )
    
    # Requête intégrée
    integrated_response = await query_mcp_api(
        "integrated/node_query",
        method="POST",
        data={
            "query": "Comment optimiser ce nœud ?",
            "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
        },
        token="votre_jwt_token"
    )
```

### CLI

```bash
# Requête RAG
python run_mcp.py cli query "Comment optimiser un nœud Lightning ?"

# Ingestion de documents
python run_mcp.py cli ingest ./docs/knowledge_base

# Analyse d'un nœud Lightning
python run_mcp.py cli analyze 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b

# Obtention d'un nœud enrichi
python run_mcp.py cli get_enriched_node 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b

# Exécution d'un test A/B
python run_mcp.py cli test_scenario base_config.json --duration 60

# Récupération des statistiques
python run_mcp.py cli stats
```

## Bonnes pratiques

1. **Optimisation du RAG**
   - Utilisez la recherche hybride pour une meilleure précision
   - Activez l'expansion de requêtes pour les questions complexes
   - Utilisez le cache multi-niveau pour améliorer les performances
   - Évaluez périodiquement la qualité des réponses

2. **Lightning Network**
   - Enrichissez toujours les données des nœuds avant analyse
   - Exécutez les tests A/B pendant au moins 24h pour des résultats fiables
   - Utilisez des backups avant de modifier les configurations de nœuds
   - Surveillez les métriques après chaque changement de configuration

3. **Performance**
   - Utilisez le cache à tous les niveaux
   - Préférez les opérations asynchrones
   - Optimisez les requêtes MongoDB avec des index appropriés
   - Utilisez le batching pour les opérations multiples

4. **Sécurité**
   - Protégez les macaroons LND et les clés API
   - Validez toutes les entrées utilisateur
   - Utilisez des connexions sécurisées pour MongoDB et Redis
   - Limitez les autorisations des tokens JWT

## Dépannage

### Problèmes courants du RAG

1. **Réponses imprécises**
   - Vérifiez la qualité des documents sources
   - Ajustez le vector_weight pour équilibrer recherche vectorielle et lexicale
   - Activez le reranking des résultats
   - Utilisez l'expansion de requêtes

2. **Problèmes de performance**
   - Vérifiez l'utilisation du cache
   - Optimisez les index MongoDB
   - Réduisez le nombre de documents récupérés

### Problèmes Lightning Network

1. **Erreurs de connexion au nœud**
   - Vérifiez les chemins des macaroons et certificats
   - Assurez-vous que le nœud est en ligne
   - Vérifiez les permissions des macaroons

2. **Tests A/B non concluants**
   - Augmentez la durée des tests
   - Réduisez les différences entre scénarios
   - Vérifiez que les métriques collectées sont significatives

### Intégration RAG-Lightning

1. **Données de nœuds manquantes**
   - Vérifiez la connectivité aux API externes (Amboss, LNRouter)
   - Assurez-vous que le nœud est public et indexé
   
2. **Recommandations non pertinentes**
   - Enrichissez la base de connaissances avec des documents spécifiques au Lightning Network
   - Ajustez les poids des différentes sources de données
   - Utilisez des contextes plus spécifiques dans les requêtes
