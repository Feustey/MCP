# 🚀 Quick Start: Activation Upstash + HTTPS

> **Temps estimé**: 30-45 minutes  
> **Prérequis**: Compte Upstash créé

---

## ⚡ MÉTHODE RAPIDE (Automatisée)

### 1. Configuration Upstash (5 minutes)

```bash
# 1. Créer compte sur Upstash
open https://console.upstash.com/

# 2. Créer base Redis:
#    - Nom: mcp-production
#    - Region: eu-west-1
#    - Type: Regional
#    - TLS: Enabled

# 3. Copier l'URL Redis (format: rediss://...)
```

### 2. Configuration Locale (5 minutes)

```bash
# Sur votre machine (dans le repo MCP)
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP

# Créer .env.production
cp env.production.template .env.production
chmod 600 .env.production

# Éditer et configurer (OBLIGATOIRE):
nano .env.production

# Variables essentielles à configurer:
# REDIS_URL=rediss://default:PASSWORD@host.upstash.io:6379
# REDIS_PASSWORD=votre_password
# MONGODB_PASSWORD=ChoisirMotDePasseSecurise123!
# SECRET_KEY=$(openssl rand -hex 32)
# ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# LNBITS_URL=https://your-lnbits-instance.com
# LNBITS_ADMIN_KEY=votre_admin_key
```

### 3. Lancer Activation Automatique (20-30 minutes)

```bash
# Exécuter le script master qui fait TOUT
./scripts/activate_upstash_and_https.sh

# Le script va automatiquement:
# ✅ Vérifier configuration
# ✅ Transférer fichiers sur production
# ✅ Activer Upstash Redis
# ✅ Configurer HTTPS avec Let's Encrypt
# ✅ Valider le tout
```

### 4. Validation (5 minutes)

```bash
# Test HTTPS
curl https://api.dazno.de/api/v1/health

# Test documentation
open https://api.dazno.de/docs

# Vérifier logs
ssh feustey@147.79.101.32 "docker logs --tail 50 mcp-api"

# Dashboard Upstash
open https://console.upstash.com/
```

---

## 📋 MÉTHODE MANUELLE (Si script échoue)

### Étape 1: Upstash

```bash
# Transférer .env.production
scp .env.production feustey@147.79.101.32:/home/feustey/mcp-production/

# Se connecter au serveur
ssh feustey@147.79.101.32

# Lancer activation Upstash
cd /home/feustey/mcp-production
./scripts/setup_upstash_redis.sh .env.production
```

### Étape 2: HTTPS

```bash
# Toujours connecté au serveur
sudo ./scripts/setup_https_letsencrypt.sh api.dazno.de feustey@gmail.com
```

---

## ✅ CHECKLIST FINALE

Après activation, vérifier:

- [ ] ✅ `curl https://api.dazno.de/` répond
- [ ] ✅ `curl http://api.dazno.de/` redirige vers HTTPS
- [ ] ✅ Dashboard Upstash affiche métriques
- [ ] ✅ Logs propres: `docker logs mcp-api | grep -i error`
- [ ] ✅ SSL grade A/A+: https://www.ssllabs.com/ssltest/analyze.html?d=api.dazno.de

---

## 🆘 PROBLÈMES COURANTS

### "DNS ne pointe pas vers serveur"

```bash
# Configurer enregistrement A chez votre registrar:
# Type: A
# Nom: api
# Valeur: 147.79.101.32
# TTL: 300

# Attendre propagation (5-30 min)
dig +short api.dazno.de
```

### "Upstash connection failed"

```bash
# Vérifier IP whitelisting dans Upstash dashboard
# Settings → Security → Add IP: 147.79.101.32
```

### "Let's Encrypt rate limit"

```bash
# Utiliser mode staging pour tester:
sudo ./scripts/setup_https_letsencrypt.sh api.dazno.de feustey@gmail.com true
```

---

## 📞 AIDE

- **Guide complet**: `cat ACTIVATION_UPSTASH_HTTPS_GUIDE.md`
- **Logs**: `ssh feustey@147.79.101.32 "docker logs -f mcp-api"`
- **Status**: `ssh feustey@147.79.101.32 "cd /home/feustey/mcp-production && docker compose ps"`

---

**Prêt ? Lancez**: `./scripts/activate_upstash_and_https.sh` 🚀

