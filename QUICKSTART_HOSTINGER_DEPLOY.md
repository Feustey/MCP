# 🚀 QuickStart - Déploiement MCP sur Hostinger

> **Temps estimé**: 1-2 heures  
> **Niveau**: Intermédiaire  
> **Date**: 16 octobre 2025

---

## 📦 Ce qui a été préparé pour vous

✅ **Configuration complète** avec clés de sécurité générées  
✅ **Script de déploiement automatisé**  
✅ **Script de validation**  
✅ **Script de backup automatique**  
✅ **Documentation complète**

---

## ⚡ Déploiement en 5 étapes

### 1️⃣ Préparez vos Credentials (15 min)

Collectez les informations suivantes :

#### Obligatoire :
- **MongoDB Atlas**: https://cloud.mongodb.com → Créer un cluster → Copier connection string
- **Redis Upstash**: https://upstash.com → Créer une database → Copier URL
- **Anthropic API**: https://console.anthropic.com → Créer une clé

#### Recommandé :
- **LNBits**: URL + Admin Key
- **Telegram Bot**: Token + Chat ID (pour alertes)

---

### 2️⃣ Connectez-vous au Serveur (2 min)

```bash
ssh user@votre-serveur-hostinger.com
```

---

### 3️⃣ Installez les Prérequis (10 min)

```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Nginx + Certbot
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx

# Déconnectez-vous et reconnectez-vous
exit
ssh user@votre-serveur-hostinger.com
```

---

### 4️⃣ Déployez MCP (30 min)

```bash
# Créer répertoire
cd /opt
sudo mkdir -p mcp && sudo chown $USER:$USER mcp
cd mcp

# Cloner le projet (ou upload via SCP)
git clone https://github.com/votre-repo/MCP.git .

# Configurer
cp config_production_hostinger.env .env.production
nano .env.production
# Remplir: MONGO_URL, REDIS_URL, ANTHROPIC_API_KEY, etc.

# Déployer
chmod +x deploy_to_hostinger.sh
./deploy_to_hostinger.sh
```

Le script va :
- ✅ Configurer Nginx
- ✅ Obtenir certificat SSL
- ✅ Démarrer les services Docker
- ✅ Télécharger les modèles Ollama
- ✅ Valider le déploiement

---

### 5️⃣ Validez (5 min)

```bash
# Script de validation
./scripts/validate_deployment.sh

# Tests manuels
curl https://api.dazno.de/api/v1/health

# Ouvrir dans navigateur
# https://api.dazno.de/docs
```

---

## ✅ C'est tout !

Votre MCP est maintenant déployé en **Mode Shadow** (observation uniquement).

### Prochaines étapes :

1. **Observer 7-14 jours** : Le système va collecter des données et générer des recommandations
2. **Analyser les rapports** : Consulter `mcp-data/reports/`
3. **Valider** : Vérifier que les recommandations sont pertinentes
4. **Activer** : Après validation, désactiver le mode shadow

---

## 📊 Monitoring Quotidien

```bash
# Status rapide
docker-compose -f docker-compose.production.yml ps

# Logs
docker-compose -f docker-compose.production.yml logs -f mcp-api

# Monitoring
python3 monitor_production.py
```

---

## 🆘 Besoin d'Aide ?

- **Guide complet** : [DEPLOY_HOSTINGER_PRODUCTION.md](DEPLOY_HOSTINGER_PRODUCTION.md)
- **Checklist détaillée** : [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **Troubleshooting** : Voir section dans guide complet

---

## 📝 Configuration Minimale .env.production

```bash
# Mode
DRY_RUN=true  # Mode shadow

# Database
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/mcp_prod
REDIS_URL=redis://default:pass@redis.upstash.io:6379

# IA
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Lightning (optionnel)
LNBITS_URL=https://your-lnbits.com
LNBITS_ADMIN_KEY=xxxxx

# Notifications (optionnel)
TELEGRAM_BOT_TOKEN=xxxxx
TELEGRAM_CHAT_ID=xxxxx
```

Les clés de sécurité (JWT_SECRET, etc.) sont **déjà générées** dans `config_production_hostinger.env`.

---

## 🎯 Critères de Succès

✅ API accessible via HTTPS  
✅ Certificat SSL valide  
✅ Tous les conteneurs "Up"  
✅ Aucune erreur critique  
✅ Mode Shadow actif  

---

**Bon déploiement ! 🚀**

