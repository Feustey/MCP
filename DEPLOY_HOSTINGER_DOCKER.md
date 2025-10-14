# 🐳 Déploiement MCP sur Hostinger avec Docker

> **Solution All-in-One** : MongoDB, Redis, API et Nginx dans Docker
> 
> Date: 13 octobre 2025  
> Version: 1.0.0

---

## 🎯 Vue d'Ensemble

Cette solution déploie **tous les services dans Docker** :
- ✅ MongoDB (base de données)
- ✅ Redis (cache)
- ✅ MCP API (application)
- ✅ Nginx (reverse proxy)

**Avantages** :
- 💰 **Gratuit** : Pas besoin de MongoDB Atlas ou Redis Cloud
- 🚀 **Performance** : Tout en local, latence < 1ms
- 🔒 **Sécurité** : MongoDB et Redis non exposés publiquement
- 📦 **Simple** : Un seul fichier docker-compose
- 🔄 **Portable** : Fonctionne partout

---

## 📦 Fichiers Créés

### Configuration Docker
1. ✅ **`docker-compose.hostinger.yml`** - Stack complète
2. ✅ **`mongo-init.js`** - Initialisation MongoDB
3. ✅ **`nginx-docker.conf`** - Configuration Nginx
4. ✅ **`env.hostinger.example`** - Template variables

### Scripts
5. ✅ **`scripts/deploy_hostinger_docker.sh`** - Déploiement automatique
6. ✅ **`scripts/backup_mongodb_docker.sh`** - Backup automatique

---

## 🚀 Déploiement en 5 Étapes

### Étape 1 : Préparer l'Environnement (2 min)

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32
cd /home/feustey/mcp-production

# Copier le template .env
cp env.hostinger.example .env
```

### Étape 2 : Générer les Secrets (1 min)

```bash
# Générer SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Générer ENCRYPTION_KEY
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

# Éditer .env et remplacer les valeurs
nano .env
```

**Variables à changer ABSOLUMENT** :
```bash
MONGODB_PASSWORD=UnMotDePasseSecurise123!
REDIS_PASSWORD=UnAutreMotDePasseSecurise456!
SECRET_KEY=<valeur_generee>
ENCRYPTION_KEY=<valeur_generee>
LNBITS_URL=https://votre-lnbits.com
LNBITS_ADMIN_KEY=votre_cle_admin
```

### Étape 3 : Déployer (20 min)

```bash
# Méthode 1: Script automatique (RECOMMANDÉ)
sudo ./scripts/deploy_hostinger_docker.sh

# Méthode 2: Manuel
docker-compose -f docker-compose.hostinger.yml up -d
```

**Le script va** :
- ✅ Vérifier les prérequis
- ✅ Builder les images Docker
- ✅ Démarrer tous les services
- ✅ Valider le déploiement
- ✅ Configurer SSL (optionnel)

### Étape 4 : Vérifier (2 min)

```bash
# Status des containers
docker-compose -f docker-compose.hostinger.yml ps

# Devrait afficher:
# mcp-mongodb   running (healthy)
# mcp-redis     running (healthy)
# mcp-api       running (healthy)
# mcp-nginx     running (healthy)

# Test MongoDB
docker exec mcp-mongodb mongosh --eval "db.runCommand('ping')"

# Test Redis
docker exec mcp-redis redis-cli ping

# Test API
curl http://localhost:8000/
curl http://localhost/  # Via Nginx

# Logs en temps réel
docker-compose -f docker-compose.hostinger.yml logs -f
```

### Étape 5 : Configurer SSL (10 min)

```bash
# Installer certbot (si pas déjà fait)
apt-get update
apt-get install -y certbot

# Obtenir le certificat
certbot certonly --standalone \
  -d api.dazno.de \
  --agree-tos \
  --email admin@dazno.de

# Copier les certificats
mkdir -p ssl
cp /etc/letsencrypt/live/api.dazno.de/fullchain.pem ssl/
cp /etc/letsencrypt/live/api.dazno.de/privkey.pem ssl/

# Éditer nginx-docker.conf
nano nginx-docker.conf
# Décommenter la section HTTPS (server {...} avec listen 443)

# Redémarrer Nginx
docker-compose -f docker-compose.hostinger.yml restart nginx

# Tester HTTPS
curl https://api.dazno.de/
```

---

## 💾 Backup MongoDB

### Backup Manuel

```bash
# Exécuter le script
./scripts/backup_mongodb_docker.sh

# Le backup sera créé dans:
# backups/mongodb/mongodb_mcp_prod_YYYYMMDD_HHMMSS.tar.gz
```

### Backup Automatique (Crontab)

```bash
# Éditer le crontab
crontab -e

# Ajouter (backup quotidien à 2h du matin):
0 2 * * * /home/feustey/mcp-production/scripts/backup_mongodb_docker.sh >> /home/feustey/mcp-production/logs/backup.log 2>&1

# Vérifier
crontab -l
```

### Restaurer un Backup

```bash
# Décompresser
cd backups/mongodb
tar -xzf mongodb_mcp_prod_20251013_020000.tar.gz

# Restaurer dans MongoDB
docker exec -i mcp-mongodb mongorestore \
  --username=mcpuser \
  --password=VotreMotDePasse \
  --authenticationDatabase=admin \
  --db=mcp_prod \
  /data/backup_20251013_020000/mcp_prod
```

---

## 📊 Monitoring

### Logs en Temps Réel

```bash
# Tous les services
docker-compose -f docker-compose.hostinger.yml logs -f

# Service spécifique
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api
docker-compose -f docker-compose.hostinger.yml logs -f mongodb
docker-compose -f docker-compose.hostinger.yml logs -f redis
docker-compose -f docker-compose.hostinger.yml logs -f nginx
```

### Statistics Docker

```bash
# Stats en temps réel
docker stats

# Utilisation disque
docker system df
```

### État des Services

```bash
# Status
docker-compose -f docker-compose.hostinger.yml ps

# Santé des containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## 🔧 Commandes Utiles

### Gestion des Services

```bash
# Démarrer
docker-compose -f docker-compose.hostinger.yml up -d

# Arrêter
docker-compose -f docker-compose.hostinger.yml down

# Redémarrer
docker-compose -f docker-compose.hostinger.yml restart

# Redémarrer un service spécifique
docker-compose -f docker-compose.hostinger.yml restart mcp-api

# Voir les logs
docker-compose -f docker-compose.hostinger.yml logs -f

# Rebuild et redémarrer
docker-compose -f docker-compose.hostinger.yml up -d --build
```

### Accès aux Containers

```bash
# Shell dans l'API
docker exec -it mcp-api bash

# MongoDB shell
docker exec -it mcp-mongodb mongosh -u mcpuser -p VotreMotDePasse --authenticationDatabase admin

# Redis CLI
docker exec -it mcp-redis redis-cli -a VotreRedisPassword

# Nginx shell
docker exec -it mcp-nginx sh
```

### Maintenance

```bash
# Nettoyer les images inutilisées
docker system prune -a

# Voir l'utilisation disque
docker system df

# Supprimer les volumes (⚠️ PERTE DE DONNÉES)
docker-compose -f docker-compose.hostinger.yml down -v
```

---

## 🔒 Sécurité

### Checklist de Sécurité

- [x] MongoDB non exposé publiquement (127.0.0.1 uniquement)
- [x] Redis non exposé publiquement (127.0.0.1 uniquement)
- [x] Mots de passe forts pour MongoDB et Redis
- [x] SECRET_KEY et ENCRYPTION_KEY uniques
- [x] SSL/TLS configuré (Let's Encrypt)
- [x] Headers de sécurité Nginx (HSTS, CSP, etc.)
- [x] Authentification sur toutes les APIs
- [x] Backups automatiques configurés

### Renouvellement SSL

```bash
# Renouvellement automatique (test)
certbot renew --dry-run

# Configurer le renouvellement automatique
echo "0 3 * * * certbot renew --quiet" | crontab -
```

---

## 📈 Comparaison Solutions

| Critère | Docker Local | MongoDB Atlas + Redis Cloud |
|---------|-------------|----------------------------|
| **Coût** | 💰 Gratuit | 💰💰 $70/mois |
| **Latence** | ⚡ < 1ms | 🐢 20-50ms |
| **Setup** | 🎯 5 étapes | 🔧 Multi-étapes |
| **Backups** | 📦 Manuel/script | ☁️ Automatique |
| **Scalabilité** | 📊 Limitée | 🚀 Illimitée |
| **Maintenance** | 🔧 À gérer | ☁️ Gérée |

**Recommandation** : Docker local pour commencer, migrer vers cloud si besoin.

---

## ⚠️ Troubleshooting

### Container ne démarre pas

```bash
# Voir les logs
docker-compose -f docker-compose.hostinger.yml logs <service>

# Vérifier la config
docker-compose -f docker-compose.hostinger.yml config

# Rebuild
docker-compose -f docker-compose.hostinger.yml up -d --build
```

### MongoDB connection error

```bash
# Vérifier que MongoDB tourne
docker ps | grep mongodb

# Vérifier les logs
docker logs mcp-mongodb

# Tester la connexion
docker exec mcp-mongodb mongosh --eval "db.runCommand('ping')"

# Vérifier le mot de passe dans .env
cat .env | grep MONGODB_PASSWORD
```

### API ne répond pas

```bash
# Vérifier les logs
docker logs mcp-api

# Vérifier la connectivité MongoDB/Redis
docker exec mcp-api ping mongodb
docker exec mcp-api ping redis

# Redémarrer
docker-compose -f docker-compose.hostinger.yml restart mcp-api
```

### Problème de permissions

```bash
# Réparer les permissions des répertoires
sudo chown -R $USER:$USER logs data config backups

# Vérifier
ls -la logs/ data/ config/
```

---

## 🎯 Prochaines Étapes

Après le déploiement :

1. ✅ **Configurer LNBits** dans .env
2. ✅ **Activer Shadow Mode** (21 jours)
3. ✅ **Configurer backups automatiques** (crontab)
4. ✅ **Monitoring** : `python monitor_production.py`
5. ✅ **Tests** : `python test_production_pipeline.py`

---

## 📚 Ressources

| Document | Description |
|----------|-------------|
| `docker-compose.hostinger.yml` | Configuration complète |
| `mongo-init.js` | Initialisation MongoDB |
| `nginx-docker.conf` | Configuration Nginx |
| `env.hostinger.example` | Template variables |
| `scripts/deploy_hostinger_docker.sh` | Script déploiement |
| `scripts/backup_mongodb_docker.sh` | Script backup |

---

## ✅ Checklist Complète

### Avant Déploiement
- [ ] Fichiers copiés sur serveur
- [ ] .env créé et personnalisé
- [ ] Secrets générés
- [ ] Docker et Docker Compose installés

### Déploiement
- [ ] Script deploy exécuté
- [ ] Tous containers running (healthy)
- [ ] MongoDB accessible
- [ ] Redis accessible
- [ ] API répond
- [ ] Nginx proxy fonctionne

### Après Déploiement
- [ ] SSL configuré
- [ ] Backups automatiques (crontab)
- [ ] Monitoring actif
- [ ] Tests passés
- [ ] Documentation lue

---

## 🎉 Succès !

Si tous les containers sont **healthy** et l'API répond, félicitations ! 🎊

**Votre stack MCP est maintenant opérationnelle avec** :
- MongoDB local (performance maximale)
- Redis local (cache ultra-rapide)
- API isolée et sécurisée
- Nginx avec SSL/TLS

**Coût mensuel : 0€** (vs $70+ avec services cloud)

---

**Version** : 1.0.0  
**Date** : 13 octobre 2025  
**Status** : ✅ Production Ready

🚀 **Enjoy MCP v1.0 !**

