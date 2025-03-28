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
- Analyse de documents avec LLM (llama3.2)
- Recherche sémantique avancée
- Synthèse de réponses contextuelles

### Système de Cache
- Mise en cache Redis pour optimiser les performances
- TTL adaptés selon le type de données :
  - Données réseau : 30 minutes
  - Statistiques des nœuds : 15 minutes
  - Résultats d'optimisation : 1 heure

## 🛠️ Installation

### Installation Locale

1. Clonez le repository :
```bash
git clone https://github.com/votre-username/mcp.git
cd mcp
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Installez et démarrez Redis :
```bash
# Sur macOS avec Homebrew
brew install redis
brew services start redis

# Sur Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server
```

4. Configurez les variables d'environnement :
```bash
cp .env.example .env
# Éditez .env avec vos clés API et configuration Redis
```

### Déploiement sur Heroku

1. Créez une nouvelle application sur Heroku :
```bash
heroku create votre-app-name
```

2. Ajoutez Redis à votre application Heroku :
```bash
heroku addons:create heroku-redis:hobby-dev
```

3. Configurez les variables d'environnement sur Heroku :
```bash
heroku config:set SPARKSEER_API_KEY=votre_clé_api
```

4. Déployez l'application :
```bash
git push heroku main
```

## ⚙️ Configuration

### Variables d'Environnement Requises
```
SPARKSEER_API_KEY=votre_clé_api
REDIS_URL=redis://localhost:6379  # URL de votre instance Redis
ENVIRONMENT=development          # development ou production
```

## 🎯 Utilisation

### API Endpoints

1. **Optimisation de Nœud**
```bash
curl -X POST "https://votre-app.herokuapp.com/optimize-node" \
     -H "Content-Type: application/json" \
     -d '{"pubkey": "votre_pubkey_lightning"}'
```

2. **Vérification de Santé**
```bash
curl "https://votre-app.herokuapp.com/health"
```

### Documentation API
- Swagger UI : `https://votre-app.herokuapp.com/docs`
- ReDoc : `https://votre-app.herokuapp.com/redoc`

## 📚 Documentation des Outils

### `get_network_summary()`
Obtient un résumé historique du réseau Lightning (cache: 30 minutes).

### `get_centralities()`
Fournit des informations sur la centralité des nœuds (cache: 30 minutes).

### `get_node_stats(pubkey)`
Statistiques en temps réel pour un nœud spécifique (cache: 15 minutes).

### `get_node_history(pubkey)`
Historique des statistiques d'un nœud (cache: 15 minutes).

### `get_channel_recommendations()`
Recommandations de canaux pour votre nœud (cache: 15 minutes).

### `get_outbound_liquidity_value()`
Évaluation de la liquidité sortante (cache: 15 minutes).

### `get_suggested_fees()`
Suggestions de frais pour les canaux (cache: 15 minutes).

### `get_bid_info()`
Informations sur les enchères maximales (cache: 15 minutes).

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

