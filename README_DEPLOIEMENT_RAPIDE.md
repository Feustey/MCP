# 🚀 Déploiement MCP - Démarrage Rapide

## ⚡ Solution Immédiate (1 minute)

Vous avez **5 conteneurs Docker arrêtés** qui peuvent être redémarrés instantanément :

```bash
./deploy_mcp.sh
```

Choisissez l'option **1** (Redémarrer les conteneurs existants).

---

## 📋 État Actuel

- ✅ Docker Desktop installé (v28.3.2)
- ⚠️ 5 conteneurs arrêtés depuis 4 jours
- ✅ API de dev active sur port 8000

## 🎯 3 Options Disponibles

### 1️⃣ Redémarrage Rapide (1 min) ⚡ RECOMMANDÉ

```bash
./deploy_mcp.sh
# Choisir option 1
```

**Idéal pour** : Redémarrer rapidement les services existants.

---

### 2️⃣ Déploiement Complet Local (15-20 min)

```bash
./deploy_mcp.sh
# Choisir option 2
```

**Idéal pour** : Rebuild après modifications du code.

---

### 3️⃣ Déploiement Distant Hostinger (10-15 min)

```bash
./deploy_mcp.sh
# Choisir option 3
```

**Idéal pour** : Déployer sur le serveur de production.

---

## 🔍 Vérification

```bash
./scripts/check_hostinger_services.sh
```

---

## 📚 Documentation Complète

- 📖 **Guide détaillé** : `GUIDE_DEPLOIEMENT_HOSTINGER.md`
- ✅ **État et scripts** : `DEPLOIEMENT_HOSTINGER_READY.md`

---

## 🆘 Aide Rapide

### Voir les logs
```bash
docker-compose -f docker-compose.hostinger.yml logs -f mcp-api
```

### Redémarrer un service
```bash
./scripts/restart_hostinger_services.sh mcp-api
```

### Arrêter le processus Python local
```bash
kill -9 $(lsof -ti :8000)
```

---

**🎉 C'est tout ! Lancez `./deploy_mcp.sh` maintenant.**

