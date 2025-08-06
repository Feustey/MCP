# 🚀 Guide de Déploiement Manuel - MCP Daznode avec Rapports

Ce guide vous permet de déployer manuellement les nouvelles fonctionnalités sur votre serveur de production.

## ✅ **Ce qui a été fait :**

1. ✅ **Synchronisation réussie** - Tous les fichiers sont sur le serveur dans `~/mcp`
2. ✅ **Scripts de rapport créés** - Rapport quotidien Daznode prêt
3. ✅ **Scripts de déploiement prêts** - Automatisation complète

## 🔧 **Étapes à suivre sur le serveur :**

### 1. Connexion au serveur
```bash
ssh feustey@147.79.101.32
# Mot de passe: Feustey@AI!
```

### 2. Aller dans le répertoire du projet
```bash
cd ~/mcp
```

### 3. Vérifier que les nouveaux fichiers sont présents
```bash
ls -la scripts/daily_daznode_report.py
ls -la scripts/remote_build_deploy.sh
ls -la scripts/README_DAZNODE_REPORT.md
```

### 4. Exécuter le déploiement automatique
```bash
./scripts/remote_build_deploy.sh
```

**OU étape par étape :**

### 4a. Construction de l'image Docker
```bash
docker build -f Dockerfile.production -t feustey/dazno:$(date +%Y%m%d-%H%M) -t feustey/dazno:latest .
```

### 4b. Arrêt des anciens services
```bash
docker-compose -f docker-compose.hostinger-production.yml down --remove-orphans
```

### 4c. Démarrage des nouveaux services
```bash
docker-compose -f docker-compose.hostinger-production.yml up -d
```

### 5. Installation du cron pour les rapports quotidiens
```bash
# Vérifier si la tâche existe déjà
crontab -l | grep daznode

# Ajouter la tâche quotidienne à 7h00
(crontab -l 2>/dev/null; echo "# Rapport quotidien Daznode - 7h00") | crontab -
(crontab -l 2>/dev/null; echo "0 7 * * * cd ~/mcp && docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1") | crontab -
```

### 6. Test de la génération du rapport
```bash
# Créer le répertoire de logs
mkdir -p logs

# Test manuel du rapport
docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod python3 scripts/daily_daznode_report.py
```

## 🧪 **Vérifications**

### Vérifier les services
```bash
# État des conteneurs
docker-compose -f docker-compose.hostinger-production.yml ps

# Test de l'API
curl http://localhost:8000/health

# Test HTTPS
curl https://api.dazno.de/health
```

### Vérifier les logs
```bash
# Logs de l'API
docker-compose -f docker-compose.hostinger-production.yml logs --tail=20 mcp-api-prod

# Logs du rapport (après le premier test)
tail -f logs/daznode_report.log
```

### Vérifier le cron
```bash
# Lister les tâches cron
crontab -l

# Vérifier les logs cron
tail -f /var/log/cron.log
```

## ⚙️ **Variables d'Environnement Requises**

Assurez-vous que ces variables sont configurées dans votre fichier `.env.production` :

```bash
# Variables Telegram (OBLIGATOIRES pour les rapports)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Variables du nœud Lightning
FEUSTEY_NODE_ID=02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b
LNBITS_URL=http://127.0.0.1:5000
LNBITS_API_KEY=your_lnbits_api_key

# Variables de base de données
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=your_mongo_password
REDIS_PASSWORD=your_redis_password
```

## 📊 **Nouvelles Fonctionnalités Ajoutées**

### 1. Rapport Quotidien Daznode
- **Planification** : Tous les jours à 7h00
- **Contenu** : KPI complets du nœud Lightning
- **Format** : Message Telegram optimisé avec émojis
- **Fichier** : `scripts/daily_daznode_report.py`

### 2. KPI Inclus dans le Rapport
- ✅ **Statut général** du nœud (🟢/🟡/🔴)
- ✅ **Métriques principales** : Capacité, canaux actifs, centralité
- ✅ **Liquidités** : Balance locale/distante, ratio d'équilibre
- ✅ **Revenus de routage** : Jour/semaine/mois
- ✅ **Performance** : Taux de réussite
- ✅ **Top canaux** : Les 3 plus importants
- ✅ **Recommandations** : Conseils automatiques d'optimisation

### 3. Scripts Utilitaires
- `test_daznode_report.py` : Test interactif du rapport
- `install_daznode_cron.sh` : Installation automatique du cron
- `README_DAZNODE_REPORT.md` : Documentation complète

## 🔍 **Dépannage**

### Si le rapport ne s'envoie pas :
```bash
# Vérifier les variables d'environnement
docker-compose -f docker-compose.hostinger-production.yml exec mcp-api-prod env | grep TELEGRAM

# Test manuel avec debug
docker-compose -f docker-compose.hostinger-production.yml exec mcp-api-prod python3 -c "
import os
print('TELEGRAM_BOT_TOKEN:', os.environ.get('TELEGRAM_BOT_TOKEN', 'NON DÉFINI'))
print('TELEGRAM_CHAT_ID:', os.environ.get('TELEGRAM_CHAT_ID', 'NON DÉFINI'))
"
```

### Si les conteneurs ne démarrent pas :
```bash
# Vérifier les logs d'erreur
docker-compose -f docker-compose.hostinger-production.yml logs

# Redémarrer en cas de problème
docker-compose -f docker-compose.hostinger-production.yml restart
```

### Si le cron ne fonctionne pas :
```bash
# Vérifier que cron est démarré
sudo systemctl status cron

# Vérifier les logs cron
sudo tail -f /var/log/syslog | grep CRON
```

## 🎉 **Résultat Attendu**

Après ce déploiement, vous devriez recevoir :

1. **Tous les jours à 7h00** : Un rapport complet sur Telegram
2. **Rapport formaté** avec tous les KPI de votre nœud Daznode
3. **Recommandations automatiques** d'optimisation
4. **Système robuste** avec gestion d'erreurs et logs

## 📞 **Support**

En cas de problème :
1. Vérifiez les logs : `tail -f logs/daznode_report.log`
2. Testez manuellement : `python3 scripts/daily_daznode_report.py`
3. Vérifiez les variables d'environnement Telegram
4. Consultez la documentation : `scripts/README_DAZNODE_REPORT.md`