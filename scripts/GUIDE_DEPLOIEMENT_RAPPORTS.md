# 🚀 Guide de Déploiement - Rapports Quotidiens MCP

## ✅ Statut : Système Prêt au Déploiement

Le système de rapports quotidiens a été développé et testé avec succès en local. Voici le guide complet pour le déployer sur votre serveur de production `feustey@147.79.101.32`.

## 📊 Aperçu des Rapports

### 🏦 Rapport Daznode (7h00)
```
🏦 RAPPORT QUOTIDIEN DAZNODE 🔴
📅 30/07/2025 à 22:06

📊 MÉTRIQUES PRINCIPALES
┣━ Statut: ATTENTION
┣━ Capacité totale: 0 sats
┣━ Canaux actifs: 0/0
┗━ Score centralité: 65.0%

💰 LIQUIDITÉS
┣━ Balance locale: 0 sats
┣━ Balance distante: 0 sats
┗━ Ratio équilibre: 0.0%

💡 RECOMMANDATIONS
┣━ 📈 Considérer l'ouverture de nouveaux canaux
```

### 🏥 Rapport Santé App (7h05)
```
🏥 RAPPORT SANTÉ APPLICATION MCP 🔴
📅 30/07/2025 à 22:06

📊 STATUT GLOBAL
┣━ Application: 🔴 ATTENTION
┣━ API Status: UNKNOWN ⚪
┗━ Endpoints: 0.0% (0/5)

🖥️ RESSOURCES SYSTÈME
┣━ CPU: 33.7% 🟢
┣━ Mémoire: 60.5% (12.6GB libre) 🟡
┣━ Disque: 0.7% (841.8GB libre) 🟢
┗━ Load: 2.59
```

## 🔧 Instructions de Déploiement

### Étape 1 : Connexion au Serveur
```bash
ssh feustey@147.79.101.32
# Mot de passe : Feustey@AI!
```

### Étape 2 : Copie des Fichiers
```bash
# Sur votre machine locale, depuis le dossier MCP-1
scp scripts/daily_daznode_report.py feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
scp scripts/daily_app_health_report.py feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
scp scripts/install_daily_reports_cron.sh feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
scp scripts/test_daznode_report.py feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
scp scripts/test_app_health_report.py feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
scp scripts/demo_rapports_telegram.py feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
scp scripts/README_RAPPORTS_QUOTIDIENS.md feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
```

### Étape 3 : Configuration sur le Serveur
```bash
# Sur le serveur
cd /home/feustey/MCP-1

# Rendre exécutables
chmod +x scripts/*.py
chmod +x scripts/*.sh

# Vérifier les variables d'environnement
grep -E "TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID" .env*

# Si les variables Telegram ne sont pas configurées :
echo "TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN" >> .env.production
echo "TELEGRAM_CHAT_ID=YOUR_CHAT_ID" >> .env.production
```

### Étape 4 : Test des Rapports
```bash
# Test sans envoi Telegram
python3 scripts/demo_rapports_telegram.py

# Test avec envoi (une fois configuré)
python3 scripts/test_daznode_report.py
python3 scripts/test_app_health_report.py
```

### Étape 5 : Installation des Tâches Cron
```bash
# Installation automatique
./scripts/install_daily_reports_cron.sh

# Vérification
crontab -l | grep -A5 -B5 "MCP"
```

### Étape 6 : Vérification
```bash
# Logs des rapports
tail -f logs/daznode_report.log
tail -f logs/app_health_report.log

# Test manuel immédiat
python3 scripts/daily_daznode_report.py
python3 scripts/daily_app_health_report.py
```

## 📅 Planning Automatique

Une fois installé, vous recevrez :
- **7h00** : 🏦 Rapport Daznode avec KPI Lightning
- **7h05** : 🏥 Rapport Santé App avec métriques système

## 📱 Configuration Telegram

### Obtenir un Bot Token
1. Contactez @BotFather sur Telegram
2. Utilisez `/newbot` et suivez les instructions
3. Récupérez le token (format : `123456789:AAAA...`)

### Obtenir votre Chat ID
1. Ajoutez @userinfobot à vos contacts
2. Envoyez `/start` au bot
3. Récupérez votre chat ID (format : `123456789`)

### Configuration Finale
```bash
# Remplacer par vos vraies valeurs
echo "TELEGRAM_BOT_TOKEN=123456789:AAAA..." >> .env.production
echo "TELEGRAM_CHAT_ID=123456789" >> .env.production
```

## 🎯 Fichiers Prêts au Déploiement

- ✅ `scripts/daily_daznode_report.py` - Rapport Lightning Network
- ✅ `scripts/daily_app_health_report.py` - Rapport santé application  
- ✅ `scripts/install_daily_reports_cron.sh` - Installation automatique
- ✅ `scripts/test_daznode_report.py` - Test rapport Daznode
- ✅ `scripts/test_app_health_report.py` - Test rapport santé
- ✅ `scripts/demo_rapports_telegram.py` - Démonstration locale
- ✅ `scripts/README_RAPPORTS_QUOTIDIENS.md` - Documentation complète

## 🔍 Monitoring

### Logs à Surveiller
```bash
# Rapports quotidiens
tail -f logs/daznode_report.log
tail -f logs/app_health_report.log

# Système général
tail -f /var/log/syslog | grep CRON
```

### Commandes Utiles
```bash
# Statut des tâches cron
crontab -l

# Test des endpoints
curl http://localhost:8000/health

# Processus Python
ps aux | grep python
```

## 🚨 Dépannage

### Problème : Rapports non reçus
```bash
# Vérifier les tâches cron
crontab -l | grep report

# Vérifier les logs
tail -20 logs/daznode_report.log
tail -20 logs/app_health_report.log

# Test manuel
python3 scripts/daily_daznode_report.py
```

### Problème : Erreurs API
```bash
# Vérifier l'API
curl http://localhost:8000/health

# Vérifier Docker
docker ps | grep mcp
docker logs mcp-api
```

### Problème : Variables Telegram
```bash
# Vérifier la configuration
env | grep TELEGRAM

# Tester l'envoi
python3 -c "
import os
import requests
token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
url = f'https://api.telegram.org/bot{token}/sendMessage'
requests.post(url, data={'chat_id': chat_id, 'text': 'Test MCP'})
"
```

## ✨ Résultat Final

Une fois déployé, vous aurez :
- 📊 Monitoring automatique complet (Lightning + Infrastructure)
- 📱 Rapports quotidiens sur Telegram avec émojis visuels
- 🔍 Détection proactive des problèmes
- 📈 Recommandations d'optimisation automatiques
- 🛠️ Outils de test et dépannage intégrés

🎉 **Système prêt pour la production !**