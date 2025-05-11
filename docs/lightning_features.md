# Documentation des fonctionnalités Lightning
> Dernière mise à jour: 7 mai 2025

# Fonctionnalités Lightning Network

## Vue d'ensemble

MCP intègre des fonctionnalités avancées pour l'analyse et l'optimisation des nœuds Lightning Network. Ce document détaille ces fonctionnalités, leurs implémentations et les méthodes de test associées.

## 1. Connectivité au graphe Lightning public

### Description
MCP se connecte aux sources de données du réseau Lightning pour collecter des informations sur la topologie globale et les métriques de nœuds.

### Implémentation

#### Client LNRouter
Le client LNRouter permet d'accéder à la structure complète du graphe Lightning et de calculer diverses métriques de centralité.

```python
from src.services.lnrouter_client import LNRouterClient

# Initialisation
client = LNRouterClient(api_key="votre_clé_api")

# Récupération de la centralité d'un nœud
node_metrics = await client.get_node_centrality("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

# Recherche des nœuds les plus centraux
top_nodes = await client.get_top_nodes(metric="betweenness", limit=10)
```

#### Intégration Amboss
L'API Amboss fournit des données sur la réputation, l'uptime et les tags communautaires des nœuds.

```python
from src.services.amboss_client import AmbossClient

# Initialisation
client = AmbossClient(api_key="votre_clé_api")

# Récupération des données d'un nœud
node_data = await client.get_node_data("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

# Récupération des tags communautaires
tags = await client.get_community_tags("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")
```

### Test
Les fonctionnalités de connectivité au graphe sont testées dans `tests/test_network_analyzer.py` et `tests/test_amboss_scraper.py`, couvrant à la fois les scénarios normaux et les cas d'erreur.

## 2. Support natif LND/Core Lightning

### Description
MCP communique directement avec votre nœud Lightning via gRPC ou REST pour un contrôle total des canaux, politiques et opérations de paiement.

### Implémentation

#### Client LNBits
Le client LNBits permet d'interagir avec un nœud Lightning via l'API LNBits.

```python
from lnbits_client import LNBitsClient

# Initialisation
client = LNBitsClient()  # Utilise les variables d'environnement

# Récupération des informations du nœud
node_info = await client.get_local_node_info()

# Récupération des canaux
channels = await client.get_channels()

# Mise à jour de la politique de frais
await client.update_channel_policy(chan_id="123456789", base_fee_msat=1000, fee_rate=500)
```

#### Client LND natif (gRPC)
Pour une communication directe avec LND via gRPC:

```python
from src.services.lnd_grpc_client import LNDClient

# Initialisation avec les chemins des certificats et macaroons
client = LNDClient(
    host="localhost:10009",
    macaroon_path="/path/to/admin.macaroon",
    tls_cert_path="/path/to/tls.cert"
)

# Récupération des informations du nœud
node_info = await client.get_node_info()

# Ouverture d'un canal
channel_point = await client.open_channel(node_pubkey="peer_pubkey", local_funding_amount=1000000)

# Routage d'un paiement
payment_result = await client.send_payment(invoice="lnbc...")
```

### Test
Les fonctionnalités LND/LNBits sont testées dans `tests/test_mcp.py` à travers une série de tests qui vérifient les opérations sur les wallets, canaux, et paiements.

## 3. Centralisation des métadonnées multi-sources

### Description
La classe `EnrichedNode` récupère et agrège les données de plusieurs sources pour fournir une vision complète d'un nœud Lightning.

### Implémentation

```python
from models.enriched_node import EnrichedNode

# Récupération d'un nœud enrichi avec toutes les sources
node = await EnrichedNode.from_all_sources("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

# Accès aux données spécifiques par source
print(f"Réputation Amboss: {node.amboss_data.get('reputation_score')}")
print(f"Centralité LNRouter: {node.lnrouter_data.get('centrality', {}).get('betweenness')}")
print(f"Canaux LND: {len(node.lnd_data.get('channels', []))}")

# Accès aux scores composites
reliability = node.get_composite_score("reliability")
routing_potential = node.get_composite_score("routing_potential")
```

### Cache et persistance
Les données récupérées sont mises en cache avec des TTL différenciés selon la volatilité des données :
- Données stables (aliases, pubkeys) : 30 jours
- Données volatiles (métriques, frais) : 1 heure

### Test
La classe `EnrichedNode` est testée dans `tests/test_network_analyzer.py` pour vérifier la récupération, l'agrégation et le calcul des métriques composites.

## 4. Suivi historique longitudinal

### Description
MCP capture et analyse des snapshots historiques de nœuds pour suivre leur évolution dans le temps.

### Implémentation

```python
from src.scripts.historical_snapshot import HistoricalSnapshotManager

# Initialisation
snapshot_manager = HistoricalSnapshotManager()

# Capture d'un snapshot pour un nœud spécifique
await snapshot_manager.capture_node_snapshot("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

# Capture des nœuds populaires
await snapshot_manager.capture_popular_nodes(limit=100)

# Récupération de l'historique d'un nœud
history = await snapshot_manager.get_node_history("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b", days=30)

# Analyse des tendances
trends = await snapshot_manager.analyze_trends("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")
```

### Configuration
Le comportement du suivi historique peut être configuré dans le fichier `.env` :

```env
# Configuration historique
TARGET_NODES=pubkey1,pubkey2
INCLUDE_POPULAR_NODES=true
POPULAR_NODE_LIMIT=100
SNAPSHOT_FREQUENCY=daily
```

### Test
Les fonctionnalités de suivi historique sont testées dans `tests/test_automation_manager.py`, qui vérifie la capture, le stockage et l'analyse des snapshots.

## 5. Test A/B de configurations

### Description
MCP inclut un framework complet pour tester et comparer différentes configurations de nœuds.

### Implémentation

```python
from test_scenarios import TestScenarioManager

# Initialisation avec un client LNBits
manager = TestScenarioManager(lnbits_client)

# Création d'un scénario de base
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

# Génération de scénarios A/B/C
scenarios = await manager.generate_a_b_test(base_scenario)

# Exécution des tests
for scenario in scenarios:
    await manager.configure_node(scenario)
    test_id = await manager.start_test_session(
        scenario_id=scenario['id'],
        duration_minutes=1440,  # 24 heures
        payment_count=500
    )

# Identification du scénario gagnant
winner = await manager.action_tracker.identify_winners([s["id"] for s in scenarios])

# Adaptation automatique des poids
if winner['action_type'] != "heuristic":
    new_weights = await manager.action_tracker.calculate_weight_adjustment()
    print(f"Nouveaux poids pour l'heuristique: {new_weights}")
```

### Test
Le framework de test A/B est testé dans `tests/test_network_optimizer.py` qui simule différents scénarios et vérifie l'identification correcte des configurations gagnantes.

## 6. Intégration RAG-Lightning

### Description
MCP intègre les capacités RAG avec les données Lightning pour fournir des recommandations contextuelles basées sur la connaissance et les données en temps réel.

### Implémentation

```python
from rag.rag import RAGWorkflow
from models.enriched_node import EnrichedNode

# Initialisation composants
rag = RAGWorkflow()
node = await EnrichedNode.from_all_sources("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

# Contexte node pour RAG
node_context = f"""
Alias: {node.alias}
Capacité totale: {node.lnd_data.get('total_capacity')} sats
Centralité: {node.lnrouter_data.get('centrality', {}).get('betweenness')}
Politique actuelle: base_fee={node.lnd_data.get('avg_base_fee')}msat, fee_rate={node.lnd_data.get('avg_fee_rate')}ppm
"""

# Requête contextualisée
response = await rag.query(
    f"Comment optimiser le nœud {node.alias} pour améliorer sa rentabilité?",
    additional_context=node_context
)
```

### Test
L'intégration RAG-Lightning est testée dans `tests/test_advanced_rag.py` qui vérifie l'expansion de requêtes, le routage et les recherches hybrides avec des requêtes liées à Lightning.

## Tester les fonctionnalités Lightning

### Tests unitaires
Pour exécuter les tests unitaires couvrant les fonctionnalités Lightning :

```bash
# Tous les tests
pytest tests/

# Tests spécifiques
pytest tests/test_network_analyzer.py
pytest tests/test_network_optimizer.py
pytest tests/test_amboss_scraper.py
```

### Tests de charge
Pour tester la performance sous charge :

```bash
# Tests de charge RAG avec contexte Lightning
pytest tests/load_tests/test_rag_performance.py
```

### Tests automatisés
Le système inclut des tests automatisés qui s'exécutent périodiquement pour vérifier l'état du réseau Lightning :

```bash
# Exécution des tests automatisés
python -m tests.test_automation_manager
```

## Conclusion

Les fonctionnalités Lightning Network de MCP offrent une solution complète pour l'analyse, l'optimisation et le suivi des nœuds. L'intégration avec le système RAG permet de combiner des connaissances générales avec des données spécifiques en temps réel pour des recommandations contextualisées et pertinentes.

Pour plus d'informations sur l'utilisation de ces fonctionnalités, consultez le document [Guide d'utilisation](usage.md).

## Compatibilité avec les clients Lightning

### LND
- Compatible avec les versions 0.15.0 et supérieures
- Support complet pour LND v0.16.1-beta incluant les améliorations du routage MPP
- Communication via gRPC et REST
