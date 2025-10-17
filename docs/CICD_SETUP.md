# Configuration CI/CD pour MCP

> Dernière mise à jour: 17 octobre 2025

## 📋 Vue d'ensemble

Ce document décrit la configuration complète du pipeline CI/CD pour automatiser le déploiement de MCP depuis GitHub vers Hostinger.

### Architecture CI/CD

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   GitHub    │      │   GitHub     │      │  Hostinger  │
│  Repository │ ───> │   Actions    │ ───> │   Server    │
│   (main)    │      │   Workflows  │      │   (prod)    │
└─────────────┘      └──────────────┘      └─────────────┘
      │                     │                      │
      │                     ├── Tests              │
      │                     ├── Build Docker       │
      │                     ├── Push GHCR          │
      │                     └── Deploy SSH ────────┤
      │                                            │
      └─────────── Push triggers ─────────────────┘
```

### Fonctionnalités

✅ **Déploiement automatique** : Push sur `main` → Déploiement automatique
✅ **Tests automatisés** : Tests unitaires avant chaque déploiement
✅ **Build Docker** : Images automatiquement construites et versionnées
✅ **Backup automatique** : Backup avant chaque déploiement
✅ **Rollback automatique** : En cas d'échec du health check
✅ **Rollback manuel** : Workflow dédié pour revenir à une version
✅ **Health checks** : Vérification automatique après déploiement
✅ **Notifications** : Slack (optionnel) pour suivre les déploiements

## 🔧 Configuration requise

### 1. Secrets GitHub à configurer

Dans les paramètres de votre repository GitHub (`Settings > Secrets and variables > Actions`), ajoutez les secrets suivants :

| Secret | Description | Exemple | Obligatoire |
|--------|-------------|---------|-------------|
| `HOSTINGER_SSH_KEY` | Clé SSH privée pour se connecter au serveur | Contenu de `~/.ssh/id_ed25519` | ✅ Oui |
| `HOSTINGER_HOST` | IP ou domaine du serveur Hostinger | `147.79.101.32` ou `api.dazno.de` | ✅ Oui |
| `HOSTINGER_USER` | Utilisateur SSH sur le serveur | `feustey` | ✅ Oui |
| `HOSTINGER_DEPLOY_DIR` | Répertoire de déploiement | `/opt/mcp` | ✅ Oui |
| `SLACK_WEBHOOK_URL` | (Optionnel) Webhook Slack pour notifications | `https://hooks.slack.com/...` | ❌ Non |

### 2. Préparation du serveur Hostinger

#### Étape A : Créer une clé SSH dédiée

Sur votre machine locale :

```bash
# Générer une nouvelle clé SSH pour GitHub Actions
ssh-keygen -t ed25519 -C "github-actions@mcp" -f ~/.ssh/github-actions-mcp

# Afficher la clé publique (à copier sur le serveur)
cat ~/.ssh/github-actions-mcp.pub

# Afficher la clé privée (à ajouter comme secret GitHub)
cat ~/.ssh/github-actions-mcp
```

#### Étape B : Configurer le serveur

Connectez-vous au serveur Hostinger :

```bash
ssh feustey@147.79.101.32
```

Ajoutez la clé publique aux autorisations :

```bash
# Créer le répertoire .ssh si inexistant
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Ajouter la clé publique
echo "VOTRE_CLE_PUBLIQUE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Créer les répertoires nécessaires
sudo mkdir -p /opt/mcp /opt/mcp-backups
sudo chown $USER:$USER /opt/mcp /opt/mcp-backups

# Tester la connexion
exit
```

#### Étape C : Tester la connexion SSH

Sur votre machine locale :

```bash
# Tester avec la nouvelle clé
ssh -i ~/.ssh/github-actions-mcp feustey@147.79.101.32 "echo 'Connection OK'"
```

Si cela fonctionne, vous pouvez ajouter la clé privée comme secret GitHub.

### 3. Configurer GitHub Container Registry (GHCR)

**Aucune configuration nécessaire !** 🎉

GitHub Actions utilise automatiquement `GITHUB_TOKEN` pour pousser les images sur GHCR (`ghcr.io`).

Les images seront disponibles à : `ghcr.io/votre-username/mcp:latest`

### 4. Activer GitHub Environments (Recommandé)

Pour ajouter une couche de protection supplémentaire :

1. Allez dans `Settings > Environments` de votre repository
2. Cliquez sur `New environment`
3. Nommez-le `production`
4. Configurez les protection rules :
   - **Required reviewers** : Ajoutez-vous ou des collaborateurs (optionnel)
   - **Wait timer** : Délai avant déploiement (optionnel, ex: 5 minutes)
   - **Deployment branches** : Sélectionnez `Selected branches` → `main` uniquement

Cela empêchera les déploiements accidentels depuis d'autres branches.

## 🚀 Utilisation

### Déploiement automatique

Un simple push sur la branche `main` déclenche automatiquement le workflow complet :

```bash
# Faire des modifications
git add .
git commit -m "feat: nouvelle fonctionnalité"

# Push sur main → déploiement automatique
git push origin main
```

Le workflow va :
1. ✅ Exécuter les tests
2. 🐳 Builder l'image Docker
3. 📤 Pusher sur GHCR
4. 📦 Créer un backup sur le serveur
5. 🚀 Déployer la nouvelle version
6. 🏥 Vérifier la santé de l'application
7. ✅ Valider ou rollback automatiquement

### Déploiement manuel

Si vous voulez déployer manuellement (sans push) :

1. Allez dans l'onglet `Actions` sur GitHub
2. Sélectionnez le workflow `🚀 Deploy to Hostinger Production`
3. Cliquez sur `Run workflow`
4. Choisissez la branche à déployer (généralement `main`)
5. (Optionnel) Cochez `Skip tests` si vous voulez aller plus vite
6. Cliquez sur `Run workflow`

### Rollback manuel

En cas de problème avec une version déployée :

1. Allez dans `Actions` sur GitHub
2. Sélectionnez le workflow `⏪ Rollback Production`
3. Cliquez sur `Run workflow`
4. Entrez le timestamp du backup ou `latest` pour le plus récent
5. Cliquez sur `Run workflow`

Pour trouver les timestamps disponibles, connectez-vous au serveur :

```bash
ssh feustey@147.79.101.32
ls -lh /opt/mcp-backups/
```

Exemple de timestamp : `20251017_143025`

## 📊 Monitoring des déploiements

### Logs GitHub Actions

Tous les logs de déploiement sont disponibles dans l'onglet `Actions` de votre repository :

1. Cliquez sur l'onglet `Actions`
2. Sélectionnez un workflow run
3. Cliquez sur un job pour voir les logs détaillés

### Vérification sur le serveur

Connectez-vous au serveur pour vérifier l'état :

```bash
# Se connecter
ssh feustey@147.79.101.32

# Voir les logs en temps réel
cd /opt/mcp
sudo docker-compose -f docker-compose.production.yml logs -f

# Status des containers
sudo docker-compose -f docker-compose.production.yml ps

# Voir les backups disponibles
ls -lh /opt/mcp-backups/

# Tester l'API
curl http://localhost:8000/api/v1/health
```

### Notifications

Si vous avez configuré le webhook Slack (`SLACK_WEBHOOK_URL`), vous recevrez des notifications pour :

- ✅ Déploiement réussi
- ❌ Déploiement échoué
- ⏪ Rollback effectué

Format de la notification :

```
Deployment to Hostinger: success
Commit: feat: nouvelle fonctionnalité
Author: votre-username
URL: https://api.dazno.de
```

## 🔒 Sécurité

### Bonnes pratiques

✅ **Clé SSH dédiée** : Une clé SSH spécifique pour GitHub Actions
✅ **Secrets chiffrés** : Tous les secrets sont chiffrés par GitHub
✅ **Permissions minimales** : L'utilisateur SSH n'a que les droits nécessaires
✅ **Backups automatiques** : Backup avant chaque déploiement
✅ **Rollback automatique** : En cas d'échec des health checks
✅ **Health checks** : Vérification systématique après déploiement
✅ **Environnement protégé** : Protection sur la branche `main`
✅ **Logs auditables** : Tous les déploiements sont tracés

### Rotation des clés

Il est recommandé de changer la clé SSH tous les 6 mois :

```bash
# Générer une nouvelle clé
ssh-keygen -t ed25519 -C "github-actions@mcp-$(date +%Y%m)" -f ~/.ssh/github-actions-mcp-new

# Ajouter la nouvelle clé sur le serveur
ssh feustey@147.79.101.32
echo "NOUVELLE_CLE_PUBLIQUE" >> ~/.ssh/authorized_keys

# Mettre à jour le secret GitHub HOSTINGER_SSH_KEY

# Après vérification, supprimer l'ancienne clé du serveur
```

## 🐛 Dépannage

### Problème : Déploiement échoue lors du health check

**Symptômes** : Le workflow échoue à l'étape "Verify deployment"

**Solutions** :

1. Vérifier les logs sur le serveur :
   ```bash
   ssh feustey@147.79.101.32
   cd /opt/mcp
   sudo docker-compose -f docker-compose.production.yml logs mcp-api-prod
   ```

2. Vérifier que l'API démarre correctement :
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. Vérifier les variables d'environnement :
   ```bash
   cat /opt/mcp/.env.production
   ```

### Problème : "Permission denied" lors du déploiement

**Symptômes** : Erreur SSH ou Docker permission denied

**Solutions** :

1. Vérifier que l'utilisateur est dans le groupe docker :
   ```bash
   ssh feustey@147.79.101.32
   groups
   # Devrait afficher "docker"
   
   # Si absent, ajouter :
   sudo usermod -aG docker $USER
   # Puis se déconnecter et reconnecter
   ```

2. Vérifier les permissions sudo :
   ```bash
   sudo -l
   # Devrait permettre docker-compose sans mot de passe
   ```

### Problème : L'image Docker n'est pas trouvée

**Symptômes** : "Error: image not found" lors du pull

**Solutions** :

1. Vérifier que l'image a bien été poussée sur GHCR :
   - Allez sur `https://github.com/VOTRE_USERNAME?tab=packages`
   - Vérifiez que le package `mcp` existe

2. Vérifier les permissions du package :
   - Le package doit être public ou accessible au repository
   - Allez dans Package settings → Manage Actions access

3. Vérifier le login GHCR sur le serveur :
   ```bash
   ssh feustey@147.79.101.32
   sudo docker login ghcr.io -u VOTRE_USERNAME
   # Entrer un Personal Access Token avec permission packages:read
   ```

### Problème : Rollback ne fonctionne pas

**Symptômes** : Le rollback échoue ou ne restaure pas la bonne version

**Solutions** :

1. Vérifier les backups disponibles :
   ```bash
   ssh feustey@147.79.101.32
   ls -lh /opt/mcp-backups/
   ```

2. Vérifier le contenu d'un backup :
   ```bash
   tar tzf /opt/mcp-backups/mcp-backup-TIMESTAMP.tar.gz
   ```

3. Rollback manuel si nécessaire :
   ```bash
   cd /opt/mcp
   sudo docker-compose -f docker-compose.production.yml down
   sudo tar xzf /opt/mcp-backups/mcp-backup-TIMESTAMP.tar.gz -C /opt/mcp
   sudo docker-compose -f docker-compose.production.yml up -d
   ```

## 📈 Workflows disponibles

### 1. Deploy to Hostinger Production

**Fichier** : `.github/workflows/deploy-production.yml`

**Déclenchement** :
- Push sur `main` (automatique)
- Manuel via `workflow_dispatch`

**Étapes** :
1. Tests & Validation
2. Build & Push Docker Image
3. Deploy to Hostinger
4. Smoke Tests

**Durée moyenne** : 8-12 minutes

### 2. Tests

**Fichier** : `.github/workflows/tests.yml`

**Déclenchement** :
- Pull Request vers `main` ou `develop`
- Push sur `develop`

**Étapes** :
1. Lint avec flake8
2. Tests unitaires avec pytest
3. Upload coverage sur codecov

**Durée moyenne** : 3-5 minutes

### 3. Rollback Production

**Fichier** : `.github/workflows/rollback.yml`

**Déclenchement** :
- Manuel uniquement via `workflow_dispatch`

**Paramètres** :
- `backup_timestamp` : Timestamp du backup ou `latest`

**Durée moyenne** : 2-3 minutes

## 🎯 Métriques de succès

Avec ce CI/CD en place, vous devriez atteindre :

- ⚡ **Déploiement rapide** : < 10 minutes du push au déploiement
- 🎯 **Fiabilité** : > 95% de déploiements réussis
- 🔄 **Rollback rapide** : < 3 minutes en cas de problème
- 📊 **Traçabilité** : 100% des déploiements loggés et auditables
- 🔒 **Sécurité** : 0 credential exposé, backups systématiques

## 📚 Ressources

- [Documentation GitHub Actions](https://docs.github.com/en/actions)
- [GitHub Container Registry (GHCR)](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [SSH Best Practices](https://www.ssh.com/academy/ssh/keygen)

## 🚀 Améliorations futures

Fonctionnalités à ajouter progressivement :

- [ ] **Blue-Green Deployment** : Zéro downtime
- [ ] **Canary Deployments** : Déploiement progressif (10% → 50% → 100%)
- [ ] **Tests d'intégration** : Tests automatiques post-déploiement
- [ ] **Métriques de performance** : Suivi automatique des performances
- [ ] **Notifications Telegram** : En plus de Slack
- [ ] **Dashboard de déploiement** : Vue d'ensemble des déploiements
- [ ] **Staging environment** : Environnement de staging automatique

## 📞 Support

En cas de problème avec le CI/CD :

1. **Vérifier les logs GitHub Actions** : Onglet `Actions`
2. **Vérifier les logs serveur** : `docker-compose logs`
3. **Consulter cette documentation** : Section Dépannage
4. **Rollback si nécessaire** : Workflow `Rollback Production`
5. **Contacter l'équipe** : Créer une issue GitHub

---

**Note** : Cette documentation est maintenue à jour. Toute modification du workflow CI/CD doit être reflétée ici.

