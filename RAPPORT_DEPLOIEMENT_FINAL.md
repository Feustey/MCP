# ❌ Rapport de Déploiement - Fix "Invalid Host Header"

**Date** : 29 octobre 2025  
**Objectif** : Ajouter `api.dazno.de` aux hôtes autorisés pour résoudre l'erreur "invalid host header"

---

## ✅ Modifications Locales Effectuées

**Fichier modifié** : `config.py` (ligne 106)

```python
# AVANT
security_allowed_hosts: List[str] = Field(
    ["app.dazno.de", "dazno.de", "www.dazno.de", "localhost"], 
    alias="SECURITY_ALLOWED_HOSTS"
)

# APRÈS  
security_allowed_hosts: List[str] = Field(
    ["api.dazno.de", "app.dazno.de", "dazno.de", "www.dazno.de", "localhost"], 
    alias="SECURITY_ALLOWED_HOSTS"
)
```

✅ **Modification locale réussie**

---

## ⚠️ Tentatives de Déploiement en Production

### Tentative 1 : Mauvais serveur (u115-pdvfcwqc2ubq@srv594809.hstgr.cloud)
- ❌ Credentials SSH incorrects
- ❌ Répertoire introuvable

### Tentative 2 : Bon serveur (root@147.79.101.32)
- ✅ Connexion SSH réussie
- ✅ Fichier `config.py` transféré vers `/root/MCP/`
- ❌ Mauvais répertoire (le conteneur n'utilise pas `/root/MCP/`)

### Tentative 3 : Bon répertoire (`/home/feustey/mcp/`)
- ✅ Fichier `config.py` transféré
- ✅ Modification vérifiée (ligne 106 contient `api.dazno.de`)
- ❌ Conteneur utilise une image Docker (pas de volume monté pour config.py)

### Tentative 4 : Rebuild de l'image Docker
- ❌ **ÉCHEC CRITIQUE** : `No space left on device`
- ❌ Le serveur est plein à **95.7%**
- ❌ MongoDB devenu **unhealthy**
- ❌ API ne démarre plus

---

## 🔴 Problèmes Identifiés

1. **Espace disque saturé** : 95.7% utilisé (95.82GB)
2. **Build Docker impossible** : Nécessite trop d'espace
3. **MongoDB unhealthy** : Impact du build raté
4. **Architecture complexe** : Le conteneur utilise l'image Docker, pas le fichier host

---

## 💡 Solution Alternative Requise

### Option A : Copier directement dans le conteneur (Recommandé)
```bash
# 1. Copier le fichier dans le conteneur en cours
docker cp config.py mcp-api:/app/config.py

# 2. Redémarrer le conteneur
docker restart mcp-api
```

**Avantages** :
- ✅ Pas de rebuild nécessaire
- ✅ Pas d'espace disque requis
- ✅ Rapide (< 1 minute)

**Inconvénients** :
- ❌ Modification perdue si le conteneur est recréé
- ❌ Solution temporaire

### Option B : Nettoyer l'espace disque puis rebuild
```bash
# 1. Nettoyer les images Docker inutilisées
docker system prune -a -f

# 2. Nettoyer les logs
find /home/feustey/mcp/logs -name "*.log" -mtime +7 -delete

# 3. Rebuild l'image
docker-compose -f docker-compose.hostinger.yml build mcp-api

# 4. Redémarrer
docker-compose -f docker-compose.hostinger.yml up -d mcp-api
```

**Avantages** :
- ✅ Solution permanente
- ✅ Modification persiste

**Inconvénients** :
- ❌ Nécessite beaucoup d'espace
- ❌ Temps long (10-15 minutes)
- ❌ Risque si nettoyage insuffisant

---

## 📋 Actions Recommandées

### URGENT (à faire maintenant)

1. **Réparer MongoDB** :
   ```bash
   docker restart mcp-mongodb
   docker logs mcp-mongodb --tail=50
   ```

2. **Option rapide** - Copier le fichier directement :
   ```bash
   ssh root@147.79.101.32
   cd /home/feustey/mcp
   docker cp config.py mcp-api:/app/config.py
   docker restart mcp-api
   sleep 15
   curl -I https://api.dazno.de/docs
   ```

### MOYEN TERME (planifier)

3. **Nettoyer l'espace disque** :
   - Supprimer les anciennes images Docker
   - Nettoyer les logs volumineux
   - Supprimer les backups obsolètes

4. **Rebuild propre** de l'image avec la bonne config

---

## 🎯 État Actuel

### Infrastructure
- 🔴 **Serveur** : 95.7% plein (CRITIQUE)
- 🔴 **MongoDB** : Unhealthy
- 🔴 **API** : Ne démarre pas
- ✅ **Redis** : Healthy
- ✅ **Ollama** : Running (unhealthy mais fonctionnel)

### Déploiement
- ✅ Modifications locales OK
- ✅ Fichier config.py transféré sur le serveur
- ❌ Modifications NON appliquées dans le conteneur
- ❌ Erreur "invalid host header" PERSISTE

---

## 🚨 Blocages

1. **Espace disque critique** empêche le rebuild
2. **MongoDB unhealthy** empêche l'API de démarrer
3. **Conteneur non fonctionnel** empêche le test de la correction

---

## 📞 Prochaines Étapes

Le déploiement nécessite une intervention manuelle pour :
1. Réparer MongoDB
2. Appliquer le fix via `docker cp` (solution rapide)
3. Planifier un nettoyage d'espace disque
4. Rebuild propre quand l'espace est disponible

**Note** : Je recommande la solution rapide (`docker cp`) maintenant, puis un nettoyage et rebuild planifié quand le serveur sera moins chargé.

---

**Auteur** : Agent AI  
**Date** : 29 octobre 2025  
**Statut** : ⏸️ EN ATTENTE D'INTERVENTION MANUELLE

