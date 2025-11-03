# ✅ Déploiement Hostinger - Prêt à l'Emploi

> Dernière mise à jour: 27 octobre 2025

## 🎯 État Actuel

### Diagnostic

✅ **Docker Desktop** : Installé et fonctionnel (v28.3.2)
⚠️ **Conteneurs Docker** : 5 conteneurs existent mais sont arrêtés depuis 4 jours
✅ **API de développement** : Une instance Python écoute sur port 8000

### Conteneurs Détectés

```
NAMES         STATUS                  IMAGE
mcp-api       Exited (137) 4 days ago mcp-api:latest
mcp-mongodb   Exited (0) 4 days ago   mongo:7.0
mcp-nginx     Exited (0) 4 days ago   nginx:alpine
mcp-redis     Exited (0) 4 days ago   redis:7-alpine
mcp-ollama    Exited (0) 4 days ago   ollama/ollama:latest
```

---

## 🚀 Scripts Créés

### 1. **Script Principal de Déploiement** : `deploy_mcp.sh`

Script intelligent qui diagnostique l'environnement et propose les meilleures options.

**Usage** :
```bash
./deploy_mcp.sh
```

**Options disponibles** :
1. ⚡ **Redémarrer les conteneurs existants** (1 min)
2. 🔨 **Déploiement complet local** (15-20 min)
3. 🌐 **Déploiement distant Hostinger** (10-15 min)
4. 🔍 **Vérifier l'état uniquement**
5. ❌ **Annuler**

---

### 2. **Vérification des Services** : `scripts/check_hostinger_services.sh`

Vérifie l'état de tous les services (conteneurs, ports, santé API).

**Usage** :
```bash
./scripts/check_hostinger_services.sh
```

**Ce qu'il vérifie** :
- ✅ État des 5 conteneurs Docker
- ✅ Healthchecks MongoDB et Redis
- ✅ Disponibilité des ports (8000, 80, 443, 11434)
- ✅ Santé de l'API (/health endpoint)
- ✅ Temps de réponse

---

### 3. **Vérification Docker** : `scripts/check_docker.sh`

Vérifie si Docker est accessible et le démarre si nécessaire.

**Usage** :
```bash
./scripts/check_docker.sh
```

**Actions** :
- Détecte l'OS (macOS/Linux)
- Vérifie si Docker Desktop est installé
- Démarre Docker si nécessaire
- Attend que Docker soit prêt (max 120s)

---

### 4. **Redémarrage Rapide** : `scripts/restart_hostinger_services.sh`

Redémarre tous les services ou un service spécifique.

**Usage** :
```bash
# Redémarrer tous les services
./scripts/restart_hostinger_services.sh

# Redémarrer un service spécifique
./scripts/restart_hostinger_services.sh mcp-api
```

---

### 5. **Déploiement Complet Local** : `deploy_hostinger_production.sh`

Déploiement complet en 7 étapes avec rebuild des images.

**Usage** :
```bash
./deploy_hostinger_production.sh
```

**Étapes** :
1. ✅ Vérifications préalables (.env, docker-compose.yml, Docker)
2. ⏹️ Arrêt des services existants
3. 🔨 Build des images Docker
4. 🗄️ Démarrage MongoDB et Redis
5. 🤖 Démarrage Ollama + téléchargement modèles
6. 🚀 Démarrage API et Nginx
7. ✅ Validation du déploiement

**Durée** : 15-20 minutes

---

### 6. **Déploiement Distant** : `deploy_remote_hostinger.sh`

Déploie sur le serveur Hostinger via SSH et rsync.

**Usage** :
```bash
./deploy_remote_hostinger.sh
```

Le script demandera :
- Adresse du serveur : `root@vps.hostinger.com`
- Chemin distant : `/root/mcp`

**Étapes** :
1. ✅ Test connexion SSH
2. ✅ Vérification Docker distant
3. 📤 Synchronisation fichiers (rsync)
4. 🚀 Déploiement sur le serveur
5. ✅ Vérification services distants

**Durée** : 10-15 minutes

---

## 📖 Guide Complet : `GUIDE_DEPLOIEMENT_HOSTINGER.md`

Documentation complète avec :
- 📋 Prérequis
- 🚀 Options de déploiement (local/distant)
- 🔍 Vérification post-déploiement
- 🛠️ Commandes de gestion
- 🚨 Dépannage
- 📊 Monitoring
- ✅ Checklist de production

---

## ⚡ Démarrage Rapide

### Option 1 : Redémarrer les Conteneurs Existants (Recommandé)

Les conteneurs existent déjà, il suffit de les redémarrer :

```bash
# Option interactive
./deploy_mcp.sh
# Choisir option 1

# OU directement
./scripts/restart_hostinger_services.sh
```

**Avantages** :
- ⚡ Très rapide (1 minute)
- 💾 Conserve les données existantes
- 🔧 Pas de rebuild nécessaire

**Note** : Le processus Python sur port 8000 devra être arrêté.

---

### Option 2 : Déploiement Complet Local

Pour un rebuild complet avec les dernières modifications :

```bash
# Option interactive
./deploy_mcp.sh
# Choisir option 2

# OU directement
./deploy_hostinger_production.sh
```

**Quand l'utiliser** :
- 🔄 Après modification du code
- 🆕 Nouvelles dépendances
- 🐛 Problèmes avec les images existantes

---

### Option 3 : Déploiement sur Serveur Hostinger

Pour déployer sur le serveur de production :

```bash
# Option interactive
./deploy_mcp.sh
# Choisir option 3

# OU directement
./deploy_remote_hostinger.sh
```

**Prérequis** :
- 🔑 Accès SSH configuré
- 🌐 Adresse du serveur Hostinger
- 📂 Fichier .env configuré

---

## 🔍 Vérification Rapide

À tout moment, vérifiez l'état :

```bash
./deploy_mcp.sh
# Choisir option 4

# OU
./scripts/check_hostinger_services.sh
```

---

## 🛠️ Commandes Utiles

### Voir les logs

```bash
# Tous les services
docker-compose -f docker-compose.hostinger.yml logs -f

# API uniquement
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api

# Ollama uniquement
docker-compose -f docker-compose.hostinger.yml logs -f ollama
```

### Arrêter le processus Python local

```bash
# Trouver le PID
lsof -i :8000

# Arrêter
kill -9 [PID]
```

### Redémarrer un service spécifique

```bash
./scripts/restart_hostinger_services.sh mcp-api
```

### Nettoyer et redéployer

```bash
# Arrêter et supprimer les volumes
docker-compose -f docker-compose.hostinger.yml down -v

# Redéployer
./deploy_hostinger_production.sh
```

---

## ✅ Checklist de Validation

Après déploiement, vérifier :

- [ ] Les 5 conteneurs sont actifs
- [ ] MongoDB healthcheck = healthy
- [ ] Redis healthcheck = healthy
- [ ] API répond sur http://localhost:8000/health
- [ ] Nginx répond sur http://localhost
- [ ] Ollama a téléchargé au moins 1 modèle
- [ ] Pas d'erreurs dans les logs
- [ ] Mode Shadow activé (DRY_RUN=true)

---

## 🎯 Recommandation Immédiate

**Pour redémarrer rapidement les conteneurs existants** :

```bash
# 1. Lancer le script principal
./deploy_mcp.sh

# 2. Choisir option 1 (Redémarrer les conteneurs)

# 3. Accepter d'arrêter le processus Python sur port 8000

# 4. Attendre 1 minute

# 5. Vérifier : tous les services devraient être actifs !
```

**C'est la solution la plus rapide pour avoir les 5 conteneurs actifs.**

---

## 📊 Architecture des Services

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  Client HTTP/HTTPS                                  │
│                                                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │                 │
         │  Nginx (80/443) │  ◄── Reverse Proxy
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │                 │
         │  MCP API (8000) │  ◄── FastAPI
         │                 │
         └─┬─────┬─────┬───┘
           │     │     │
   ┌───────┘     │     └───────┐
   │             │             │
   ▼             ▼             ▼
┌─────────┐  ┌──────┐  ┌────────────┐
│ MongoDB │  │ Redis│  │   Ollama   │
│  (27017)│  │(6379)│  │  (11434)   │
└─────────┘  └──────┘  └────────────┘
```

---

## 🆘 Support

En cas de problème :

1. **Voir l'état** : `./scripts/check_hostinger_services.sh`
2. **Voir les logs** : `docker-compose -f docker-compose.hostinger.yml logs -f`
3. **Redémarrer** : `./scripts/restart_hostinger_services.sh`
4. **Guide complet** : Consulter `GUIDE_DEPLOIEMENT_HOSTINGER.md`

---

## 📚 Fichiers Créés

### Scripts

- ✅ `deploy_mcp.sh` - Script principal intelligent
- ✅ `deploy_hostinger_production.sh` - Déploiement complet local
- ✅ `deploy_remote_hostinger.sh` - Déploiement distant
- ✅ `scripts/check_hostinger_services.sh` - Vérification services
- ✅ `scripts/check_docker.sh` - Vérification Docker
- ✅ `scripts/restart_hostinger_services.sh` - Redémarrage rapide

### Documentation

- ✅ `GUIDE_DEPLOIEMENT_HOSTINGER.md` - Guide complet
- ✅ `DEPLOIEMENT_HOSTINGER_READY.md` - Ce fichier

---

**🎉 Tout est prêt pour le déploiement !**

Lancez simplement `./deploy_mcp.sh` et suivez les instructions.

