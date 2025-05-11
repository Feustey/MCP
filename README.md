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
