# Objectif Fonctionnel MCP

> Dernière mise à jour: 25 juin 2025

## Définition précise de l'objectif

Le système MCP (Model Context Protocol) a pour objectif principal d'**optimiser automatiquement la politique de frais des canaux Lightning**, en détectant les canaux sous-performants et en ajustant dynamiquement les frais pour maximiser les revenus tout en maintenant un acheminement efficace des paiements.

### Objectif opérationnel précis

**L'application détecte un canal sous-performant depuis 48h et ajuste dynamiquement sa politique de frais selon une stratégie calibrée par type de canal.**

## Critères de détection des canaux sous-performants

Un canal est considéré sous-performant lorsqu'il remplit au moins l'un des critères suivants pendant une période de 48 heures consécutives:

1. **Taux de réussite des forwards inférieur à 70%**
   - Calcul: `forwards_réussis / tentatives_de_forwards`
   - Seuil: < 0.7

2. **Ratio d'activité inférieur à 20% par rapport à la moyenne des canaux**
   - Calcul: `forwards_canal / moyenne_forwards_tous_canaux`
   - Seuil: < 0.2

3. **Déséquilibre de liquidité extrême**
   - Calcul: `min(balance_locale, balance_distante) / capacité_totale`
   - Seuil: < 0.15 (moins de 15% de la capacité du canal est disponible d'un côté)

4. **Inefficacité des frais**
   - Calcul: `revenus_générés / (capacité_canal * jours_ouvert * 0.001)`
   - Seuil: < 0.5

5. **Score global inférieur à 45%**
   - Calcul: somme pondérée des métriques individuelles
   - Seuil: < 0.45

## Logique d'ajustement des frais

L'ajustement des frais est réalisé selon une logique différenciée par type de canal:

### 1. Canaux avec grands hubs (Major Hubs)

- **Condition de déclenchement**: Canal sous-performant avec un nœud de haute centralité (> 0.8)
- **Ajustement des frais**:
  - **Base fee**: Augmentation de 20% (max 1000 msats)
  - **Fee rate**:
    - Entrant: Augmentation de 15% (max 200 ppm)
    - Sortant: Réduction de 5% (min 50 ppm)
- **Fréquence**: Maximum une fois tous les 7 jours pour éviter les oscillations

### 2. Canaux régionaux (Regional Nodes)

- **Condition de déclenchement**: Canal sous-performant avec un nœud de centralité moyenne (0.4-0.8)
- **Ajustement des frais**:
  - **Base fee**: Augmentation de 15% (max 800 msats)
  - **Fee rate**:
    - Entrant: Augmentation de 10% (max 150 ppm)
    - Sortant: Inchangé
- **Fréquence**: Maximum une fois tous les 5 jours

### 3. Canaux de services spécialisés (Specialized Services)

- **Condition de déclenchement**: Canal sous-performant avec un nœud offrant un service spécifique
- **Ajustement des frais**:
  - **Base fee**: Augmentation de 10% (max 600 msats)
  - **Fee rate**:
    - Entrant: Augmentation de 8% (max 120 ppm)
    - Sortant: Réduction de 10% (min 30 ppm)
- **Fréquence**: Maximum une fois tous les 10 jours (stabilité privilégiée)

### 4. Canaux de volume (Volume Channels)

- **Condition de déclenchement**: Canal sous-performant avec historique de volume élevé
- **Ajustement des frais**:
  - **Base fee**: Réduction de 20% (min 300 msats)
  - **Fee rate**:
    - Entrant: Augmentation de 5% (max 100 ppm)
    - Sortant: Réduction de 15% (min 25 ppm)
- **Fréquence**: Maximum une fois tous les 3 jours (réactivité privilégiée)

## Limites et garde-fous

Pour garantir la sécurité et éviter les comportements indésirables, le système respecte les limites suivantes:

1. **Limites d'ajustement absolues**:
   - Base fee: entre 200 et 2000 msats
   - Fee rate entrant: entre 50 et 500 ppm
   - Fee rate sortant: entre 20 et 300 ppm

2. **Limites d'ajustement relatif**:
   - Maximum +/- 50% d'ajustement en une seule opération
   - Maximum +/- 100% d'ajustement sur 30 jours glissants

3. **Seuils de confiance**:
   - Score de confiance minimum: 0.65 (sur 1.0)
   - Minimum de 10 forwards sur la période d'observation
   - Au moins 72 heures d'historique du canal

4. **Circuit breakers**:
   - Arrêt automatique si détection de plus de 3 rollbacks en 24h
   - Désactivation des ajustements pendant les pannes réseau détectées
   - Mode dry-run activé automatiquement si des comportements anormaux sont détectés

## Classification des canaux

La classification des canaux est essentielle pour appliquer la stratégie d'ajustement appropriée. Elle est réalisée selon les critères suivants:

### Major Hubs
- Canaux connectés à des nœuds avec plus de 100 canaux
- Exemples: ACINQ, LNBig, Wallet of Satoshi, Bitrefill, River Financial
- Capacité généralement > 3M sats

### Regional Nodes
- Canaux connectés à des nœuds ayant une forte présence régionale
- Centralité réseau moyenne à élevée (0.4-0.8)
- Capacité généralement entre 1M et 3M sats

### Specialized Services
- Canaux connectés à des nœuds offrant des services spécifiques
- Exemples: boutiques en ligne, services de paiement spécialisés
- Identification basée sur les métadonnées et comportements historiques

### Volume Channels
- Canaux présentant historiquement un volume élevé de transactions
- Ratio volume/capacité > 0.5 sur 30 jours
- Capacité optimale pour le routage (typiquement 0.5M-2M sats)

## KPIs et Mesures de Succès

Le succès de l'optimisation est mesuré selon les indicateurs suivants:

1. **Revenu par sat de capacité**
   - Formule: `revenus_générés / capacité_totale`
   - Objectif: Augmentation de 20% sur 30 jours

2. **Taux de réussite des forwards**
   - Formule: `forwards_réussis / tentatives_de_forwards`
   - Objectif: > 85%

3. **Efficacité de la capacité**
   - Formule: `volume_acheminé / capacité_totale`
   - Objectif: > 0.7 par mois

4. **Équilibre de liquidité**
   - Formule: `min(balance_locale, balance_distante) / capacité_totale`
   - Objectif: > 0.25 en moyenne

5. **Score global MCP**
   - Formule: Agrégation pondérée de tous les scores
   - Objectif: > 0.75

## Monitoring et Rollback

Chaque ajustement de politique de frais est:

1. **Journalisé** dans un fichier JSON avec tous les paramètres
2. **Suivi** pour analyser son impact sur 24h, 72h et 168h
3. **Réversible** via un mécanisme de rollback automatique
4. **Validé** contre les garde-fous définis

Le système génère automatiquement un rapport d'analyse 7 jours après chaque modification significative, évaluant l'impact des ajustements et fournissant des recommandations futures.

---

Cet objectif fonctionnel définit précisément le comportement attendu du système MCP pour la détection et l'ajustement des canaux sous-performants, avec des critères stricts, une logique d'ajustement différenciée, et des mesures de succès concrètes. 