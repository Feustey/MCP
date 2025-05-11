### Plan de Bataille Brutal pour MCP sur Umbrel – Objectif : Production stable et semi-autonome

---

## PHASE 1 — Assainissement & Cadrage

**1. Cartographie complète du système**

* Crée un diagramme d’architecture modulaire : ingestion > preprocessing > scoring > decision > action > logs.
* Chaque composant doit être isolé, testable, et redémarrable individuellement.

**2. Dictionnaire de données**

* Défini toutes les structures : JSON standard pour un canal, un nœud, une politique.
* Aucun champ optionnel ni ambigü. Tu veux du strict, pas du “ça dépend”.

**3. Objectif fonctionnel précis**

* Exemple : “L’app détecte un canal sous-performant depuis 48h et ajuste dynamiquement la fee base à +20%”.

---

## PHASE 2 — Environnement de Dev & Test

**1. Conteneurisation**

* Tu crées un Docker Compose : FastAPI + Redis + Mongo + Script RAG + Interface CLI ou Web.
* Tu répliques l’environnement Umbrel localement à 95%.

**2. Test unitaire & d’intégration**

* Tu écris des tests **dès maintenant** : scoring, simulation de fee updates, parsing Amboss, gestion erreurs.
* Tu tests la réponse du système à des données corrompues, absentes ou aberrantes.

**3. Simulateur de Nœud**

* Simule différents comportements de nœuds : saturé, inactif, abusé, star, etc.
* Test la prise de décision automatique de l’app avec plusieurs heuristiques actives.

---

## PHASE 3 — Core Engine “Pilotage de Fees”

**1. Heuristiques pondérées**

* Implémente les pondérations sur base de : centralité, volume, uptime, age du canal, forward activity.
* Chaque facteur doit pouvoir être désactivé via config YAML ou .env.

**2. Decision engine**

* Tu écris une fonction pure : `evaluate_channel(channel_data) -> decision`.
* Elle renvoie : NO\_ACTION / INCREASE\_FEES / LOWER\_FEES / CLOSE\_CHANNEL avec des logs explicites.

**3. Sécurité & rollback**

* Chaque update de politique est loguée, vérifiable, et réversible.
* Ajoute un dry-run mode pour valider les actions sans exécution.

---

## PHASE 4 — Intégration Umbrel & Automatisation

**1. Emballage en App Umbrel**

* Structure Umbrel : `/umbrel-app.yml`, `docker-compose.yml`, volumes mappés.
* L’UI (facultative) est accessible depuis l’interface Umbrel pour logs et contrôle manuel.

**2. Cron & Trigger**

* Un cron (ou un trigger Reactif sur nouvel event Amboss) lance l’analyse toutes les 6h.
* Si action validée → appel vers `lncli` ou `lnbits` pour modifier la politique.

**3. Observabilité**

* Logs par niveau : `INFO / WARN / ACTION / ERROR` dans Mongo ou Prometheus.
* Ajoute un dashboard minimal via Grafana ou une page web avec historique des décisions.


Voici un kit de monitoring opérationnel pour ton app sur Umbrel :

📈 prometheus.yml (minimaliste)
yaml
Copier
Modifier
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mcp-fastapi'
    metrics_path: /metrics
    static_configs:
      - targets: ['mcp-app:8000']
Place ce fichier dans /etc/prometheus/prometheus.yml si tu l’exécutes via Docker, sinon adapte selon ton environnement.

📊 Dashboard Grafana prêt à l’emploi
Nom : MCP Lightning Optimizer

Panels :
- Taux d’erreur (http_requests_total{status="500"})
- Latence moyenne /api/v1/nodes/*
- Histogramme des décisions prises (tagué par type)
- Fréquence des mises à jour de fees
- Dernière erreur critique
-Uptime de FastAPI


📦 Commandes Docker (optionnelles)
bash
Copier
Modifier
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana


---

## PHASE 5 — Production contrôlée

**1. Shadow Mode**

* L’app fonctionne 7 jours en "observation only". Elle log les actions qu’elle *aurait* prises.
* Tu compares manuellement ses décisions avec ce que tu aurais fait.

**2. Failover Plan**

* Si un module plante → le reste tourne.
* Si un provider (Amboss, LNbits) devient indisponible → fallback local ou retry backoff.

**3. Release progressive**

* Push uniquement sur ton Umbrel.
* Logs streamés.
* Aucun update auto tant qu’il reste un crash non résolu.

---

## Borne finale = MVP stable sur Umbrel

→ Scanne, évalue, ajuste automatiquement les fees selon des règles pondérées et traçables.
→ Peut être désactivé à tout moment.
→ Zéro action sans log clair et rollback immédiat possible.


