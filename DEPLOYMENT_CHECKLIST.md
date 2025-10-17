# ✅ Checklist de Déploiement Production MCP sur Hostinger

> **Date:** 16 octobre 2025  
> **Version:** 1.0.0  
> **Objectif:** Déploiement production stable avec mode shadow

---

## 📦 Fichiers Générés

### Configuration
- ✅ `config_production_hostinger.env` - Template de configuration avec clés générées
- ✅ `.env.production` - À créer sur le serveur (copie de config_production_hostinger.env)

### Scripts
- ✅ `deploy_to_hostinger.sh` - Script de déploiement automatisé
- ✅ `scripts/validate_deployment.sh` - Validation post-déploiement
- ✅ `scripts/backup_daily.sh` - Backup automatique quotidien
- ✅ `scripts/configure_nginx_production.sh` - Configuration Nginx (existant)

### Documentation
- ✅ `DEPLOY_HOSTINGER_PRODUCTION.md` - Guide complet de déploiement
- ✅ `DEPLOYMENT_CHECKLIST.md` - Cette checklist

### Configuration Docker
- ✅ `docker-compose.production.yml` - Configuration production validée

---

## 🔐 Clés de Sécurité Générées

Les clés suivantes ont été automatiquement générées :

```bash
JWT_SECRET=wJI5rn-opEt9P20sRYvairf7UQ43Y6SWRdFDpy8N6uY
SECRET_KEY=ex3Q7sKFN7EAxXtBCsyog3PQp-kajD1HPM3HewC6luw
JWT_SECRET_KEY=Pkq11JrTYC9ysOkK05Y3t_vq8x5nKO_I2CnGOWS9wlI
SECURITY_SECRET_KEY=Qgendr-lcmpNNpBrXSFILg9A8jkKpI5eUHLJ33lQ0iU
MACAROON_ENCRYPTION_KEY=zuS_fcVzbaCwbx7bl4TK6wRazudNYNDVibB8E7aIzpk=
```

⚠️ **Ces clés sont déjà incluses dans `config_production_hostinger.env`**

---

## 📋 Checklist Avant Déploiement

### 1. Services Cloud (OBLIGATOIRE)

- [ ] **MongoDB Atlas**
  - [ ] Compte créé sur https://cloud.mongodb.com
  - [ ] Cluster créé (M0 gratuit OK)
  - [ ] Utilisateur database créé
  - [ ] Network access configuré (0.0.0.0/0 ou IP spécifique)
  - [ ] Connection string obtenue
  - [ ] Testé la connexion

- [ ] **Redis Upstash**
  - [ ] Compte créé sur https://upstash.com
  - [ ] Database Redis créée
  - [ ] Connection string obtenue
  - [ ] Testé la connexion

- [ ] **Anthropic AI**
  - [ ] Compte créé sur https://console.anthropic.com
  - [ ] API key générée
  - [ ] Credits disponibles

### 2. Lightning Network (RECOMMANDÉ)

- [ ] **LNBits OU LND**
  - [ ] Instance accessible
  - [ ] Admin key obtenue
  - [ ] Invoice/Read key obtenue
  - [ ] Testé l'API

### 3. Notifications (OPTIONNEL)

- [ ] **Telegram Bot**
  - [ ] Bot créé via @BotFather
  - [ ] Token obtenu
  - [ ] Chat ID obtenu

### 4. Infrastructure Serveur

- [ ] **Serveur Hostinger**
  - [ ] Accès SSH configuré
  - [ ] Sudo disponible
  - [ ] Minimum 8 GB RAM
  - [ ] Minimum 100 GB disque

- [ ] **Domaine DNS**
  - [ ] Domaine configuré (ex: api.dazno.de)
  - [ ] Record A pointant vers IP du serveur
  - [ ] Propagation DNS vérifiée (ping api.dazno.de)

### 5. Préparation Locale

- [ ] Projet MCP cloné ou téléchargé
- [ ] Fichier `config_production_hostinger.env` présent
- [ ] Tous les credentials collectés et notés

---

## 🚀 Checklist de Déploiement

### Phase 1: Préparation Serveur (30 min)

- [ ] Connexion SSH au serveur
  ```bash
  ssh user@votre-serveur-hostinger.com
  ```

- [ ] Installation Docker
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  ```

- [ ] Installation Docker Compose
  ```bash
  sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  ```

- [ ] Installation Nginx + Certbot
  ```bash
  sudo apt install -y nginx certbot python3-certbot-nginx
  ```

- [ ] Déconnexion/Reconnexion (pour activer groupe docker)
  ```bash
  exit
  ssh user@votre-serveur-hostinger.com
  ```

### Phase 2: Upload du Projet (15 min)

- [ ] Création du répertoire
  ```bash
  cd /opt
  sudo mkdir -p mcp && sudo chown $USER:$USER mcp
  cd mcp
  ```

- [ ] Upload du projet (choisir une méthode)
  - [ ] **Via Git**:
    ```bash
    git clone https://github.com/votre-repo/MCP.git .
    ```
  
  - [ ] **Via SCP** (depuis votre machine locale):
    ```bash
    scp -r /chemin/local/MCP user@serveur:/opt/mcp/
    ```

- [ ] Vérification des fichiers
  ```bash
  ls -la
  ```

### Phase 3: Configuration (20 min)

- [ ] Copie du fichier de configuration
  ```bash
  cp config_production_hostinger.env .env.production
  ```

- [ ] Édition de .env.production
  ```bash
  nano .env.production
  ```

- [ ] Variables remplies (minimum):
  - [ ] `MONGO_URL` (MongoDB Atlas)
  - [ ] `REDIS_URL` (Upstash)
  - [ ] `REDIS_HOST`
  - [ ] `REDIS_PORT`
  - [ ] `REDIS_PASSWORD`
  - [ ] `LNBITS_URL` (si applicable)
  - [ ] `LNBITS_ADMIN_KEY` (si applicable)
  - [ ] `ANTHROPIC_API_KEY`
  - [ ] `TELEGRAM_BOT_TOKEN` (optionnel)
  - [ ] `TELEGRAM_CHAT_ID` (optionnel)

- [ ] Vérification DRY_RUN=true (mode shadow)
  ```bash
  grep "DRY_RUN=true" .env.production
  ```

### Phase 4: Déploiement Automatique (45 min)

- [ ] Lancement du script
  ```bash
  chmod +x deploy_to_hostinger.sh
  ./deploy_to_hostinger.sh
  ```

- [ ] Suivre les instructions à l'écran

- [ ] Confirmer le téléchargement des modèles Ollama
  - [ ] Option 1: llama3:70b (recommandé si 16+ GB RAM)
  - [ ] Option 2: llama3:8b (plus rapide, 8 GB RAM OK)

### Phase 5: Validation (15 min)

- [ ] Exécution du script de validation
  ```bash
  ./scripts/validate_deployment.sh
  ```

- [ ] Tous les tests passent (ou warnings acceptables)

- [ ] Tests manuels:
  - [ ] `curl http://localhost:8000/`
  - [ ] `curl https://api.dazno.de/`
  - [ ] Ouvrir https://api.dazno.de/docs dans navigateur

- [ ] Vérification des logs
  ```bash
  docker-compose -f docker-compose.production.yml logs -f mcp-api
  ```

- [ ] Aucune erreur critique

---

## 📊 Post-Déploiement (7-14 jours)

### Mode Shadow - Observation

- [ ] **Jour 1-7: Observation Active**
  - [ ] Vérifier logs quotidiennement
  - [ ] Analyser rapports dans `mcp-data/reports/`
  - [ ] Surveiller alertes Telegram
  - [ ] Vérifier performance (CPU, RAM, disque)

- [ ] **Jour 8-14: Validation**
  - [ ] Pas d'erreurs critiques
  - [ ] Recommandations pertinentes
  - [ ] Système stable
  - [ ] Performance acceptable

### Configuration Monitoring

- [ ] Cron job monitoring
  ```bash
  crontab -e
  # Ajouter: 0 */6 * * * cd /opt/mcp && python3 monitor_production.py >> logs/monitoring.log 2>&1
  ```

- [ ] Cron job backup
  ```bash
  # Ajouter: 0 3 * * * /opt/mcp/scripts/backup_daily.sh
  ```

- [ ] Tester backup manuel
  ```bash
  ./scripts/backup_daily.sh
  ```

### Désactivation Mode Shadow (Après validation)

⚠️ **Seulement après 7-14 jours d'observation réussie**

- [ ] Éditer .env.production
  ```bash
  nano .env.production
  # Changer: DRY_RUN=false
  ```

- [ ] Redémarrer API
  ```bash
  docker-compose -f docker-compose.production.yml restart mcp-api
  ```

- [ ] Vérifier logs
  ```bash
  docker-compose -f docker-compose.production.yml logs -f mcp-api | grep "MODE"
  # Doit afficher: "PRODUCTION MODE - Real changes enabled"
  ```

- [ ] **Surveillance renforcée 48h**
  - [ ] Vérifier logs toutes les 4h
  - [ ] Monitorer changements appliqués
  - [ ] Vérifier impact sur canaux
  - [ ] Prêt à rollback si nécessaire

---

## 🎯 Validation Finale

### Critères de Succès

- [ ] ✅ API accessible via HTTPS
- [ ] ✅ Tous les conteneurs Docker "Up"
- [ ] ✅ Aucune erreur critique dans logs
- [ ] ✅ Health check retourne 200
- [ ] ✅ Mode Shadow actif (DRY_RUN=true)
- [ ] ✅ SSL valide (A ou A+)
- [ ] ✅ Monitoring fonctionnel
- [ ] ✅ Backup automatique configuré
- [ ] ✅ Ollama modèles téléchargés
- [ ] ✅ Qdrant opérationnel

### Tests de Non-Régression

- [ ] Test endpoint health: `curl https://api.dazno.de/api/v1/health`
- [ ] Test documentation: `curl https://api.dazno.de/docs`
- [ ] Test MongoDB: Connexion OK depuis conteneur
- [ ] Test Redis: Connexion OK depuis conteneur
- [ ] Test Qdrant: `curl http://localhost:6333/health` depuis conteneur
- [ ] Test Ollama: `docker exec mcp-ollama ollama list`

---

## 📞 Support

### Ressources

- **Guide complet**: [DEPLOY_HOSTINGER_PRODUCTION.md](DEPLOY_HOSTINGER_PRODUCTION.md)
- **Status projet**: [PHASE5-STATUS.md](PHASE5-STATUS.md)
- **Roadmap**: [_SPECS/Roadmap-Production-v1.0.md](_SPECS/Roadmap-Production-v1.0.md)

### Commandes Rapides

```bash
# Status
docker-compose -f docker-compose.production.yml ps

# Logs
docker-compose -f docker-compose.production.yml logs -f

# Validation
./scripts/validate_deployment.sh

# Monitoring
python3 monitor_production.py

# Backup
./scripts/backup_daily.sh

# Restart
docker-compose -f docker-compose.production.yml restart

# Stop
docker-compose -f docker-compose.production.yml down
```

### Troubleshooting

Consulter la section **Troubleshooting** dans [DEPLOY_HOSTINGER_PRODUCTION.md](DEPLOY_HOSTINGER_PRODUCTION.md)

---

## ✅ Sign-off

- [ ] **Déploiement initial complété**
  - Date: __________________
  - Par: __________________
  - Statut: ☐ Succès ☐ Avec warnings ☐ Échec

- [ ] **Validation 7 jours**
  - Date: __________________
  - Statut: ☐ OK ☐ Problèmes identifiés

- [ ] **Validation 14 jours**
  - Date: __________________
  - Décision: ☐ Désactiver Shadow ☐ Prolonger observation

- [ ] **Activation production (DRY_RUN=false)**
  - Date: __________________
  - Par: __________________
  - Validation 48h post-activation: ☐ OK ☐ Problèmes

---

**Dernière mise à jour:** 16 octobre 2025  
**Version:** 1.0.0

