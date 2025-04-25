# Documentation de MongoOperations

## Vue d'ensemble

Le module `MongoOperations` gère toutes les opérations de base de données MongoDB pour le système. Il fournit une interface robuste et optimisée pour le stockage et la récupération des données du réseau Lightning.

## Collections et Indexes

### Collections principales

1. **nodes**
   - Stocke les données des nœuds Lightning
   - Indexes : 
     - `(pubkey, last_updated)`
     - `(alias)`
     - `(capacity)`
     - `(channels)`

2. **channels**
   - Stocke les données des canaux
   - Indexes :
     - `(channel_id, last_updated)`
     - `(node1_pubkey, node2_pubkey)`
     - `(capacity)`
     - `(fee_rate.base_fee, fee_rate.fee_rate)`

3. **metrics**
   - Stocke les métriques réseau
   - Indexes :
     - `(last_update)`
     - `(total_capacity)`
     - `(total_channels)`

4. **documents**
   - Stocke les documents du système RAG
   - Indexes :
     - `(metadata.type, metadata.timestamp)`
     - `(content)`

5. **query_history**
   - Stocke l'historique des requêtes
   - Indexes :
     - `(timestamp)`
     - `(query)`

6. **error_logs**
   - Stocke les logs d'erreurs
   - Indexes :
     - `(timestamp)`
     - `(error_type)`
     - `(context.node_id)`

## Méthodes principales

### Connexion et configuration

```python
async def connect(self)
```
Établit la connexion à MongoDB et configure les index.

### Gestion des nœuds

```python
async def save_node_data(self, node_data: NodeData)
```
Sauvegarde ou met à jour les données d'un nœud avec validation.

```python
async def get_node_history(self, node_id: str, start_date: datetime, end_date: datetime) -> List[Dict]
```
Récupère l'historique d'un nœud avec optimisation des performances.

### Gestion des métriques

```python
async def get_network_metrics_history(self, days: int = 30) -> List[Dict]
```
Récupère l'historique des métriques réseau sur une période donnée.

### Statistiques

```python
async def _update_node_stats(self, node_data: NodeData)
```
Met à jour les statistiques globales du nœud.

## Optimisations

### Indexation

- Utilisation d'index composés pour les requêtes fréquentes
- Index textuels pour la recherche
- Index sur les champs de tri courants

### Agrégations

- Pipeline d'agrégation optimisé pour les requêtes historiques
- Regroupement efficace des données
- Filtrage intelligent

### Performance

- Connexion asynchrone
- Gestion du pool de connexions
- Mise en cache des résultats fréquents

## Gestion des erreurs

- Journalisation détaillée des erreurs
- Retry automatique sur les erreurs temporaires
- Validation des données avant insertion

## Exemples d'utilisation

### Sauvegarde d'un nœud

```python
node_data = NodeData(
    pubkey="02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
    alias="MonNœud",
    capacity=1000000,
    channels=10,
    first_seen=datetime.now(),
    last_updated=datetime.now()
)

await mongo_ops.save_node_data(node_data)
```

### Récupération de l'historique

```python
start_date = datetime.now() - timedelta(days=7)
end_date = datetime.now()
history = await mongo_ops.get_node_history(
    "02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
    start_date,
    end_date
)
```

## Bonnes pratiques

1. **Validation des données**
   - Toujours valider les données avant insertion
   - Utiliser les modèles Pydantic pour la validation

2. **Gestion des connexions**
   - Utiliser le contexte `async with`
   - Fermer les connexions après utilisation

3. **Optimisation des requêtes**
   - Utiliser les index appropriés
   - Limiter les résultats quand possible
   - Utiliser l'agrégation pour les requêtes complexes

4. **Gestion des erreurs**
   - Logger toutes les erreurs
   - Implémenter des stratégies de retry
   - Valider les entrées utilisateur 

workflow = AugmentedRAGWorkflow(model_name="gpt-4")
await workflow.initialize()

result = await workflow.query_augmented(
    "Comment ont évolué les frais de transaction ce mois-ci?",
    dynamic_weighting=True
) 