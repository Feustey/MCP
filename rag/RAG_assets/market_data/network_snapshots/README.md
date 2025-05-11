# Snapshots du Réseau Lightning

Ce dossier contient des snapshots du réseau Lightning Network récupérés le 6 mai 2023. Ces données servent de référence pour suivre l'évolution du réseau et pour alimenter le système RAG (Retrieval-Augmented Generation).

## Contenu des fichiers

### Données Sparkseer

- **sparkseer_ln_summary_ts.json**: Résumé temporel du réseau Lightning incluant le nombre de nœuds, le nombre de canaux et la capacité totale.
- **sparkseer_centralities.json**: Mesures de centralité pour les nœuds du réseau, indiquant leur importance dans le graphe.
- **sparkseer_channel_recommendations.json**: Recommandations de canaux pour améliorer la connectivité du réseau.
- **sparkseer_suggested_fees.json**: Suggestions de frais pour optimiser les revenus des nœuds.
- **sparkseer_outbound_liquidity_value.json**: Évaluation de la valeur de la liquidité sortante pour différents canaux.

### Données manquantes ou incomplètes

- **sparkseer_nodes.json**: Fichier vide, données non récupérées.
- **sparkseer_channels.json**: Fichier vide, données non récupérées.
- **lnbits_wallets.json**: Données LNBits non récupérées en raison d'une erreur d'authentification.
- **network_metrics.json**: Métriques réseau incomplètes car dépendantes de top_nodes et channel_metrics.

## Utilisation

Ces snapshots sont utilisés pour:

1. Fournir un contexte historique aux requêtes du système RAG
2. Servir de base de référence pour les comparaisons d'évolution du réseau
3. Alimenter les modèles d'optimisation de frais et de canal

## Notes techniques

- La collecte est effectuée via l'API Sparkseer (https://api.sparkseer.space)
- Les données sont récupérées à l'aide du script `aggregate_all.py` ou `run_aggregation.py`
- La collecte des données Amboss a été désactivée car elle nécessite une instance Redis

## Prochaines étapes

- Configurer correctement l'authentification LNBits pour récupérer les données des wallets
- Mettre en place Redis pour intégrer les données Amboss
- Programmer une actualisation périodique des données pour suivre l'évolution du réseau 