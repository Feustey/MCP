# Guide de lancement de MCP en mode production locale

# Guide d'exécution
> Dernière mise à jour: 7 mai 2025

Ce guide vous permettra de démarrer le système MCP complet en local, d'interroger les données d'un nœud, d'obtenir des recommandations et d'accéder aux tableaux de métriques.

## 1. Prérequis

### 1.1 Services requis
- **MongoDB** : Base de données principale (démarrer avec `mongod`)
- **Redis** : Système de cache et gestion des requêtes (démarrer avec `redis-server`)
- **Python 3.9** : Vérifiez avec `python3.9 --version`

### 1.2 Configuration du fichier .env

Créez un fichier `.env` à la racine du projet avec les paramètres suivants :

```
# MongoDB
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=mcp

# Redis (cache et rate limiting)
REDIS_URL=redis://localhost:6379/0

# LNBits (connexion au nœud)
LNBITS_URL=http://192.168.0.45:5000
LNBITS_API_KEY=votre_api_key_lnbits
LNBITS_ADMIN_KEY=votre_admin_key_lnbits
LNBITS_NETWORK=mainnet  # ou testnet

# OpenAI (pour les modèles)
OPENAI_API_KEY=votre_cle_openai

# LND (facultatif, pour connexion directe)
LND_HOST=localhost:10009
LND_MACAROON_PATH=/chemin/vers/.lnd/data/chain/bitcoin/mainnet/admin.macaroon
LND_TLS_CERT_PATH=/chemin/vers/.lnd/tls.cert

# Amboss (facultatif, pour enrichissement de données)
AMBOSS_API_KEY=votre_cle_amboss

# Configuration RAG
RAG_VECTOR_WEIGHT=0.7
```

## 2. Installation

### 2.1 Installation des dépendances

```bash
# Créer un environnement virtuel
python3.9 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 2.2 Initialisation de la base de données

Si c'est votre première utilisation du système, vous devez initialiser la base de données et charger les données initiales :

```bash
# Initialiser les collections MongoDB
python scripts/init_mongodb.py

# Charger les données de base pour le RAG
python rag/init_rag.py
```

## 3. Topup du wallet (pour tests et transactions)

Si vous avez besoin d'alimenter votre wallet LNBits pour les tests et scénarios, notamment sur le testnet :

```bash
# Alimenter le wallet avec 10M de sats (en plusieurs transactions)
python topup_wallet.py 10000000
```

## 4. Lancement des composants principaux

### 4.1 Serveur API principal

```bash
# Démarrer le serveur API
python server.py
```

Le serveur démarre par défaut sur http://localhost:8000 avec les endpoints API documentés.

### 4.2 Système de collecte de données

```bash
# Lancer le processus de collecte de données
python run_test_system.py
```

Ce script lance le cycle complet de collecte et d'analyse des données.

### 4.3 Optimisation des nœuds

Pour optimiser un nœud spécifique (par exemple, feustey) :

```bash
# Optimisation avec scan de liquidité
python optimize_feustey_config.py

# Optimisation sans scan de liquidité (plus rapide)
python optimize_feustey_config_no_liquidity.py
```

## 5. Interfaces d'interrogation

### 5.1 API REST

L'API REST est accessible sur http://localhost:8000 avec les endpoints suivants :

- **GET /** : Vérifier que l'API est opérationnelle
- **GET /health** : Vérifier l'état des services
- **POST /query** : Interroger le système RAG
- **GET /stats** : Récupérer les statistiques du système
- **GET /recent-queries** : Récupérer l'historique des requêtes récentes

Exemple d'appel API:
```bash
curl -X POST http://localhost:8000/query -d "query_text=Comment optimiser mon nœud lightning?"
```

### 5.2 Workflow RAG

Pour interroger directement le RAG avec des questions sur les nœuds, utilisez le script `lnbits_rag_integration.py` :

```bash
python lnbits_rag_integration.py --node-id <pubkey_du_noeud> --query "Comment améliorer la connectivité de ce nœud?"
```

### 5.3 Analyse d'un nœud spécifique

Pour collecter et analyser un nœud spécifique :

```bash
python amboss_scraper.py --node-id <pubkey_du_noeud>
```

## 6. Visualisation des métriques

### 6.1 Rapports générés

Les rapports d'analyse sont générés dans :
```
rag/RAG_assets/reports/<pubkey_du_noeud>/
```

### 6.2 Tableaux de bord

Pour visualiser les métriques collectées :

1. Les données brutes se trouvent dans `rag/RAG_assets/metrics/`
2. Les rapports d'analyse sont dans `rag/RAG_assets/reports/`
3. Les logs et outputs détaillés sont dans `rag/RAG_assets/logs/`

### 6.3 Scripts d'analyse ad-hoc

Pour générer des analyses personnalisées :

```bash
# Agréger toutes les données
python aggregate_all.py

# Lancer une agrégation spécifique
python run_aggregation.py
```

## 7. Intégration avec LNBits

Le système MCP s'intègre avec LNBits pour automatiser la collecte de données et l'optimisation :

```bash
# Lancer l'intégration
python lnbits_rag_integration.py --mode=collect
```

## 8. Tester le système complet

Pour vérifier que tout fonctionne correctement :

```bash
# Tester la connexion LNBits
python test_lnbits_connection.py

# Tester le flux API
python test_api_flow.py

# Tester la santé du système
python test_health.py
```

## 9. Script shell pour le lancement complet

Voici un script shell complet que vous pouvez utiliser pour démarrer l'ensemble du système :

```bash
#!/bin/bash

echo "Démarrage des services MCP en mode production..."

# Vérifier que MongoDB est en cours d'exécution
echo "Vérification de MongoDB..."
mongo --eval "db.serverStatus()" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "MongoDB n'est pas en cours d'exécution. Démarrage..."
    mongod --fork --logpath /var/log/mongodb.log
else
    echo "MongoDB est déjà en cours d'exécution."
fi

# Vérifier que Redis est en cours d'exécution
echo "Vérification de Redis..."
redis-cli ping >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Redis n'est pas en cours d'exécution. Démarrage..."
    redis-server --daemonize yes
else
    echo "Redis est déjà en cours d'exécution."
fi

# Activer l'environnement virtuel
echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Démarrer le serveur API
echo "Démarrage du serveur API..."
python server.py &
SERVER_PID=$!
echo "Serveur API démarré avec PID: $SERVER_PID"

# Attendre que le serveur soit prêt
echo "Attente du démarrage complet du serveur..."
sleep 5

# Tester la connexion LNBits
echo "Test de la connexion LNBits..."
python test_lnbits_connection.py
if [ $? -ne 0 ]; then
    echo "Avertissement: La connexion LNBits a échoué. Vérifiez les paramètres dans .env"
fi

# Démarrer le système de collecte de données en arrière-plan
echo "Démarrage du système de collecte de données..."
python run_test_system.py &
COLLECT_PID=$!
echo "Système de collecte démarré avec PID: $COLLECT_PID"

echo "MCP est maintenant en cours d'exécution!"
echo "Serveur API disponible sur: http://localhost:8000"
echo ""
echo "Pour arrêter le système, exécutez: kill $SERVER_PID $COLLECT_PID"
```

## 10. Dépannage

Si vous rencontrez des problèmes:

1. **Erreur de connexion MongoDB**: Vérifiez que MongoDB est bien démarré et accessible
2. **Erreur de connexion Redis**: Vérifiez que Redis est bien démarré sur le port par défaut
3. **Erreur de connexion LNBits**: Vérifiez vos clés API et URL dans le fichier .env
4. **Problèmes avec les modèles**: Vérifiez votre clé OpenAI et l'accès aux modèles

Consultez les logs pour plus de détails:
```
tail -f rag/RAG_assets/logs/mcp.log
```

## 11. Maintenance

Pour une maintenance régulière du système:

```bash
# Nettoyage des données temporaires
python clean-build.sh

# Mise à jour des dépendances
pip install -r requirements.txt --upgrade
```

Ce guide devrait vous permettre de lancer l'application MCP complète en mode production locale et d'utiliser toutes ses fonctionnalités pour collecter des données, analyser les nœuds Lightning et obtenir des recommandations basées sur l'IA.
