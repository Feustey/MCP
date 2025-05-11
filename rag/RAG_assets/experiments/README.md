# Optimisation des Nœuds Lightning via RAG et Ollama

Ce système permet d'optimiser automatiquement la configuration des nœuds Lightning Network en utilisant une approche basée sur le RAG (Retrieval-Augmented Generation) avec Ollama.

## Prérequis

1. Python 3.9+
2. Ollama installé et en cours d'exécution
3. Accès à un nœud LNBits sur le testnet
4. Les dépendances Python listées dans `requirements.txt`

## Installation

1. Cloner le dépôt :
```bash
git clone <votre-repo>
cd <votre-repo>
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement :
```bash
cp .env.example .env
```

Éditer le fichier `.env` avec vos informations :
```
LNBITS_TESTNET_URL=https://testnet.lnbits.com
LNBITS_API_KEY=votre_api_key_testnet
OLLAMA_MODEL=llama2
```

## Utilisation

1. Lancer l'optimisation :
```bash
python optimize_feustey_config.py
```

Le script va :
- Générer 5 scénarios de configuration différents
- Tester chaque scénario sur le testnet
- Évaluer les performances
- Produire un rapport détaillé

2. Les résultats seront sauvegardés dans :
- `rag/RAG_assets/experiments/` pour les scénarios
- `rag/RAG_assets/reports/feustey/` pour les rapports

## Structure des Scénarios

Chaque scénario généré inclut :
- Structure des frais (base_fee, fee_rate)
- Stratégie de connexion
- Politique de gestion de liquidité
- Configuration de rééquilibrage

Exemple de scénario :
```json
{
  "scenario_1": {
    "name": "Équilibrage Agressif",
    "description": "Configuration optimisée pour maximiser les opportunités de routage",
    "fee_structure": {
      "base_fee_msat": 100,
      "outbound_fee_rate_ppm": 200
    },
    "connection_strategy": {
      "target_nodes": ["exchanges", "merchants"],
      "min_capacity_per_channel": 500000
    },
    "liquidity_management": {
      "target_local_ratio": 0.40,
      "rebalance_threshold": 0.30
    }
  }
}
```

## Métriques Évaluées

- Taux de succès des routages
- Revenus par satoshi verrouillé
- Frais moyens gagnés
- Qualité de l'équilibre des canaux

## Personnalisation

Vous pouvez ajuster :
- La durée des tests (`duration_minutes` dans `optimize_feustey_config.py`)
- Les poids des métriques dans `calculate_score()`
- Les paramètres de génération des scénarios dans le prompt template

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Soumettre une Pull Request

## Licence

MIT 