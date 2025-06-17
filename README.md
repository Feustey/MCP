# MCP - Moniteur et Contrôleur de Performance pour Lightning Network

> Système d'optimisation automatisé pour nœuds Lightning Network basé sur le testing A/B et RAG

## À propos

MCP est un système d'optimisation complet qui aide les opérateurs de nœuds Lightning à améliorer leurs performances en ajustant automatiquement les paramètres comme les frais de routage en fonction des données réelles du réseau et des tests A/B.

## Fonctionnalités principales

- **Simulateur de nœuds Lightning** - Test à grande échelle avec différents profils de nœuds (saturé, inactif, abusé, etc.)
- **Moteur d'analyse multicritère** - Évaluation avancée des performances de canaux Lightning
- **Système de rollback robuste** - Retour à l'état précédent en cas d'erreur
- **Monitoring avancé** - Tableaux de bord Grafana pour visualiser les performances
- **Pipeline de décision automatisé** - Ajustements de frais basés sur des scores de performance
- **Mode dry-run** - Test des recommandations sans appliquer les changements

## Structure du projet

```
MCP/
├── app/               # Application principale FastAPI
├── data/              # Données consolidées (métriques, rapports)
├── docker-compose.yml # Configuration des services
├── Dockerfile         # Image Docker pour MCP
├── grafana/           # Dashboards et configurations Grafana
├── rag/               # Système RAG pour analyse de données
├── scripts/           # Scripts utilitaires
├── src/               # Code source principal
│   ├── api/           # Points d'accès API
│   ├── clients/       # Clients pour services externes
│   ├── optimizers/    # Algorithmes d'optimisation
│   ├── tools/         # Outils utilitaires (simulateur)
└── tests/             # Tests unitaires et d'intégration
```

## Prérequis

- Python 3.9+
- Docker et Docker Compose
- Accès à un nœud Lightning (optionnel pour développement)

## Installation

### Installation locale

```bash
# Cloner le dépôt
git clone https://github.com/yourusername/MCP.git
cd MCP

# Installer les dépendances
make setup
```

### Démarrage avec Docker

```bash
# Construire et démarrer les services
make run-docker

# Vérifier les logs
docker-compose logs -f
```

## Utilisation

### Simuler différents profils de nœuds

```bash
make simulation
```

### Accéder aux tableaux de bord

```bash
make grafana
```
Par défaut, l'identifiant et le mot de passe sont tous deux `admin`.

### Exécuter les tests

```bash
# Tests unitaires
make test

# Tests d'intégration
make test-int
```

## Environnement de production

Pour un déploiement en production, configurez les variables d'environnement dans un fichier `.env`:

```
LNBITS_URL=https://votre-serveur-lnbits.com
LNBITS_INVOICE_READ_KEY=votre-clé-de-lecture
LNBITS_ADMIN_KEY=votre-clé-admin
```

## Shadow Mode

Par défaut, le système fonctionne en mode "shadow" (dry-run) pour observer les recommandations sans les appliquer automatiquement. Pour activer les changements automatiques, modifiez le paramètre `DRY_RUN=false` dans le fichier `.env`.

## Développement

### Pipeline de décision

Le pipeline de décision suit ce processus:
1. Collection des données du nœud
2. Évaluation multicritère par le système de scoring
3. Recommandations d'optimisation
4. Exécution contrôlée des ajustements (avec rollback si nécessaire)
5. Surveillance des performances post-modification

### Ajout de nouveaux profils de nœuds

Pour ajouter un nouveau profil de nœud dans le simulateur, modifiez `src/tools/node_simulator.py` en ajoutant vos paramètres dans le dictionnaire `NODE_BEHAVIORS`.

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Contribution

Les contributions sont les bienvenues! Veuillez consulter notre guide de contribution `CONTRIBUTING.md` avant de soumettre une pull request.

# MCP-llama

## Installation sur Umbrel

1. **Ajoutez l'application MCP via l'App Store Umbrel ou en ligne de commande.**
2. **Vérifiez que le volume LND est bien monté dans le conteneur :**
   - Le dossier `/lnd` dans le conteneur doit contenir `admin.macaroon` et `tls.cert`.
   - Le volume est défini dans `umbrel-app.yml` :
     ```yaml
     volumes:
       - mcp-data:/data
       - lnd:/lnd:ro
     ```
3. **Configurez votre fichier `.env` dans `/data` si besoin (voir `.env.example`).**
4. **Vérifiez les permissions :**
   - L'utilisateur du conteneur doit avoir accès en lecture à `/lnd/admin.macaroon` et `/lnd/tls.cert`.
   - En cas d'erreur, consultez les logs MCP ou exécutez :
     ```bash
     ls -l /lnd
     ```
5. **Démarrez l'application via l'interface Umbrel.**
6. **Accédez à l'interface MCP via le dashboard Umbrel (port 8000).**

Pour toute question, ouvrez une issue sur [le repo GitHub](https://github.com/you/mcp/issues).

## Déploiement MVP sur Umbrel (v0.1.0-beta)

### Prérequis
- Umbrel OS à jour
- Application MCP installée via l'App Store ou en ligne de commande
- Accès au volume LND (`/lnd`) et MongoDB

### Installation
1. **Installer MCP depuis l'App Store Umbrel**
2. **Vérifier le montage du volume LND**
   - `/lnd/admin.macaroon` et `/lnd/tls.cert` doivent être accessibles en lecture dans le conteneur
3. **Configurer le fichier `.env` dans `/data`**
   - Par défaut, le mode dry-run est activé (`DRYRUN=true`)
   - Pour activer les modifications réelles, passez `DRYRUN=false` (déconseillé en phase MVP)
4. **Lancer le script d'installation rapide (optionnel)**
   ```bash
   bash scripts/umbrel_install.sh
   ```
5. **Démarrer l'application via l'interface Umbrel**
6. **Accéder à l'interface MCP sur le port 8000 du dashboard**

### Logging renforcé
- Tous les logs sont stockés dans `logs/fee_optimizer.log` et `/data/logs/`
- Les erreurs critiques, rollbacks et notifications sont également envoyés via Telegram (si configuré)
- Les recommandations shadow mode sont visibles dans Grafana et via l'API `/api/v1/fee-optimizer/recommendations`

### Conseils pour la phase MVP
- **Gardez le mode dry-run activé** pour éviter toute modification réelle sur le nœud
- **Surveillez les logs et dashboards** pour détecter toute anomalie
- **Testez les rollbacks et la récupération d'erreur** avant de passer en mode actif
- **Consultez la documentation technique dans `/docs/` pour les détails d'architecture et de sécurité**

## Suivi post-déploiement & feedback

### Tableau de bord des instances déployées
- Chaque instance MCP envoie un heartbeat périodique (script `scripts/instance_heartbeat.py`) vers un serveur central ou Google Form/Sheet.
- Le payload inclut : ID d'instance, version, timestamp, statut, logs récents.
- À planifier en cron (ex : toutes les heures) :
  ```bash
  0 * * * * python3 scripts/instance_heartbeat.py
  ```
- Les données sont visualisées dans un dashboard centralisé (Grafana, Notion, Google Data Studio…)

### Canal de feedback rapide
- **Groupe Telegram testeurs** : [t.me/mcp_testers](https://t.me/mcp_testers) (exemple)
- **Formulaire Google Form** : [Lien à insérer ici]
- **Lien GitHub Issues** : https://github.com/you/mcp/issues
- Ces liens sont affichés dans l'interface MCP et dans la documentation utilisateur.

### Itérations hebdomadaires (phase MVP)
- **Semaine 1** : collecte des premiers retours, correction des bugs critiques, amélioration de la doc
- **Semaine 2** : analyse des métriques d'usage, ajustements UX, bilan intermédiaire
- **Semaine 3** : stabilisation, nettoyage, préparation de la prochaine version
- Suivi des tâches via un board Kanban (GitHub Projects, Notion, Trello)
- Récap hebdomadaire envoyé sur le canal de feedback

# Déploiement sur Hostinger

Depuis mai 2025, MongoDB et Redis doivent être installés localement sur le serveur (Hostinger). Le docker-compose ne gère plus ces services : il ne lance que l'application MCP. 

- Installez MongoDB et Redis sur votre serveur
- Configurez le fichier .env.production à la racine avec les bonnes URLs (localhost)
- Lancez MCP avec Docker ou docker-compose
