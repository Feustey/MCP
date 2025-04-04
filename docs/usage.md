# Guide d'utilisation

## Configuration initiale

1. Assurez-vous que les services MongoDB et Redis sont en cours d'exécution
2. Configurez vos variables d'environnement dans le fichier `.env`
3. Installez les dépendances Python : `pip install -r requirements.txt`

## Utilisation de base

### Initialisation du workflow RAG

```python
from src.rag import RAGWorkflow

# Création d'une instance du workflow
rag = RAGWorkflow()

# Ingestion de documents
await rag.ingest_documents("chemin/vers/documents")
```

### Interrogation du système

```python
# Question simple
response = await rag.query("Quelle est la structure du projet ?")

# Question avec contexte spécifique
response = await rag.query(
    "Comment fonctionne le système de cache ?",
    context_docs=["cache.py", "redis_operations.py"]
)
```

### Gestion des documents

```python
from src.models import Document

# Création d'un nouveau document
doc = Document(
    content="Contenu du document",
    source="document.txt",
    embedding=[0.1] * 1536,  # Dimension des embeddings OpenAI
    metadata={"auteur": "John Doe"}
)

# Sauvegarde du document
doc_id = await rag.save_document(doc)

# Récupération du document
retrieved_doc = await rag.get_document(doc_id)
```

### Historique des requêtes

```python
# Récupération des requêtes récentes
recent_queries = await rag.get_recent_queries(limit=5)

# Statistiques du système
stats = await rag.get_system_stats()
```

## Fonctionnalités avancées

### Gestion du cache

Le système utilise Redis pour mettre en cache les réponses fréquentes. Le cache est configurable via les variables d'environnement :

```env
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600  # Durée de vie du cache en secondes
```

### Personnalisation des prompts

Les prompts système peuvent être personnalisés en modifiant les fichiers dans le dossier `prompts/` :

- `system_prompt.txt` : Prompt principal pour le modèle
- `query_prompt.txt` : Prompt pour la génération de requêtes
- `response_prompt.txt` : Prompt pour la génération de réponses

### Métriques et monitoring

Le système collecte automatiquement des métriques sur :
- Nombre total de documents
- Nombre de requêtes
- Temps de traitement moyen
- Taux de hit du cache

Ces métriques sont stockées dans MongoDB et peuvent être consultées via l'API.

## Bonnes pratiques

1. **Gestion des erreurs**
   - Toujours utiliser try/except pour gérer les erreurs potentielles
   - Vérifier les codes de retour des opérations asynchrones

2. **Performance**
   - Utiliser le cache quand c'est possible
   - Limiter la taille des documents ingérés
   - Optimiser les requêtes MongoDB

3. **Sécurité**
   - Ne jamais exposer les clés API dans le code
   - Valider les entrées utilisateur
   - Utiliser des connexions sécurisées pour MongoDB et Redis

## Dépannage

### Problèmes courants

1. **Erreurs de connexion**
   - Vérifier que les services sont en cours d'exécution
   - Vérifier les variables d'environnement
   - Vérifier les logs des services

2. **Erreurs de performance**
   - Vérifier la taille des documents
   - Optimiser les requêtes MongoDB
   - Vérifier l'utilisation du cache

3. **Erreurs de mémoire**
   - Limiter la taille des documents
   - Optimiser les requêtes
   - Vérifier les fuites de mémoire 