# Guide de Référence: Système RAG avec Enrichissement du Contexte

## Vue d'ensemble

Le système RAG (Retrieval-Augmented Generation) avec Enrichissement du Contexte est une évolution majeure de notre architecture RAG traditionnelle. Il permet d'exploiter efficacement toutes les sources de données disponibles (documents textuels, métriques historiques, résultats d'hypothèses) pour offrir des réponses plus précises, contextualisées et riches en informations.

## Architecture

Le système s'articule autour de deux composants principaux:

1. **EnhancedContextManager** (`src/context_enrichment.py`)
   - Gère l'indexation et la récupération de documents à partir de sources multiples
   - Implémente des stratégies de chunking adaptées à chaque type de contenu
   - Maintient un index vectoriel unifié pour la recherche sémantique

2. **EnhancedRAGWorkflow** (`src/enhanced_rag.py`)
   - Étend le RAGWorkflow standard avec des capacités d'enrichissement du contexte
   - Propose des méthodes optimisées pour la génération de réponses enrichies
   - Gère le cache intelligent avec un système de tags multi-sources

## Fonctionnalités clés

### 1. Indexation multi-collections

Le système unifie les données provenant de plusieurs collections MongoDB:
- Documents textuels
- Métriques historiques des nœuds et canaux
- Résultats d'hypothèses validées

L'index unifié est construit en appliquant des stratégies de traitement adaptées à chaque type de contenu.

### 2. Embeddings contextuels

Les embeddings sont enrichis avec des métadonnées pertinentes:
- Pour les métriques: informations sur le nœud et la période concernés
- Pour les hypothèses: type d'hypothèse et résultats globaux
- Pour les documents: informations sur le domaine et le contexte

Cette approche améliore significativement la pertinence des résultats en permettant au modèle de mieux "comprendre" chaque type de contenu.

### 3. Chunking intelligent

Contrairement à une approche "taille fixe", le système utilise des stratégies de chunking adaptées:

| Type de contenu | Stratégie de chunking |
|-----------------|------------------------|
| Documents textuels | Découpage par paragraphes avec fenêtre glissante |
| Métriques | Conservation de l'unité métrique avec formatage adapté |
| Hypothèses | Séparation entre informations générales et métriques d'impact |

### 4. Récupération Augmentée

Le système combine plusieurs approches pour optimiser la qualité et la pertinence des réponses:

#### Requêtes hybrides
- **Recherche vectorielle**: Exploite l'index vectoriel unifié pour la similarité sémantique
- **Filtrage temporel**: Applique des contraintes temporelles pour les données historiques
- **Filtrage par métadonnées**: Sélectionne les documents selon leurs métadonnées (nœud, type)
- **Récupération directe**: Complète les résultats vectoriels avec des requêtes MongoDB directes

#### Pondération dynamique des sources
- Ajuste automatiquement l'importance des différentes sources selon le type de requête:
  
  | Type de requête | Documents | Métriques | Hypothèses |
  |-----------------|-----------|-----------|------------|
  | Technique       | 1.0       | 0.5       | 0.7        |
  | Historique      | 0.6       | 1.0       | 0.5        |
  | Prédictive      | 0.5       | 0.8       | 1.0        |

#### Détection avancée de contraintes
- **Contraintes temporelles**: Détecte et interprète les expressions temporelles ("dernière semaine", "il y a 3 mois")
- **Identifiants de nœuds**: Extrait automatiquement les IDs de nœuds Lightning mentionnés
- **Types de données**: Identifie les collections pertinentes basées sur le contexte de la requête

#### Scoring multi-facteurs
- Les résultats sont classés selon une combinaison optimisée de facteurs:
  - Score de similarité vectorielle
  - Poids de source adapté au type de requête
  - Score de correspondance par mots-clés
  - Facteur temporel (récence)

## Utilisation

### Initialisation

```python
from src.enhanced_rag import EnhancedRAGWorkflow
from src.redis_operations import RedisOperations

# Initialisation avec Redis pour le cache (optionnel)
redis_ops = RedisOperations(redis_url)
rag = EnhancedRAGWorkflow(redis_ops=redis_ops)

# Initialisation et chargement/construction des index
await rag.initialize()
```

### Requêtes basiques

```python
# Requête simple
response = await rag.query_enhanced("Qu'est-ce que le réseau Lightning Network?")

# Requête avec plus de contexte
response = await rag.query_enhanced(
    "Quelles sont les performances du réseau?",
    top_k=10  # Récupérer plus de documents de contexte
)
```

### Requêtes avec contraintes

```python
from datetime import datetime, timedelta

# Requête avec contrainte temporelle
response = await rag.query_enhanced(
    "Comment ont évolué les frais de transaction?",
    time_range=(datetime.now() - timedelta(days=30), datetime.now())
)

# Filtrage par collection
response = await rag.query_enhanced(
    "Donnez-moi des exemples d'hypothèses validées",
    collection_filters={"hypotheses": True, "metrics": False, "documents": False}
)

# Requête ciblant un nœud spécifique
response = await rag.query_enhanced(
    "Quelle est la performance de ce nœud?",
    node_ids=["03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f"]
)
```

### Requêtes avec contraintes implicites

Les contraintes peuvent également être exprimées naturellement dans la requête:

```python
# Contrainte temporelle implicite
response = await rag.query_enhanced(
    "Comment ont évolué les frais pendant la dernière semaine?"
)

# Contrainte de nœud implicite
response = await rag.query_enhanced(
    "Montrez-moi les performances du nœud 03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f"
)

# Contrainte de collection implicite
response = await rag.query_enhanced(
    "Quelles hypothèses ont été validées récemment?"
)
```

### Maintien de l'index

L'index unifié doit être régulièrement rafraîchi pour intégrer les nouvelles données:

```python
# Rafraîchir l'index manuellement
await rag.refresh_unified_index()
```

Pour une mise à jour automatisée, un script de maintenance peut être programmé:

```bash
# Exécution quotidienne via cron
0 2 * * * python scripts/refresh_unified_index.py
```

## Stratégies d'enrichissement

### 1. Extraction de contraintes 

Le système extrait automatiquement les contraintes implicites des requêtes:

| Expression dans la requête | Contrainte extraite |
|----------------------------|------------------------|
| "dernière semaine" | Filtre temporel sur les 7 derniers jours |
| "il y a 3 mois" | Filtre temporel sur les 90 derniers jours |
| "nœud 03abc..." | Filtre sur l'ID du nœud mentionné |
| "hypothèses validées" | Filtre sur la collection d'hypothèses |
| "métriques de performance" | Filtre sur la collection de métriques |

### 2. Détection du type de requête

Le système classifie automatiquement les requêtes pour optimiser la récupération:

| Type de requête | Mots-clés typiques | Priorité des sources |
|-----------------|---------------------|----------------------|
| Technique | "comment fonctionne", "qu'est-ce que", "expliquer" | Documents > Hypothèses > Métriques |
| Historique | "évolution", "tendance", "changement", "passé" | Métriques > Documents > Hypothèses |
| Prédictive | "recommander", "optimiser", "futur", "suggérer" | Hypothèses > Métriques > Documents |

### 3. Formatage adaptatif

Le contexte est formaté différemment selon les types de documents récupérés:

- Les métriques sont présentées sous forme tabulaire
- Les hypothèses sont structurées avec mise en évidence des conclusions
- Les documents textuels sont organisés par pertinence

### 4. Tags de cache intelligents

Le système de cache utilise des tags spécifiques pour une invalidation ciblée:

- Tags temporels (date:YYYY-MM-DD)
- Tags de type de document (doctype:metrics_history)
- Tags de nœud (node:03abc...)
- Tags de source (source:hypothesis)

## Scénarios d'utilisation

### Analyse historique

```
REQUÊTE: "Comment ont évolué les frais moyens sur le réseau pendant la dernière année?"

[Le système identifie une requête historique, priorise les métriques temporelles 
et combine automatiquement des documents explicatifs et des métriques historiques]
```

### Recommandations basées sur hypothèses

```
REQUÊTE: "Quelle stratégie de frais a montré les meilleurs résultats?"

[Le système identifie une requête prédictive, priorise les hypothèses validées
et synthétise les conclusions]
```

### Analyse de nœud spécifique

```
REQUÊTE: "Quelles sont les performances du nœud 03864ef025d... et comment les améliorer?"

[Le système extrait l'ID du nœud, combine requête vectorielle et directe MongoDB
pour récupérer les métriques spécifiques à ce nœud]
```

### Requête multi-critères

```
REQUÊTE: "Quelles hypothèses de frais ont été validées sur les grands canaux durant le dernier mois?"

[Le système extrait trois contraintes: type d'hypothèse, période temporelle et caractéristique
des canaux, puis utilise une combinaison de recherche vectorielle et directe]
```

## Performance et limitations

- **Temps de réponse**: L'enrichissement du contexte peut augmenter légèrement le temps de traitement (~200-500ms supplémentaires)
- **Utilisation mémoire**: L'index unifié requiert plus de mémoire qu'un index standard
- **Limite de collections**: Performance optimale jusqu'à ~10 collections différentes

## Extension et maintenance

Le système est conçu pour être facilement extensible:

1. Ajout d'une nouvelle source de données:
   - Implémenter une stratégie de chunking adaptée
   - Ajouter la nouvelle source dans `_get_documents_from_all_sources()`
   - Mettre à jour l'extraction de contraintes si nécessaire

2. Optimisation des performances:
   - Ajuster les tailles de batch pour le traitement parallèle
   - Configurer les limites de documents par collection
   - Régler la fréquence de rafraîchissement de l'index unifié
   
3. Extension des capacités de récupération:
   - Ajouter de nouveaux patterns de détection de contraintes dans `_compile_extraction_patterns()`
   - Configurer de nouvelles matrices de poids dans `self.source_weights` pour des types de requêtes supplémentaires
   - Implémenter des facteurs de scoring additionnels dans `_hybrid_retrieval()` 