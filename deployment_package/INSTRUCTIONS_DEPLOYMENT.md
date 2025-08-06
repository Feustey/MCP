# ⚡ Instructions de Déploiement Immédiat

## 🎯 Package Prêt au Déploiement

Tous les fichiers sont prêts dans le dossier `deployment_package/`. Voici comment procéder :

## 📦 Étape 1 : Transférer les Fichiers

```bash
# Depuis votre machine locale, copier tout le contenu vers le serveur
scp deployment_package/* feustey@147.79.101.32:/home/feustey/MCP-1/scripts/

# Ou utiliser rsync si disponible
rsync -av deployment_package/ feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
```

## ⚙️ Étape 2 : Déploiement sur le Serveur

```bash
# Se connecter au serveur
ssh feustey@147.79.101.32

# Aller dans le répertoire MCP
cd /home/feustey/MCP-1

# Exécuter le déploiement automatique
./scripts/DEPLOY_NOW.sh
```

## 📱 Étape 3 : Configuration Telegram

```bash
# Éditer le fichier de configuration
nano .env.production

# Ajouter ou modifier ces lignes :
TELEGRAM_BOT_TOKEN=123456789:AAAA...  # Votre token de @BotFather
TELEGRAM_CHAT_ID=123456789            # Votre ID de @userinfobot
```

## 🧪 Étape 4 : Test Immédiat

```bash
# Test complet avec envoi Telegram
python3 scripts/TEST_RAPPORTS_PRODUCTION.py

# Ou tests individuels
python3 scripts/daily_daznode_report.py      # Rapport Lightning
python3 scripts/daily_app_health_report.py   # Rapport Santé App
```

## 📊 Résultat Attendu

Vous devriez recevoir sur Telegram :

### 🏦 Rapport Daznode
```
🏦 RAPPORT QUOTIDIEN DAZNODE 🟢
📅 31/07/2025 à 22:15

📊 MÉTRIQUES PRINCIPALES
┣━ Statut: EXCELLENT
┣━ Capacité totale: 15.5 M sats
┣━ Canaux actifs: 12/15
┗━ Score centralité: 65.2%
```

### 🏥 Rapport Santé App
```
🏥 RAPPORT SANTÉ APPLICATION MCP 🟢
📅 31/07/2025 à 22:16

📊 STATUT GLOBAL
┣━ Application: EXCELLENT
┣━ API Status: HEALTHY 🟢
┗━ Endpoints: 94.3% (33/35)
```

## ⏰ Planning Automatique

Une fois déployé, vous recevrez automatiquement :
- **7h00** : 🏦 Rapport Daznode complet
- **7h05** : 🏥 Rapport Santé Application

## 🔍 Vérification

```bash
# Vérifier les tâches cron
crontab -l | grep MCP

# Surveiller les logs
tail -f logs/daznode_report.log
tail -f logs/app_health_report.log
```

## 🚨 En Cas de Problème

```bash
# Vérifier l'API
curl http://localhost:8000/health

# Tester Telegram
python3 -c "
import requests, os
token = os.environ.get('TELEGRAM_BOT_TOKEN')  
chat_id = os.environ.get('TELEGRAM_CHAT_ID')
url = f'https://api.telegram.org/bot{token}/sendMessage'
resp = requests.post(url, data={'chat_id': chat_id, 'text': 'Test MCP ✅'})
print('Envoi:', resp.status_code)
"
```

## ✅ Fichiers du Package

- `daily_daznode_report.py` - Rapport Lightning Network
- `daily_app_health_report.py` - Rapport santé système
- `DEPLOY_NOW.sh` - Script de déploiement automatique
- `TEST_RAPPORTS_PRODUCTION.py` - Test en production
- `install_daily_reports_cron.sh` - Installation cron
- Documentation complète (README, guides)

## 🎉 C'est Parti !

Copiez les fichiers et exécutez `./scripts/DEPLOY_NOW.sh` sur le serveur. 
Vous aurez vos rapports quotidiens MCP dans quelques minutes ! 🚀