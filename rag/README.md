# Intégration du module RAG de MCP-llama dans MCP

## Objectif
Fusionner les capacités avancées de RAG (Retrieval-Augmented Generation), de recherche sémantique, de cache et de monitoring développées dans MCP-llama dans le projet MCP principal, tout en préservant la robustesse de l’analyse Lightning existante.

## Étapes du merge

1. **Préparation**
   - Créer une branche dédiée (ex : `feature/rag-integration`)
   - Ajouter les dépendances nécessaires dans `requirements.txt`.
   - Installer les dépendances et vérifier la compatibilité Python.

2. **Import des modules RAG**
   - Copier les fichiers suivants de MCP-llama vers un dossier `rag/` dans MCP :
     - `rag.py`, `rag_evaluator.py`, `hybrid_retriever.py`, `multilevel_cache.py`, `query_expansion.py`, `advanced_generator.py`, `init_rag.py`
   - Ajouter les tests associés dans le dossier de tests de MCP.

3. **Intégration du cache et du monitoring**
   - Intégrer `multilevel_cache.py` dans l’architecture MCP.
   - Ajouter le monitoring RAG dans le système de logs/monitoring de MCP.

4. **Fusion des API**
   - Fusionner les endpoints FastAPI de MCP-llama relatifs au RAG dans l’API principale de MCP.
   - Exposer les endpoints `/rag/query`, `/rag/stats`, `/rag/ingest`, `/rag/history`.

5. **Harmonisation du scoring et de la configuration**
   - Fusionner la logique de scoring avancée de MCP-llama avec celle de MCP.
   - Centraliser la configuration (profils, blocklist, poids).

6. **Tests et validation**
   - Exécuter tous les tests unitaires et d’intégration.
   - Ajouter des tests croisés.
   - Vérifier la performance et la stabilité de l’ensemble.

7. **Documentation**
   - Mettre à jour le README et la documentation technique.

## Règles Cursor pour l’intégration

- Toujours créer une branche dédiée pour chaque étape majeure.
- Utiliser des commits atomiques et explicites.
- Documenter chaque module importé dans le README et dans le code.
- Ajouter des tests pour chaque nouvelle fonctionnalité intégrée.
- Vérifier la compatibilité des dépendances avant tout merge.
- Utiliser les outils de linting et de formatage automatiques.
- S’assurer que tous les endpoints API sont documentés.
- Mettre à jour la documentation à chaque étape.

## Bonnes pratiques d’intégration

- Prioriser la modularité : chaque composant RAG doit pouvoir être activé/désactivé indépendamment.
- Préserver la rétrocompatibilité avec les scripts Lightning existants.
- Centraliser la gestion des erreurs et du monitoring.
- Prévoir des hooks pour l’extension future (ex : nouveaux modèles LLM, nouveaux types de recherche).

---

*Ce document doit être mis à jour à chaque étape du merge. Pour toute modification majeure, ouvrir une issue ou une pull request dédiée.*
