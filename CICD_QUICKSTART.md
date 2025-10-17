# 🚀 CI/CD Quickstart - MCP

> Guide de démarrage rapide pour activer le CI/CD en 10 minutes

## ⚡ Configuration rapide (10 minutes)

### 1️⃣ Générer la clé SSH (2 min)

```bash
# Sur votre machine locale
ssh-keygen -t ed25519 -C "github-actions@mcp" -f ~/.ssh/github-actions-mcp

# Afficher la clé publique
cat ~/.ssh/github-actions-mcp.pub
```

👉 **Copier la clé publique** affichée

### 2️⃣ Configurer le serveur (3 min)

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32

# Ajouter la clé publique
echo "COLLER_LA_CLE_PUBLIQUE_ICI" >> ~/.ssh/authorized_keys

# Créer les répertoires
sudo mkdir -p /opt/mcp /opt/mcp-backups
sudo chown $USER:$USER /opt/mcp /opt/mcp-backups

# Vérifier que docker fonctionne sans sudo
docker ps

# Si erreur, ajouter au groupe docker
sudo usermod -aG docker $USER
# Puis se déconnecter et reconnecter
```

### 3️⃣ Configurer les secrets GitHub (3 min)

1. Allez sur votre repository GitHub
2. `Settings` → `Secrets and variables` → `Actions`
3. Cliquez sur `New repository secret`
4. Ajoutez ces secrets :

| Nom | Valeur |
|-----|--------|
| `HOSTINGER_SSH_KEY` | Contenu de `cat ~/.ssh/github-actions-mcp` (clé privée complète) |
| `HOSTINGER_HOST` | `147.79.101.32` |
| `HOSTINGER_USER` | `feustey` |
| `HOSTINGER_DEPLOY_DIR` | `/opt/mcp` |

### 4️⃣ Tester (2 min)

```bash
# Sur votre machine locale
# Push sur main déclenche le déploiement
git add .
git commit -m "feat: enable CI/CD"
git push origin main

# Ou déploiement manuel :
# GitHub → Actions → "Deploy to Hostinger Production" → Run workflow
```

## ✅ Vérification

Le workflow devrait :
1. ✅ Passer les tests
2. 🐳 Builder l'image Docker
3. 📤 Push sur GHCR
4. 🚀 Déployer sur Hostinger
5. 🏥 Health check OK

**Durée totale** : ~8-12 minutes

## 🔍 Vérifier le déploiement

```bash
# Test API
curl https://api.dazno.de/api/v1/health

# Logs sur le serveur
ssh feustey@147.79.101.32
cd /opt/mcp
sudo docker-compose -f docker-compose.production.yml logs -f
```

## 📊 Workflows disponibles

### Déploiement automatique
- Push sur `main` → Déploiement automatique

### Déploiement manuel
1. GitHub → `Actions`
2. `Deploy to Hostinger Production`
3. `Run workflow`

### Rollback
1. GitHub → `Actions`
2. `Rollback Production`
3. `Run workflow`
4. Entrer `latest` ou un timestamp

## 🐛 Problèmes fréquents

### ❌ "Permission denied (publickey)"

```bash
# Vérifier la clé sur le serveur
ssh feustey@147.79.101.32
cat ~/.ssh/authorized_keys
# La clé publique doit être présente
```

### ❌ "docker: permission denied"

```bash
ssh feustey@147.79.101.32
sudo usermod -aG docker $USER
# Déconnexion/reconnexion nécessaire
exit
```

### ❌ Health check failed

```bash
# Voir les logs
ssh feustey@147.79.101.32
cd /opt/mcp
sudo docker-compose -f docker-compose.production.yml logs mcp-api-prod
```

## 📚 Documentation complète

Pour plus de détails : `docs/CICD_SETUP.md`

## 🎉 C'est tout !

Vous avez maintenant un CI/CD fonctionnel :

- ✅ Push → Deploy automatique
- ✅ Tests automatiques
- ✅ Backups automatiques
- ✅ Rollback en 1 clic
- ✅ Health checks
- ✅ Logs traçables

**Enjoy! 🚀**

