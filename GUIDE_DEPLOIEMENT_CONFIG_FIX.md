# 🚀 Guide de Déploiement - Correction "Invalid Host Header"

## 📋 Problème Résolu

**Erreur** : "invalid host header" lors de l'accès à https://api.dazno.de/docs

**Cause** : Le domaine `api.dazno.de` n'était pas dans la liste des hôtes autorisés par le middleware `TrustedHostMiddleware` de FastAPI.

**Solution** : Ajout de `"api.dazno.de"` dans `config.py` à la liste `security_allowed_hosts`.

---

## ✅ Modifications Effectuées Localement

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

---

## 🔧 Déploiement en Production - Méthode Manuelle

### Option 1 : Via SSH Direct (Recommandé)

```bash
# 1. Connectez-vous au serveur Hostinger
ssh u115-pdvfcwqc2ubq@srv594809.hstgr.cloud

# 2. Naviguez vers le répertoire MCP
cd domains/api.dazno.de/MCP

# 3. Éditez le fichier config.py
nano config.py

# 4. Trouvez la ligne 106 et modifiez-la pour ajouter "api.dazno.de" :
#    security_allowed_hosts: List[str] = Field(
#        ["api.dazno.de", "app.dazno.de", "dazno.de", "www.dazno.de", "localhost"], 
#        alias="SECURITY_ALLOWED_HOSTS"
#    )

# 5. Sauvegardez (Ctrl+O, Enter, Ctrl+X)

# 6. Vérifiez la modification
grep -n "api.dazno.de.*app.dazno.de" config.py

# 7. Reconstruisez l'image Docker
docker-compose -f docker-compose.hostinger.yml build mcp-api

# 8. Redémarrez le conteneur
docker-compose -f docker-compose.hostinger.yml up -d mcp-api

# 9. Attendez quelques secondes puis vérifiez le statut
docker ps | grep mcp-api

# 10. Vérifiez les logs
docker logs mcp-api --tail=20

# 11. Testez le endpoint health
curl http://localhost:8000/health

# 12. Testez le endpoint docs
curl -I https://api.dazno.de/docs
```

---

### Option 2 : Via SCP (Transfert du fichier)

```bash
# 1. Depuis votre machine locale, transférez le fichier modifié
scp /Users/stephanecourant/Documents/DAZ/MCP/MCP/config.py \
    u115-pdvfcwqc2ubq@srv594809.hstgr.cloud:domains/api.dazno.de/MCP/

# 2. Connectez-vous en SSH
ssh u115-pdvfcwqc2ubq@srv594809.hstgr.cloud

# 3. Suivez les étapes 2 et 6-12 de l'Option 1
```

---

## ✅ Vérifications Post-Déploiement

### 1. Vérifier le conteneur
```bash
docker ps --filter name=mcp-api
```
**Attendu** : Le conteneur doit être "Up" et "healthy"

### 2. Vérifier les logs
```bash
docker logs mcp-api --tail=30 | grep -E "(Configuration|allowed_hosts|TrustedHost|Application)"
```
**Attendu** : Logs de démarrage sans erreur

### 3. Tester le endpoint health
```bash
curl -s http://localhost:8000/health | jq
```
**Attendu** : `{"status": "healthy", ...}`

### 4. Tester le endpoint docs (le problème initial)
```bash
curl -I https://api.dazno.de/docs
```
**Attendu** : `HTTP/2 200` (et non plus "invalid host header")

### 5. Test final dans le navigateur
Ouvrez dans votre navigateur : **https://api.dazno.de/docs**

**Attendu** : La documentation Swagger s'affiche correctement sans erreur "invalid host header"

---

## 🐛 Dépannage

### Problème : Le conteneur ne démarre pas

```bash
# Vérifier les erreurs
docker logs mcp-api --tail=50

# Vérifier la configuration Docker
docker-compose -f docker-compose.hostinger.yml config | grep -A5 mcp-api

# Redémarrage complet
docker-compose -f docker-compose.hostinger.yml down
docker-compose -f docker-compose.hostinger.yml up -d
```

### Problème : L'erreur persiste

1. **Attendez 30-60 secondes** - Le conteneur peut mettre du temps à démarrer complètement
2. **Vérifiez que la modification est bien présente** :
   ```bash
   docker exec mcp-api grep "api.dazno.de" /app/config.py
   ```
3. **Vérifiez la variable d'environnement** :
   ```bash
   docker exec mcp-api printenv | grep ALLOWED_HOSTS
   ```

### Problème : Nginx cache l'ancienne version

```bash
# Redémarrer Nginx
docker-compose -f docker-compose.hostinger.yml restart nginx

# Ou vider le cache Nginx si configuré
docker exec nginx nginx -s reload
```

---

## 📝 Checklist de Déploiement

- [ ] Connexion SSH au serveur réussie
- [ ] Fichier `config.py` modifié (ligne 106 contient "api.dazno.de")
- [ ] Image Docker reconstruite (`docker-compose build`)
- [ ] Conteneur redémarré (`docker-compose up -d`)
- [ ] Conteneur en statut "Up" et "healthy"
- [ ] Logs sans erreur
- [ ] Test `/health` : OK (200)
- [ ] Test `/docs` : OK (200, sans "invalid host header")
- [ ] Test navigateur : Swagger s'affiche correctement

---

## 🎯 Résumé des Commandes Rapides

```bash
# Tout en une fois (après connexion SSH)
cd domains/api.dazno.de/MCP && \
nano config.py && \
docker-compose -f docker-compose.hostinger.yml build mcp-api && \
docker-compose -f docker-compose.hostinger.yml up -d mcp-api && \
sleep 10 && \
docker logs mcp-api --tail=20 && \
curl -I https://api.dazno.de/docs
```

---

## 📞 Support

Si vous rencontrez des difficultés :
1. Vérifiez les logs : `docker logs mcp-api --tail=50`
2. Vérifiez le statut : `docker ps -a | grep mcp`
3. Contactez le support technique

---

**Date de création** : 29 octobre 2025  
**Dernière mise à jour** : 29 octobre 2025  
**Version** : 1.0

