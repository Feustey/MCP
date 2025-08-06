# 📊 Rapport Quotidien Daznode

Ce module génère et envoie automatiquement un rapport quotidien complet des KPI de votre nœud Lightning Network via Telegram.

## 🎯 Fonctionnalités

### KPI Principaux Inclus
- **Statut général** : Évaluation globale (🟢 Excellent / 🟡 Bon / 🔴 Attention)
- **Métriques de base** : Capacité totale, nombre de canaux actifs/total, score de centralité
- **Liquidités** : Balance locale/distante, ratio d'équilibre optimisé
- **Revenus** : Frais de routage (jour/semaine/mois)
- **Performance** : Taux de réussite des paiements
- **Top canaux** : Les 3 canaux les plus importants
- **Recommandations** : Conseils automatiques d'optimisation

### Format du Rapport
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

📈 REVENUS DE ROUTAGE
┣━ Aujourd'hui: 2.5 K sats
┣━ Cette semaine: 18.3 K sats
┗━ Ce mois: 75.6 K sats

⚡ PERFORMANCE
┗━ Taux de réussite: 87.3%

🔝 TOP CANAUX
┣━ #1: 5.2 M sats (45% local)
┣━ #2: 3.8 M sats (62% local)
┣━ #3: 2.1 M sats (38% local)

💡 RECOMMANDATIONS
┣━ ✅ Équilibre des liquidités correct
┣━ 🌟 Excellente position dans le réseau
┣━ 📈 Considérer l'ouverture de nouveaux canaux

🤖 Rapport généré automatiquement à 07:00
```

## 🚀 Installation Rapide

### 1. Configuration des Variables d'Environnement

Ajoutez dans votre fichier `.env` :

```bash
# Configuration Telegram (OBLIGATOIRE)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Configuration du nœud (OPTIONNEL)
FEUSTEY_NODE_ID=02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b
LNBITS_URL=http://127.0.0.1:5000
LNBITS_API_KEY=your_lnbits_api_key
```

### 2. Test du Système

```bash
# Test interactif
./scripts/test_daznode_report.py

# Test direct (envoi immédiat)
cd /Users/feustey/DAZ/MCP/MCP-1
python3 scripts/daily_daznode_report.py
```

### 3. Installation de la Planification Automatique

```bash
# Installation automatique du cron (7h00 tous les jours)
./scripts/install_daznode_cron.sh

# Vérification de l'installation
crontab -l | grep daznode
```

## 📝 Fichiers Créés

- `daily_daznode_report.py` : Script principal de génération du rapport
- `test_daznode_report.py` : Script de test interactif
- `install_daznode_cron.sh` : Installation automatique de la planification
- `crontab_daznode_report.txt` : Configuration cron complète

## 🔧 Configuration Avancée

### Personnalisation du Planning

Modifiez `crontab_daznode_report.txt` pour changer l'heure :

```bash
# Exemple : tous les jours à 6h30
30 6 * * * cd /Users/feustey/DAZ/MCP/MCP-1 && /usr/bin/python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1
```

### Sources de Données

Le script collecte automatiquement les données depuis :
1. **LNBits API** : Informations du nœud et du portefeuille
2. **MongoDB** : Historique des canaux et métriques
3. **Fichiers collectés** : Données du réseau Lightning
4. **Données par défaut** : En cas d'indisponibilité des sources

### Gestion d'Erreurs

- **Connexion LNBits échouée** : Utilise les données MongoDB + valeurs par défaut
- **MongoDB indisponible** : Utilise les données LNBits + fichiers locaux
- **Telegram échoué** : Log l'erreur + retry automatique
- **Données manquantes** : Affiche un message d'avertissement dans le rapport

## 📊 Logs et Surveillance

### Emplacements des Logs
```bash
# Log principal du rapport
tail -f logs/daznode_report.log

# Logs système
tail -f /var/log/cron.log

# Test des logs
grep -i daznode logs/*.log
```

### Surveillance des Performances
```bash
# Vérifier les exécutions récentes
grep "Rapport quotidien" logs/daznode_report.log | tail -5

# Statistiques d'envoi Telegram
grep "envoyé avec succès" logs/daznode_report.log | wc -l
```

## 🔍 Dépannage

### Problèmes Courants

**1. Rapport non reçu**
```bash
# Vérifier le cron
crontab -l | grep daznode

# Vérifier les logs
tail -20 logs/daznode_report.log

# Test manuel
python3 scripts/daily_daznode_report.py
```

**2. Variables d'environnement**
```bash
# Vérifier les variables
env | grep TELEGRAM
env | grep LNBITS

# Recharger les variables
source .env
```

**3. Permissions**
```bash
# Rendre exécutable
chmod +x scripts/*.py scripts/*.sh

# Vérifier le chemin Python
which python3
```

## 📧 Contact et Support

- **Logs détaillés** : Activés automatiquement
- **Mode debug** : Modifier le niveau de logging dans le script
- **Telegram de test** : Utiliser `test_daznode_report.py`

## 🎉 Résultat

Vous recevrez désormais **tous les jours à 7h00** un rapport complet et formaté avec tous les KPI de votre nœud Daznode, directement sur Telegram ! 

Le rapport inclut des recommandations automatiques et s'adapte à la disponibilité de vos sources de données.