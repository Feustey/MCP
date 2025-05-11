# Plan de correction des imports
> Dernière mise à jour: 7 mai 2025

## 1. **Cartographie des modules et packages**

### Packages principaux contenant des modules partagés :
- `mcp/` : modules de scoring, heuristiques, analyse de graphe, etc.
- `src/` : logique métier, modèles, opérations Mongo, gestion réseau, RAG, etc.
- `rag/` : modules RAG spécialisés (génération, cache, évaluation…)
- `auth/` : gestion JWT, permissions, modèles utilisateurs, etc.
- `app/` : API FastAPI, routes, services, modèles API.

---

## 2. **Actions à mener**

### 2.1. **Définir le package principal**
- Choisir `src/` comme package principal pour la logique métier commune.
- Les modules partagés doivent être importés via `from src.<module> import ...` ou `from mcp.<module> import ...` selon leur emplacement.

### 2.2. **Ajouter des fichiers `__init__.py`**
- Vérifier et ajouter un fichier `__init__.py` dans :
  - `src/`
  - `mcp/`
  - `rag/`
  - `auth/`
  - `app/`
  - Tous les sous-dossiers contenant des modules à importer.

### 2.3. **Uniformiser les imports**
- Remplacer tous les imports relatifs ou ambigus par des imports absolus cohérents.
  - Exemple :  
    - `from models import Document` → `from src.models import Document` (si `models.py` est dans `src/`)
    - `from mongo_operations import ...` → `from src.mongo_operations import ...`
    - `from rag.cache_manager import ...` si le module est dans `rag/`
    - `from mcp.heuristic import Heuristic` si le module est dans `mcp/`
- Corriger tous les scripts, modules et notebooks concernés.

### 2.4. **Supprimer les manipulations de `sys.path`**
- Supprimer les ajouts manuels au `sys.path` dans les scripts (ex : dans `scripts/daily_node_analysis.py`).
- Utiliser le package principal et le `PYTHONPATH` pour permettre les imports.

### 2.5. **Vérifier les modules externes**
- S'assurer que tous les modules externes utilisés (`faiss`, `llama_index`, `redis.asyncio`, etc.) sont bien listés dans `requirements.txt` et installés.

### 2.6. **Gérer les imports conditionnels**
- Laisser les imports conditionnels pour les modules optionnels (ex : `rag_evaluator`), mais documenter leur nécessité dans le README.

### 2.7. **Automatiser la vérification**
- Ajouter un test automatique qui tente d'importer tous les modules du projet (test d'import global).
- Ajouter ce test à la CI si possible.

### 2.8. **Documenter la convention d'import**
- Ajouter une section dans le README expliquant la structure des packages et la convention d'import.

---

## 3. **Checklist de correction (à cocher au fur et à mesure)**

- [ ] Tous les dossiers de code contiennent un `__init__.py`
- [ ] Tous les imports sont absolus et cohérents (plus d'imports relatifs ou ambigus)
- [ ] Plus de manipulation de `sys.path` dans les scripts
- [ ] Tous les modules externes sont dans `requirements.txt`
- [ ] Les imports conditionnels sont documentés
- [ ] Un test d'import global existe et passe
- [ ] La convention d'import est documentée dans le README

---

## 4. **Exemples d'imports corrigés**

```python
# Mauvais
from models import Document
from mongo_operations import MongoOperations

# Bon (si les modules sont dans src/)
from src.models import Document
from src.mongo_operations import MongoOperations

# Bon (si les modules sont dans mcp/)
from mcp.heuristic import Heuristic

# Bon (pour rag/)
from rag.cache_manager import CacheManager
```

---

**Ce plan servira de référence pour corriger tous les imports et vérifier les règles Cursor.**  
Prêt à passer à la correction fichier par fichier ! 