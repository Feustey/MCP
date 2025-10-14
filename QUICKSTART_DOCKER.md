# ⚡ Quick Start : Docker All-in-One

> Déployer MCP avec MongoDB et Redis en **5 commandes**
> 
> Temps total : **30 minutes**

---

## 🎯 Solution Choisie

**Docker All-in-One** : MongoDB + Redis + API + Nginx dans un seul docker-compose

**Avantages** :
- 💰 **Gratuit** (vs $70/mois pour services cloud)
- ⚡ **Rapide** (latence < 1ms)
- 🎯 **Simple** (1 fichier)
- 🔒 **Sécurisé** (MongoDB/Redis non exposés)

---

## 🚀 5 Commandes pour Déployer

```bash
# 1. Se connecter au serveur
ssh feustey@147.79.101.32
cd /home/feustey/mcp-production

# 2. Préparer l'environnement
cp env.hostinger.example .env
nano .env  # Changer les mots de passe et secrets

# 3. Déployer
sudo ./scripts/deploy_hostinger_docker.sh

# 4. Vérifier
docker-compose -f docker-compose.hostinger.yml ps

# 5. Tester
curl http://localhost/
```

**C'est tout !** 🎉

---

## 📝 Configuration Minimale (.env)

```bash
# Générer les secrets
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

# Éditer .env
MONGODB_PASSWORD=UnMotDePasseSecurise123!
REDIS_PASSWORD=UnAutreMotDePasseSecurise456!
SECRET_KEY=<valeur_générée>
ENCRYPTION_KEY=<valeur_générée>
LNBITS_URL=https://votre-lnbits.com
LNBITS_ADMIN_KEY=votre_cle_admin
```

---

## ✅ Validation

```bash
# Tous les containers doivent être "healthy"
docker-compose -f docker-compose.hostinger.yml ps

# Test API
curl http://localhost:8000/  # Direct
curl http://localhost/        # Via Nginx

# Test MongoDB
docker exec mcp-mongodb mongosh --eval "db.runCommand('ping')"

# Test Redis  
docker exec mcp-redis redis-cli ping
```

---

## 📊 Monitoring

```bash
# Logs en temps réel
docker-compose -f docker-compose.hostinger.yml logs -f

# Stats
docker stats

# Status
docker-compose -f docker-compose.hostinger.yml ps
```

---

## 🔧 Commandes Utiles

```bash
# Redémarrer
docker-compose -f docker-compose.hostinger.yml restart

# Arrêter
docker-compose -f docker-compose.hostinger.yml down

# Rebuild
docker-compose -f docker-compose.hostinger.yml up -d --build

# Backup MongoDB
./scripts/backup_mongodb_docker.sh
```

---

## 🔒 SSL (Optionnel)

```bash
# Obtenir certificat
certbot certonly --standalone -d api.dazno.de --agree-tos

# Copier
cp /etc/letsencrypt/live/api.dazno.de/*.pem ssl/

# Activer HTTPS dans nginx-docker.conf
nano nginx-docker.conf  # Décommenter section HTTPS

# Redémarrer
docker-compose -f docker-compose.hostinger.yml restart nginx
```

---

## 📚 Documentation Complète

- **Guide complet** : [DEPLOY_HOSTINGER_DOCKER.md](DEPLOY_HOSTINGER_DOCKER.md)
- **Troubleshooting** : [DEPLOY_HOSTINGER_DOCKER.md](DEPLOY_HOSTINGER_DOCKER.md#-troubleshooting)
- **Backup** : [DEPLOY_HOSTINGER_DOCKER.md](DEPLOY_HOSTINGER_DOCKER.md#-backup-mongodb)

---

## ✨ Résultat

Après déploiement, vous avez :

- ✅ MongoDB local (haute performance)
- ✅ Redis local (cache ultra-rapide)
- ✅ API MCP opérationnelle
- ✅ Nginx reverse proxy
- ✅ SSL/TLS (si configuré)
- ✅ Backups automatiques (après crontab)

**Coût : 0€/mois** 🎊

---

**Version** : 1.0.0  
**Date** : 13 octobre 2025  

🚀 **Enjoy !**

