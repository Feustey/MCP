# 📊 Système de Rapports Quotidiens MCP

Ce système génère automatiquement **deux rapports quotidiens complémentaires** envoyés sur Telegram pour un monitoring complet de votre infrastructure Lightning Network.

## 🎯 Vue d'Ensemble

### 📅 Planning des Rapports
- **7h00** - 🏦 **Rapport Daznode** : KPI du nœud Lightning Network
- **7h05** - 🏥 **Rapport Santé App** : KPI de l'application et infrastructure

## 📊 Rapport 1 : Daznode (7h00)

### 🎯 Objectif
Surveillance complète de votre nœud Lightning Network avec métriques business et recommandations d'optimisation.

### 📈 KPI Inclus
- **Statut général** : Évaluation globale (🟢/🟡/🔴)
- **Métriques Lightning** : Capacité, canaux actifs, score centralité
- **Liquidités** : Balance locale/distante, ratio d'équilibre
- **Revenus** : Frais de routage (jour/semaine/mois)
- **Performance** : Taux de réussite des paiements
- **Top canaux** : Analyse des 3 plus importants
- **Recommandations** : Conseils automatiques d'optimisation

### 📱 Format du Rapport
```
🏦 RAPPORT QUOTIDIEN DAZNODE 🟢
📅 30/07/2025 à 07:00

📊 MÉTRIQUES PRINCIPALES
┣━ Statut: EXCELLENT
┣━ Capacité totale: 15.5 M sats
┣━ Canaux actifs: 12/15
┗━ Score centralité: 65.2%

💰 LIQUIDITÉS
┣━ Balance locale: 8.2 M sats
┣━ Balance distante: 7.3 M sats
┗━ Ratio équilibre: 52.9%

💡 RECOMMANDATIONS
┣━ ✅ Équilibre des liquidités correct
┗━ 🌟 Excellente position dans le réseau
```

## 🏥 Rapport 2 : Santé Application (7h05)

### 🎯 Objectif
Monitoring technique de l'application MCP : santé système, performance des APIs et utilisation des endpoints.

### 🔧 KPI Inclus
- **Statut global** : Santé générale de l'application
- **Ressources système** : CPU, mémoire, disque, load average
- **Performance API** : Temps de réponse, disponibilité endpoints
- **Composants** : État Redis, MongoDB, RAG, etc.
- **Endpoints** : Test de tous les endpoints critiques (35+)
- **Erreurs** : Détection des endpoints en panne ou lents
- **Réseau** : Trafic entrant/sortant sur 24h

### 📱 Format du Rapport
```
🏥 RAPPORT SANTÉ APPLICATION MCP 🟢
📅 30/07/2025 à 07:05

📊 STATUT GLOBAL
┣━ Application: EXCELLENT
┣━ API Status: HEALTHY 🟢
┗━ Endpoints: 94.3% (33/35)

🖥️ RESSOURCES SYSTÈME
┣━ CPU: 23.4% 🟢
┣━ Mémoire: 67.8% (2.1GB libre) 🟡
┣━ Disque: 45.2% (12.3GB libre) 🟢
┗━ Load: 0.85

⚡ PERFORMANCE API
┣━ Temps moyen: 145ms
┣━ Santé endpoint: 89ms 🟢
┗━ Métriques endpoint: 234ms 🟢

🔧 COMPOSANTS
┣━ REDIS: HEALTHY 🟢
┣━ MONGODB: HEALTHY 🟢
┗━ RAG: HEALTHY 🟢
```

## 🚀 Installation

### 1. Installation Automatique (Recommandée)
```bash
# Installation complète des deux rapports
./scripts/install_daily_reports_cron.sh
```

### 2. Installation Manuelle
```bash
# Ajouter au crontab
crontab -e

# Ajouter ces lignes :
0 7 * * * cd /path/to/mcp && python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1
5 7 * * * cd /path/to/mcp && python3 scripts/daily_app_health_report.py >> logs/app_health_report.log 2>&1
```

## 🧪 Tests

### Test du Rapport Daznode
```bash
./scripts/test_daznode_report.py
```

### Test du Rapport Santé App
```bash
./scripts/test_app_health_report.py
```

## ⚙️ Configuration

### Variables d'Environnement Requises

```bash
# Variables Telegram (OBLIGATOIRES)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Variables du nœud Lightning (pour Rapport Daznode)
FEUSTEY_NODE_ID=02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b
LNBITS_URL=http://127.0.0.1:5000
LNBITS_API_KEY=your_lnbits_api_key

# Variables de l'application (pour Rapport Santé)
API_BASE_URL=http://localhost:8000

# Variables de base de données
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=your_mongo_password
REDIS_PASSWORD=your_redis_password
```

## 📁 Structure des Fichiers

```
scripts/
├── daily_daznode_report.py          # Rapport du nœud Lightning
├── daily_app_health_report.py       # Rapport de santé de l'app
├── test_daznode_report.py            # Test rapport Daznode
├── test_app_health_report.py         # Test rapport santé app
├── install_daily_reports_cron.sh     # Installation automatique
├── crontab_daznode_report.txt        # Configuration cron
└── README_RAPPORTS_QUOTIDIENS.md     # Cette documentation

logs/
├── daznode_report.log                # Logs rapport Daznode
├── app_health_report.log             # Logs rapport santé app
└── [autres logs...]
```

## 🔍 Monitoring et Logs

### Surveillance des Rapports
```bash
# Logs du rapport Daznode
tail -f logs/daznode_report.log

# Logs du rapport santé app
tail -f logs/app_health_report.log

# Vérifier les tâches cron
crontab -l | grep -A5 -B5 MCP

# Logs système des tâches cron
sudo tail -f /var/log/syslog | grep CRON
```

### Vérification des Envois
```bash
# Statistiques d'envoi Telegram
grep "envoyé avec succès" logs/*_report.log | wc -l

# Dernières exécutions
grep "Rapport.*terminé" logs/*_report.log | tail -10
```

## 🔧 Dépannage

### Problèmes Courants

**1. Rapports non reçus**
```bash
# Vérifier le cron
crontab -l | grep report

# Vérifier les logs
tail -20 logs/daznode_report.log
tail -20 logs/app_health_report.log

# Test manuel
python3 scripts/daily_daznode_report.py
python3 scripts/daily_app_health_report.py
```

**2. Erreurs de connexion API**
```bash
# Vérifier que l'API fonctionne
curl http://localhost:8000/health

# Vérifier les variables d'environnement
env | grep API_BASE_URL
env | grep TELEGRAM
```

**3. Problèmes de permissions**
```bash
# Rendre exécutable
chmod +x scripts/*.py

# Vérifier les chemins
ls -la scripts/daily_*_report.py
```

## 📈 Métriques Surveillées

### Rapport Daznode
- ✅ **35+ métriques Lightning Network**
- ✅ **Analyse de rentabilité en temps réel**
- ✅ **Recommandations d'optimisation automatiques**
- ✅ **Surveillance de la liquidité**
- ✅ **Performance des canaux individuels**

### Rapport Santé App
- ✅ **35+ endpoints API testés**
- ✅ **Métriques système (CPU, RAM, disque)**
- ✅ **État des composants (Redis, MongoDB, RAG)**
- ✅ **Performance réseau**
- ✅ **Détection d'anomalies automatique**

## 🎉 Avantages

### 📊 Monitoring Complet
- **360°** : Vue complète Lightning + Infrastructure
- **Proactif** : Détection d'anomalies avant pannes
- **Automatisé** : Aucune intervention manuelle

### 📱 Expérience Optimisée
- **Format Mobile** : Optimisé pour lecture sur smartphone
- **Émojis Intuitifs** : Status visuels immédiats
- **Actions Suggérées** : Recommandations concrètes

### 🔧 Maintenance Facilitée
- **Logs Détaillés** : Traçabilité complète
- **Tests Intégrés** : Validation avant mise en production
- **Auto-recovery** : Gestion d'erreurs robuste

## 📞 Support

En cas de problème :
1. **Logs** : Consultez `logs/*_report.log`
2. **Tests** : Exécutez les scripts de test
3. **Variables** : Vérifiez la configuration des variables d'environnement
4. **API** : Testez manuellement les endpoints

---

💡 **Résultat** : Vous recevez chaque matin une vue complète de votre infrastructure Lightning avec tous les KPI nécessaires pour une gestion proactive et optimisée ! 🚀