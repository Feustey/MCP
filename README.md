# MCP - Analyseur de Réseau Lightning avec Sparkseer

Ce projet est une application Python qui permet d'analyser et d'optimiser votre présence sur le réseau Lightning en utilisant l'API Sparkseer. Il combine des fonctionnalités d'analyse de réseau avec un système RAG (Retrieval-Augmented Generation) pour fournir des insights avancés.

## 🚀 Fonctionnalités

### Analyse du Réseau
- Résumé historique du réseau Lightning (capacité, nœuds, canaux)
- Analyse de centralité des nœuds
- Statistiques en temps réel et historiques des nœuds

### Optimisation
- Recommandations de canaux
- Évaluation de la liquidité sortante
- Suggestions de frais pour les canaux existants
- Informations sur les enchères maximales

### Système RAG
- Analyse de documents avec LLM (OpenAI GPT-3.5)
- Recherche sémantique avancée
- Synthèse de réponses contextuelles

### Système de Cache
- Mise en cache Redis pour optimiser les performances
- TTL adaptés selon le type de données :
  - Données réseau : 30 minutes
  - Statistiques des nœuds : 15 minutes
  - Résultats d'optimisation : 1 heure

### Validation Lightning
- Validation des clés publiques Lightning
- Validation des identifiants de nœuds Lightning
- Conversion entre formats de clés et d'identifiants

## 🚀 Démarrage Rapide

1. **Installation des dépendances**
```bash
pip install -r requirements.txt
```

2. **Configuration des variables d'environnement**
```bash
cp .env.example .env
# Éditez .env avec vos clés API
```

3. **Démarrage du serveur**
```bash
uvicorn api:app --host 0.0.0.0 --port 8002
```

## 🔧 Utilisation

### Endpoints Principaux

1. **Optimisation de Nœud**
```bash
# Endpoint avec node_id dans le corps de la requête
curl -X POST "http://localhost:8002/optimize-node" \
     -H "Content-Type: application/json" \
     -d '{"node_id": "votre_pubkey_lightning"}'

# Endpoint avec node_id dans l'URL
curl -X POST "http://localhost:8002/node/votre_pubkey_lightning/optimize"
```

2. **Statistiques de Nœud**
```bash
curl "http://localhost:8002/node/votre_pubkey_lightning/stats"
```

3. **Historique de Nœud**
```bash
curl "http://localhost:8002/node/votre_pubkey_lightning/history"
```

4. **Validation de Clé Lightning**
```bash
curl -X POST "http://localhost:8002/lightning/validate-key" \
     -H "Content-Type: application/json" \
     -d '{"pubkey": "votre_pubkey_lightning"}'
```

5. **Validation de Node ID Lightning**
```bash
curl -X POST "http://localhost:8002/lightning/validate-node" \
     -H "Content-Type: application/json" \
     -d '{"node_id": "votre_node_id_lightning"}'
```

6. **Vérification de Santé**
```bash
curl "http://localhost:8002/health"
```

### Notes Importantes
- Pour les endpoints `/node/{node_id}/...`, le `node_id` doit être inclus dans l'URL et non dans les paramètres de requête
- Pour l'endpoint `/optimize-node`, le `node_id` doit être envoyé dans le corps de la requête au format JSON
- L'authentification est gérée par Dazlng

### Documentation API
- Swagger UI : `http://localhost:8002/docs`
- ReDoc : `http://localhost:8002/redoc`

## 📚 Documentation des Outils

### `get_network_summary()`
Obtient un résumé historique du réseau Lightning (cache: 30 minutes).

### `get_centralities()`
Fournit des informations sur la centralité des nœuds (cache: 30 minutes).

### `get_node_stats(node_id)`
Statistiques en temps réel pour un nœud spécifique (cache: 15 minutes).

### `get_node_history(node_id)`
Historique des statistiques d'un nœud (cache: 15 minutes).

### `get_channel_recommendations()`
Recommandations de canaux pour votre nœud (cache: 15 minutes).

### `get_outbound_liquidity_value()`
Évaluation de la liquidité sortante (cache: 15 minutes).

### `get_suggested_fees()`
Suggestions de frais pour les canaux (cache: 15 minutes).

### `get_bid_info()`
Informations sur les enchères maximales (cache: 15 minutes).

## ⚠️ Problèmes Connus

1. **Endpoints Requérant un node_id**
   - Les endpoints suivants nécessitent un paramètre `node_id` dans l'URL :
     - `/node/{node_id}/optimize`
     - `/node/{node_id}/history`
     - `/node/{node_id}/stats`

2. **Rate Limiting**
   - Les limites de taux sont configurées par endpoint :
     - Optimisation : 30 requêtes/minute
     - Données Sparkseer : 100 requêtes/minute
     - Health check : 300 requêtes/minute

3. **Authentification**
   - L'authentification est gérée par Dazlng

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [Sparkseer](https://sparkseer.space) pour leur API
- La communauté Lightning Network pour leur support

