# Documentation sur la collecte de données
> Dernière mise à jour: 7 mai 2025

# Collecte et analyse de données Lightning Network

## Système de collecte de données

### Architecture de collecte
- **Collecteurs modulaires** : Infrastructure permettant d'intégrer facilement de nouvelles sources de données
- **Pipeline de traitement** : Extraction → Nettoyage → Transformation → Stockage → Analyse
- **Intégration MCP-llama** : Utilisation d'agents intelligents pour l'interprétation des données et la génération de recommandations
- **Stockage hybride** : MongoDB pour les données structurées, système de fichiers pour les données volumineuses

### Périodicité de collecte
- **Temps réel** : Événements de forwarding, changements d'état des canaux
- **Horaire** : Métriques de performance, équilibrage des canaux
- **Quotidienne** : Analyse approfondie, calcul des scores, génération de rapports

## Analyse des sources de données Lightning Network

### Sources actuellement intégrées
1. **LND API** 
   - Métriques des canaux, forwarding events, balance de liquidité
   - Politiques de routage et frais appliqués

2. **Amboss.Space API**
   - Données de réputation et scores des nœuds
   - Utilisées pour la sélection optimale des pairs

3. **Mempool.Space API**
   - Surveillance des frais on-chain et de la congestion
   - Optimisation du timing des opérations d'ouverture/fermeture

### Sources à intégrer (développement en cours)
1. **LNRouter**
   - Analyse topologique du réseau
   - Optimisation des routes et identification des nœuds stratégiques

2. **Lightning Terminal**
   - Automatisation de l'équilibrage des canaux
   - Optimisation des ratios de liquidité locale/distante

## État actuel du RAG

### Structure organisationnelle
- **Documents** : Base de connaissances référentielles
- **Nodes** : Données historiques et configurations par nœud
- **Reports** : Analyses de performance et recommandations

### Cycle de mise à jour
- **Métriques** : Collectées et analysées quotidiennement
- **Logs** : Agrégés en temps réel
- **Market data** : Mise à jour quotidienne ou à chaque changement significatif

### EnrichedNode (Nouveau module)
- Agrégation de métadonnées multi-sources en un objet unifié
- Facilite l'analyse et la prise de décision en fournissant une vue holistique
- Permet des analyses comparatives avancées entre différentes configurations

## Utilisation des données collectées

### Optimisation heuristique
- Scoring multi-factoriel des nœuds candidats pour ouverture de canaux
- Évaluation continue de la performance des canaux existants
- Ajustement automatique des politiques de frais basé sur l'historique de routing

### Tests A/B automatisés
- Comparaison systématique de différentes configurations
- Isolement des variables pour mesurer l'impact individuel
- Agrégation des résultats pour des recommandations basées sur les données

### Analyse prédictive (en développement)
- Modélisation du comportement du réseau pour anticiper les besoins de liquidité
- Prédiction des opportunités de routing basée sur des patterns historiques
- Recommandations proactives d'ajustement de configuration
