# Vector Store Qdrant pour MCP (RAG)

Dernière mise à jour: 11 mai 2025

## Objectif
Ce document décrit l'intégration de Qdrant comme backend vectoriel pour le système RAG du projet MCP. Qdrant remplace FAISS pour la recherche sémantique et l'indexation des embeddings.

## Pourquoi Qdrant ?
- **Open source, auto-hébergeable, scalable**
- **API simple (REST/gRPC), client Python officiel**
- **Aucun lock-in cloud, facile à dockeriser**
- **Supporte la recherche vectorielle rapide (cosine, dot, euclidean)**

## Configuration Docker Compose

Ajoutez ce service à votre `docker-compose.yml` :

```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
  volumes:
    - ./data/qdrant:/qdrant/storage
  restart: unless-stopped
```

## Variables d'environnement

- `QDRANT_HOST` (défaut: `localhost`)
- `QDRANT_PORT` (défaut: `6333`)
- `QDRANT_COLLECTION` (défaut: `mcp_rag`)

## Utilisation dans le code
- Le backend FAISS est supprimé.
- Toute ingestion ou recherche vectorielle passe par le client Qdrant (`qdrant-client`).
- Voir la classe `DocumentStore` dans `rag/rag.py`.

## Ajout de documents
- Les embeddings sont générés (Ollama ou autre) puis insérés dans Qdrant via `upsert`.
- Les métadonnées (source, chunk, etc.) sont stockées dans le payload Qdrant.

## Recherche
- La méthode `search` interroge Qdrant pour obtenir les documents les plus proches d'un embedding de requête.

## Commandes utiles

- Lancer Qdrant localement :
  ```sh
  docker run -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant:latest
  ```
- Accéder à l'API REST : http://localhost:6333

## Tests
- Vérifiez l'intégration avec les scripts d'ingestion et de requête RAG.
- Les tests unitaires doivent mocker le client Qdrant.

## Migration
- Les anciens index FAISS ne sont plus utilisés.
- Les embeddings existants doivent être ré-injectés dans Qdrant si besoin.

---
Pour toute question, voir la classe `DocumentStore` ou contacter l'équipe technique MCP. 