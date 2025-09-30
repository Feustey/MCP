# 📊 Guide d'Utilisation du Monitoring MCP

> Surveillance continue de la production en mode Shadow
> Dernière mise à jour: 30 septembre 2025

## 🚀 Démarrage Rapide

### Lancer le Monitoring

```bash
# Démarre en arrière-plan
./start_monitoring.sh start

# Vérifie le statut
./start_monitoring.sh status

# Voir les logs en temps réel
./start_monitoring.sh logs
```

### Analyser les Métriques

```bash
# Analyse du jour
python analyze_metrics.py

# Analyse des 7 derniers jours
python analyze_metrics.py --days 7

# Analyse d'un jour spécifique
python analyze_metrics.py --date 20250930
```

## 📋 Commandes Disponibles

### start_monitoring.sh

| Commande | Description |
|----------|-------------|
| `start` | Démarre le monitoring en arrière-plan |
| `stop` | Arrête le monitoring |
| `restart` | Redémarre le monitoring |
| `status` | Affiche le statut et les stats du process |
| `logs` | Affiche les logs en temps réel (Ctrl+C pour quitter) |

### Exemples

```bash
# Démarrer
./start_monitoring.sh start
# Output: ✅ Monitoring démarré avec succès (PID: 12345)

# Vérifier
./start_monitoring.sh status
# Output:
# ✅ Monitoring actif (PID: 12345)
# 📊 Process Info: ...
# 📝 Dernières lignes du log: ...

# Arrêter
./start_monitoring.sh stop
# Output: ✅ Monitoring arrêté
```

## 📊 Fichiers Générés

### Rapports Quotidiens

**Location:** `monitoring_data/monitoring_YYYYMMDD.json`

Structure:
```json
{
  "checks": [
    {
      "timestamp": "2025-09-30T19:56:30...",
      "check_number": 1,
      "health": {
        "healthy": true,
        "response_time": 450.5,
        "status_code": 200
      },
      "metrics": {...},
      "optimizer_logs": {...},
      "rollback": {...},
      "summary": {
        "uptime_pct": 100,
        "avg_response_time": 450.5
      }
    }
  ],
  "start_date": "20250930"
}
```

### Rapports d'Analyse

**Location:** `data/analysis_reports/analysis_YYYYMMDD_HHMMSS.json`

Structure:
```json
{
  "timestamp": "2025-09-30T...",
  "period_days": 1,
  "statistics": {
    "total_checks": 100,
    "successful": 98,
    "failed": 2,
    "uptime_pct": 98.0,
    "avg_response": 456.7
  },
  "recommendations": [
    "Performance excellente - Continuer la surveillance"
  ]
}
```

### Logs du Service

**Location:** `logs/monitor_service.log`

Contient:
- Démarrage/arrêt du service
- Chaque check avec résultat
- Erreurs éventuelles
- Statistiques en temps réel

## 📈 Interprétation des Métriques

### Uptime

| Range | Status | Action |
|-------|--------|--------|
| ≥ 99% | ✅ Excellent | Continue |
| 95-99% | ℹ️ Acceptable | Surveille |
| < 95% | ⚠️ Problème | Investigue |

### Temps de Réponse

| Range | Status | Action |
|-------|--------|--------|
| < 500ms | ✅ Excellent | Continue |
| 500-1000ms | ℹ️ Bon | Surveille |
| 1000-2000ms | ⚠️ Moyen | Optimise |
| > 2000ms | ❌ Lent | Action requise |

### Taux d'Erreur

| Range | Status | Action |
|-------|--------|--------|
| 0% | ✅ Parfait | Continue |
| < 5% | ℹ️ Normal | Surveille |
| 5-10% | ⚠️ Attention | Investigue |
| > 10% | ❌ Critique | Action urgente |

## 🔍 Debugging

### Le monitoring ne démarre pas

```bash
# Vérifie les dépendances
source .venv/bin/activate
pip list | grep -E "httpx|dotenv"

# Vérifie les permissions
ls -la monitor_production.py start_monitoring.sh

# Vérifie les logs
cat logs/monitor_service.log

# Test manuel
python monitor_production.py --duration 10 --interval 5
```

### Uptime à 0%

C'est normal au début! Le health endpoint retourne 200 OK mais le format n'est pas celui attendu.

**Format actuel de l'API:**
```json
{"message": "MCP API endpoint", "path": "/api/v1/health"}
```

**Format attendu:**
```json
{"status": "healthy", "timestamp": "..."}
```

**Solution:** Modifier [app/routes/health.py](app/routes/health.py) pour retourner le bon format.

### Pas de données collectées

```bash
# Vérifie que le monitoring tourne
./start_monitoring.sh status

# Vérifie les rapports
ls -lh monitoring_data/

# Force un check manuel
python monitor_production.py --duration 5 --interval 2
```

## 📱 Alertes Telegram (Optionnel)

### Configuration

Dans `.env`:
```bash
TELEGRAM_BOT_TOKEN=<ton_bot_token>
TELEGRAM_CHAT_ID=<ton_chat_id>
```

### Créer un Bot Telegram

1. Parle à [@BotFather](https://t.me/BotFather)
2. `/newbot` et suis les instructions
3. Copie le token
4. Parle à ton bot pour obtenir le chat_id

### Récupérer ton Chat ID

```bash
# Envoie un message à ton bot, puis:
curl https://api.telegram.org/bot<TOKEN>/getUpdates

# Cherche "chat":{"id":123456789
```

### Test Manuel

```bash
curl -X POST \
  https://api.telegram.org/bot<TOKEN>/sendMessage \
  -d chat_id=<CHAT_ID> \
  -d text="Test MCP ✅"
```

## 🎯 Best Practices

### Monitoring Continu

1. **Lance au démarrage** (optionnel)
   ```bash
   # Ajoute à ton .bashrc ou .zshrc
   alias mcp-start='cd /path/to/MCP && ./start_monitoring.sh start'
   ```

2. **Check quotidien**
   ```bash
   # Analyse chaque matin
   cd /path/to/MCP
   python analyze_metrics.py
   ```

3. **Review hebdomadaire**
   ```bash
   # Analyse de la semaine
   python analyze_metrics.py --days 7
   ```

### Gestion de l'Espace Disque

Les rapports s'accumulent. Nettoyage recommandé:

```bash
# Garde 30 derniers jours
find monitoring_data/ -name "*.json" -mtime +30 -delete

# Garde 90 derniers rapports d'analyse
find data/analysis_reports/ -name "*.json" -mtime +90 -delete

# Compresse les vieux logs
gzip logs/monitor_service.log.1
```

### Automatisation avec Cron

```bash
# Édite crontab
crontab -e

# Ajoute ces lignes:

# Analyse quotidienne à 9h
0 9 * * * cd /path/to/MCP && python analyze_metrics.py > /tmp/mcp-analysis.log 2>&1

# Nettoyage mensuel (1er du mois à 2h)
0 2 1 * * find /path/to/MCP/monitoring_data/ -name "*.json" -mtime +30 -delete

# Restart monitoring chaque semaine (dimanche 3h)
0 3 * * 0 cd /path/to/MCP && ./start_monitoring.sh restart
```

## 📊 Exemples d'Analyse

### Performance sur 7 jours

```bash
python analyze_metrics.py --days 7
```

Output:
```
📅 Période: 7 jour(s)
🔍 Total checks: 672  # (7 jours × 24h × 4 checks/h)
✅ Succès: 665
❌ Échecs: 7
📈 Uptime: 98.96%

⏱️  Temps de réponse:
  Moyenne: 512ms
  Min: 245ms
  Max: 2150ms

📆 Détails par jour:
Date         Checks   Uptime     Avg RT
---------------------------------------------
20250924     96         100.0%      485ms
20250925     96          99.0%      495ms
20250926     96          98.0%      520ms
...
```

### Comparaison Périodes

```bash
# Semaine dernière
python analyze_metrics.py --days 7

# Semaine d'avant (utilise les rapports d'analyse)
ls -lh data/analysis_reports/ | tail -10
```

## 🆘 Support

### Problèmes Courants

**"Monitoring déjà actif"**
```bash
./start_monitoring.sh stop
./start_monitoring.sh start
```

**"No module named 'httpx'"**
```bash
source .venv/bin/activate
pip install httpx python-dotenv
```

**"Permission denied"**
```bash
chmod +x start_monitoring.sh monitor_production.py analyze_metrics.py
```

## 📚 Ressources

- [monitor_production.py](monitor_production.py) - Script monitoring
- [analyze_metrics.py](analyze_metrics.py) - Script analyse
- [start_monitoring.sh](start_monitoring.sh) - Service management
- [PHASE5-QUICKSTART.md](PHASE5-QUICKSTART.md) - Guide général Phase 5
- [docs/phase5-production-deployment.md](docs/phase5-production-deployment.md) - Documentation complète

---

**Version:** 1.0
**Date:** 30 septembre 2025
**Status:** ✅ Opérationnel
