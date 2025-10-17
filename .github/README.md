# GitHub Workflows - MCP

Ce répertoire contient les workflows GitHub Actions pour l'automatisation du CI/CD de MCP.

## 🚀 Workflows disponibles

### 1. Deploy to Hostinger Production
**Fichier:** `workflows/deploy-production.yml`

Workflow principal de déploiement automatisé en production.

**Déclenchement:**
- Automatique : Push sur `main` (excluant fichiers `.md`, `docs/`, `_SPECS/`)
- Manuel : Via interface GitHub Actions

**Jobs:**
1. **Tests & Validation** : Tests unitaires, linting, validation docker-compose
2. **Build & Push Docker** : Construction et push de l'image sur GHCR
3. **Deploy** : Déploiement sur Hostinger via SSH
4. **Smoke Tests** : Tests post-déploiement

**Durée moyenne:** 8-12 minutes

### 2. Tests
**Fichier:** `workflows/tests.yml`

Tests automatisés pour les Pull Requests et la branche develop.

**Déclenchement:**
- Pull Request vers `main` ou `develop`
- Push sur `develop`

**Jobs:**
- Tests unitaires avec pytest
- Coverage analysis
- Linting avec flake8
- Multi-version Python (3.9, 3.10)

**Durée moyenne:** 3-5 minutes

### 3. Rollback Production
**Fichier:** `workflows/rollback.yml`

Rollback manuel vers une version précédente.

**Déclenchement:**
- Manuel uniquement

**Paramètres:**
- `backup_timestamp` : Timestamp du backup ou `latest`

**Durée moyenne:** 2-3 minutes

## 🔧 Configuration

### Secrets requis

Configurez ces secrets dans `Settings > Secrets and variables > Actions` :

| Secret | Description |
|--------|-------------|
| `HOSTINGER_SSH_KEY` | Clé SSH privée pour connexion au serveur |
| `HOSTINGER_HOST` | IP ou domaine du serveur (ex: `147.79.101.32`) |
| `HOSTINGER_USER` | Utilisateur SSH (ex: `feustey`) |
| `HOSTINGER_DEPLOY_DIR` | Répertoire de déploiement (ex: `/opt/mcp`) |
| `SLACK_WEBHOOK_URL` | (Optionnel) Webhook Slack pour notifications |

### GitHub Container Registry

Les images Docker sont automatiquement poussées sur GHCR :
- Registry: `ghcr.io`
- Repository: `ghcr.io/OWNER/REPO`
- Tags: `latest`, `main-SHA`, `branch-name`

Aucune configuration supplémentaire nécessaire, `GITHUB_TOKEN` est utilisé automatiquement.

## 📋 Templates

### Issue Templates
- **deployment_issue.md** : Pour reporter des problèmes de déploiement

### Pull Request Template
- **PULL_REQUEST_TEMPLATE.md** : Template standardisé pour les PRs

## 📚 Documentation

- [Guide de configuration CI/CD](../docs/CICD_SETUP.md) - Configuration détaillée
- [Quickstart CI/CD](../CICD_QUICKSTART.md) - Démarrage rapide en 10 minutes
- [Deployment Runbook](../docs/DEPLOYMENT_RUNBOOK.md) - Procédures opérationnelles

## 🔍 Monitoring

Suivez l'état des workflows dans l'onglet `Actions` de GitHub :

1. Vue d'ensemble : Tous les runs récents
2. Filtres : Par workflow, branch, status
3. Logs détaillés : Click sur un run > job pour voir les logs

## 🚨 En cas de problème

1. **Déploiement échoué** : Vérifier les logs dans Actions
2. **Tests échoués** : Corriger les erreurs et re-push
3. **Service down après déploiement** : Utiliser le workflow Rollback
4. **Problème de connexion SSH** : Vérifier les secrets et la clé SSH

## 🎯 Best Practices

- ✅ Toujours tester localement avant de push
- ✅ Créer une PR pour review avant merge sur `main`
- ✅ Surveiller les logs de déploiement
- ✅ Vérifier la santé du service après déploiement
- ✅ Documenter les changements importants

## 🔄 Workflow de développement

```bash
# 1. Créer une branche feature
git checkout -b feature/ma-fonctionnalite

# 2. Développer et commit
git add .
git commit -m "feat: description"

# 3. Push et créer PR
git push origin feature/ma-fonctionnalite

# 4. Tests automatiques s'exécutent
# 5. Review de code
# 6. Merge vers main
# 7. Déploiement automatique en production
```

---

**Dernière mise à jour:** 17 octobre 2025

