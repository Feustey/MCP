# Analyse des Heuristiques Complexes de Hydrus pour la Sélection de Nœuds

Source : [https://github.com/aftermath2/hydrus](https://github.com/aftermath2/hydrus)

Le projet Hydrus, un agent de gestion de liquidité pour le Lightning Network, utilise une approche sophistiquée basée sur des heuristiques complexes et pondérées pour sélectionner les nœuds auxquels ouvrir de nouveaux canaux. Cette approche vise à optimiser la sélection au-delà des simples métriques de centralité.

## Facteurs Pris en Compte

Hydrus évalue plusieurs facteurs pour chaque nœud potentiel :

1.  **Capacité :** La capacité totale en BTC du nœud.
2.  **Centralité :** Diverses métriques de centralité au sein du graphe du réseau Lightning.
3.  **Canaux :**
    *   Nombre de canaux **actifs**.
    *   Âge des canaux actifs (les canaux plus anciens peuvent indiquer une stabilité).
    *   Les canaux désactivés ne sont pas pris en compte.
4.  **Politiques de Routage :**
    *   Frais appliqués par le nœud sur ses canaux.
    *   Plages de montants HTLC (min/max) acceptées.
5.  **Connectivité :**
    *   Disponibilité sur clearnet et/ou Tor.
    *   Temps de latence pour atteindre le nœud (ping).
6.  **Fonctionnalités :** Les fonctionnalités spécifiques du protocole Lightning supportées par le nœud.
7.  **Historique :**
    *   Éviction des nœuds avec lesquels un canal a été fermé récemment par l'agent Hydrus.
    *   Éviction des nœuds auxquels l'agent est déjà connecté.

## Pondération et Configuration

*   Chaque heuristique se voit attribuer un **poids** qui influence le score final du nœud.
*   Ces poids sont **configurables**, permettant aux utilisateurs d'ajuster l'algorithme selon leurs préférences ou stratégies (par exemple, privilégier des nœuds avec des frais plus bas ou une meilleure connectivité).
*   L'objectif est de classer les nœuds potentiels du réseau selon ce score composite et de tenter d'ouvrir des canaux avec les mieux classés.

## Distinction vs Autopilot (LND)

Le README de Hydrus note que cette approche multi-heuristiques est plus complète que celle d'Autopilot de LND (qui se concentre principalement sur quelques heuristiques de centralité) et offre plus de flexibilité grâce à la configuration des poids. 