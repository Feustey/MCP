# Instructions de Déploiement Unifié sur Hostinger

## 🚀 Configuration Préparée

J'ai préparé une architecture unifiée pour vos deux applications sur Hostinger :

### **Fichiers créés :**
- `docker-compose.hostinger-unified.yml` - Stack Docker complète
- `config/nginx/hostinger-unified.conf` - Configuration Nginx unifiée
- `.env.unified-production` - Variables d'environnement
- `config/nginx/.htpasswd` - Authentification monitoring
- `config/prometheus/prometheus-unified.yml` - Configuration monitoring

## 📋 Étapes pour Finaliser le Déploiement

### 1. Une fois la connexion SSH rétablie :

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32

# Aller dans le répertoire de production unifié
cd /home/feustey/unified-production
```

### 2. Copier les fichiers manquants :

```bash
# Depuis votre machine locale
rsync -avz .env.unified-production config/nginx/.htpasswd config/prometheus/prometheus-unified.yml feustey@147.79.101.32:/home/feustey/unified-production/

# Renommer le fichier d'environnement
ssh feustey@147.79.101.32 "cd /home/feustey/unified-production && mv .env.unified-production .env.production"
```

### 3. Arrêter les anciens services :

```bash
# Sur le serveur Hostinger
cd /home/feustey/unified-production

# Arrêter tous les conteneurs existants
docker stop $(docker ps -aq) || true
docker rm $(docker ps -aq) || true

# Nettoyer les ressources
docker system prune -f
```

### 4. Démarrer la nouvelle configuration :

```bash
# Charger les variables d'environnement
export $(cat .env.production | grep -v '^#' | xargs)

# Démarrer tous les services
docker-compose -f docker-compose.hostinger-unified.yml up -d

# Vérifier le statut
docker-compose -f docker-compose.hostinger-unified.yml ps
```

### 5. Vérifier les logs :

```bash
# Logs généraux
docker-compose -f docker-compose.hostinger-unified.yml logs --tail=50

# Logs spécifiques
docker-compose -f docker-compose.hostinger-unified.yml logs nginx
docker-compose -f docker-compose.hostinger-unified.yml logs mcp-api
docker-compose -f docker-compose.hostinger-unified.yml logs t4g-api
```

## 🏗️ Architecture Déployée

### **Ports et Services :**
- **Port 80/443** : Nginx (reverse proxy unique)
- **Port 8000** : MCP API (interne seulement)
- **Port 8001** : Token-for-Good API (interne seulement)
- **Port 27017** : MongoDB (interne)
- **Port 6379** : Redis (interne)
- **Port 9090** : Prometheus (via http://localhost:8080/prometheus/)
- **Port 3000** : Grafana (via http://localhost:8080/grafana/)

### **Routage Nginx :**
- `https://api.dazno.de` → MCP API (port 8000)
- `https://token-for-good.com` → T4G API (port 8001)
- Monitoring accessible uniquement en local avec authentification

### **CORS Configuré :**
- Autorisé pour `https://app.dazno.de` (Vercel)
- Support des requêtes cross-origin pour les deux apps

## 🔧 Tests de Vérification

### 1. Test MCP API :
```bash
curl -I https://api.dazno.de/health
# Doit retourner HTTP/2 200
```

### 2. Test Token-for-Good :
```bash
curl -I https://token-for-good.com/health
# Doit retourner HTTP/2 200
```

### 3. Test CORS :
```bash
curl -H "Origin: https://app.dazno.de" -I https://api.dazno.de/api/v1/health
# Doit inclure les headers Access-Control-Allow-Origin
```

## 🛡️ Sécurité

### **Firewall configuré :**
```bash
# Autoriser seulement HTTP/HTTPS publics
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Bloquer l'accès direct aux ports des applications
sudo ufw deny 8000/tcp
sudo ufw deny 8001/tcp
sudo ufw deny 9090/tcp
sudo ufw deny 3000/tcp

sudo ufw reload
```

## 📊 Monitoring

- **Prometheus** : http://SERVEUR_IP:8080/prometheus (admin/admin123)
- **Grafana** : http://SERVEUR_IP:8080/grafana (admin/MCP_T4G_Admin_2025!)

## 🔄 Maintenance

### Redémarrer un service :
```bash
docker-compose -f docker-compose.hostinger-unified.yml restart [nom-service]
```

### Voir les logs en temps réel :
```bash
docker-compose -f docker-compose.hostinger-unified.yml logs -f [nom-service]
```

### Mise à jour :
```bash
docker-compose -f docker-compose.hostinger-unified.yml pull
docker-compose -f docker-compose.hostinger-unified.yml up -d
```

## ⚠️ Points d'Attention

1. **Base de données** : Les deux apps utilisent le même MongoDB avec des bases différentes
2. **Redis** : Bases Redis séparées (0 pour MCP, 1 pour T4G)
3. **SSL** : Certificats nécessaires pour les deux domaines
4. **Logs** : Centralisés dans `/home/feustey/unified-production/logs/`

---

Cette configuration élimine tous les conflits de ports et optimise les performances en utilisant un reverse proxy unique avec des services backend isolés.