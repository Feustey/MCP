# 🚀 Instructions de Déploiement Production

> Créé le 27 octobre 2025

## ✅ État Actuel

**Environnement local** :
- ✅ 5/5 conteneurs actifs (mongodb, redis, api, nginx, ollama)
- ✅ Configuration en mode production
- ✅ DRY_RUN=true (Shadow Mode activé)
- ✅ 9 modèles Ollama installés
- ✅ Scripts de déploiement créés

---

## 🎯 Deux Options de Déploiement

### Option 1️⃣ : Déploiement sur Serveur Distant Hostinger (RECOMMANDÉ)

**Si vous avez un serveur Hostinger avec accès SSH**

#### A. Lancer le script interactif

```bash
./deploy_production_now.sh
```

Le script vous demandera :
- 🔑 Adresse du serveur (ex: `root@vps-12345.hostinger.com`)
- 📂 Chemin du projet (défaut: `/root/mcp`)

#### B. Ce que le script fait

1. ✅ **Test connexion SSH** (10s)
2. ✅ **Vérification Docker distant** (5s)
3. 📤 **Synchronisation fichiers** (2-3 min)
4. 🔨 **Build image Docker** (5-10 min)
5. 🚀 **Démarrage services** (2-3 min)
6. ✅ **Vérification déploiement** (30s)

**Durée totale** : 10-15 minutes

---

### Option 2️⃣ : Environnement Local en Mode Production

**Si vous voulez tester localement en mode production avant de déployer**

Votre environnement local est DÉJÀ configuré en mode production :

```bash
# Vérifier la configuration
grep -E "^(ENVIRONMENT|DRY_RUN)" .env

# Résultat attendu :
# ENVIRONMENT=production
# DRY_RUN=true
```

**Vous n'avez rien à faire** - les conteneurs locaux tournent déjà en mode production !

---

## 📋 Prérequis pour le Déploiement Distant

### 1. Accès SSH au Serveur

Vérifiez que vous pouvez vous connecter :

```bash
ssh root@votre-serveur.hostinger.com
```

Si non, configurez votre clé SSH :

```bash
# Générer une clé SSH (si vous n'en avez pas)
ssh-keygen -t ed25519 -C "votre@email.com"

# Copier la clé sur le serveur
ssh-copy-id root@votre-serveur.hostinger.com
```

### 2. Docker sur le Serveur

Docker doit être installé sur le serveur distant :

```bash
# Se connecter au serveur
ssh root@votre-serveur.hostinger.com

# Installer Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Vérifier
docker --version
```

### 3. Fichier .env Configuré

Assurez-vous que votre fichier `.env` local contient :

```bash
# Environnement
ENVIRONMENT=production
DRY_RUN=true
ENABLE_SHADOW_MODE=true

# Services
MONGODB_USER=mcpuser
MONGODB_PASSWORD=[votre-mot-de-passe-sécurisé]
REDIS_PASSWORD=[votre-mot-de-passe-redis]

# API Keys (si nécessaires)
LNBITS_URL=[votre-url-lnbits]
LNBITS_ADMIN_KEY=[votre-clé]

# Sécurité
SECRET_KEY=[généré-aléatoirement]
ENCRYPTION_KEY=[généré-aléatoirement]
```

---

## 🚀 Déploiement Pas à Pas

### Étape 1 : Préparation

```bash
cd /Users/stephanecourant/Documents/DAZ/MCP/MCP

# Vérifier que tous les fichiers sont présents
ls -la docker-compose.hostinger.yml .env Dockerfile.production
```

### Étape 2 : Lancement

```bash
./deploy_production_now.sh
```

### Étape 3 : Saisie des Informations

Le script vous demande :

```
Adresse du serveur [user@host.hostinger.com]: root@vps-12345.hostinger.com
Chemin du projet sur le serveur [/root/mcp]: /root/mcp
```

### Étape 4 : Confirmation

```
Configuration:
  • Serveur : root@vps-12345.hostinger.com
  • Chemin  : /root/mcp

Confirmer et continuer? [y/N]: y
```

### Étape 5 : Attente

Le script va :
- ✅ Tester la connexion SSH
- ✅ Vérifier Docker
- 📤 Synchroniser les fichiers
- 🔨 Builder l'image (le plus long)
- 🚀 Démarrer les services
- ✅ Vérifier l'état

**Durée** : 10-15 minutes

### Étape 6 : Vérification

À la fin, vous verrez :

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     ✅ DÉPLOIEMENT PRODUCTION TERMINÉ !                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## 🔍 Vérification Post-Déploiement

### Sur le Serveur

```bash
# Voir l'état des conteneurs
ssh root@votre-serveur.hostinger.com 'cd /root/mcp && docker-compose -f docker-compose.hostinger.yml ps'

# Voir les logs
ssh root@votre-serveur.hostinger.com 'cd /root/mcp && docker-compose -f docker-compose.hostinger.yml logs -f mcp-api'
```

### Tester l'API

```bash
# Health check (remplacez par votre domaine)
curl https://votre-domaine.com/health

# Ou par IP
curl http://[IP-SERVEUR]:8000/health
```

---

## 🛠️ Commandes de Gestion

### Redémarrer les services

```bash
ssh root@votre-serveur.hostinger.com 'cd /root/mcp && docker-compose -f docker-compose.hostinger.yml restart'
```

### Arrêter les services

```bash
ssh root@votre-serveur.hostinger.com 'cd /root/mcp && docker-compose -f docker-compose.hostinger.yml down'
```

### Mettre à jour

```bash
# Re-lancer le script de déploiement
./deploy_production_now.sh
```

---

## 🚨 Dépannage

### Erreur : "Connection refused"

```bash
# Vérifier que vous pouvez vous connecter en SSH
ssh root@votre-serveur.hostinger.com

# Tester avec verbose
ssh -v root@votre-serveur.hostinger.com
```

### Erreur : "Docker command not found"

Docker n'est pas installé sur le serveur :

```bash
# Se connecter et installer
ssh root@votre-serveur.hostinger.com
curl -fsSL https://get.docker.com | sh
```

### Erreur : "Permission denied"

Votre clé SSH n'est pas configurée :

```bash
ssh-copy-id root@votre-serveur.hostinger.com
```

### Les conteneurs ne démarrent pas

```bash
# Voir les logs
ssh root@votre-serveur.hostinger.com 'cd /root/mcp && docker-compose -f docker-compose.hostinger.yml logs'
```

---

## ✅ Checklist de Production

Après le déploiement, vérifier :

- [ ] Les 5 conteneurs sont actifs sur le serveur
- [ ] MongoDB est accessible (healthcheck healthy)
- [ ] Redis est accessible (healthcheck healthy)
- [ ] L'API répond sur /health
- [ ] Nginx est actif (ports 80/443)
- [ ] Ollama est actif
- [ ] Mode Shadow activé (DRY_RUN=true)
- [ ] Les logs ne montrent pas d'erreurs
- [ ] Le firewall autorise les ports nécessaires
- [ ] SSL/HTTPS configuré (si applicable)

---

## 📊 Architecture de Production

```
┌────────────────────────────────────────────┐
│  Internet                                  │
└────────────────┬───────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │  Firewall     │  Port 80, 443
         └───────┬───────┘
                 │
                 ▼
    ┌────────────────────────┐
    │  SERVEUR HOSTINGER     │
    │                        │
    │  ┌──────────────────┐  │
    │  │  Nginx (80/443)  │  │
    │  └────────┬─────────┘  │
    │           │            │
    │           ▼            │
    │  ┌──────────────────┐  │
    │  │  MCP API (8000)  │  │
    │  └─┬──┬──┬──────────┘  │
    │    │  │  │             │
    │    ▼  ▼  ▼             │
    │  ┌──┐┌──┐┌────────┐   │
    │  │DB││  ││Ollama  │   │
    │  └──┘└──┘└────────┘   │
    │  Mongo Redis           │
    └────────────────────────┘
```

---

## 🎯 Commande Rapide

Si vous êtes prêt avec vos credentials SSH :

```bash
./deploy_production_now.sh
```

Puis suivez les instructions interactives !

---

## 📚 Documentation Associée

- Guide complet : `GUIDE_DEPLOIEMENT_HOSTINGER.md`
- Rapport local : `RAPPORT_DEPLOIEMENT_27OCT2025.md`
- Scripts créés : `FICHIERS_CREES_27OCT2025.md`

---

**🚀 Prêt à déployer en production sur Hostinger !**

