# Documentation du Système RAG Augmenté

## Vue d'ensemble

Le système RAG (Retrieval-Augmented Generation) Augmenté est une évolution du système RAG avec Enrichissement du Contexte. Il ajoute les fonctionnalités suivantes :

- **Pondération dynamique adaptative** des sources de données
- **Extraction avancée de contraintes** depuis les requêtes en langage naturel
- **Ajustement automatique** des paramètres basé sur l'historique des requêtes
- **Prompts personnalisés** selon le type de requête identifié

## Architecture

Le système s'articule autour de deux composants principaux :

1. **AugmentedRetrievalManager** (`src/enhanced_retrieval.py`)
   - Étend les capacités du `EnhancedContextManager`
   - Implémente l'extraction avancée de contraintes et la pondération dynamique
   - Maintient un historique des requêtes pour l'apprentissage

2. **AugmentedRAGWorkflow** (`src/augmented_rag.py`)
   - Étend le `EnhancedRAGWorkflow` avec les capacités augmentées
   - Ajoute des templates de prompts adaptés au type de requête
   - Offre une gestion de cache avancée avec tags multiples

## Utilisation

### Installation et configuration

```python
from src.augmented_rag import AugmentedRAGWorkflow
from src.redis_operations import RedisOperations

# Initialisation avec Redis pour le cache
redis_ops = RedisOperations(redis_url)
rag = AugmentedRAGWorkflow(
    model_name="gpt-4",
    embedding_model="all-MiniLM-L6-v2",
    redis_ops=redis_ops
)

# Initialisation du système
await rag.initialize()
```

### Requêtes simples

```python
# Requête avec pondération dynamique et prompts adaptatifs
response = await rag.query_augmented(
    "Comment ont évolué les frais de transaction sur le réseau Lightning pendant le dernier mois?"
)

# Récupération de la réponse générée
answer = response["response"]
```

### Requêtes avec paramètres personnalisés

```python
# Requête avec paramètres avancés
response = await rag.query_augmented(
    "Quelles sont les meilleures stratégies de frais basées sur les hypothèses validées?",
    top_k=8,  # Plus de documents de contexte
    dynamic_weighting=True,  # Pondération dynamique activée
    use_adaptive_prompt=True,  # Adaptation du prompt au type de requête
    cache_ttl=7200  # Cache valide 2 heures
)
```

## Fonctionnalités principales

### 1. Extraction avancée de contraintes

Le système détecte automatiquement des contraintes implicites dans les requêtes :

| Expression dans la requête | Contrainte extraite |
|----------------------------|---------------------|
| "aujourd'hui" | Filtre sur la journée courante |
| "hier" | Filtre sur la journée précédente |
| "cette semaine" | Filtre sur la semaine en cours |
| "dernier mois" | Filtre sur le mois précédent |
| "informations sur les métriques" | Filtre sur les documents de métriques |
| "hypothèses validées" | Filtre sur les documents d'hypothèses |

### 2. Pondération dynamique des sources

Le système ajuste automatiquement l'importance relative des sources de données :

```python
# Les poids par défaut des sources
source_weights = {
    "metrics_history": 1.0,  # Documents de métriques
    "hypothesis": 0.8,       # Documents d'hypothèses
    "documentation": 0.7,    # Documentation technique
    "logs": 0.6              # Journaux d'événements
}
```

Ces poids sont ajustés dynamiquement en fonction :
- Des mots-clés présents dans la requête
- Du type de requête détecté (technique, historique, prédictive)
- Des contraintes extraites
- De l'historique des requêtes passées

### 3. Prompts adaptatifs

Le système utilise différents templates de prompts selon le type de requête :

| Type de requête | Template de prompt |
|-----------------|-------------------|
| Technique | "Voici des informations techniques sur {sujet}: {contexte}\n\nRépondez à cette question technique: {requête}" |
| Historique | "Voici des données historiques concernant {sujet}: {contexte}\n\nRépondez à cette question sur l'historique: {requête}" |
| Prédictive | "Voici des informations pertinentes pour établir une prédiction: {contexte}\n\nRépondez à cette demande de prédiction: {requête}" |

### 4. Gestion avancée du cache

Le système implémente un cache intelligent avec des tags multiples :

- **Tags de type de requête** : `query_type:technical`, `query_type:historical`, etc.
- **Tags de source** : `source:metrics_history`, `source:documentation`, etc.

Cela permet une invalidation ciblée du cache :

```python
# Invalider uniquement les entrées liées aux métriques
await rag.invalidate_cache_by_tag("source:metrics_history")

# Invalider uniquement les requêtes prédictives
await rag.invalidate_cache_by_tag("query_type:predictive")
```

## Évolution et apprentissage

Le système s'améliore avec l'usage grâce à l'analyse des requêtes :

```python
# Rafraîchir les poids des sources avec des requêtes représentatives
updated_weights = await rag.refresh_source_weights([
    "Comment fonctionne le routage dans Lightning?",
    "Quelle est l'évolution des performances récemment?",
    "Quelles hypothèses ont été validées pour les frais optimaux?"
])
```

## Exemples d'utilisation

### Analyse de performance historique

```python
response = await rag.query_augmented(
    "Comment ont évolué les performances du réseau depuis le mois dernier?"
)
```

Le système :
1. Identifie une requête de type "historique"
2. Extrait la contrainte temporelle ("mois dernier")
3. Augmente le poids des sources "metrics_history"
4. Utilise le template de prompt adapté aux requêtes historiques

### Recommandation basée sur hypothèses

```python
response = await rag.query_augmented(
    "Quelle stratégie de frais recommandes-tu pour optimiser les revenus?"
)
```

Le système :
1. Identifie une requête de type "prédictive"
2. Augmente le poids des sources "hypothesis"
3. Utilise le template de prompt adapté aux requêtes prédictives

## Intégration avec d'autres systèmes

Le système RAG Augmenté peut être facilement intégré dans des applications existantes :

```python
# Exemple d'intégration dans une API FastAPI
@app.post("/query")
async def process_query(query_request: QueryRequest):
    rag = get_rag_workflow()  # Récupérer l'instance du workflow
    
    response = await rag.query_augmented(
        query_request.query,
        top_k=query_request.top_k or 5,
        dynamic_weighting=query_request.dynamic_weighting or True
    )
    
    return {
        "answer": response["response"],
        "query_type": response["query_type"],
        "processing_time": response.get("metadata", {}).get("processing_time")
    }
```

## Performance et limitations

- **Temps de traitement** : L'extraction avancée ajoute ~50-100ms au temps de traitement
- **Utilisation mémoire** : L'historique des requêtes peut consommer de la mémoire supplémentaire
- **Précision** : Les performances dépendent de la qualité des sources et de leur diversité

## Évolutions futures

- Intégration d'un modèle NLP dédié pour l'extraction de contraintes
- Apprentissage automatique des poids optimaux par retour utilisateur
- Enrichissement dynamique du contexte basé sur les questions de suivi
- Support multilingue pour l'extraction de contraintes 