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

## 🛠️ Installation

1. Clonez le repository :
```bash
git clone https://github.com/votre-username/mcp.git
cd mcp
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurez les variables d'environnement :
```bash
cp .env.example .env
# Éditez .env avec votre clé API Sparkseer
```

## ⚙️ Configuration

Créez un fichier `.env` avec les variables suivantes :
```
SPARKSEER_API_KEY=votre_clé_api
```

## 🎯 Utilisation

1. Lancez le serveur :
```bash
python server.py
```

2. Les outils disponibles peuvent être utilisés via l'interface en ligne de commande.

## 📚 Documentation des Outils

### `get_network_summary()`
Obtient un résumé historique du réseau Lightning.

### `get_centralities()`
Fournit des informations sur la centralité des nœuds.

### `get_node_stats(pubkey)`
Statistiques en temps réel pour un nœud spécifique.

### `get_node_history(pubkey)`
Historique des statistiques d'un nœud.

### `get_channel_recommendations()`
Recommandations de canaux pour votre nœud.

### `get_outbound_liquidity_value()`
Évaluation de la liquidité sortante.

### `get_suggested_fees()`
Suggestions de frais pour les canaux.

### `get_bid_info()`
Informations sur les enchères maximales.

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

