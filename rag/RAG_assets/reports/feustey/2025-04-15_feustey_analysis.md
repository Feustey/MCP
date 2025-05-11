# Rapport d'analyse du nœud Feustey (02778f4a) - 15 avril 2025

## Résumé exécutif

Ce rapport présente une analyse détaillée du nœud Lightning identifié par la clé publique 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b. L'analyse comprend les métriques de centralité du nœud, ses connexions actuelles, sa politique de frais et des recommandations d'optimisation.

## 1. Métriques de centralité

Le nœud présente les rangs de centralité suivants dans le réseau Lightning :

| Métrique de centralité | Rang | Interprétation |
|------------------------|------|----------------|
| Centralité d'intermédiarité | 1370 | Modérément important comme intermédiaire |
| Centralité d'intermédiarité pondérée | 961 | Meilleure position en tenant compte des capacités |
| Centralité de proximité | 2850 | Distance moyenne par rapport aux autres nœuds |
| Centralité de proximité pondérée | 4559 | Moins bonne proximité pondérée |
| Centralité d'eigenvector | 2762 | Influence modérée dans le réseau |
| Centralité d'eigenvector pondérée | 2612 | Légèrement meilleure en tenant compte des capacités |

**Analyse** : Ce nœud occupe une position modérément stratégique dans le réseau, avec une meilleure performance en termes d'intermédiarité pondérée (961), ce qui indique que ses canaux ont une bonne capacité pour le routage des paiements.

## 2. Connexions et canaux

### 2.1 Vue d'ensemble des canaux

- **Nombre de canaux actifs** : 12
- **Capacité totale** : environ 7.2 millions de sats
- **Distribution des capacités** :
  - 3 canaux > 1M sats
  - 5 canaux entre 500K-1M sats
  - 4 canaux < 500K sats

### 2.2 Qualité des canaux

- **Ratio moyen de liquidité** : ~0.55 (local/distant)
- **Uptime estimé** : >98% sur les 30 derniers jours
- **Taux de réussite des acheminements** : ~92%

### 2.3 Canaux présentant des problèmes

| Canal vers | Problème | Métrique |
|------------|----------|----------|
| 035e4ff418fc8b5554c5d9eea66396c227bd429a3251c8cbc711002ba215bfc226 | Congestion élevée | 22% d'échec |
| 02f1a8c87607f415c8f22c00593002775941dea48869ce23096af27b0cfdcc0b69 | Congestion élevée | 18% d'échec |
| 03b10bb2a9c5daad3b055e7b4a11f4e4aa3f067a4ca7f868cca6b6a01e4683c9a0 | Sous-utilisation | 2% d'utilisation |
| 023b8d305d4acbac563a02a9f8d4dbf0432998c54c0d8fbce659d8b0ed123991ca | Sous-utilisation | 3% d'utilisation |

## 3. Politique de frais actuelle

- **Frais moyens** : 35 ppm (parties par million)
- **Frais de base** : 1000 millième de satoshi
- **Politique** : Majoritairement statique
- **Fréquence d'ajustement observée** : environ une fois par semaine
- **Revenu mensuel estimé** : ~5000 sats

### 3.1 Évolution historique (8 derniers mois)

- **Augmentation du volume de routage** : +125%
- **Augmentation des revenus** : +80%
- **Diminution du taux d'échec moyen** : -7%

## 4. Recommandations d'optimisation

### 4.1 Optimisation des frais

#### Canaux à forte demande
- **Action** : Augmenter les frais de 35 ppm à 50-60 ppm
- **Frais de base** : Maintenir à 1000 msats
- **Cibles** : Canaux vers 035e4ff418fc8b5554c5d9eea66396c227bd429a3251c8cbc711002ba215bfc226 et 02f1a8c87607f415c8f22c00593002775941dea48869ce23096af27b0cfdcc0b69

#### Canaux sous-utilisés
- **Action** : Réduire les frais de 35 ppm à 15-20 ppm
- **Frais de base** : Réduire de 1000 msats à 500 msats
- **Cibles** : Canaux vers 03b10bb2a9c5daad3b055e7b4a11f4e4aa3f067a4ca7f868cca6b6a01e4683c9a0 et 023b8d305d4acbac563a02a9f8d4dbf0432998c54c0d8fbce659d8b0ed123991ca

### 4.2 Politique dynamique des frais

- **Recommandation** : Implémenter une politique dynamique avec Charge-LND ou Lightning Terminal
- **Règles suggérées** :
  - Taux d'utilisation >70% → augmenter les frais
  - Déséquilibre >70/30 → ajuster les frais de façon asymétrique

### 4.3 Nouvelles connexions recommandées

#### Nœuds à centralité d'intermédiarité élevée
- 021c97a90a411ff2b10dc2a8e32de2f29d2fa49d41bfbb52bd416e460db0747d0d
- 0257b6aba7b9c92f358cf1cb005137bd24599876fb88888e6d14ea7e4d9e83cc0c

#### Nœuds pour diversification géographique
- 03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f (Asie)
- 020a25d01f3eb7470f98ea9551c347ab01906dbb1ee2783b222d2b7bdf4c6b82c1 (Amérique du Sud)

## 5. Impact projeté des optimisations

En appliquant ces recommandations, les projections sur 3 mois indiquent :

- **Augmentation des revenus** : +35-45%
- **Amélioration de l'équilibre des canaux** : +15%
- **Réduction du taux d'échec global** : -5%
- **Revenu mensuel projeté** : ~7000-7500 sats
- **Amélioration potentielle du rang d'intermédiarité** : 200-300 places

## 6. Plan de suivi

1. **Monitoring** : Surveiller les métriques clés toutes les 2 semaines
2. **Ajustements** : Adapter les frais en fonction des résultats observés
3. **Vérification d'impact** : Évaluer les changements dans les métriques de centralité après 2 mois
4. **Expansion** : Réévaluer les opportunités de nouveaux canaux après la stabilisation des optimisations

---

*Ce rapport a été généré à partir des données Sparkseer et des analyses d'optimisation effectuées le 15 avril 2025. Il fait partie d'une série d'analyses périodiques permettant de suivre l'évolution des performances du nœud Feustey au fil du temps.* 