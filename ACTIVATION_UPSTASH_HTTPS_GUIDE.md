# 🚀 Guide Activation Upstash Redis + HTTPS

> **Date**: 15 octobre 2025  
> **Objectif**: Activer Redis Cloud (Upstash) et HTTPS (Let's Encrypt)  
> **Durée estimée**: 30-45 minutes

---

## 📋 PRÉREQUIS

### 1. Compte Upstash
- [ ] Créer compte sur https://upstash.com/
- [ ] Email vérifié
- [ ] Carte bancaire (optionnel, free tier disponible)

### 2. DNS Configuré
- [ ] Domaine `api.dazno.de` pointe vers `147.79.101.32`
- [ ] Propagation DNS complète (vérifier: `dig +short api.dazno.de`)

### 3. Accès Serveur
- [ ] SSH actif: `ssh feustey@147.79.101.32`
- [ ] Privilèges sudo disponibles
- [ ] Docker en cours d'exécution

---

## 🎯 PARTIE 1: ACTIVATION UPSTASH REDIS

### Étape 1: Créer Base Redis sur Upstash

1. **Connexion**: https://console.upstash.com/
2. **Créer une base**:
   - Cliquer "Create Database"
   - **Name**: `mcp-production`
   - **Type**: Regional (Pay as you go) ou Global (plus cher)
   - **Region**: `eu-west-1` (Europe/Frankfurt)
   - **TLS**: Enabled (obligatoire)
   - **Eviction**: `allkeys-lru` (recommandé)

3. **Récupérer credentials**:
   - Onglet "Details"
   - Copier **Endpoint** et **Password**
   - Format attendu: `rediss://default:xxxxx@eu1-xxxxx.upstash.io:6379`

### Étape 2: Configuration Locale

Sur votre machine locale (dans le repo MCP):

```bash
# Créer fichier .env.production depuis le template
cp env.production.template .env.production
chmod 600 .env.production

# Éditer avec vos credentials Upstash
nano .env.production
```

**Variables à configurer**:

```bash
# Redis Upstash
REDIS_URL=rediss://default:VOTRE_PASSWORD@eu1-xxxxx.upstash.io:6379
REDIS_PASSWORD=VOTRE_PASSWORD
REDIS_TLS=true
REDIS_MAX_CONNECTIONS=10

# MongoDB (garder local pour l'instant)
MONGODB_USER=mcpuser
MONGODB_PASSWORD=VotrePasswordSecurise123!
MONGODB_DATABASE=mcp_prod

# Sécurité (générer des clés fortes)
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# LNBits (vos credentials)
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_ADMIN_KEY=your_admin_key
LNBITS_INVOICE_KEY=your_invoice_key

# Mode
ENVIRONMENT=production
DRY_RUN=true
```

### Étape 3: Transfert sur Serveur Production

```bash
# Depuis votre machine locale
scp .env.production feustey@147.79.101.32:/home/feustey/mcp-production/.env.production

# Sécuriser les permissions
ssh feustey@147.79.101.32 "chmod 600 /home/feustey/mcp-production/.env.production"
```

### Étape 4: Lancer Script d'Activation Upstash

Sur le serveur de production:

```bash
ssh feustey@147.79.101.32

cd /home/feustey/mcp-production

# Rendre le script exécutable
chmod +x scripts/setup_upstash_redis.sh

# Lancer l'activation
./scripts/setup_upstash_redis.sh .env.production
```

**Le script va**:
1. ✅ Vérifier credentials Upstash
2. ✅ Tester connexion avec PING
3. ✅ Backup Redis local (si données présentes)
4. ✅ Créer `docker-compose.hostinger.upstash.yml`
5. ✅ Redémarrer stack avec Upstash
6. ✅ Valider fonctionnement

### Étape 5: Validation

```bash
# Vérifier logs API
docker logs -f mcp-api | grep -i redis

# Test connexion Redis depuis API
curl http://localhost:8000/api/v1/health

# Surveiller dashboard Upstash
# https://console.upstash.com/ → Database → Metrics
```

**Métriques à surveiller**:
- **Latency**: < 20ms (Europe)
- **Commands/s**: Augmente avec usage
- **Memory**: Croissance normale
- **Hit rate**: > 80% après warm-up

### Étape 6: Rendre Permanent (après validation)

```bash
# Si tout fonctionne bien après 24-48h
cd /home/feustey/mcp-production
mv docker-compose.hostinger.yml docker-compose.hostinger.local.backup
mv docker-compose.hostinger.upstash.yml docker-compose.hostinger.yml

# Redémarrer pour confirmer
docker compose -f docker-compose.hostinger.yml down
docker compose -f docker-compose.hostinger.yml --env-file .env.production up -d
```

---

## 🔒 PARTIE 2: ACTIVATION HTTPS (LET'S ENCRYPT)

### Étape 1: Vérifier DNS

```bash
# Sur le serveur ou local
dig +short api.dazno.de

# Doit retourner: 147.79.101.32
```

Si pas encore propagé:
1. Aller sur votre registrar de domaine
2. Configurer enregistrement A:
   - **Type**: A
   - **Nom**: api
   - **Valeur**: 147.79.101.32
   - **TTL**: 300
3. Attendre propagation (5-30 minutes)

### Étape 2: Lancer Script HTTPS

Sur le serveur de production:

```bash
ssh feustey@147.79.101.32

cd /home/feustey/mcp-production

# Rendre le script exécutable
chmod +x scripts/setup_https_letsencrypt.sh

# Lancer installation SSL
sudo ./scripts/setup_https_letsencrypt.sh api.dazno.de feustey@gmail.com
```

**Arguments**:
- `api.dazno.de`: Votre domaine
- `feustey@gmail.com`: Email pour notifications Let's Encrypt

**Le script va**:
1. ✅ Vérifier DNS pointe vers serveur
2. ✅ Installer Certbot + plugin Nginx
3. ✅ Configurer Nginx (HTTP temporaire)
4. ✅ Générer certificat Let's Encrypt
5. ✅ Activer HTTPS + redirection
6. ✅ Configurer auto-renouvellement
7. ✅ Tests de validation

### Étape 3: Validation HTTPS

```bash
# Test depuis le serveur
curl https://api.dazno.de/

# Test redirection HTTP → HTTPS
curl -I http://api.dazno.de/
# Doit retourner: Location: https://api.dazno.de/

# Test API
curl https://api.dazno.de/api/v1/health
```

### Étape 4: Test Sécurité SSL

Ouvrir dans navigateur:
```
https://www.ssllabs.com/ssltest/analyze.html?d=api.dazno.de
```

**Note attendue**: A ou A+ (excellent)

### Étape 5: Vérifier Auto-Renouvellement

```bash
# Test dry-run (simulation)
sudo certbot renew --dry-run

# Doit retourner: "Congratulations, all simulated renewals succeeded"
```

**Renouvellement automatique**:
- Certificat valide 90 jours
- Renouvellement auto tous les 60 jours
- Cron job créé par Certbot: `/etc/cron.d/certbot`

---

## ✅ VALIDATION FINALE

### Tests à Effectuer

```bash
# 1. Test HTTPS API
curl https://api.dazno.de/api/v1/health
# Attendu: {"status":"healthy",...}

# 2. Test Documentation Swagger
# Ouvrir dans navigateur: https://api.dazno.de/docs

# 3. Test Redis Upstash (depuis l'API)
# Les endpoints API doivent cacher correctement

# 4. Vérifier logs
ssh feustey@147.79.101.32
cd /home/feustey/mcp-production
docker logs -f mcp-api

# 5. Dashboard Upstash
# https://console.upstash.com/ → Voir métriques temps réel
```

### Checklist Finale

- [ ] ✅ HTTPS actif sur api.dazno.de
- [ ] ✅ Certificat SSL valide (Let's Encrypt)
- [ ] ✅ Redirection HTTP → HTTPS fonctionne
- [ ] ✅ Grade SSL: A ou A+ (SSL Labs)
- [ ] ✅ Upstash Redis connecté
- [ ] ✅ Latency Redis < 20ms
- [ ] ✅ API accessible: https://api.dazno.de/
- [ ] ✅ Swagger docs: https://api.dazno.de/docs
- [ ] ✅ Logs propres (no errors)
- [ ] ✅ Auto-renouvellement SSL testé

---

## 📊 MÉTRIQUES À SURVEILLER

### Upstash Dashboard

Connectez-vous sur https://console.upstash.com/

**Métriques importantes**:
- **Latency (ms)**: Doit rester < 20ms
- **Commands/sec**: Augmente avec usage
- **Hit rate**: > 80% optimal
- **Memory usage**: Croissance linéaire normale
- **Throughput**: Read/write ratio ~3:1 (normal pour cache)

### Logs Application

```bash
# Logs temps réel
docker logs -f mcp-api | grep -E "(redis|cache|error)"

# Recherche erreurs Redis
docker logs mcp-api 2>&1 | grep -i "redis.*error"
```

---

## 🚨 TROUBLESHOOTING

### Problème: Upstash Connection Failed

**Symptômes**: Logs indiquent "Failed to connect to Redis"

**Solutions**:
1. Vérifier IP whitelisting dans Upstash (Settings → Security)
2. Vérifier credentials dans .env.production
3. Tester connexion directe:
   ```bash
   redis-cli -u "rediss://default:password@host.upstash.io:6379" PING
   ```

### Problème: Certificat SSL Non Valide

**Symptômes**: "SSL certificate problem" dans navigateur

**Solutions**:
1. Vérifier DNS: `dig +short api.dazno.de`
2. Régénérer certificat:
   ```bash
   sudo certbot delete --cert-name api.dazno.de
   sudo ./scripts/setup_https_letsencrypt.sh api.dazno.de feustey@gmail.com
   ```

### Problème: Rate Limit Let's Encrypt

**Symptômes**: "too many certificates already issued"

**Solutions**:
1. Attendre 1 semaine (limite: 5 certs/domaine/semaine)
2. Utiliser mode staging pour tester:
   ```bash
   sudo ./scripts/setup_https_letsencrypt.sh api.dazno.de feustey@gmail.com true
   ```

### Problème: Port 443 Inaccessible

**Symptômes**: Connexion HTTPS timeout

**Solutions**:
1. Vérifier firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 443/tcp
   ```
2. Vérifier Nginx écoute bien:
   ```bash
   sudo netstat -tlnp | grep :443
   ```

---

## 📝 COMMANDES RAPIDES

```bash
# === UPSTASH ===

# Redémarrer avec Upstash
cd /home/feustey/mcp-production
docker compose -f docker-compose.hostinger.upstash.yml up -d

# Logs Redis
docker logs mcp-api | grep -i redis

# Dashboard Upstash
# https://console.upstash.com/

# === HTTPS ===

# Status certificat SSL
sudo certbot certificates

# Renouveler certificat (manuel)
sudo certbot renew

# Test renouvellement
sudo certbot renew --dry-run

# Logs Let's Encrypt
sudo tail -f /var/log/letsencrypt/letsencrypt.log

# Reload Nginx après changement config
sudo nginx -t && sudo systemctl reload nginx

# === API ===

# Status services
docker compose ps

# Logs API
docker logs -f mcp-api

# Test health
curl https://api.dazno.de/api/v1/health

# Redémarrer API uniquement
docker compose restart mcp-api
```

---

## 🎯 PROCHAINES ÉTAPES APRÈS ACTIVATION

1. **Monitoring** (Priorité 3)
   - Setup Prometheus + Grafana
   - Alertes sur latency Redis
   - Dashboard SSL expiration

2. **Optimisations** (Priorité 3)
   - Tuning cache TTL
   - Warm-up automatique
   - Connection pooling optimization

3. **Sécurité** (Priorité 2)
   - Activer MongoDB Atlas
   - Backup automatique S3
   - Rotation credentials

4. **Production** (Priorité 1)
   - Compléter 21 jours Shadow Mode
   - Tests avec nœud Lightning réel
   - Activation mode semi-auto

---

## 📞 SUPPORT

**Upstash Support**:
- Dashboard: https://console.upstash.com/
- Docs: https://docs.upstash.com/redis
- Discord: https://discord.com/invite/w9SenAtbme

**Let's Encrypt Support**:
- Docs: https://letsencrypt.org/docs/
- Community: https://community.letsencrypt.org/

**MCP Project**:
- Logs: `/home/feustey/mcp-production/logs/`
- Config: `/home/feustey/mcp-production/.env.production`
- Docs: `docs/` directory

---

**✅ Configuration complétée le**: ________________  
**👤 Par**: ________________  
**📝 Notes**:


