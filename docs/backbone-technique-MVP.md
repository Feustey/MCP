Voici une nouvelle version consolidée et structurée de ton document technique **MCP (Model Context Protocol)**, conçue pour servir de backbone robuste au plan de mise en production :

---

# MCP — Backbone Technique pour l’Optimisation Autonome d’un Nœud Lightning sur Umbrel

---

## 1. Objectif Global

Déployer une application Umbrel semi-autonome capable de :

- Collecter, agréger et analyser les données d’un nœud Lightning.
- Évaluer la performance de ses canaux selon des heuristiques pondérées.
- Prendre des décisions automatisées sur les politiques de fees ou la fermeture des canaux.
- Exécuter ces décisions tout en assurant transparence, traçabilité et réversibilité.

---

## 2. Architecture Générale

### Modules Clés

1. **Ingestion**

   - Sources : Amboss, LNbits, Sparkseer, Mempool.space.
   - Format unifié JSON → stock MongoDB + cache Redis.
   - Fréquence : périodique (cron) ou évènementielle.

2. **Preprocessing**

   - Nettoyage, enrichissement, normalisation.
   - Pondération des métriques critiques.

3. **Scoring Engine**

   - Algorithme à pondérations multiples.
   - Chaque canal reçoit un score de performance.
   - Résultat : map `<channel_id>: score`.

4. **Decision Engine**

   - Évalue le score vs seuils définis.
   - Produit une `decision` : `NO_ACTION`, `INCREASE_FEES`, `DECREASE_FEES`, `CLOSE_CHANNEL`.
   - Stock dans Mongo avec horodatage.

5. **Execution Layer**

   - API vers `lncli` ou LNbits pour appliquer les politiques.
   - Dry-run supporté pour tests.
   - Logs avec possibilité de rollback.

6. **Interface (optionnelle)**

   - Dashboard Web (Next.js).
   - Historique des décisions, état des canaux, logs.

---

## 3. Glossaire

| Terme            | Définition                                                        |
| ---------------- | ----------------------------------------------------------------- |
| MCP              | Protocole orchestrant ingestion, décision et exécution.           |
| Provider         | Source de données (Amboss, LNbits, etc.).                         |
| Heuristique      | Métrique évaluant un canal (centralité, volume, frais, activité). |
| Score            | Résultat pondéré des heuristiques.                                |
| Decision         | Action à appliquer sur un canal.                                  |
| Execution Module | Partie qui applique la décision en appelant l’interface node.     |

---

## 4. Flux d’un Cas d’Usage

1. Le cron daily déclenche le module d’ingestion.
2. Les données sont nettoyées, enrichies, normalisées.
3. Le moteur de scoring évalue tous les canaux.
4. Les décisions sont prises et stockées.
5. Un second cron applique les décisions via LNbits (si mode actif).
6. Tout est loggué, archivé, traçable et réversible.

---

## 5. Déploiement Umbrel

### Structure Umbrel App

- `umbrel-app.yml` : nom, description, dépendances.
- `docker-compose.yml` : FastAPI + Redis + Mongo.
- Volumes partagés avec le node.
- UI accessible via interface Umbrel.

### Sécurité & Résilience

- Modules redémarrables individuellement.
- Timeout, retry, fallback implémentés.
- Dry-run par défaut en phase pré-prod.
- Observabilité : logs, stats, alertes (via Grafana si besoin).

---

## 6. Roadmap vers la Prod

| Étape                      | Statut | Priorité |
| -------------------------- | ------ | -------- |
| Diagramme d’architecture   | ❌     | 🔥       |
| Glossaire formel           | ⚠️     | 🔥       |
| Simulateur de nœud         | ❌     | 🔥       |
| Environnement Docker local | ⚠️     | 🔥       |
| Test unitaire scoring      | ❌     | 🔥       |
| Cron + Execution dry-run   | ❌     | ⚡       |
| Emballage Umbrel complet   | ❌     | ⚡       |
| Monitoring / Logging       | ⚠️     | ⚡       |

---
