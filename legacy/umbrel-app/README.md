# Token4Good - App Umbrel

Analyse de nœuds Lightning, collecte de métriques, RAG local.  
Compatible Umbrel Marketplace.

## Lancement local

```bash
umbrel-dev run ./umbrel-app
```

## Volumes
- Toutes les données persistantes sont stockées dans `/app/data` (monté sur `/data` par Umbrel).

## Port exposé
- 80 (redirigé vers 8080 dans le conteneur) 