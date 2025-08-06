# 🚀 Commandes Manuelles - Déploiement et Test des Alertes

## ⚡ Exécution Automatique (Recommandée)

```bash
# Depuis votre machine locale
./deployment_package/EXECUTE_IMMEDIATEMENT.sh
```

Cette commande fait tout automatiquement dès que le serveur est accessible.

## 📋 Commandes Manuelles (Si Nécessaire)

### 1. Test de Connectivité
```bash
ping -c 1 147.79.101.32
ssh feustey@147.79.101.32 "echo 'Connexion OK'"
```

### 2. Transfert des Fichiers
```bash
scp deployment_package/* feustey@147.79.101.32:/home/feustey/MCP-1/scripts/
```

### 3. Connexion au Serveur
```bash
ssh feustey@147.79.101.32
# Mot de passe: Feustey@AI!
```

### 4. Déploiement (Sur le Serveur)
```bash
cd /home/feustey/MCP-1
chmod +x scripts/DEPLOY_NOW.sh
./scripts/DEPLOY_NOW.sh
```

### 5. Relance des Services Docker
```bash
# Arrêter les services
docker-compose down

# Redémarrer les services  
docker-compose up -d

# Vérifier l'état
docker ps
curl http://localhost:8000/health
```

### 6. Configuration Telegram
```bash
# Éditer le fichier de configuration
nano .env.production

# Ajouter ces lignes (remplacer par vos vraies valeurs):
TELEGRAM_BOT_TOKEN=123456789:AAAA-BBBB_CCCC...
TELEGRAM_CHAT_ID=123456789
```

### 7. Test des Alertes Telegram
```bash
# Test du rapport Daznode (Lightning Network)
python3 scripts/daily_daznode_report.py

# Test du rapport Santé Application  
python3 scripts/daily_app_health_report.py

# Ou test complet
python3 scripts/TEST_RAPPORTS_PRODUCTION.py
```

### 8. Vérification des Résultats
```bash
# Vérifier les tâches cron
crontab -l | grep MCP

# Surveiller les logs
tail -f logs/daznode_report.log
tail -f logs/app_health_report.log

# État des services
docker ps | grep mcp
```

## 📱 Contenu Attendu des Alertes

### 🏦 Rapport Daznode (7h00)
```
🏦 RAPPORT QUOTIDIEN DAZNODE 🟢
📅 31/07/2025 à 22:30

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

### 🏥 Rapport Santé App (7h05)
```
🏥 RAPPORT SANTÉ APPLICATION MCP 🟢
📅 31/07/2025 à 22:31

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
```

## 🎯 Résultat Final

Après exécution, vous aurez :
- ✅ Services MCP relancés et opérationnels
- ✅ Rapports quotidiens programmés (7h00 et 7h05)
- ✅ Alertes Telegram testées et fonctionnelles
- ✅ Monitoring automatique complet

## 🚨 En Cas de Problème

### Serveur Non Accessible
```bash
# Attendre quelques minutes et relancer
./deployment_package/EXECUTE_IMMEDIATEMENT.sh
```

### Variables Telegram Manquantes
```bash
# Sur le serveur, ajouter les variables:
echo "TELEGRAM_BOT_TOKEN=VotreBotToken" >> .env.production
echo "TELEGRAM_CHAT_ID=VotreChatID" >> .env.production
```

### Services Docker Non Démarrés
```bash
# Vérifier les logs
docker-compose logs
# Redémarrer manuellement
docker-compose restart
```

🎉 **Prêt à déployer dès que le serveur sera accessible !**