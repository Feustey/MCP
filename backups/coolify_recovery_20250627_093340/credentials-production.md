# Identifiants de Production MCP
> Dernière mise à jour: 7 mai 2025
> ⚠️ **CONFIDENTIEL** - Ne pas partager

## 🔐 Grafana Dashboard

### Accès Web
- **URL**: https://api.dazno.de/grafana ou http://localhost:3000
- **Utilisateur**: `admin`
- **Mot de passe**: `XBaxdvkgwUZ+eTCkpT/HOX8Qu+okPNSPETjbkeDIvA8=`

### Configuration interne
- **Secret Key**: `grTauu84NHKgGl5CxB9rNOiJLv6qv2lp7qX88EW2QycqTXOSIrdkG6wNrNLTv63ZP/Q2nNIERkX6g7+hoCuAOw==`

## 🗄️ Base de données MongoDB

### Accès Admin
- **Host**: mongodb:27017 (interne) ou localhost:27017 (externe)
- **Utilisateur**: `mcp_admin`
- **Mot de passe**: `keIXF+iOh14XH3KdmqRopWsZDwD59ha1uUrzRi8/giU=`
- **Database**: `mcp_prod`
- **Auth Database**: `admin`

### Chaîne de connexion
```
mongodb://mcp_admin:keIXF+iOh14XH3KdmqRopWsZDwD59ha1uUrzRi8/giU=@mongodb:27017/mcp_prod?authSource=admin
```

## 🔄 Cache Redis

### Accès
- **Host**: redis:6379 (interne) ou localhost:6379 (externe)
- **Mot de passe**: `aIrQCtPGNb5cv6nKfqFcepe9EdL82OxNc92xyEIT6M0=`

### Commande de connexion
```bash
redis-cli -h localhost -p 6379 -a "aIrQCtPGNb5cv6nKfqFcepe9EdL82OxNc92xyEIT6M0="
```

## 🔑 JWT Authentication

### Configuration API
- **Secret**: `xiFWGli2ZPbW1DVhSZ/b8G2XV9H/7yix+ypdKOTnRhYUeWe5gi4XVZoyH0LUsjNO9BckE1JCDjAFWb4P2moS9Q==`
- **Algorithme**: HS256
- **Expiration**: 24 heures

## 📊 Autres services

### Prometheus
- **URL**: http://localhost:9090
- **Auth**: Aucune (accès interne uniquement)

### API MCP
- **URL**: https://api.dazno.de ou http://localhost:8000
- **Health**: https://api.dazno.de/health
- **Docs**: https://api.dazno.de/docs

## 🚨 Actions à effectuer

1. **Copier les valeurs** depuis `config/env.production.secure` vers `.env.production`
2. **Remplir les tokens manquants**:
   - `SPARKSEER_API_KEY=votre_vraie_cle_sparkseer`
   - `TELEGRAM_BOT_TOKEN=votre_token_telegram`
   - `TELEGRAM_CHAT_ID=votre_chat_id`
3. **Sécuriser les fichiers**:
   ```bash
   chmod 600 .env.production
   chmod 600 config/env.production.secure
   chmod 600 config/credentials-production.md
   ```

## 🔄 Génération de nouveaux mots de passe

Si vous devez renouveler les mots de passe, utilisez :
```bash
# Mot de passe 32 bytes
openssl rand -base64 32

# Clé secrète 64 bytes  
openssl rand -base64 64
```

---

> ⚠️ **Sécurité**: Ces identifiants donnent un accès complet au système MCP.
> Stockez-les de manière sécurisée et ne les partagez qu'avec les personnes autorisées. 